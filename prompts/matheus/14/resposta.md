# Correção do `NameError: name 'Path' is not defined`

### Causa
Faltava a importação de `Path` da biblioteca padrão `pathlib` no topo de [`src/rag/chunker.py`](file:///home/matheus-carvalho/Documentos/HackathonLEPV/src/rag/chunker.py).

### Solução Aplicada
Foi adicionado `from pathlib import Path` no arquivo [`src/rag/chunker.py`](file:///home/matheus-carvalho/Documentos/HackathonLEPV/src/rag/chunker.py).

### Como Rodar Agora
Como o modelo já foi baixado (`471MB`) e você já está na raiz do projeto com o venv ativado, basta executar novamente:

```bash
python3 -m src.rag.indexer
```
