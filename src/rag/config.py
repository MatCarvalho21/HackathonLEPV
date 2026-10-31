import os
from pathlib import Path

# Raiz do projeto
ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# Diretórios padrão
PDFS_DIR = ROOT_DIR / "pdfs"
CHROMA_PERSIST_DIR = ROOT_DIR / "chroma_db"

# Nome da coleção no ChromaDB
COLLECTION_NAME = "desenvolvimento_infantil_kb"

# Modelo de Embeddings Open-Source Multilíngue:
# 1. "BAAI/bge-m3": Estado da arte para RAG multilíngue (100+ línguas, 1024 dimensões, contexto de até 8192 tokens).
#    Excelente performance cruzada (perguntas em português recuperando documentos em inglês/português).
# 2. "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2": Alternativa ultra-leve (~470MB, 384 dim),
#    ideal se for rodar estritamente em CPU modesta com resposta rápida.
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-m3")

# Parâmetros de Divisão de Texto (Chunking)
CHUNK_SIZE = 800         # Caracteres por bloco
CHUNK_OVERLAP = 150      # Caracteres de sobreposição entre blocos consecutivos

# Parâmetros de Processamento
BATCH_SIZE = 64          # Quantidade de chunks por lote ao enviar para o ChromaDB
