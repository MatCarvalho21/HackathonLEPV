"""Loop agêntico do mapeamento de perfil.

Fluxo:
  formulário ──código──▶ dossiê ──▶ [modelo ⇄ ferramentas] ──▶ entregar_relatorio ──código──▶ validação
                                         │                                                 │ erro → volta ao modelo
                                         └─ solicitar_informacoes_responsavel → PAUSA       └─ ok → avaliacao 'proposta'
                                            (responsável responde → retomar())

Toda a conversa com o modelo fica em `sessao["mensagens"]`, o que permite pausar,
retomar e auditar cada passo (quais buscas fez, o que perguntou, por que errou).
"""
from __future__ import annotations

import json
import logging
from uuid import uuid4

from src.agente_perfil import config, repositorio as repo
from src.agente_perfil.dossie import CONTEXTUAIS, POR_IDADE, dossie_para_prompt, montar_dossie
from src.agente_perfil.ferramentas import buscar_base, ferramentas_disponiveis
from src.agente_perfil.llm import ClienteFeatherless, ClienteLLM
from src.agente_perfil.prompts import (SISTEMA, SISTEMA_REAVALIACAO, mensagem_ajuste, mensagem_inicial,
                                      mensagem_reavaliacao)
from src.agente_perfil.reavaliacao import comparar, montar_dossie_reavaliacao, validar_evolucao
from src.agente_perfil.relatorio import Relatorio, RelatorioReavaliacao, validar

logger = logging.getLogger(__name__)
VERSAO_AGENTE = "perfil-v1"


class ErroAgente(Exception):
    pass


# ------------------------------------------------------------------ API pública
# preparar_* são rápidas: montam e salvam a sessão ('executando'). executar() roda o loop
# (1-2 min) e pode ir para uma thread; o frontend acompanha por GET /sessoes/{id}.

INSTRUCAO_DEMO = ("MODO DEMONSTRAÇÃO: antes de entregar o relatório, faça obrigatoriamente UMA rodada de "
                  "`solicitar_informacoes_responsavel` com 1 a 3 perguntas sobre as lacunas mais relevantes do dossiê.")


def preparar_inicio(formulario_id: str, demo: bool = False) -> dict:
    formulario = repo.obter_formulario(formulario_id)
    if formulario is None:
        raise KeyError(f"Formulário {formulario_id} não encontrado.")
    dossie = montar_dossie(formulario)
    conteudo = mensagem_inicial(dossie_para_prompt(dossie))
    if demo:
        conteudo += "\n\n" + INSTRUCAO_DEMO
    sessao = _nova_sessao(formulario, dossie, [
        {"role": "system", "content": SISTEMA},
        {"role": "user", "content": conteudo},
    ])
    _evento(sessao, "Li o formulário e calculei o semáforo dos domínios por idade.")
    repo.salvar_sessao(sessao)
    return sessao


def preparar_retomada(sessao_id: str, respostas: dict[str, str]) -> dict:
    """Recebe as respostas do responsável ({id_pergunta: texto}; vazio = não respondeu)."""
    sessao = repo.obter_sessao(sessao_id)
    if sessao is None:
        raise KeyError(f"Sessão {sessao_id} não encontrada.")
    if sessao["status"] != "aguardando_responsavel":
        raise ErroAgente(f"A sessão não está aguardando respostas (status: {sessao['status']}).")
    pendente = sessao.pop("perguntas_pendentes")
    itens = []
    for p in pendente["perguntas"]:
        texto = (respostas.get(p["id"]) or "").strip()
        evid = f"extra:{p['id']}"
        itens.append({"evidencia": evid, "dominio": p["dominio"], "pergunta": p["pergunta"],
                      "resposta": texto or "(o responsável não respondeu)"})
        if texto:
            sessao["respostas_extras"][evid] = {"dominio": p["dominio"], "pergunta": p["pergunta"], "resposta": texto}
    sessao["mensagens"].append({"role": "tool", "tool_call_id": pendente["tool_call_id"],
                                "content": json.dumps({"respostas": itens}, ensure_ascii=False)})
    sessao["status"] = "executando"
    _evento(sessao, f"Recebi suas respostas ({sum(1 for i in itens if 'não respondeu' not in i['resposta'])} de {len(itens)}).")
    repo.salvar_sessao(sessao)
    return sessao


