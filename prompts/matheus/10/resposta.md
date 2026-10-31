# Pipeline RAG para a Base de Conhecimento em Desenvolvimento Infantil

Construí a pipeline completa e modular para o RAG na pasta [`src/rag/`](file:///home/matheus-carvalho/Documentos/HackathonLEPV/src/rag), pronta para processar os 29 PDFs presentes em [`pdfs/`](file:///home/matheus-carvalho/Documentos/HackathonLEPV/pdfs) e fornecer ao agente de IA uma ferramenta de consulta em tempo real durante seu loop de atuação.

Nenhum comando foi executado. Todo o código está pronto e estruturado.

---

## 1. Escolhas de Arquitetura

1. **Modelo de Embeddings Open-Source Multilíngue**:
   - **Recomendado (Padrão):** [`BAAI/bge-m3`](https://huggingface.co/BAAI/bge-m3)
     - Estado da arte em RAG multilíngue (100+ idiomas).
     - Janela de contexto de até 8.192 tokens e vetores densos de 1.024 dimensões.
     - **Essencial para a sua base:** permite que o agente faça perguntas em português e recupere com altíssima acurácia trechos em inglês (como os relatórios da EEF e guias da OMS) além dos materiais em português (Caderneta da Criança, marcos e portarias do MEC).
   - **Alternativa Leve (CPU-only):** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (~470 MB, 384 dimensões), para rodar rápido se a máquina não tiver GPU dedicada.
2. **Banco Vetorial Local**: **ChromaDB**
   - Roda 100% embarcado em Python, sem necessidade de Docker, portas ou serviços externos durante o hackathon.
   - Os índices e vetores ficam salvos e persistidos na pasta `chroma_db/`.
3. **Divisão de Texto (Chunking)**:
   - Fatiamento recursivo por parágrafos, frases e pontuação (~800 caracteres com 150 de sobreposição).
   - Preserva metadados detalhados: documento de origem (`source`), número exato da página (`page`), número do chunk e contagem de caracteres.

---

## 2. Estrutura de Arquivos Criados

Os arquivos foram organizados dentro de [`src/rag/`](file:///home/matheus-carvalho/Documentos/HackathonLEPV/src/rag):

- [`requirements.txt`](file:///home/matheus-carvalho/Documentos/HackathonLEPV/src/rag/requirements.txt): dependências mínimas e sem conflitos (`chromadb`, `sentence-transformers`, `pypdf`, `tqdm`).
- [`config.py`](file:///home/matheus-carvalho/Documentos/HackathonLEPV/src/rag/config.py): caminhos do projeto, nomes de coleção e hiperparâmetros de chunking e embedding.
- [`pdf_loader.py`](file:///home/matheus-carvalho/Documentos/HackathonLEPV/src/rag/pdf_loader.py): extrator de texto robusto página a página usando `pypdf`, com limpeza de hifenizações, caracteres nulos e quebras de linha irregulares.
- [`chunker.py`](file:///home/matheus-carvalho/Documentos/HackathonLEPV/src/rag/chunker.py): fatiador recursivo que gera IDs determinísticos (`slug_p{pagina}_c{idx}`) e metadados compatíveis com o ChromaDB.
- [`indexer.py`](file:///home/matheus-carvalho/Documentos/HackathonLEPV/src/rag/indexer.py): script de indexação em lote (batching de 64 itens) com suporte a indexação incremental (não reprocessa PDFs já indexados, a menos que passe `--reindex`).
- [`retriever.py`](file:///home/matheus-carvalho/Documentos/HackathonLEPV/src/rag/retriever.py): classe `KnowledgeRetriever`, função `consultar_base_conhecimento` e schema de Tool para o agente (OpenAI/Gemini/LangChain compatible).
- [`test_query.py`](file:///home/matheus-carvalho/Documentos/HackathonLEPV/src/rag/test_query.py): script CLI para você testar consultas e ver como o texto formatado chega ao modelo.
- [`README.md`](file:///home/matheus-carvalho/Documentos/HackathonLEPV/src/rag/README.md): documentação rápida de apoio.

---

## 3. Passo a Passo: Como Rodar

### Passo 1: Criar o Ambiente Virtual e Instalar Pacotes

No terminal, na raiz do projeto:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r src/rag/requirements.txt
```

### Passo 2: Executar a Indexação dos PDFs

Para processar todos os PDFs da pasta `pdfs/` e criar o banco vetorial no ChromaDB:

```bash
python3 -m src.rag.indexer
```

*Dicas úteis:*
- Se quiser forçar a recriação do zero: `python3 -m src.rag.indexer --reindex`
- Se quiser indexar apenas um arquivo específico: `python3 -m src.rag.indexer --filter milestones`

### Passo 3: Testar a Recuperação no Terminal

Faça uma pergunta de teste para validar a precisão semântica:

```bash
python3 -m src.rag.test_query "Como lidar com mordidas e crises de comportamento em crianças?"
```

Ou:

```bash
python3 -m src.rag.test_query "Quais são os marcos de desenvolvimento esperados entre 2 e 3 anos?"
```

---

## 4. Como Integrar no Loop do Agente

### Opção 1: Chamada Direta no Código do Agente (Simples e Rápido)

```python
from src.rag.retriever import consultar_base_conhecimento

# Durante a execução do agente:
termo = "Criança de 4 anos com atraso na fala e crises de birra na escola"
contexto_recuperado = consultar_base_conhecimento(termo, top_k=3)

# O contexto retornado já vem formatado com as fontes:
# ### [Trecho 1] Documento: `BackpackConnection_behavior_meltdown_PR.pdf` (Página 1) | Relevância: 0.82
# ...texto...
```

### Opção 2: Tool / Function Calling (Para o LLM Decidir Quando Chamar)

Se o seu agente usa LangChain, CrewAI, AutoGen ou a API nativa da OpenAI / Gemini, passe o `AGENT_TOOL_SCHEMA` definido em [`src/rag/retriever.py`](file:///home/matheus-carvalho/Documentos/HackathonLEPV/src/rag/retriever.py):

```python
from src.rag.retriever import AGENT_TOOL_SCHEMA, consultar_base_conhecimento

# Lista de tools do LLM:
tools = [AGENT_TOOL_SCHEMA]

# Quando a resposta do LLM requisitar tool_call:
def handle_tool_call(tool_name, arguments):
    if tool_name == "consultar_base_conhecimento":
        return consultar_base_conhecimento(
            termo_busca=arguments["termo_busca"],
            top_k=arguments.get("top_k", 4)
        )
```
