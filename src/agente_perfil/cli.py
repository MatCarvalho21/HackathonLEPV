"""Roda o agente pelo terminal, sem frontend.

    python -m src.agente_perfil.cli src/agente_perfil/exemplos/formulario_lia_38m.json
    python -m src.agente_perfil.cli <arquivo> --sem-rag          # não carrega a base vetorial
    python -m src.agente_perfil.cli <arquivo> --ajuste "Quero focar no sono"

O arquivo é o corpo que o frontend envia em POST /api/formularios. As perguntas
complementares do agente são feitas no terminal (Enter vazio = não responder).
"""
import argparse
import json
import logging
import os
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("formulario", type=Path)
    ap.add_argument("--sem-rag", action="store_true")
    ap.add_argument("--ajuste", help="Após gerar, pede um ajuste com este comentário")
    ap.add_argument("--saida", type=Path, help="Salva a avaliação final em JSON")
    a = ap.parse_args()
    if a.sem_rag:
        os.environ["RAG_DESATIVADO"] = "1"
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    from fastapi.testclient import TestClient
    from backend.main import app
    from src.agente_perfil import agente

    cliente = TestClient(app)
    r = cliente.post("/api/formularios", json=json.loads(a.formulario.read_text(encoding="utf-8")))
    if r.status_code != 201:
        sys.exit(f"Formulário rejeitado: {r.status_code} {r.text}")
    formulario_id = r.json()["id"]
    print(f"Formulário salvo: {formulario_id}\nRodando o agente...")

    res = agente.iniciar(formulario_id)
    while res["status"] == "aguardando_responsavel":
        print(f"\n🤔 O agente quer saber mais: {res['motivo']}")
        respostas = {}
        for p in res["perguntas"]:
            opcoes = f" [{' / '.join(p['opcoes'])}]" if p.get("opcoes") else ""
            respostas[p["id"]] = input(f"  ({p['dominio']}) {p['pergunta']}{opcoes}\n  > ")
        res = agente.retomar(res["sessao_id"], respostas)

    if res["status"] == "erro":
        sys.exit(f"Erro: {res['erro']}")
    if a.ajuste:
        print(f"\nPedindo ajuste: {a.ajuste}")
        res = agente.ajustar(res["avaliacao_id"], a.ajuste)
        if res["status"] != "concluida":
            sys.exit(f"Erro no ajuste: {res.get('erro')}")

    av = res["avaliacao"]
    rel = av["perfil"]["relatorio"]
    print(f"\n✅ Avaliação {av['id']} ({av['status']}) | passos={res['passos']} buscas={res['buscas_feitas']} "
          f"tokens={res['uso_tokens']}")
    print("\nRESUMO:\n" + rel["resumo"])
    print("\nSEMÁFORO: " + " · ".join(f"{k}={v}" for k, v in av["niveis"].items()))
    print("\nFOCO: " + "; ".join(f"{f['dominio']}: {f['por_que']}" for f in rel["foco_prioritario"]))
    print("\nMETAS:")
    for m in rel["metas"]:
        print(f"  [{m['horizonte']}/{m['prazo_semanas']}sem/{m['dominio']}] {m['texto']}")
    print("\nDICAS:")
    for d in rel["dicas"]:
        print(f"  - {d['titulo']} {d['fontes']}")
    if rel["alertas"]:
        print("\nALERTAS: " + "; ".join(x["texto"] for x in rel["alertas"]))
    print("\nFONTES: " + json.dumps(av["perfil"]["fontes"], ensure_ascii=False))
    if a.saida:
        a.saida.write_text(json.dumps(av, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\nSalvo em {a.saida}")


if __name__ == "__main__":
    main()
