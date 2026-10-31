import argparse
import json
import logging
import os
import time
from pathlib import Path
from typing import List, Optional, Set

import chromadb
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from src.rag.chunker import parse_and_chunk_markdown, DocumentChunk
from src.rag.config import (
    MARKDOWN_DIR,
    PDFS_DIR,
    CHROMA_PERSIST_DIR,
    COLLECTION_NAME,
    EMBEDDING_MODEL_NAME,
    DEVICE,
    BATCH_SIZE,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def load_markdown_documents(markdown_dir: Path = MARKDOWN_DIR, doc_filter: Optional[str] = None):
    """Carrega todos os arquivos Markdown gerados pelo conversor."""
    if not markdown_dir.exists():
        return []

    md_files = sorted(list(markdown_dir.glob("*.md")))
    if doc_filter:
        md_files = [f for f in md_files if doc_filter.lower() in f.name.lower()]

    documents = []
    for md_file in md_files:
        meta_file = md_file.with_suffix(".meta.json")
        source_name = md_file.stem + ".pdf"
        total_pages = 1

        if meta_file.exists():
            try:
                meta_data = json.loads(meta_file.read_text(encoding="utf-8"))
                source_name = meta_data.get("source", source_name)
                total_pages = meta_data.get("total_pages", 1)
            except Exception:
                pass

        content = md_file.read_text(encoding="utf-8")
        documents.append({
            "source": source_name,
            "md_path": md_file,
            "content": content,
            "total_pages": total_pages
        })

    return documents


def get_existing_chunk_ids(collection) -> Set[str]:
    """Retorna o conjunto de IDs de chunks já indexados no ChromaDB."""
    try:
        existing_data = collection.get(include=[])
        if existing_data and "ids" in existing_data:
            return set(existing_data["ids"])
    except Exception as e:
        logger.warning(f"Aviso ao consultar IDs existentes no ChromaDB: {e}")
    return set()


def run_indexing(
    force_reindex: bool = False,
    doc_filter: Optional[str] = None,
    batch_size: int = BATCH_SIZE,
    device: str = DEVICE
):
    """Executa a indexação vetorial de forma incremental com aceleração por GPU."""
    start_time = time.time()

    logger.info("=" * 70)
    logger.info("INDEXAÇÃO VETORIAL (INCREMENTAL & GPU)")
    logger.info(f"Dispositivo selecionado: {device.upper()}")
    logger.info(f"Modelo de Embeddings: {EMBEDDING_MODEL_NAME}")
    logger.info(f"Tamanho do lote (Batch Size): {batch_size}")
    logger.info(f"Diretório do ChromaDB: {CHROMA_PERSIST_DIR}")
    logger.info("=" * 70)

    # 1. Carrega os Markdowns estruturados
    documents = load_markdown_documents(MARKDOWN_DIR, doc_filter=doc_filter)

    if not documents:
        logger.warning(
            f"Nenhum arquivo .md encontrado em '{MARKDOWN_DIR}'!\n"
            "Dica: Execute primeiro o conversor de PDFs:\n"
            "  python3 -m src.rag.convert_to_markdown\n"
        )
        return

    logger.info(f"Total de documentos Markdown encontrados: {len(documents)}")

    # 2. Divide os documentos em chunks hierárquicos
    all_chunks: List[DocumentChunk] = []
    for doc in tqdm(documents, desc="Fatiando documentos em blocos semânticos", unit="doc"):
        doc_chunks = parse_and_chunk_markdown(
            markdown_content=doc["content"],
            source_filename=doc["source"],
            default_page=1
        )
        all_chunks.extend(doc_chunks)

    total_chunks_detected = len(all_chunks)
    logger.info(f"Total de chunks estruturados identificados: {total_chunks_detected}")
    if not all_chunks:
        logger.warning("Nenhum chunk foi gerado.")
        return

    # 3. Inicializa o cliente do ChromaDB
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_PERSIST_DIR))

    if force_reindex:
        try:
            logger.info(f"Recriando coleção '{COLLECTION_NAME}' (--reindex ativado)...")
            chroma_client.delete_collection(name=COLLECTION_NAME)
        except Exception:
            pass

    collection = chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

    # 4. Modo Incremental: Identifica chunks que já foram gravados anteriormente
    existing_ids = set() if force_reindex else get_existing_chunk_ids(collection)
    chunks_to_process = [c for c in all_chunks if c.chunk_id not in existing_ids]

    logger.info(f"Chunks já existentes no ChromaDB: {len(existing_ids)}")
    logger.info(f"Novos chunks a serem processados: {len(chunks_to_process)}")

    if not chunks_to_process:
        logger.info("🎉 Todos os chunks já estão perfeitamente indexados! Nada a fazer.")
        return

    # 5. Carrega o modelo de embeddings na GPU
    logger.info(f"Carregando modelo '{EMBEDDING_MODEL_NAME}' no dispositivo '{device}'...")
    embedder = SentenceTransformer(EMBEDDING_MODEL_NAME, device=device)

    # Limita o comprimento máximo de sequência por precaução contra textos extremos
    if hasattr(embedder, "max_seq_length") and embedder.max_seq_length > 4096:
        embedder.max_seq_length = 4096

    # 6. Processa apenas os chunks pendentes em lotes seguros
    total_to_process = len(chunks_to_process)
    logger.info(f"Gravando {total_to_process} chunks restantes no ChromaDB em lotes de {batch_size}...")

    is_cuda = device.startswith("cuda")
    if is_cuda:
        try:
            import torch
            torch.cuda.empty_cache()
        except ImportError:
            pass

    with tqdm(range(0, total_to_process, batch_size), desc="Gravando no ChromaDB", unit="lote") as pbar:
        for i in pbar:
            batch = chunks_to_process[i : i + batch_size]
            batch_ids = [c.chunk_id for c in batch]
            batch_texts = [c.text for c in batch]
            batch_metadatas = [c.metadata for c in batch]

            # Vetorização densa normalizada
            embeddings = embedder.encode(
                batch_texts,
                batch_size=len(batch),
                normalize_embeddings=True,
                show_progress_bar=False
            ).tolist()

            collection.upsert(
                ids=batch_ids,
                documents=batch_texts,
                metadatas=batch_metadatas,
                embeddings=embeddings
            )

            # Limpa cache da GPU periodicamente para evitar fragmentação de memória
            if is_cuda and (i // batch_size) % 5 == 0:
                try:
                    import torch
                    torch.cuda.empty_cache()
                except ImportError:
                    pass

    elapsed = time.time() - start_time
    logger.info("=" * 70)
    logger.info(f"INDEXAÇÃO CONCLUÍDA EM {elapsed:.2f}s")
    logger.info(f"Total acumulado na coleção '{COLLECTION_NAME}': {collection.count()} chunks")
    logger.info("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Indexador Incremental para ChromaDB (com suporte a GPU)")
    parser.add_argument("--reindex", action="store_true", help="Força a recriação do índice do zero (apaga dados existentes)")
    parser.add_argument("--filter", type=str, default=None, help="Filtra documentos por termo no nome")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE, help=f"Tamanho do lote de embeddings (padrão: {BATCH_SIZE})")
    parser.add_argument("--device", type=str, default=DEVICE, help=f"Dispositivo de execução (padrão: {DEVICE})")
    args = parser.parse_args()

    run_indexing(
        force_reindex=args.reindex,
        doc_filter=args.filter,
        batch_size=args.batch_size,
        device=args.device
    )