def preparar_reavaliacao(crianca_id: str, comentario: str | None = None, formulario_id: str | None = None) -> dict:
    """Nova versão do perfil a partir do vigente + todos os registros desde então (+ formulário atualizado, opcional)."""
    base = repo.avaliacao_vigente(crianca_id)
    if base is None:
        raise ErroAgente("A reavaliação parte de um perfil aprovado.")
    sessao = _sessao_reavaliacao(base, comentario, [], formulario_id)
    n = sessao["dossie"]["periodo"]["registros_desde_a_ultima_avaliacao"]
    _evento(sessao, f"Reuni o perfil vigente e {n} registro(s) feitos desde a última avaliação.")
    if formulario_id:
        _evento(sessao, "Recalculei as cores das áreas por idade com o formulário atualizado.")
    repo.salvar_sessao(sessao)
    return sessao


def _sessao_reavaliacao(base: dict, comentario: str | None, mensagens_extras: list[dict],
                        formulario_id: str | None = None) -> dict:
    dossie = montar_dossie_reavaliacao(base["crianca_id"], base, comentario, formulario_id)
    formulario = repo.obter_formulario(formulario_id or base["formulario_id"])
    sessao = _nova_sessao(formulario, dossie, [
        {"role": "system", "content": SISTEMA_REAVALIACAO},
        {"role": "user", "content": mensagem_reavaliacao(dossie_para_prompt(dossie))},
        *mensagens_extras,
    ])
    sessao.update(tipo="reavaliacao", reavaliacao={"base_id": base["id"], "pedido": comentario,
                                                   "formulario_id": formulario_id})
    if comentario:
        sessao["respostas_extras"]["extra:pedido"] = {"dominio": None, "pergunta": "Pedido ao solicitar a reavaliação",
                                                      "resposta": comentario}
    return sessao


def preparar_ajuste(avaliacao_id: str, comentario: str) -> dict:
    """O responsável pediu ajustes numa proposta: nova sessão que gera versão ligada à anterior."""
    anterior = repo.obter_avaliacao(avaliacao_id)
    if anterior is None:
        raise KeyError(f"Avaliação {avaliacao_id} não encontrada.")
    if anterior["status"] != "proposta":
        raise ErroAgente("Só é possível ajustar uma proposta ainda não aprovada.")
    relatorio_anterior = anterior["perfil"]["relatorio"]
    pedido_ajuste = {"role": "user", "content": mensagem_ajuste(json.dumps(relatorio_anterior, ensure_ascii=False), comentario)}
    if anterior["tipo"] == "reavaliacao":
        base = repo.obter_avaliacao(anterior["perfil"]["reavaliacao"]["base_id"])
        if not base or base["status"] != "vigente":
            raise ErroAgente("O perfil usado como base desta reavaliação não está mais vigente.")
        sessao = _sessao_reavaliacao(base, anterior["perfil"]["reavaliacao"].get("pedido"), [pedido_ajuste],
                                     anterior["perfil"]["reavaliacao"].get("formulario_id"))
    else:
        formulario = repo.obter_formulario(anterior["formulario_id"])
        dossie = montar_dossie(formulario)
        sessao = _nova_sessao(formulario, dossie, [
            {"role": "system", "content": SISTEMA},
            {"role": "user", "content": mensagem_inicial(dossie_para_prompt(dossie))},
            pedido_ajuste,
        ])
    sessao.update(avaliacao_anterior_id=avaliacao_id, comentario_responsavel=comentario,
                  fontes_kb=anterior["perfil"].get("fontes", {}),
                  respostas_extras={**sessao["respostas_extras"], **anterior["perfil"].get("respostas_complementares", {}),
                                    "extra:ajuste": {"dominio": None, "pergunta": "Pedido de ajuste", "resposta": comentario}},
                  rodadas_perguntas=config.MAX_RODADAS_PERGUNTAS)  # no ajuste não volta a perguntar
    _evento(sessao, "Recebi seu pedido de ajuste e reabri a proposta anterior.")
    repo.salvar_sessao(sessao)
    return sessao


def executar(sessao: dict, llm: ClienteLLM | None = None) -> dict:
    resultado = _executar(sessao, llm)
    if resultado["status"] == "concluida" and sessao.get("avaliacao_anterior_id"):
        repo.atualizar_status_avaliacao(sessao["avaliacao_anterior_id"], "descartada")
    return resultado


# Atalhos síncronos (CLI e testes)
def iniciar(formulario_id: str, llm: ClienteLLM | None = None, demo: bool = False) -> dict:
    return executar(preparar_inicio(formulario_id, demo), llm)


def retomar(sessao_id: str, respostas: dict[str, str], llm: ClienteLLM | None = None) -> dict:
    return executar(preparar_retomada(sessao_id, respostas), llm)


