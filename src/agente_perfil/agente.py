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
from src.agente_perfil.prompts import SISTEMA, mensagem_ajuste, mensagem_inicial
from src.agente_perfil.relatorio import validar

logger = logging.getLogger(__name__)
VERSAO_AGENTE = "perfil-v1"


class ErroAgente(Exception):
    pass


# ------------------------------------------------------------------ API pública
def iniciar(formulario_id: str, llm: ClienteLLM | None = None) -> dict:
    formulario = repo.obter_formulario(formulario_id)
    if formulario is None:
        raise KeyError(f"Formulário {formulario_id} não encontrado.")
    dossie = montar_dossie(formulario)
    sessao = _nova_sessao(formulario, dossie, [
        {"role": "system", "content": SISTEMA},
        {"role": "user", "content": mensagem_inicial(dossie_para_prompt(dossie))},
    ])
    return _executar(sessao, llm)


def retomar(sessao_id: str, respostas: dict[str, str], llm: ClienteLLM | None = None) -> dict:
    """Recebe as respostas do responsável ({id_pergunta: texto}; vazio = não respondeu) e continua o loop."""
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
    return _executar(sessao, llm)


def ajustar(avaliacao_id: str, comentario: str, llm: ClienteLLM | None = None) -> dict:
    """O responsável pediu ajustes numa proposta: gera nova versão ligada à anterior."""
    anterior = repo.obter_avaliacao(avaliacao_id)
    if anterior is None:
        raise KeyError(f"Avaliação {avaliacao_id} não encontrada.")
    if anterior["status"] != "proposta":
        raise ErroAgente("Só é possível ajustar uma proposta ainda não aprovada.")
    formulario = repo.obter_formulario(anterior["formulario_id"])
    dossie = montar_dossie(formulario)
    relatorio_anterior = anterior["perfil"]["relatorio"]
    sessao = _nova_sessao(formulario, dossie, [
        {"role": "system", "content": SISTEMA},
        {"role": "user", "content": mensagem_inicial(dossie_para_prompt(dossie))},
        {"role": "user", "content": mensagem_ajuste(json.dumps(relatorio_anterior, ensure_ascii=False), comentario)},
    ])
    sessao.update(avaliacao_anterior_id=avaliacao_id, comentario_responsavel=comentario,
                  fontes_kb=anterior["perfil"].get("fontes", {}),
                  respostas_extras={**anterior["perfil"].get("respostas_complementares", {}),
                                    "extra:ajuste": {"dominio": None, "pergunta": "Pedido de ajuste", "resposta": comentario}},
                  rodadas_perguntas=config.MAX_RODADAS_PERGUNTAS)  # no ajuste não volta a perguntar
    resultado = _executar(sessao, llm)
    if resultado["status"] == "concluida":
        repo.atualizar_status_avaliacao(avaliacao_id, "descartada")
    return resultado


def resumo_sessao(sessao: dict) -> dict:
    """O que a API devolve ao frontend (sem o histórico completo)."""
    out = {"sessao_id": sessao["id"], "formulario_id": sessao["formulario_id"], "status": sessao["status"],
           "passos": sessao["passos"], "buscas_feitas": sessao["buscas_feitas"], "uso_tokens": sessao["uso_tokens"]}
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
        "id": str(uuid4()), "formulario_id": formulario["id"], "status": "executando",
        "criado_em": repo.agora(), "versao_agente": VERSAO_AGENTE, "modelo": config.MODELO,
        "dossie": dossie, "mensagens": mensagens,
        "passos": 0, "buscas_feitas": 0, "rodadas_perguntas": 0, "tentativas_validacao": 0,
        "fontes_kb": {}, "respostas_extras": {}, "ajustes_automaticos": [],
        "uso_tokens": {"prompt": 0, "completion": 0},
        "avaliacao_anterior_id": None, "comentario_responsavel": None, "avaliacao_id": None, "erro": None,
    }


def _executar(sessao: dict, llm: ClienteLLM | None) -> dict:
    llm = llm or ClienteFeatherless()
    sessao["status"] = "executando"
    try:
        while sessao["passos"] < config.MAX_PASSOS:
            tools = ferramentas_disponiveis(sessao["buscas_feitas"], sessao["rodadas_perguntas"])
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
                if concluiu:
                    sessao["status"] = "concluida"
                    repo.salvar_sessao(sessao)
                    return resumo_sessao(sessao)
            if pausa:
                sessao["status"] = "aguardando_responsavel"
                sessao["perguntas_pendentes"] = pausa
                sessao["rodadas_perguntas"] += 1
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
        proximo = len(sessao["fontes_kb"]) + 1
        texto, fontes = buscar_base(args.get("consulta", ""), proximo)
        sessao["fontes_kb"].update(fontes)
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
        dados = args.get("relatorio", args) if isinstance(args.get("relatorio"), dict) else args
        _correcoes_automaticas(sessao, dados)
        rel, erros = validar(dados, sessao["dossie"], set(sessao["respostas_extras"]), set(sessao["fontes_kb"]))
        if erros:
            sessao["tentativas_validacao"] += 1
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
        if (cod in POR_IDADE or cod in CONTEXTUAIS) and d.get("status") != calculado.get(cod):
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


def _salvar_avaliacao(sessao: dict, relatorio: dict) -> str:
    formulario = repo.obter_formulario(sessao["formulario_id"])
    citadas = {f for d in relatorio["dicas"] for f in d["fontes"]}
    citadas |= {ev for d in relatorio["dominios"] for e in d["pontos_fortes"] + d["pontos_de_atencao"]
                for ev in e["evidencias"] if ev.startswith("kb:")}
    av = {
        "id": str(uuid4()),
        "crianca_id": None,  # ainda não há tabela crianca no MVP local
        "formulario_id": sessao["formulario_id"],
        "sessao_id": sessao["id"],
        "avaliacao_anterior_id": sessao["avaliacao_anterior_id"],
        "tipo": "inicial",
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
        },
        "niveis": {d["codigo"]: d["status"] for d in relatorio["dominios"]},
        "metas": relatorio["metas"],
        "comentario_responsavel": sessao["comentario_responsavel"],
        "criado_em": repo.agora(),
    }
    repo.inserir_avaliacao(av)
    return av["id"]
