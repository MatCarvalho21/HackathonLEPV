import argparse
import sys
from src.rag.config import COLLECTION_NAME, EMBEDDING_MODEL_NAME, RERANKER_MODEL_NAME, DEVICE
from src.rag.retriever import get_retriever


def print_search_results(query: str, results: list):
    print("\n" + "=" * 80)
    print(f"🔍 CONSULTA: \"{query}\"")
    print(f"⚙️  DISPOSITIVO: {DEVICE.upper()} | EMBEDDER: {EMBEDDING_MODEL_NAME} | RERANKER: {RERANKER_MODEL_NAME}")
    print(f"📊 RESULTADOS RELEVANTES: {len(results)}")
    print("=" * 80)

    if not results:
        print("❌ Nenhum trecho relevante encontrado para esta busca.")
        return

    for rank, item in enumerate(results, start=1):
        source = item.get("source", "N/A")
        page = item.get("page", 1)
        section = item.get("section", "Geral")
        is_table = " [TABELA]" if item.get("is_table") else ""
        sim_score = item.get("score", 0.0)
        rerank_score = item.get("rerank_score", sim_score)
        text = item.get("text", "").strip()

        print(f"\n[{rank}] 📄 {source} (Pág. {page}) {is_table}")
        print(f"    🏷️  Seção: {section}")
        print(f"    ⭐ Score Reranker: {rerank_score:.4f} (Similaridade Cosseno: {sim_score:.4f})")
        print("    " + "-" * 76)
        # Indenta o texto do resultado para melhor leitura
        for line in text.splitlines()[:12]:
            print(f"    {line}")
        if len(text.splitlines()) > 12:
            print("    ...")
    print("\n" + "=" * 80)


def run_cli():
    parser = argparse.ArgumentParser(description="Teste interativo de busca RAG com Two-Stage Retrieval")
    parser.add_argument("query", nargs="?", type=str, default=None, help="Pergunta para pesquisar na base")
    parser.add_argument("--top-k", type=int, default=4, help="Quantidade de resultados finais (padrão: 4)")
    parser.add_argument("--no-rerank", action="store_true", help="Desativa o Cross-Encoder Reranker")
    args = parser.parse_args()

    print("\nInicializando retriever na GPU...")
    retriever = get_retriever()

    if args.query:
        results = retriever.search(
            query=args.query,
            top_k=args.top_k,
            use_reranker=not args.no_rerank
        )
        print_search_results(args.query, results)
        return

    # Modo Interativo Contínuo
    print("\n" + "=" * 80)
    print(" 🚀 MODO DE CONSULTA INTERATIVO (Digite 'sair' ou 'q' para encerrar)")
    print("=" * 80)

    while True:
        try:
            user_input = input("\n🔍 Digite sua consulta: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["sair", "exit", "quit", "q"]:
                print("Encerrando consulta. Até mais!")
                break

            results = retriever.search(
                query=user_input,
                top_k=args.top_k,
                use_reranker=not args.no_rerank
            )
            print_search_results(user_input, results)

        except (KeyboardInterrupt, EOFError):
            print("\nEncerrando consulta.")
            break


if __name__ == "__main__":
    run_cli()
