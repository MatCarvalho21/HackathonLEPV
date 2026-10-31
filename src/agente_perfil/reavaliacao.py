"""Reavaliação: nova versão do perfil a partir do perfil vigente + tudo o que foi registrado desde então.

O responsável pode (opcional) atualizar o formulário antes. O dossiê da reavaliação junta, por código:
- o perfil vigente (cores, foco, metas com escala GAS, dicas);
- TODOS os registros do dia a dia, com data, autor (nome e papel) e conteúdo, separados entre
  "desde a última avaliação" e "anteriores" (são poucos tokens);
- o histórico de progresso de cada meta (check-ins GAS) e o placar das estratégias testadas;
- o pedido do responsável, se ele escreveu algum ao solicitar a reavaliação;
- se houver, o FORMULÁRIO ATUALIZADO: com ele, as cores das áreas por idade voltam a ser calculadas
  pelas regras (como na avaliação inicial), agora com as respostas novas.

A comparação entre as versões (cor antes → depois, progresso de cada meta, volume de registros)
é calculada aqui em código e guardada em `perfil.reavaliacao`; o modelo escreve a narrativa em
`relatorio.evolucao`, validada contra esses dados.
"""
from __future__ import annotations

from datetime import date, datetime

from src.agente_perfil import repositorio as repo
from src.agente_perfil.dossie import CONTEXTUAIS, FUNCIONAIS, POR_IDADE, idade_por_extenso, montar_dossie

FUNCOES = {"professor": "professor(a)", "pedagogo": "pedagogo(a)", "medico": "médico(a)", "terapeuta": "terapeuta",
           "familiar": "familiar", "outro": "acompanhante", "responsavel": "responsável"}

NOMES = {"COM_R": "Compreensão", "COM_E": "Comunicação expressiva", "FAL": "Fala e verbalização",
         "SOC": "Interação social", "BRI": "Brincadeira", "COG": "Cognição e aprendizagem", "MOT_A": "Motor amplo",
         "MOT_F": "Motor fino", "AUT": "Autonomia e autocuidado", "REG": "Regulação e comportamento",
         "ATE": "Atenção e funções executivas", "SEN": "Processamento sensorial", "SAU": "Saúde e corpo",
         "CTX": "Contexto e participação"}
ORDEM_COR = {"vermelho": 1, "amarelo": 2, "verde": 3}


def id_registro(r: dict) -> str:
    return f"reg:{r['id'][:8]}"


def _idade_meses(nascimento: str) -> int:
    n, h = date.fromisoformat(nascimento[:10]), date.today()
    return max(0, (h.year - n.year) * 12 + h.month - n.month - (h.day < n.day))


def _papel(r: dict) -> str:
    """Função de quem registrou: responsável, professor(a), médico(a), familiar..."""
    return FUNCOES.get(r.get("autor_funcao") or ("responsavel" if r.get("autor") != "professor" else "outro"), "acompanhante")


def linha_registro(r: dict) -> str:
    """Uma linha por registro: ID citável, data, quem registrou, tipo, local, áreas e conteúdo."""
    d = r.get("dados") or {}
    partes = [f"[{id_registro(r)}] {r['ocorrido_em'][:10]} · {r.get('autor_nome') or '?'} ({_papel(r)}) · {r['tipo']}"]
    if r.get("local"):
        partes.append(f"em {r['local']}")
    if r.get("dominios"):
        partes.append("áreas " + ",".join(r["dominios"]))
    corpo = []
    if r["tipo"] == "comportamento":
        abc = " → ".join(x for x in (d.get("antecedente"), d.get("comportamento"), d.get("consequencia")) if x)
        corpo.append(f"ABC: {abc}")
        if d.get("intensidade"):
            corpo.append(f"intensidade {d['intensidade']}/5")
        if d.get("duracao_min") is not None:
            corpo.append(f"{d['duracao_min']} min")
    elif r["tipo"] == "checkin_meta":
        corpo.append(f"meta {r.get('meta_id')} nível GAS {d.get('nivel_gas')}")
    elif r["tipo"] == "saude":
        corpo.append(" ".join(x for x in (d.get("categoria"), d.get("profissional")) if x))
    for k in ("activity", "reaction", "support", "nivel_ajuda", "engajamento", "duracao_min"):
        if d.get(k) and r["tipo"] != "comportamento":
            corpo.append(f"{k}: {d[k]}")
    if r.get("estrategia"):
        corpo.append(f"estratégia “{r['estrategia']}”: {r.get('resultado')}")
    if r.get("texto"):
        corpo.append(r["texto"].replace("\n", " "))
    return " · ".join(partes) + ": " + " | ".join(c for c in corpo if c)


