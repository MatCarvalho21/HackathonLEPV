import json
import logging
from typing import List, Dict, Any, Optional

import chromadb
from sentence_transformers import SentenceTransformer

from src.rag.config import (
    CHROMA_PERSIST_DIR,
    COLLECTION_NAME,
    EMBEDDING_MODEL_NAME,
    RERANKER_MODEL_NAME,
    DEVICE,
    TOP_K_INITIAL,
    TOP_K_FINAL,
    RERANKER_MIN_SCORE,
)

logger = logging.getLogger(__name__)


class KnowledgeRetriever:
    """
    Componente de recuperação (Two-Stage Retriever):
    1. Primeira etapa (Bi-Encoder): Busca densa rápida no ChromaDB (Top 20).
    2. Segunda etapa (Cross-Encoder): Reranking profundo com BAAI/bge-reranker-v2-m3 (Top 4).
    """

    def __init__(
        self,
        persist_dir: str = str(CHROMA_PERSIST_DIR),
        collection_name: str = COLLECTION_NAME,
        embed_model_name: str = EMBEDDING_MODEL_NAME,
        rerank_model_name: str = RERANKER_MODEL_NAME,
        device: str = DEVICE,
        enable_reranker: bool = True
    ):
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.embed_model_name = embed_model_name
        self.rerank_model_name = rerank_model_name
        self.device = device
        self.enable_reranker = enable_reranker

        # Conexão com ChromaDB
        self.chroma_client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection = self.chroma_client.get_collection(name=self.collection_name)

        # 1. Carrega modelo denso de embeddings (Bi-Encoder)
        logger.info(f"Carregando Bi-Encoder '{self.embed_model_name}' em {self.device}...")
        self.embedder = SentenceTransformer(self.embed_model_name, device=self.device)

        # 2. Carrega modelo Cross-Encoder (Reranker)
        self.reranker = None
        if self.enable_reranker:
            try:
                from sentence_transformers import CrossEncoder
                logger.info(f"Carregando Cross-Encoder Reranker '{self.rerank_model_name}' em {self.device}...")
                self.reranker = CrossEncoder(self.rerank_model_name, device=self.device)
            except Exception as e:
                logger.warning(f"Reranker não pôde ser carregado ({e}). Continuando apenas com Bi-Encoder.")

    def search(
        self,
        query: str,
        top_k: int = TOP_K_FINAL,
        initial_candidates: int = TOP_K_INITIAL,
        where: Optional[Dict[str, Any]] = None,
        use_reranker: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Executa a busca semântica em duas etapas.
        """
        if not query.strip():
            return []

        # Etapa 1: Busca densa no ChromaDB
        query_embedding = self.embedder.encode([query], normalize_embeddings=True).tolist()
        n_fetch = max(initial_candidates, top_k * 3)

        query_params = {
            "query_embeddings": query_embedding,
            "n_results": n_fetch,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            query_params["where"] = where

        try:
            results = self.collection.query(**query_params)
        except Exception as e:
            logger.error(f"Erro ao consultar ChromaDB: {e}")
            return []

        candidates = []
        if results and results.get("documents"):
            docs = results["documents"][0]
            metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
            distances = results["distances"][0] if results.get("distances") else [0.0] * len(docs)
            ids = results["ids"][0] if results.get("ids") else [""] * len(docs)

            for doc_text, meta, dist, chunk_id in zip(docs, metas, distances, ids):
                # Distância cosseno normalizada: similaridade = 1 - dist
                sim_score = max(0.0, 1.0 - dist)
                candidates.append({
                    "id": chunk_id,
                    "text": doc_text,
                    "source": meta.get("source", "desconhecido"),
                    "section": meta.get("section", "Geral"),
                    "page": meta.get("page", 1),
                    "is_table": meta.get("is_table", False),
                    "score": round(sim_score, 4),
                    "metadata": meta
                })

        if not candidates:
            return []

        # Etapa 2: Reranking com Cross-Encoder
        if use_reranker and self.reranker is not None and len(candidates) > 1:
            pairs = [[query, c["text"]] for c in candidates]
            rerank_scores = self.reranker.predict(pairs)

            for c, r_score in zip(candidates, rerank_scores):
                c["rerank_score"] = round(float(r_score), 4)

            # Ordena decrescente pela pontuação do Reranker
            candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
        else:
            for c in candidates:
                c["rerank_score"] = c["score"]
            candidates.sort(key=lambda x: x["score"], reverse=True)

        return candidates[:top_k]

    def get_formatted_context(
        self,
        query: str,
        top_k: int = TOP_K_FINAL,
        min_score: float = RERANKER_MIN_SCORE
    ) -> str:
        """
        Retorna contexto pronto e formatado em Markdown com rastreabilidade de
        documento, seção, página e evidência científica para inserção no LLM.
        """
        results = self.search(query=query, top_k=top_k)
        if not results:
            return "Nenhuma informação relevante encontrada na base de conhecimento."

        context_blocks = []
        for i, item in enumerate(results, start=1):
            source = item["source"]
            page = item["page"]
            section = item["section"]
            score = item.get("rerank_score", item["score"])
            text = item["text"]
            tipo = " [Tabela]" if item.get("is_table") else ""

            block = (
                f"### [Evidência {i}{tipo}] `{source}` (Página {page}) | Seção: *{section}* | Relevância: {score:.2f}\n"
                f"{text}\n"
            )
            context_blocks.append(block)

        return "\n---\n".join(context_blocks)


# ---------------------------------------------------------------------------
# Instância Singleton para reutilização sem recarregar pesos na GPU
# ---------------------------------------------------------------------------
_retriever_instance: Optional[KnowledgeRetriever] = None


def get_retriever() -> KnowledgeRetriever:
    """Retorna uma instância única em memória do retriever."""
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = KnowledgeRetriever()
    return _retriever_instance


def consultar_base_conhecimento(termo_busca: str, top_k: int = TOP_K_FINAL) -> str:
    """Função utilitária para os agentes de IA consultarem a base."""
    retriever = get_retriever()
    return retriever.get_formatted_context(query=termo_busca, top_k=top_k)


# ---------------------------------------------------------------------------
# Schema de Tool (Function Calling) compatível com OpenAI/Gemini/Claude
# ---------------------------------------------------------------------------
AGENT_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "consultar_base_conhecimento",
        "description": (
            "Consulta a base de conhecimento técnico e científico de desenvolvimento infantil "
            "(marcos do desenvolvimento, Caderneta da Criança, diretrizes da OMS, relatórios da EEF, "
            "e estratégias para crianças com necessidades especiais). "
            "Use sempre que precisar de fundamentação teórica, intervenções pedagógicas ou marcos etários."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "termo_busca": {
                    "type": "string",
                    "description": "A dúvida, termo ou tópico de pesquisa (ex: 'mordidas e comportamentos agressivos em sala de aula', 'marcos de 2 a 3 anos fala', 'estratégias PEI e apoio sem laudo')."
                },
                "top_k": {
                    "type": "integer",
                    "description": "Quantidade máxima de trechos a retornar (padrão: 4).",
                    "default": 4
                }
            },
            "required": ["termo_busca"]
        }
    }
}
