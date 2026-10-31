venv) matheus-carvalho@matheus-carvalho-Inspiron-15-3511:~/Documentos/HackathonLEPV/src/rag$ cd ../..
python3 -m src.rag.indexer
======================================================================
 PIPELINE DE INDEXAÇÃO VETORIAL (RAG) - DESENVOLVIMENTO INFANTIL
======================================================================
Diretório de PDFs:      /home/matheus-carvalho/Documentos/HackathonLEPV/pdfs
Banco ChromaDB:         /home/matheus-carvalho/Documentos/HackathonLEPV/chroma_db
Coleção:                desenvolvimento_infantil_kb
Modelo de Embeddings:   sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
Chunk Size / Overlap:   800 / 150 caracteres
----------------------------------------------------------------------
Total de arquivos PDF localizados: 74

Carregando modelo de embeddings 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'...
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
modules.json: 100%|██████████████████████████████████████████████████████| 229/229 [00:00<00:00, 717kB/s]
config_sentence_transformers.json: 100%|█████████████████████████████████| 122/122 [00:00<00:00, 499kB/s]
README.md: 100%|████████████████████████████████████████████████████| 3.89k/3.89k [00:00<00:00, 7.04MB/s]
sentence_bert_config.json: 100%|███████████████████████████████████████| 53.0/53.0 [00:00<00:00, 169kB/s]
config.json: 100%|██████████████████████████████████████████████████████| 645/645 [00:00<00:00, 2.08MB/s]
model.safetensors: downloading bytes: ███████████████████████████████████████████████|  446MB, 21.7MB/s  
model.safetensors: reconstructing file: 100%|███████████████████████████████|  471MB /  471MB, 36.1MB/s  
Loading weights: 100%|███████████████████████████████████████████████| 199/199 [00:00<00:00, 9653.68it/s]
tokenizer_config.json: 100%|████████████████████████████████████████████| 526/526 [00:00<00:00, 1.70MB/s]
tokenizer.json: downloading bytes: ██████████████████████████████████████████████████| 5.42MB,  476kB/s  
tokenizer.json: reconstructing file: 100%|██████████████████████████████████| 9.08MB / 9.08MB,  822kB/s  
special_tokens_map.json: 100%|███████████████████████████████████████████| 239/239 [00:00<00:00, 718kB/s]
config.json: 100%|███████████████████████████████████████████████████████| 190/190 [00:00<00:00, 632kB/s]
Modelo carregado com sucesso.

[Etapa 1/2] Extraindo e fatiando documentos...
Processando PDFs:   0%|                                                           | 0/74 [00:00<?, ?it/s]
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "/home/matheus-carvalho/Documentos/HackathonLEPV/src/rag/indexer.py", line 174, in <module>
    run_indexing(force_reindex=args.reindex, pdf_filter=args.filter)
  File "/home/matheus-carvalho/Documentos/HackathonLEPV/src/rag/indexer.py", line 111, in run_indexing
    chunks = chunk_pages(pages, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/matheus-carvalho/Documentos/HackathonLEPV/src/rag/chunker.py", line 110, in chunk_pages
    doc_slug = sanitize_id(Path(source).stem)
                           ^^^^
NameError: name 'Path' is not defined
