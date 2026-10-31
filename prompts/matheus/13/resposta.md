# Correção do erro `ModuleNotFoundError: No module named 'src'`

O erro ocorreu porque o comando foi executado dentro da subpasta `src/rag/`. O Python procura o módulo `src` a partir do diretório atual.

### Solução 1: Voltar para a raiz do repositório (Recomendada)
Basta voltar dois níveis para a raiz do projeto e rodar o comando:

```bash
cd ../..
python3 -m src.rag.indexer
```

---

### Solução 2: Rodar diretamente de dentro da pasta `src/rag/`
Se preferir continuar dentro do diretório `src/rag/`, adicione a raiz ao `PYTHONPATH`:

```bash
PYTHONPATH=../.. python3 -m src.rag.indexer
```
