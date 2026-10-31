# Guia de Execução: Criação do Banco de Dados Vetorial (ChromaDB)

## 1. Preciso converter para Markdown (.md) primeiro?
**Não.** A pipeline lê diretamente os arquivos `.pdf` da pasta `pdfs/`. 
O módulo [`src/rag/pdf_loader.py`](file:///home/matheus-carvalho/Documentos/HackathonLEPV/src/rag/pdf_loader.py) já extrai o texto página por página, limpa quebras e formatações, e envia diretamente para o particionador de texto (`chunker.py`) e para o ChromaDB. A conversão para markdown é opcional e serve apenas para leitura humana de inspeção.

---

## 2. Qual sequência de arquivos / comandos rodar?

Todos os comandos devem ser executados a partir da raiz do repositório (`/home/matheus-carvalho/Documentos/HackathonLEPV`).

### Passo 1: Preparar o ambiente virtual e instalar dependências
```bash
# 1. Cria o ambiente virtual (se ainda não existir)
python3 -m venv venv

# 2. Ativa o ambiente virtual
source venv/bin/activate

# 3. Instala as bibliotecas necessárias (chromadb, sentence-transformers, pypdf, tqdm)
pip install -r src/rag/requirements.txt
```

### Passo 2: Executar a indexação (criação do ChromaDB)

O arquivo central que orquestra tudo é o [`src/rag/indexer.py`](file:///home/matheus-carvalho/Documentos/HackathonLEPV/src/rag/indexer.py).

#### Opção A (Recomendada para CPU - Mais Rápida):
Como a máquina opera em **CPU** (sem GPU dedicada), o modelo padrão pode demorar. Use o modelo multilíngue ultra-leve:
```bash
export EMBEDDING_MODEL_NAME="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
python3 -m src.rag.indexer
```

#### Opção B (Modelo Padrão de Alta Precisão - BAAI/bge-m3):
```bash
python3 -m src.rag.indexer
```

#### Comandos úteis do indexador:
```bash
# Para testar apenas um PDF ou grupo específico (ex: marcos do CDC):
python3 -m src.rag.indexer --filter cdc

# Para resetar e reindexar tudo do zero:
python3 -m src.rag.indexer --reindex
```

### Passo 3: Testar a base criada (opcional)
Para testar consultas semânticas no terminal:
```bash
python3 -m src.rag.test_query "Quais os marcos esperados para uma criança de 3 anos?"
```

---

## 3. Vai ser rápido?

- **Com o modelo padrão (`BAAI/bge-m3`) em CPU**: **Não será rápido**.
  - O download inicial do modelo tem ~2.2 GB.
  - A pasta `pdfs/` contém **74 arquivos** (alguns com mais de 20 MB e dezenas de páginas, gerando milhares de chunks).
  - Em CPU pura, processar todos os 74 PDFs com `bge-m3` pode levar entre **30 a 60 minutos**.
- **Com o modelo leve (`paraphrase-multilingual-MiniLM-L12-v2`)**:
  - O download tem apenas ~470 MB.
  - A vetorização é muito mais rápida em CPU, economizando bastante tempo de processamento.
- **Indexação Incremental**: O indexador não reprocessa arquivos que já estão salvos no ChromaDB; se você interromper, ele retoma de onde parou.
