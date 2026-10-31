# Teste do Banco Vetorial (Top 5 Mais Próximos)

Atualizamos o arquivo [`src/rag/test_query.py`](file:///home/matheus-carvalho/Documentos/HackathonLEPV/src/rag/test_query.py) para buscar as **5 partes mais próximas** (`top_k=5`) e adicionamos um **Modo Interativo contínuo**.

### Opção 1: Modo Interativo (digitar perguntas no terminal)
Basta rodar sem argumentos:
```bash
python3 -m src.rag.test_query
```
Ele abrirá um prompt contínuo:
```text
🔍 Digite sua consulta: marcos do desenvolvimento motor aos 2 anos
```
Ele trará os 5 trechos mais próximos (documento, página, score de similaridade e o texto). Para sair, basta digitar `sair` ou `q`.

---

### Opção 2: Passar a query direto como argumento
```bash
python3 -m src.rag.test_query "Como lidar com comportamentos de mordida e agressão?"
```
