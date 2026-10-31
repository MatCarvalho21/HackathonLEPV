import json
from typing import List, Dict, Any, Optional

import chromadb
from sentence_transformers import SentenceTransformer

from src.rag.config import (
    CHROMA_PERSIST_DIR,
    COLLECTION_NAME,
    EMBEDDING_MODEL_NAME,
)


class KnowledgeRetriever:
    """
    Componente de recuperação (Retriever) para agentes de IA consultarem
    a base de conhecimento vetorial indexada no ChromaDB.
    """

    def __init__(
        self,
        persist_dir: str = str(CHROMA_PERSIST_DIR),
        collection_name: str = COLLECTION_NAME,
        model_name: str = EMBEDDING_MODEL_NAME,
    ):
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.model_name = model_name

        # Inicializa conexão com o ChromaDB
        self.chroma_client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection = self.chroma_client.get_collection(name=self.collection_name)

        # Carrega o modelo de embeddings multilíngue
        self.embedder = SentenceTransformer(self.model_name)

    def search(
        self,
        query: str,
        top_k: int = 4,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Executa busca por similaridade semântica para a consulta dada.
        
        Args:
            query: Pergunta ou termo de pesquisa em português ou inglês.
            top_k: Quantidade de trechos mais relevantes a retornar.
            where: Filtros de metadados opcionais (ex: {"source": "milestonesPT.pdf"}).
            
        Returns:
            Lista de resultados contendo texto, metadados, id e score de similaridade.
        """
        if not query.strip():
            return []

        # Gera o vetor da consulta
        query_embedding = self.embedder.encode([query], normalize_embeddings=True).tolist()

        # Consulta a coleção no ChromaDB
        query_params = {
            "query_embeddings": query_embedding,
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            query_params["where"] = where

        results = self.collection.query(**query_params)

        formatted_results = []
        if results and results.get("documents"):
            docs = results["documents"][0]
            metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
            distances = results["distances"][0] if results.get("distances") else [0.0] * len(docs)
            ids = results["ids"][0] if results.get("ids") else [""] * len(docs)

            for doc_text, meta, dist, chunk_id in zip(docs, metas, distances, ids):
                # Como usamos distância cosseno normalizada: similaridade = 1 - distância
                similarity_score = max(0.0, 1.0 - dist)
                formatted_results.append({
                    "id": chunk_id,
                    "text": doc_text,
                    "source": meta.get("source", "desconhecido"),
                    "page": meta.get("page", 1),
                    "score": round(similarity_score, 4),
                    "metadata": meta
                })

        return formatted_results

    def get_formatted_context(self, query: str, top_k: int = 4, min_score: float = 0.35) -> str:
        """
        Retorna o contexto formatado em Markdown pronto para ser inserido diretamente
        no prompt do LLM ou no scratchpad do agente com referências e fontes.
        """
        results = self.search(query=query, top_k=top_k)
        
        # Filtra trechos com relevância aceitável
        relevant = [r for r in results if r["score"] >= min_score]
        if not relevant:
            relevant = results[:2]  # Fallback: traz os 2 melhores se o score for baixo

        if not relevant:
            return "Nenhuma informação relevante encontrada na base de conhecimento."

        context_blocks = []
        for i, item in enumerate(relevant, start=1):
            source = item["source"]
            page = item["page"]
            score = item["score"]
            text = item["text"]
            
            block = (
                f"### [Trecho {i}] Documento: `{source}` (Página {page}) | Relevância: {score:.2f}\n"
                f"{text}\n"
            )
            context_blocks.append(block)

        return "\n---\n".join(context_blocks)


# ---------------------------------------------------------------------------
# Instância Singleton para reutilização rápida no loop do agente
# ---------------------------------------------------------------------------
_retriever_instance: Optional[KnowledgeRetriever] = None


def get_retriever() -> KnowledgeRetriever:
    """Retorna uma instância única em memória do retriever (evita recarregar modelo)."""
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = KnowledgeRetriever()
    return _retriever_instance


def consultar_base_conhecimento(termo_busca: str, top_k: int = 4) -> str:
    """
    Função pronta para ser chamada diretamente pelo agente (ou plugada como Tool).
    
    Exemplo:
        resposta = consultar_base_conhecimento("Marcos do desenvolvimento de linguagem para 3 anos")
    """
    retriever = get_retriever()
    return retriever.get_formatted_context(query=termo_busca, top_k=top_k)


# ---------------------------------------------------------------------------
# Schema de Tool (Function Calling) no formato compatível com OpenAI/Gemini/LangChain
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
