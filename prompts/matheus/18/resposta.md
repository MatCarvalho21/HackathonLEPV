# Implementação Concluída: Pipeline RAG com Docling, Semantic Chunking e Reranker

Todas as etapas do novo pipeline foram implementadas e validadas sintaticamente na pasta [`src/rag/`](file:///home/matheus/matheus/HackathonLEPV/src/rag/). Conforme você solicitou, **nenhum processamento ou download foi executado** — deixamos tudo pronto para você rodar no seu tempo.

A sua interação está devidamente registrada em [`prompts/matheus/18/pergunta.md`](file:///home/matheus/matheus/HackathonLEPV/prompts/matheus/18/pergunta.md) e esta resposta salva em [`prompts/matheus/18/resposta.md`](file:///home/matheus/matheus/HackathonLEPV/prompts/matheus/18/resposta.md).

---

## 🛠️ Resumo do que foi construído

1. [`src/rag/requirements.txt`](file:///home/matheus/matheus/HackathonLEPV/src/rag/requirements.txt): Adicionados `docling` (IBM layout/tabelas), `transformers`, `sentence-transformers`, `accelerate` e utilitários.
2. [`src/rag/config.py`](file:///home/matheus/matheus/HackathonLEPV/src/rag/config.py): Configuração com detecção automática de CUDA (GPU), diretórios (`data/markdown_docs`, `chroma_db`), batch size de 128 (aproveitando os 24GB de VRAM) e modelos (`BAAI/bge-m3` e `BAAI/bge-reranker-v2-m3`).
3. [`src/rag/convert_to_markdown.py`](file:///home/matheus/matheus/HackathonLEPV/src/rag/convert_to_markdown.py): Conversor inteligente com IBM Docling que preserva hierarquia de títulos e tabelas completas em Markdown com fallback automático e metadados `.meta.json`.
4. [`src/rag/chunker.py`](file:///home/matheus/matheus/HackathonLEPV/src/rag/chunker.py): Fatiador hierárquico ciente de Markdown que rastreia breadcrumbs de seções (`Capítulo > Subseção`), não quebra linhas de tabelas no meio e injeta metadados ricos em cada bloco.
5. [`src/rag/indexer.py`](file:///home/matheus/matheus/HackathonLEPV/src/rag/indexer.py): Indexador otimizado para GPU que processa os Markdowns gerados em lotes rápidos e grava no ChromaDB com barra de progresso.
6. [`src/rag/retriever.py`](file:///home/matheus/matheus/HackathonLEPV/src/rag/retriever.py): Sistema de recuperação em duas etapas (Bi-Encoder recupera Top 20 -> Cross-Encoder Reranker reordena para Top 4 de altíssima precisão).
7. [`src/rag/test_query.py`](file:///home/matheus/matheus/HackathonLEPV/src/rag/test_query.py): Interface de terminal interativa com comparação de scores (Similaridade vs Reranker).
8. [`src/rag/README.md`](file:///home/matheus/matheus/HackathonLEPV/src/rag/README.md): Documentação atualizada do pipeline.

---

## 💻 Passo a Passo para Rodar na sua Máquina

### 1. Entrar na pasta do projeto e criar o ambiente virtual
```bash
cd /home/matheus/matheus/HackathonLEPV

# Cria o ambiente virtual
python3 -m venv .venv

# Ativa o ambiente
source .venv/bin/activate
```

---

### 2. Instalar o PyTorch com suporte a CUDA 12
Como a sua máquina possui duas GPUs NVIDIA Quadro RTX 6000 e driver CUDA 12.9:
```bash
pip install --upgrade pip

# Instala o PyTorch compilado com suporte a CUDA 12.4
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
```

> **Verificação rápida da GPU**:
> ```bash
> python3 -c "import torch; print('CUDA disponível:', torch.cuda.is_available(), '| Dispositivos:', torch.cuda.device_count(), '| GPU:', torch.cuda.get_device_name(0))"
> ```

---

### 3. Instalar as dependências do RAG
```bash
pip install -r src/rag/requirements.txt
```

---

### 4. Converter os PDFs para Markdown Estruturado (Docling)
Lê os 74 PDFs de `/pdfs` e salva os Markdowns com tabelas intactas em `data/markdown_docs/`:

```bash
# Converter todos os PDFs:
python3 -m src.rag.convert_to_markdown
```

*(Opcional: se quiser testar a conversão em apenas 3 arquivos primeiro, rode `python3 -m src.rag.convert_to_markdown --limit 3`)*

---

### 5. Indexar no ChromaDB com GPU
Fatia os Markdowns em blocos semânticos, gera os embeddings com o `BAAI/bge-m3` na GPU e salva na coleção:

```bash
# Criação do índice vetorial completo:
python3 -m src.rag.indexer --reindex
```

---

### 6. Testar as Consultas e o Reranker

Você pode passar uma pergunta direta:
```bash
python3 -m src.rag.test_query "Quais os marcos motores esperados para uma criança de 2 a 3 anos?"
```

Ou entrar no **Modo Interativo** para testar várias dúvidas seguidas:
```bash
python3 -m src.rag.test_query
```