def ajustar(avaliacao_id: str, comentario: str, llm: ClienteLLM | None = None) -> dict:
    return executar(preparar_ajuste(avaliacao_id, comentario), llm)


def resumo_sessao(sessao: dict) -> dict:
    """O que a API devolve ao frontend (sem o histórico completo)."""
    out = {"sessao_id": sessao["id"], "formulario_id": sessao["formulario_id"], "crianca_id": sessao.get("crianca_id"),
           "status": sessao["status"],
           "passos": sessao["passos"], "buscas_feitas": sessao["buscas_feitas"], "uso_tokens": sessao["uso_tokens"],
           "eventos": sessao.get("eventos", []), "avaliacao_anterior_id": sessao.get("avaliacao_anterior_id"),
           "tipo": sessao.get("tipo", "inicial")}
    if sessao["status"] == "aguardando_responsavel":
        p = sessao["perguntas_pendentes"]
        out["motivo"] = p["motivo"]
        out["perguntas"] = p["perguntas"]
    if sessao["status"] == "concluida":
        out["avaliacao_id"] = sessao["avaliacao_id"]
        out["avaliacao"] = repo.obter_avaliacao(sessao["avaliacao_id"])
    if sessao["status"] == "erro":
        out["erro"] = sessao["erro"]
    return out


# ------------------------------------------------------------------ internos
def _nova_sessao(formulario: dict, dossie: dict, mensagens: list[dict]) -> dict:
    return {
        "id": str(uuid4()), "formulario_id": formulario["id"], "crianca_id": formulario.get("crianca_id"),
        "status": "executando",
        "criado_em": repo.agora(), "versao_agente": VERSAO_AGENTE, "modelo": config.MODELO,
        "dossie": dossie, "mensagens": mensagens,
        "passos": 0, "buscas_feitas": 0, "rodadas_perguntas": 0, "tentativas_validacao": 0,
        "fontes_kb": {}, "respostas_extras": {}, "ajustes_automaticos": [], "eventos": [],
        "uso_tokens": {"prompt": 0, "completion": 0}, "tipo": "inicial", "reavaliacao": None,
        "avaliacao_anterior_id": None, "comentario_responsavel": None, "avaliacao_id": None, "erro": None,
    }


def _evento(sessao: dict, texto: str) -> None:
    sessao.setdefault("eventos", []).append({"em": repo.agora(), "texto": texto})


def _executar(sessao: dict, llm: ClienteLLM | None) -> dict:
    sessao["status"] = "executando"
    try:
        llm = llm or ClienteFeatherless()
        while sessao["passos"] < config.MAX_PASSOS:
            _evento(sessao, "Analisando as informações…" if sessao["passos"] == 0 else "Pensando no próximo passo…")
            repo.salvar_sessao(sessao)
            tools = ferramentas_disponiveis(sessao["buscas_feitas"], sessao["rodadas_perguntas"],
                                            reavaliacao=sessao.get("tipo") == "reavaliacao")
            resposta = llm.completar(sessao["mensagens"], tools)
            sessao["passos"] += 1
            uso = resposta.pop("uso", {}) or {}
            sessao["uso_tokens"]["prompt"] += uso.get("prompt_tokens") or 0
            sessao["uso_tokens"]["completion"] += uso.get("completion_tokens") or 0
            sessao["mensagens"].append(resposta)
            logger.info("passo %s: %s", sessao["passos"],
                        [tc["function"]["name"] for tc in resposta.get("tool_calls", [])] or "texto")

            chamadas = resposta.get("tool_calls") or []
            if not chamadas:
                if uso.get("finish_reason") == "length":
                    aviso = "Sua resposta foi cortada por tamanho. Seja mais conciso e entregue"
                else:
                    aviso = "Não responda em texto livre. Entregue"
                sessao["mensagens"].append({"role": "user", "content":
                                            f"{aviso} o relatório chamando a ferramenta `entregar_relatorio`."})
                continue

            pausa = None
            for tc in chamadas:
                retorno, pausa_tc, concluiu = _tratar_chamada(sessao, tc)
                if pausa_tc:
                    pausa = pausa_tc
                    continue  # a resposta desta chamada só existe quando o responsável responder
                sessao["mensagens"].append({"role": "tool", "tool_call_id": tc["id"], "content": retorno})
                repo.salvar_sessao(sessao)
                if concluiu:
                    _evento(sessao, "Relatório validado e salvo como proposta.")
                    sessao["status"] = "concluida"
                    repo.salvar_sessao(sessao)
                    return resumo_sessao(sessao)
            if pausa:
                sessao["status"] = "aguardando_responsavel"
                sessao["perguntas_pendentes"] = pausa
                sessao["rodadas_perguntas"] += 1
                _evento(sessao, f"Preciso de mais informações: {len(pausa['perguntas'])} pergunta(s) para você.")
                repo.salvar_sessao(sessao)
                return resumo_sessao(sessao)
            if sessao["tentativas_validacao"] >= config.MAX_TENTATIVAS_VALIDACAO:
                raise ErroAgente("O relatório não passou na validação após várias tentativas.")
        raise ErroAgente(f"Limite de {config.MAX_PASSOS} passos atingido sem relatório.")
    except Exception as e:
        logger.exception("Falha no agente")
        sessao["status"] = "erro"
        sessao["erro"] = f"{type(e).__name__}: {e}"
        repo.salvar_sessao(sessao)
        return resumo_sessao(sessao)


