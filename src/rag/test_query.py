import sys
from src.rag.retriever import get_retriever


def test_query(query: str):
    print("=" * 70)
    print(" TESTE DE CONSULTA AO BANCO VETORIAL (RAG)")
    print("=" * 70)
    print(f"Pergunta: \"{query}\"\n")
    print("Recuperando trechos mais relevantes com o modelo multilíngue...")

    retriever = get_retriever()
    results = retriever.search(query=query, top_k=4)

    if not results:
        print("[!] Nenhum resultado retornado. O banco foi indexado com sucesso?")
        return

    print(f"\nEncontrados {len(results)} trechos relevantes:\n")
    for i, res in enumerate(results, start=1):
        print(f"--- [Resultado #{i}] ------------------------------------------")
        print(f"Fonte:       {res['source']}")
        print(f"Página:      {res['page']}")
        print(f"Score Cosseno: {res['score']:.4f}")
        print(f"ID Chunk:    {res['id']}")
        print("Trecho:")
        print(f"  {res['text'][:350]}...")
        print()

    print("=" * 70)
    print("FORMATO QUE O AGENTE DE IA RECEBE NO PROMPT:")
    print("=" * 70)
    formatted = retriever.get_formatted_context(query=query, top_k=3)
    print(formatted)
    print("=" * 70)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        query_text = " ".join(sys.argv[1:])
    else:
        query_text = "Como lidar com mordidas e crises de comportamento em crianças?"
        print(f"Nenhuma consulta passada via argumento. Usando consulta padrão de exemplo: '{query_text}'\n")

    test_query(query_text)
