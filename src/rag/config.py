import os
from pathlib import Path

# Configuração de alocação de memória do PyTorch para evitar fragmentação
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

# Raiz do projeto
ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# Diretórios principais
PDFS_DIR = ROOT_DIR / "pdfs"
DATA_DIR = ROOT_DIR / "data"
MARKDOWN_DIR = DATA_DIR / "markdown_docs"
CHROMA_PERSIST_DIR = ROOT_DIR / "chroma_db"

# Garante a existência dos diretórios de dados
DATA_DIR.mkdir(parents=True, exist_ok=True)
MARKDOWN_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)

# Nome da coleção no ChromaDB
COLLECTION_NAME = "desenvolvimento_infantil_kb"

# Detecção e Seleção Inteligente de GPU (Escolhe a GPU com mais memória livre)
def get_default_device() -> str:
    forced = os.getenv("RAG_DEVICE")
    if forced:
        return forced
    try:
        import torch
        if torch.cuda.is_available():
            count = torch.cuda.device_count()
            if count > 1:
                # Escolhe automaticamente a GPU com maior VRAM livre (ex: GPU 1)
                best_device = "cuda:1"
                max_free = 0
                for i in range(count):
                    try:
                        free, _ = torch.cuda.mem_get_info(i)
                        if free > max_free:
                            max_free = free
                            best_device = f"cuda:{i}"
                    except Exception:
                        pass
                return best_device
            return "cuda:0"
    except Exception:
        pass
    return "cpu"

DEVICE = get_default_device()

# Modelos Open-Source de Alta Fidelidade
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-m3")
RERANKER_MODEL_NAME = os.getenv("RERANKER_MODEL_NAME", "BAAI/bge-reranker-v2-m3")

# Configurações de Chunking Estruturado
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1200"))       # Caracteres por bloco de prosa
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))   # Sobreposição de contexto
PRESERVE_TABLES_WHOLE = True                             # Nunca quebra tabelas no meio

# Configurações de Recuperação (Two-Stage Retrieval)
TOP_K_INITIAL = int(os.getenv("TOP_K_INITIAL", "20"))    # Candidatos iniciais do ChromaDB
TOP_K_FINAL = int(os.getenv("TOP_K_FINAL", "4"))         # Trechos finais após Reranker
RERANKER_MIN_SCORE = float(os.getenv("RERANKER_MIN_SCORE", "0.20"))

# Tamanho de lote seguro para evitar picos de memória OOM na atenção (32 é rápido e estável)
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "32" if DEVICE.startswith("cuda") else "16"))