def _tratar_chamada(sessao: dict, tc: dict) -> tuple[str, dict | None, bool]:
    """Executa uma chamada de ferramenta. Devolve (resultado, pausa, concluiu)."""
    nome = tc["function"]["name"]
    try:
        args = json.loads(tc["function"]["arguments"] or "{}")
    except json.JSONDecodeError as e:
        if nome == "entregar_relatorio":
            sessao["tentativas_validacao"] += 1
        return f"Erro: argumentos não são JSON válido ({e}). Envie de novo.", None, False

    if nome == "consultar_base_conhecimento":
        if sessao["buscas_feitas"] >= config.MAX_BUSCAS_RAG or config.RAG_DESATIVADO:
            return "Limite de buscas atingido. Siga com o que já tem.", None, False
        sessao["buscas_feitas"] += 1
        _evento(sessao, f"Consultando a base de conhecimento: “{args.get('consulta', '')}”")
        proximo = len(sessao["fontes_kb"]) + 1
        texto, fontes = buscar_base(args.get("consulta", ""), proximo)
        sessao["fontes_kb"].update(fontes)
        docs = sorted({f["documento"] for f in fontes.values()})
        _evento(sessao, f"Encontrei {len(fontes)} trecho(s) relevantes em {', '.join(docs)}." if docs
                else "Nada relevante na base para essa busca; sigo sem citar fonte.")
        return texto, None, False

    if nome == "solicitar_informacoes_responsavel":
        if sessao["rodadas_perguntas"] >= config.MAX_RODADAS_PERGUNTAS:
            return "Não é possível fazer novas perguntas agora. Entregue o relatório com o que tem e registre as lacunas em `limitacoes`.", None, False
        perguntas = [p for p in args.get("perguntas", []) if p.get("pergunta")][:config.MAX_PERGUNTAS_POR_RODADA]
        if not perguntas:
            return "Erro: nenhuma pergunta válida.", None, False
        for i, p in enumerate(perguntas, 1):
            p["id"] = f"r{sessao['rodadas_perguntas'] + 1}q{i}"  # ids únicos entre rodadas
        return "", {"tool_call_id": tc["id"], "motivo": args.get("motivo", ""), "perguntas": perguntas}, False

    if nome == "entregar_relatorio":
        _evento(sessao, "Escrevi o relatório; conferindo regras, evidências e linguagem.")
        dados = args.get("relatorio", args) if isinstance(args.get("relatorio"), dict) else args
        _correcoes_automaticas(sessao, dados)
        reav = sessao.get("tipo") == "reavaliacao"
        rel, erros = validar(dados, sessao["dossie"], set(sessao["respostas_extras"]), set(sessao["fontes_kb"]),
                             modelo=RelatorioReavaliacao if reav else Relatorio)
        if rel is not None and reav:
            erros = validar_evolucao(rel.model_dump(), sessao["dossie"])
        if erros:
            sessao["tentativas_validacao"] += 1
            _evento(sessao, f"Revisão automática encontrou {len(erros)} ponto(s) a corrigir; reescrevendo.")
            return ("O relatório NÃO foi aceito. Corrija estes pontos e chame `entregar_relatorio` de novo com o "
                    "relatório completo:\n- " + "\n- ".join(erros)), None, False
        sessao["avaliacao_id"] = _salvar_avaliacao(sessao, rel.model_dump())
        return "Relatório aceito.", None, True

    return f"Ferramenta desconhecida: {nome}", None, False


