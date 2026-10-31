# Correção: GPU 1 (Livre) e Indexação Incremental

## 1. O que causou o OutOfMemory (OOM)?
* O PyTorch estava usando por padrão a `GPU 0` (`cuda:0`). Nela, outro processo (do usuário Samuel) já ocupava cerca de 4 GB, sobrando pouca margem.
* No lote 36 (com `batch_size=128`), alguns chunks de documentos/tabelas mais longos geraram um pico de matriz de atenção que tentou alocar 10.12 GiB de uma vez, estourando a memória residual da GPU 0.

---

## 2. O que foi ajustado no código:

1. **Uso da GPU 1 (`cuda:1`)**:
   * O [`src/rag/config.py`](file:///home/matheus/matheus/HackathonLEPV/src/rag/config.py) agora detecta automaticamente a GPU com **mais VRAM livre**. Como a `GPU 1` tem **23.3 GB 100% livres**, ela é selecionada como padrão (`cuda:1`).
   * Também ativamos `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` para evitar fragmentação de memória.

2. **Indexação 100% Incremental**:
   * O [`src/rag/indexer.py`](file:///home/matheus/matheus/HackathonLEPV/src/rag/indexer.py) agora consulta os IDs já persistidos no ChromaDB antes de calcular os embeddings.
   * **Diagnóstico atual**: Dos 6.422 chunks totais, **4.608 chunks já foram gravados com sucesso** antes do erro!
   * Faltam apenas **1.814 chunks** (~28% do total). Ao rodar agora, ele **não recalcula nada do que já foi feito**, indo direto para os chunks que faltam.

3. **Lotes Otimizados e Limpeza de Cache**:
   * Reduzimos o `batch_size` para **32** (evita picos de 10 GB na atenção de chunks longos) e adicionamos `torch.cuda.empty_cache()` periódico para manter a VRAM sempre limpa.

---

## 3. Como rodar agora para continuar de onde parou:

Basta rodar **sem** a flag `--reindex`:

```bash
# Certifique-se de estar com o ambiente ativo:
source .venv/bin/activate

# Retoma a indexação apenas dos 1.814 chunks restantes na GPU 1:
python3 -m src.rag.indexer
```

O processo terminará em cerca de **1 a 2 minutos**.

*(A sua mensagem foi registrada em [`prompts/matheus/20/pergunta.md`](file:///home/matheus/matheus/HackathonLEPV/prompts/matheus/20/pergunta.md) e esta resposta salva em [`prompts/matheus/20/resposta.md`](file:///home/matheus/matheus/HackathonLEPV/prompts/matheus/20/resposta.md)).*
