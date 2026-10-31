import sys
from src.rag.retriever import get_retriever


def test_query(query: str, top_k: int = 5):
    print("=" * 70)
    print(" TESTE DE CONSULTA AO BANCO VETORIAL (RAG)")
    print("=" * 70)
    print(f"Pergunta: \"{query}\"\n")
    print(f"Recuperando os {top_k} trechos mais relevantes...\n")

    retriever = get_retriever()
    results = retriever.search(query=query, top_k=top_k)

    if not results:
        print("[!] Nenhum resultado retornado. O banco foi indexado com sucesso?")
        return

    print(f"Encontrados {len(results)} trechos relevantes:\n")
    for i, res in enumerate(results, start=1):
        print(f"--- [Resultado #{i}] ------------------------------------------")
        print(f"Fonte:         {res['source']}")
        print(f"Página:        {res['page']}")
        print(f"Similaridade:  {res['score']:.4f}")
        print(f"ID Chunk:      {res['id']}")
        print("Trecho:")
        print(f"  {res['text']}")
        print()

    print("=" * 70)
    print("FORMATO QUE O AGENTE DE IA RECEBE NO PROMPT:")
    print("=" * 70)
    formatted = retriever.get_formatted_context(query=query, top_k=top_k)
    print(formatted)
    print("=" * 70)


def interactive_mode(top_k: int = 5):
    print("=" * 70)
    print(" MODO INTERATIVO RAG - BASE DE CONHECIMENTO VETORIAL")
    print(" Digite sua pergunta no terminal (ou 'sair'/'q' para encerrar)")
    print("=" * 70)
    
    # Carrega modelo e conexão com o ChromaDB
    retriever = get_retriever()
    print("Base conectada com sucesso! Pronto para consultas.\n")

    while True:
        try:
            query = input("🔍 Digite sua consulta: ").strip()
            if not query:
                continue
            if query.lower() in ["sair", "exit", "quit", "q"]:
                print("Encerrando.")
                break

            results = retriever.search(query=query, top_k=top_k)
            if not results:
                print("Nenhum resultado encontrado.\n")
                continue

            print(f"\nTop {len(results)} trechos mais próximos encontrados:")
            print("-" * 70)
            for i, res in enumerate(results, start=1):
                print(f"[{i}] {res['source']} (Página {res['page']}) | Similaridade: {res['score']:.4f}")
                print(f"    {res['text'][:350]}...")
                print("-" * 70)
            print()
        except (KeyboardInterrupt, EOFError):
            print("\nEncerrando.")
            break


if __name__ == "__main__":
    if len(sys.argv) > 1:
        query_text = " ".join(sys.argv[1:])
        test_query(query_text, top_k=5)
    else:
        interactive_mode(top_k=5)

