# Imagens do deploy. Três estágios:
#   frontend → compila o React (Vite) para arquivos estáticos
#   web      → Caddy servindo o front e encaminhando /api para o backend (HTTPS automático)
#   api      → FastAPI + agente + RAG (embedding e5-small em CPU), banco no Supabase

# ---------------------------------------------------------------- frontend
FROM node:22-alpine AS frontend
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY index.html vite.config.js ./
COPY public ./public
COPY prompts/matheus/07/ouput.json ./prompts/matheus/07/ouput.json
COPY src ./src
RUN npm run build

# ---------------------------------------------------------------- web (Caddy)
FROM caddy:2-alpine AS web
COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY --from=frontend /app/dist /srv

# ---------------------------------------------------------------- api (FastAPI)
FROM python:3.12-slim AS api
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/opt/hf \
    RAG_DEVICE=cpu \
    TOKENIZERS_PARALLELISM=false \
    OMP_NUM_THREADS=2
WORKDIR /app

# Torch só CPU (a versão com CUDA tem vários GB e não serve numa máquina sem GPU).
RUN pip install torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu
COPY backend/requirements.txt deploy/requirements-rag.txt /tmp/reqs/
RUN pip install -r /tmp/reqs/requirements.txt -r /tmp/reqs/requirements-rag.txt

# Baixa o modelo de embedding no build, para a 1ª busca não depender da internet nem esperar o download.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/multilingual-e5-small', device='cpu')"
ENV HF_HUB_OFFLINE=1

# Só o que o backend lê em tempo de execução (o resto fica de fora pelo .dockerignore).
COPY backend ./backend
COPY src/agente_perfil ./src/agente_perfil
COPY src/rag ./src/rag
COPY prompts/matheus/07/ouput.json ./prompts/matheus/07/ouput.json
COPY chroma_db ./chroma_db

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"

# Um worker só: o agente roda em threads dentro do processo e o pool do Supabase é por processo.
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]
