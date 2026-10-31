import argparse
import sys
import time
from pathlib import Path
from typing import List, Set

import chromadb
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from src.rag.config import (
    PDFS_DIR,
    CHROMA_PERSIST_DIR,
    COLLECTION_NAME,
    EMBEDDING_MODEL_NAME,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    BATCH_SIZE,
)
from src.rag.pdf_loader import extract_pages_from_pdf
from src.rag.chunker import chunk_pages, DocumentChunk


def get_indexed_sources(collection) -> Set[str]:
    """Obtém os nomes de arquivos PDF que já possuem registros na coleção."""
    try:
        existing = collection.get(include=["metadatas"])
        if existing and existing.get("metadatas"):
            return {m.get("source") for m in existing["metadatas"] if m and "source" in m}
    except Exception as e:
        print(f"[Aviso] Não foi possível verificar documentos existentes: {e}")
    return set()


def run_indexing(force_reindex: bool = False, pdf_filter: str = None):
    """
    Executa a pipeline completa de indexação:
    1. Varredura dos PDFs
    2. Extração de páginas e limpeza
    3. Divisão em chunks estruturados
    4. Geração de embeddings com SentenceTransformers
    5. Armazenamento persistente no ChromaDB
    """
    start_time = time.time()
    print("=" * 70)
    print(" PIPELINE DE INDEXAÇÃO VETORIAL (RAG) - DESENVOLVIMENTO INFANTIL")
    print("=" * 70)
    print(f"Diretório de PDFs:      {PDFS_DIR}")
    print(f"Banco ChromaDB:         {CHROMA_PERSIST_DIR}")
    print(f"Coleção:                {COLLECTION_NAME}")
    print(f"Modelo de Embeddings:   {EMBEDDING_MODEL_NAME}")
    print(f"Chunk Size / Overlap:   {CHUNK_SIZE} / {CHUNK_OVERLAP} caracteres")
    print("-" * 70)

    if not PDFS_DIR.exists():
        print(f"[Erro] O diretório '{PDFS_DIR}' não foi encontrado.")
        sys.exit(1)

    pdf_files = sorted(list(PDFS_DIR.glob("*.pdf")))
    if not pdf_files:
        print(f"[Aviso] Nenhum arquivo .pdf encontrado em '{PDFS_DIR}'.")
        return

    if pdf_filter:
        pdf_files = [p for p in pdf_files if pdf_filter.lower() in p.name.lower()]
        print(f"Filtro aplicado: {len(pdf_files)} arquivos correspondentes.")

    print(f"Total de arquivos PDF localizados: {len(pdf_files)}")

    # 1. Inicializa o cliente persistente do ChromaDB
    CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_PERSIST_DIR))

    if force_reindex:
        try:
            chroma_client.delete_collection(name=COLLECTION_NAME)
            print(f"[Reset] Coleção '{COLLECTION_NAME}' apagada para reindexação total.")
        except Exception:
            pass

    collection = chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

    already_indexed = set() if force_reindex else get_indexed_sources(collection)
    if already_indexed:
        print(f"Documentos já indexados anteriormente no banco: {len(already_indexed)}")

    # 2. Carrega o modelo de embeddings multilíngue
    print(f"\nCarregando modelo de embeddings '{EMBEDDING_MODEL_NAME}'...")
    embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)
    print("Modelo carregado com sucesso.")

    # 3. Processa cada PDF
    all_chunks: List[DocumentChunk] = []
    processed_files_count = 0
    skipped_count = 0

    print("\n[Etapa 1/2] Extraindo e fatiando documentos...")
    for pdf_path in tqdm(pdf_files, desc="Processando PDFs"):
        if not force_reindex and pdf_path.name in already_indexed:
            skipped_count += 1
            continue

        pages = extract_pages_from_pdf(pdf_path)
        if not pages:
            print(f"[Aviso] Documento sem texto extraído: '{pdf_path.name}'")
            continue

        chunks = chunk_pages(pages, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
        all_chunks.extend(chunks)
        processed_files_count += 1

    print(f"\nDocumentos processados: {processed_files_count}")
    if skipped_count > 0:
        print(f"Documentos pulados (já indexados): {skipped_count}")
    print(f"Total de novos chunks gerados: {len(all_chunks)}")

    if not all_chunks:
        print("\nNenhum novo chunk para indexar. O banco vetorial já está atualizado!")
        print(f"Total atual de itens na coleção: {collection.count()}")
        return

    # 4. Geração de Embeddings e Upsert em lotes (Batch)
    print(f"\n[Etapa 2/2] Vetorizando e salvando no ChromaDB (Lotes de {BATCH_SIZE})...")

    total_chunks = len(all_chunks)
    for i in tqdm(range(0, total_chunks, BATCH_SIZE), desc="Indexando no ChromaDB"):
        batch = all_chunks[i : i + BATCH_SIZE]

        batch_ids = [c.chunk_id for c in batch]
        batch_texts = [c.text for c in batch]
        batch_metadatas = [c.metadata for c in batch]

        # Gera os vetores densos normalizados (para distância cosseno)
        batch_embeddings = embedder.encode(
            batch_texts,
            normalize_embeddings=True,
            show_progress_bar=False
        ).tolist()

        # Upsert garante que se o id já existir ele atualiza, senão insere
        collection.upsert(
            ids=batch_ids,
            documents=batch_texts,
            metadatas=batch_metadatas,
            embeddings=batch_embeddings
        )

    duration = time.time() - start_time
    print("\n" + "=" * 70)
    print(f" INDEXAÇÃO CONCLUÍDA COM SUCESSO EM {duration:.2f}s")
    print("=" * 70)
    print(f"Total de registros na coleção '{COLLECTION_NAME}': {collection.count()}")
    print("O banco vetorial está pronto para ser consultado pelos agentes!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Indexador de PDFs para RAG no ChromaDB")
    parser.add_argument(
        "--reindex",
        action="store_true",
        help="Força a recriação completa da coleção apagando os índices antigos"
    )
    parser.add_argument(
        "--filter",
        type=str,
        default=None,
        help="Filtra PDFs específicos pelo nome para indexar"
    )
    args = parser.parse_args()

    run_indexing(force_reindex=args.reindex, pdf_filter=args.filter)