def _checkins_por_meta(registros: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for r in sorted(registros, key=lambda x: x["ocorrido_em"]):
        if r["tipo"] == "checkin_meta" and r.get("meta_id"):
            out.setdefault(r["meta_id"], []).append({"data": r["ocorrido_em"][:10], "nivel": (r.get("dados") or {}).get("nivel_gas"),
                                                     "texto": r.get("texto"), "por": f"{r.get('autor_nome')} ({_papel(r)})",
                                                     "evidencia": id_registro(r)})
    return out


def montar_dossie_reavaliacao(crianca_id: str, base: dict, comentario: str | None,
                              formulario_novo_id: str | None = None) -> dict:
    """Dossiê da reavaliação. `base` é a avaliação vigente que será comparada."""
    crianca = repo.obter_crianca(crianca_id)
    formulario = repo.obter_formulario(base["formulario_id"]) if base.get("formulario_id") else None
    novo = montar_dossie(repo.obter_formulario(formulario_novo_id)) if formulario_novo_id else None
    rel = base["perfil"]["relatorio"]
    desde = base.get("aceita_em") or base["criado_em"]
    registros = repo.listar_registros(crianca_id, limite=1000)
    novos = [r for r in registros if r["ocorrido_em"] >= desde or r["criado_em"] >= desde]
    antigos = [r for r in registros if r not in novos]
    checkins = _checkins_por_meta(registros)
    meses = _idade_meses(crianca["data_nascimento"])

    evid_validas = {id_registro(r) for r in registros}
    if formulario:  # marcos e relatos do formulário original continuam citáveis
        evid_validas |= set(montar_dossie(formulario)["_evidencias_validas"])
    evid_validas |= set(base["perfil"].get("respostas_complementares", {}))
    calculado_novo = {}
    if novo:
        evid_validas |= set(novo["_evidencias_validas"])
        calculado_novo = {d["codigo"]: d["status_calculado"] for d in novo["dominios"] if d["codigo"] in POR_IDADE}
        perfil_form = repo.obter_formulario(formulario_novo_id)["perfil"]
    else:
        perfil_form = (formulario or {}).get("perfil", {})
    dominios = []
    for d in rel["dominios"]:
        cod = d["codigo"]
        tipo = "por_idade" if cod in POR_IDADE else "funcional" if cod in FUNCIONAIS else "contextual"
        dominios.append({
            "codigo": cod, "nome": NOMES.get(cod, cod), "tipo": tipo,
            "status_anterior": d["status"],
            # Sem formulário novo, nenhuma cor é fixada por regra (exceto as contextuais, sem cor).
            # Com formulário novo, as áreas por idade usam a cor calculada pelas respostas atualizadas.
            "status_calculado": "contextual" if cod in CONTEXTUAIS else calculado_novo.get(cod),
            "justificativa_anterior": d["justificativa_status"],
            "pontos_de_atencao_anteriores": [e["texto"] for e in d["pontos_de_atencao"]],
            "registros_no_periodo": sum(1 for r in novos if cod in (r.get("dominios") or [])),
        })

    return {
        "tipo": "reavaliacao",
        "crianca": {
            "apelido": crianca["nome"], "idade_meses": meses, "idade": idade_por_extenso(meses),
            "interesses": crianca.get("interesses") or perfil_form.get("interesses"),
            "prioridades_da_familia_no_formulario": perfil_form.get("prioridades"),
            "condicoes_relatadas_pela_familia": perfil_form.get("condicoes_relatadas") or [],
        },
        "pedido_do_responsavel": comentario,
        "formulario_atualizado": ({k: v for k, v in novo.items() if not k.startswith("_") and k != "formulario_id"}
                                  if novo else None),
        "periodo": {"avaliacao_vigente_aprovada_em": desde[:10], "hoje": date.today().isoformat(),
                    "dias": (datetime.now().date() - date.fromisoformat(desde[:10])).days,
                    "registros_desde_a_ultima_avaliacao": len(novos), "registros_anteriores": len(antigos)},
        "avaliacao_vigente": {
            "resumo": rel["resumo"], "caracteristicas": rel["caracteristicas"],
            "foco_prioritario": rel["foco_prioritario"],
            "metas": [{**{k: m[k] for k in ("id", "horizonte", "dominio", "texto", "prazo_semanas", "como_acompanhar", "gas")},
                       "checkins_gas": checkins.get(m["id"], [])} for m in rel["metas"]],
            "dicas": [{"titulo": x["titulo"], "dominio": x["dominio"]} for x in rel["dicas"]],
            "alertas": rel.get("alertas", []),
        },
        "estrategias_testadas": [{k: e[k] for k in ("estrategia", "local", "tentativas", "funcionou", "parcial", "nao_funcionou")}
                                 for e in repo.historico_estrategias(crianca_id)],
        "registros_desde_a_ultima_avaliacao": [linha_registro(r) for r in reversed(novos)],
        "registros_anteriores": [linha_registro(r) for r in reversed(antigos)],
        "alertas_calculados": novo["alertas_calculados"] if novo else [],
        "dominios": dominios,
        "_evidencias_validas": sorted(evid_validas),
        "_base_id": base["id"],
        "_formulario_novo_id": formulario_novo_id,
    }


def direcao(antes: str, depois: str) -> str:
    if antes == depois:
        return "igual"
    if antes in ORDEM_COR and depois in ORDEM_COR:
        return "melhorou" if ORDEM_COR[depois] > ORDEM_COR[antes] else "piorou"
    return "mudou"  # envolve cinza (informação insuficiente)


def comparar(base: dict, relatorio: dict, crianca_id: str) -> dict:
    """Comparação calculada em código entre o perfil vigente (base) e a nova proposta."""
    desde = base.get("aceita_em") or base["criado_em"]
    registros = repo.listar_registros(crianca_id, limite=1000)
    novos = [r for r in registros if r["ocorrido_em"] >= desde or r["criado_em"] >= desde]
    checkins = _checkins_por_meta(registros)
    antes = {d["codigo"]: d["status"] for d in base["perfil"]["relatorio"]["dominios"]}
    novas_metas = {m["id"] for m in relatorio["metas"]}
    por_tipo: dict[str, int] = {}
    for r in novos:
        por_tipo[r["tipo"]] = por_tipo.get(r["tipo"], 0) + 1
    return {
        "base_id": base["id"],
        "periodo": {"de": desde[:10], "ate": date.today().isoformat(),
                    "dias": (datetime.now().date() - date.fromisoformat(desde[:10])).days},
        "registros": {"total": len(novos), "por_tipo": por_tipo,
                      "por_responsavel": sum(1 for r in novos if r["autor"] != "professor"),
                      "por_professor": sum(1 for r in novos if r["autor"] == "professor")},
        "areas": [{"codigo": d["codigo"], "antes": antes.get(d["codigo"]), "depois": d["status"],
                   "direcao": direcao(antes.get(d["codigo"]), d["status"])} for d in relatorio["dominios"]],
        "metas": [{"id": m["id"], "texto": m["texto"], "horizonte": m["horizonte"], "dominio": m["dominio"],
                   "niveis": [c["nivel"] for c in checkins.get(m["id"], [])],
                   "ultimo_nivel": (checkins.get(m["id"]) or [{}])[-1].get("nivel"),
                   "continua": m["id"] in novas_metas}
                  for m in base["perfil"]["relatorio"]["metas"]],
    }


def validar_evolucao(rel: dict, dossie: dict) -> list[str]:
    """Regras extras da reavaliação: o balanço tem que bater com os dados."""
    erros: list[str] = []
    ev = rel.get("evolucao") or {}
    anteriores = {d["codigo"]: d["status_anterior"] for d in dossie["dominios"]}
    metas_antes = {m["id"]: m for m in dossie["avaliacao_vigente"]["metas"]}
    novas = {m["id"] for m in rel["metas"]}
    areas = {a["codigo"]: a for a in ev.get("areas", [])}

    for d in rel["dominios"]:
        cod, antes = d["codigo"], anteriores.get(d["codigo"])
        if antes and d["status"] != antes:
            if cod not in areas:
                erros.append(f"{cod}: a cor mudou ({antes} → {d['status']}); explique em `evolucao.areas`.")
            elif not areas[cod].get("evidencias") and not any(e["evidencias"] for e in d["pontos_fortes"] + d["pontos_de_atencao"]):
                erros.append(f"{cod}: mudança de cor sem evidência. Cite registros (reg:...) ou respostas (extra:...).")
    for cod in areas:
        if cod not in anteriores:
            erros.append(f"evolucao.areas: domínio desconhecido {cod}.")

    balanco = {b["meta_id"]: b for b in ev.get("metas_anteriores", [])}
    faltando = set(metas_antes) - set(balanco)
    if faltando:
        erros.append(f"evolucao.metas_anteriores: faça o balanço de todas as metas anteriores. Faltando: {sorted(faltando)}.")
    for mid, b in balanco.items():
        if mid not in metas_antes:
            erros.append(f"evolucao.metas_anteriores: meta desconhecida '{mid}'.")
            continue
        if b["destino"] in ("mantida", "ajustada") and mid not in novas:
            erros.append(f"meta {mid}: destino '{b['destino']}' exige manter o mesmo id em `metas`.")
        if b["destino"] in ("concluida", "substituida") and mid in novas:
            erros.append(f"meta {mid}: destino '{b['destino']}', mas o id continua em `metas`. Use um id novo para a meta nova.")
        niveis = [c["nivel"] for c in metas_antes[mid]["checkins_gas"] if c["nivel"] is not None]
        if b["situacao"] == "sem_dados" and niveis:
            erros.append(f"meta {mid}: há {len(niveis)} check-in(s) de progresso; a situação não é 'sem_dados'.")
        if b["situacao"] == "alcancada" and (not niveis or max(niveis) < 0) and not b.get("evidencias"):
            erros.append(f"meta {mid}: 'alcancada' sem check-in no nível 0 ou acima; cite a evidência (reg:/extra:).")
    return erros