def _correcoes_automaticas(sessao: dict, dados: dict) -> None:
    """Corrige em código o que é regra (cores calculadas) e remove evidências inventadas."""
    calculado = {d["codigo"]: d["status_calculado"] for d in sessao["dossie"]["dominios"]}
    validas = set(sessao["dossie"]["_evidencias_validas"]) | set(sessao["respostas_extras"]) | set(sessao["fontes_kb"])
    for d in dados.get("dominios") or []:
        if not isinstance(d, dict):
            continue
        cod = d.get("codigo")
        if (cod in POR_IDADE or cod in CONTEXTUAIS) and calculado.get(cod) and d.get("status") != calculado.get(cod):
            sessao["ajustes_automaticos"].append(f"{cod}: status {d.get('status')} → {calculado[cod]}")
            d["status"] = calculado[cod]
        for campo in ("pontos_fortes", "pontos_de_atencao"):
            for e in d.get(campo) or []:
                if isinstance(e, dict) and isinstance(e.get("evidencias"), list):
                    invalidas = [x for x in e["evidencias"] if x not in validas]
                    if invalidas:
                        sessao["ajustes_automaticos"].append(f"{cod}: evidências removidas {invalidas}")
                        e["evidencias"] = [x for x in e["evidencias"] if x in validas]
    for dica in dados.get("dicas") or []:
        if isinstance(dica, dict) and isinstance(dica.get("fontes"), list):
            dica["fontes"] = [f for f in dica["fontes"] if f in sessao["fontes_kb"]]
    ev = dados.get("evolucao")
    if sessao.get("tipo") == "reavaliacao" and isinstance(ev, dict):
        # "antes" é fato (perfil vigente) e "depois" é a cor desta proposta: o código preenche.
        antes = {d["codigo"]: d["status_anterior"] for d in sessao["dossie"]["dominios"]}
        depois = {d.get("codigo"): d.get("status") for d in dados.get("dominios") or [] if isinstance(d, dict)}
        for a in ev.get("areas") or []:
            if isinstance(a, dict) and a.get("codigo") in antes:
                a["antes"], a["depois"] = antes[a["codigo"]], depois.get(a["codigo"], a.get("depois"))
        for item in [*(ev.get("conquistas") or []), *(ev.get("areas") or []), *(ev.get("metas_anteriores") or [])]:
            if isinstance(item, dict) and isinstance(item.get("evidencias"), list):
                invalidas = [x for x in item["evidencias"] if x not in validas]
                if invalidas:
                    sessao["ajustes_automaticos"].append(f"evolução: evidências removidas {invalidas}")
                    item["evidencias"] = [x for x in item["evidencias"] if x in validas]


def _salvar_avaliacao(sessao: dict, relatorio: dict) -> str:
    formulario = repo.obter_formulario(sessao["formulario_id"])
    citadas = {f for d in relatorio["dicas"] for f in d["fontes"]}
    citadas |= {ev for d in relatorio["dominios"] for e in d["pontos_fortes"] + d["pontos_de_atencao"]
                for ev in e["evidencias"] if ev.startswith("kb:")}
    av = {
        "id": str(uuid4()),
        "crianca_id": formulario["crianca_id"],
        "formulario_id": sessao["formulario_id"],
        "sessao_id": sessao["id"],
        "avaliacao_anterior_id": sessao["avaliacao_anterior_id"],
        "tipo": sessao.get("tipo", "inicial"),
        "status": "proposta",
        "respostas_formulario": {
            **{q["id"]: q["resposta"] for d in formulario["dominios"] for q in d["perguntas"]},
            **{k: v["resposta"] for k, v in sessao["respostas_extras"].items()},
        },
        "perfil": {
            "relatorio": relatorio,
            "fontes": {k: v for k, v in sessao["fontes_kb"].items() if k in citadas},
            "respostas_complementares": sessao["respostas_extras"],
            "gerado_por": {"agente": VERSAO_AGENTE, "modelo": sessao["modelo"], "sessao_id": sessao["id"],
                           "ajustes_automaticos": sessao["ajustes_automaticos"]},
            **({"reavaliacao": {**comparar(repo.obter_avaliacao(sessao["reavaliacao"]["base_id"]), relatorio, formulario["crianca_id"]),
                                "pedido": sessao["reavaliacao"].get("pedido"),
                                "formulario_id": sessao["reavaliacao"].get("formulario_id"),
                                "formulario_atualizado": bool(sessao["reavaliacao"].get("formulario_id"))}}
               if sessao.get("tipo") == "reavaliacao" else {}),
        },
        "niveis": {d["codigo"]: d["status"] for d in relatorio["dominios"]},
        "metas": relatorio["metas"],
        "comentario_responsavel": sessao["comentario_responsavel"],
        "criado_em": repo.agora(),
    }
    repo.inserir_avaliacao(av)
    return av["id"]
