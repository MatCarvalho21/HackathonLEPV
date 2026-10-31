# Pipeline RAG - Base de Conhecimento em Desenvolvimento Infantil

Esta pipeline foi construída para o hackathon para processar os PDFs de referência em `/pdfs` (Caderneta da Criança, Guias da OMS, Relatórios EEF, Portarias do MEC, Pyramid Model e materiais de marcos de desenvolvimento) e disponibilizá-los para consultas semânticas no loop de atuação do agente de IA.

---

## 🛠️ Tecnologias Utilizadas

1. **ChromaDB**: Banco de dados vetorial leve, local e persistente (não necessita de Docker ou serviços externos). Os dados ficam salvos na pasta `/chroma_db`.
2. **Modelo de Embeddings Multilíngue**:
   - **Padrão**: `BAAI/bge-m3` — modelo open-source estado da arte com suporte a mais de 100 idiomas (excelente para queries em português buscando trechos em inglês como os relatórios da OMS e da EEF).
   - **Alternativa Ultra-Leve para CPU**: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (~470MB).
3. **PyPDF**: Extração segura de texto página a página.
4. **Recursive Chunking**: Divisão de parágrafos preservando números de página e metadados de citação.

---

## 🚀 Como Configurar e Rodar

### 1. Criar e Ativar o Ambiente Virtual

No terminal, na raiz do repositório (`/home/matheus-carvalho/Documentos/HackathonLEPV`):

```bash
# Cria o ambiente virtual Python
python3 -m venv venv

# Ativa o ambiente virtual
source venv/bin/activate

# Instala as dependências
pip install -r src/rag/requirements.txt
```

---

### 2. Executar a Indexação dos PDFs

Para ler os PDFs na pasta `pdfs/`, extrair o texto, gerar os vetores e salvar no ChromaDB:

```bash
# Indexação incremental (indexa apenas novos PDFs)
python3 -m src.rag.indexer

# Para forçar reindexação completa do zero:
python3 -m src.rag.indexer --reindex

# Para indexar apenas um PDF específico (ex: marcos):
python3 -m src.rag.indexer --filter milestones
```

> **Nota:** Na primeira execução, o `SentenceTransformers` fará o download do modelo open-source automaticamente do Hugging Face.

---

### 3. Testar a Busca no Terminal

Você pode fazer perguntas diretamente no terminal para verificar a precisão dos trechos recuperados:

```bash
python3 -m src.rag.test_query "Como agir diante de crises e comportamentos de mordida em sala de aula?"
```

Ou testar marcos do desenvolvimento:

```bash
python3 -m src.rag.test_query "Quais os marcos motores e de linguagem esperados para uma criança de 3 anos?"
```

---

## 🤖 Como Integrar no Loop do Agente de IA

Existem duas formas simples de plugar a ferramenta no seu agente:

### Opção A: Chamada Direta em Python

```python
from src.rag.retriever import consultar_base_conhecimento

# Durante a tomada de decisão do agente:
pergunta_usuario = "Meu filho tem 4 anos e está tendo muitas crises de raiva na escola. O que fazer?"

# Busca trechos fundamentados com citações (documento + página)
contexto_pedagogico = consultar_base_conhecimento(pergunta_usuario, top_k=3)

# Injete o contexto no prompt do LLM:
prompt_sistema = f"""
Você é um assistente pedagógico especializado em crianças com necessidades especiais.
Utilize as seguintes diretrizes e evidências científicas para responder:

{contexto_pedagogico}

Responda com empatia e sempre indique as práticas recomendadas.
"""
```

### Opção B: Tool / Function Calling (OpenAI / Claude / Gemini / LangChain)

Em `src/rag/retriever.py`, exportamos o schema padronizado `AGENT_TOOL_SCHEMA`:

```python
from src.rag.retriever import AGENT_TOOL_SCHEMA, consultar_base_conhecimento

# Passe AGENT_TOOL_SCHEMA na lista de 'tools' da chamada da API do modelo.
# Quando o agente decidir chamar a tool "consultar_base_conhecimento":
def executar_tool(nome_tool, argumentos):
    if nome_tool == "consultar_base_conhecimento":
        termo = argumentos.get("termo_busca")
        top_k = argumentos.get("top_k", 4)
        return consultar_base_conhecimento(termo, top_k=top_k)
```

---

## ⚡ Dica de Otimização para Máquinas sem GPU

Caso você esteja rodando em um notebook sem placa de vídeo dedicada e ache o `BAAI/bge-m3` pesado, você pode alternar facilmente para o modelo ultra-leve definindo a variável de ambiente:

```bash
export EMBEDDING_MODEL_NAME="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
python3 -m src.rag.indexer --reindex
```
