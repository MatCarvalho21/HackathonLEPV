"""Configuração do agente de mapeamento de perfil."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _carregar_env(caminho: Path = ROOT / ".env") -> None:
    """Lê o .env da raiz sem depender de python-dotenv (aceita `CHAVE = valor`)."""
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


_carregar_env()

API_KEY = os.getenv("FEATHERLESS_API_KEY") or os.getenv("API_KEY", "")
BASE_URL = os.getenv("LLM_BASE_URL", "https://api.featherless.ai/v1")
MODELO = os.getenv("LLM_MODELO", "deepseek-ai/DeepSeek-V4.1-Flash-1017")
MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "16000"))   # o relatório final é um JSON longo
TEMPERATURA = float(os.getenv("LLM_TEMPERATURA", "0.3"))
TIMEOUT_S = float(os.getenv("LLM_TIMEOUT_S", "300"))

# Limites do loop agêntico
MAX_PASSOS = int(os.getenv("AGENTE_MAX_PASSOS", "14"))          # chamadas ao modelo por execução
MAX_BUSCAS_RAG = int(os.getenv("AGENTE_MAX_BUSCAS", "6"))       # consultas à base por execução
MAX_RODADAS_PERGUNTAS = int(os.getenv("AGENTE_MAX_RODADAS", "1"))  # vezes que pode voltar ao responsável
MAX_PERGUNTAS_POR_RODADA = 5
MAX_TENTATIVAS_VALIDACAO = 3
RAG_DESATIVADO = os.getenv("RAG_DESATIVADO", "0") == "1"
RAG_MIN_RELEVANCIA = float(os.getenv("AGENTE_RAG_MIN_RELEVANCIA", "0.15"))  # nota do reranker

FORM_DB = Path(os.getenv("FORM_DB", str(ROOT / "backend/data/plataforma.sqlite3")))
