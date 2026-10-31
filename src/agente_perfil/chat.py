"""Chat do responsável/professor sobre uma criança.

Cada resposta recebe, no prompt de sistema:
  1. regras fixas do assistente;
  2. RESUMO ATIVO da criança, montado por código a partir do perfil vigente
     (semáforo, foco, metas + último check-in, dicas, estratégias que funcionaram ou não);
  3. os últimos registros do dia a dia em linhas compactas.
Ferramentas: `consultar_base_conhecimento` (RAG) e `buscar_registros` (SQL), para o que
não coube no contexto. O histórico da conversa vai como mensagens normais.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from src.agente_perfil import config, repositorio as repo
from src.agente_perfil.dossie import LEGENDA_STATUS, idade_por_extenso
from src.agente_perfil.ferramentas import BUSCAR_BASE, buscar_base
from src.agente_perfil.llm import ClienteFeatherless, ClienteLLM

logger = logging.getLogger(__name__)

NOMES = {"COM_R": "Compreensão", "COM_E": "Comunicação expressiva", "FAL": "Fala", "SOC": "Interação social",
         "BRI": "Brincadeira", "COG": "Cognição", "MOT_A": "Motor amplo", "MOT_F": "Motor fino",
         "AUT": "Autonomia", "REG": "Regulação", "ATE": "Atenção", "SEN": "Sensorial", "SAU": "Saúde", "CTX": "Contexto"}
MAX_PASSOS_CHAT = 5
MAX_BUSCAS_CHAT = 2
HISTORICO_MENSAGENS = 16
REGISTROS_NO_CONTEXTO = 15

SISTEMA_CHAT = """Você é o assistente da plataforma Primeiros Passos. Conversa com quem cuida de uma criança \
(o responsável pelo perfil ou um acompanhante: professor, pedagogo, médico, terapeuta, familiar) sobre o desenvolvimento e o dia a dia DESSA criança.

Você recebe abaixo o RESUMO ATIVO da criança (perfil aprovado pela família, metas, estratégias já testadas) e os \
REGISTROS RECENTES. Use-os sempre: personalize pelo nome, interesses e metas; não repita estratégias que já \
"não funcionaram" sem propor uma variação; lembre do que funcionou.

Ferramentas:
- `buscar_registros`: para perguntas sobre fatos antigos ou específicos ("quantas crises em outubro?", "o que a \
professora anotou sobre a fala?") que não estejam nos registros recentes.
- `consultar_base_conhecimento`: para fundamentar orientações em fontes oficiais (Caderneta da Criança, OMS, CDC…). \
Use quando a pergunta pedir orientação técnica ou algo fora do perfil. Cite a fonte de forma simples \
("segundo a Caderneta da Criança…") SOMENTE se a informação estiver no trecho retornado pela busca. Nunca atribua \
a um documento algo que não veio da busca; conhecimento geral você apresenta sem citar fonte.

Como responder:
- Português do Brasil, acolhedor, direto e prático. Respostas curtas (até ~180 palavras), com passos concretos \
encaixados na rotina quando for orientação. Use listas curtas e **negrito** com moderação.
- Comece validando a preocupação quando houver uma; termine, se fizer sentido, sugerindo registrar na plataforma o \
que acontecer (ex.: "registre como comportamento para vermos o padrão").
- NUNCA diagnostique nem sugira diagnóstico, idade mental ou escore. Condições relatadas pela família são relato.
- Sinais de alerta (perda de habilidades, convulsão, febre alta, risco à segurança, suspeita de violência, \
sofrimento intenso do cuidador) → oriente procurar serviço de saúde/rede de proteção sem demora.
- Se não souber ou a informação não estiver no perfil/registros, diga isso. Não invente fatos sobre a criança.
- Você não altera o perfil nem as metas; se o responsável quiser mudar algo, oriente usar "pedir ajuste" no perfil.
"""

BUSCAR_REGISTROS = {
    "type": "function",
    "function": {
        "name": "buscar_registros",
        "description": "Busca registros do dia a dia da criança (comportamento, atividade, conquista, saúde, observação, "
                       "progresso de meta, estratégia testada) por tipo, área, texto e período.",
        "parameters": {
            "type": "object",
            "properties": {
                "tipo": {"type": "string", "enum": ["atividade", "comportamento", "conquista", "observacao",
                                                    "checkin_meta", "feedback_estrategia", "saude"]},
                "dominio": {"type": "string", "enum": list(NOMES)},
                "texto": {"type": "string", "description": "Palavra a procurar no texto do registro"},
                "dias": {"type": "integer", "description": "Somente os últimos N dias (padrão: todos)"},
            },
        },
    },
}


# ------------------------------------------------------------------ contexto
def _linha_registro(r: dict) -> str:
    d = r.get("dados") or {}
    data = r["ocorrido_em"][:10]
    quem = (r.get("autor_funcao") or "acompanhante") if r.get("autor") == "professor" else "resp"
    base = f"[reg:{r['id'][:8]}] {data} {quem} {r['tipo']}"
    if r.get("local"):
        base += f" ({r['local']})"
    if r.get("dominios"):
        base += " " + ",".join(r["dominios"])
    if r["tipo"] == "comportamento":
        partes = [d.get("antecedente"), d.get("comportamento"), d.get("consequencia")]
        corpo = " → ".join(p for p in partes if p)
        if d.get("intensidade"):
            corpo += f" | intensidade {d['intensidade']}/5"
        if d.get("duracao_min") is not None:
            corpo += f" | {d['duracao_min']} min"
    elif r["tipo"] == "checkin_meta":
        corpo = f"meta {r.get('meta_id')} nível {d.get('nivel_gas')}"
    elif r["tipo"] == "saude":
        corpo = f"{d.get('categoria', '')} {d.get('profissional', '')}".strip()
    else:
        corpo = ""
    if r.get("estrategia"):
        corpo += f" | estratégia “{r['estrategia']}”: {r.get('resultado')}"
    extras = {k: v for k, v in d.items() if k in ("activity", "reaction", "support", "result", "nivel_ajuda", "engajamento") and v}
    if extras:
        corpo += " | " + "; ".join(f"{k}: {v}" for k, v in extras.items())
    texto = (r.get("texto") or "").replace("\n", " ")
    return f"{base}: {corpo} {('— ' + texto) if texto else ''}".strip()


def contexto_crianca(crianca_id: str) -> str:
    """Resumo ativo da criança, gerado por código (cabe em ~1.500 tokens)."""
    crianca = repo.obter_crianca(crianca_id)
    if not crianca:
        raise KeyError(f"Criança {crianca_id} não encontrada.")
    nasc = datetime.fromisoformat(crianca["data_nascimento"])
    hoje = datetime.now()
    meses = (hoje.year - nasc.year) * 12 + hoje.month - nasc.month - (hoje.day < nasc.day)
    linhas = [f"Criança: {crianca['nome']}, {idade_por_extenso(max(meses, 0))}."]
    if crianca.get("interesses"):
        linhas.append("Interesses: " + ", ".join(crianca["interesses"]) + ".")

    av = repo.avaliacao_vigente(crianca_id)
    if not av:
        proposta = repo.avaliacao_proposta(crianca_id)
        linhas.append("Ainda não há perfil aprovado" + (" (há uma proposta aguardando revisão da família)." if proposta else "."))
        form = repo.ultimo_formulario(crianca_id)
        if form:
            p = form["perfil"]
            linhas.append(f"Do formulário inicial: prioridades da família: {p.get('prioridades')}; "
                          f"interesses: {p.get('interesses') or '—'}; observações de saúde: {p.get('observacoes_saude') or '—'}.")
    else:
        rel = av["perfil"]["relatorio"]
        linhas.append(f"Perfil aprovado em {(av.get('aceita_em') or '')[:10]}. Resumo: {rel['resumo']}")
        linhas.append("Características: " + "; ".join(rel["caracteristicas"]))
        linhas.append("Semáforo: " + " · ".join(f"{NOMES.get(d['codigo'], d['codigo'])}={d['status']}" for d in rel["dominios"])
                      + f"  (legenda: {', '.join(f'{k}={v}' for k, v in LEGENDA_STATUS.items())})")
        for d in rel["dominios"]:
            if d["status"] in ("amarelo", "vermelho"):
                atencao = "; ".join(e["texto"] for e in d["pontos_de_atencao"][:2])
                linhas.append(f"  - {NOMES.get(d['codigo'])}: {d['justificativa_status']} Próximos passos: {atencao}")
        linhas.append("Foco prioritário: " + " | ".join(f"{NOMES.get(f['dominio'])}: {f['por_que']}" for f in rel["foco_prioritario"]))

        checkins: dict[str, dict] = {}
        for r in repo.listar_registros(crianca_id, tipo="checkin_meta", limite=100):
            checkins.setdefault(r["meta_id"], r)  # já vem do mais recente
        linhas.append("Metas ativas:")
        for m in rel["metas"]:
            ult = checkins.get(m["id"])
            prog = f"último check-in {ult['ocorrido_em'][:10]}: nível {ult['dados'].get('nivel_gas')}" if ult else "sem check-in ainda"
            linhas.append(f"  - [{m['id']}·{m['horizonte']}·{NOMES.get(m['dominio'])}] {m['texto']} ({prog}; alvo: {m['gas']['zero']})")
        linhas.append("Dicas do plano: " + " | ".join(f"“{d['titulo']}” ({NOMES.get(d['dominio'])})" for d in rel["dicas"]))
        if rel.get("alertas"):
            linhas.append("Alertas do perfil: " + " | ".join(a["recomendacao"] for a in rel["alertas"]))

    estrategias = repo.historico_estrategias(crianca_id)
    if estrategias:
        linhas.append("Estratégias já testadas (funcionou/parcial/não): " + " | ".join(
            f"“{e['estrategia']}” em {e['local'] or '—'}: {e['funcionou']}/{e['parcial']}/{e['nao_funcionou']}" for e in estrategias[:10]))

    recentes = repo.listar_registros(crianca_id, limite=REGISTROS_NO_CONTEXTO)
    total_semana = len(repo.listar_registros(crianca_id, desde=(datetime.now(timezone.utc) - timedelta(days=7)).isoformat()))
    linhas.append(f"\nREGISTROS RECENTES ({len(recentes)} mais novos; {total_semana} nos últimos 7 dias):")
    linhas.extend(_linha_registro(r) for r in recentes) if recentes else linhas.append("(nenhum registro ainda)")
    return "\n".join(linhas)


# ------------------------------------------------------------------ loop
def responder(crianca_id: str, texto: str, autor: str, autor_id: str, conversa_id: str | None = None,
              llm: ClienteLLM | None = None) -> dict:
    texto = texto.strip()
    if not texto:
        raise ValueError("Mensagem vazia.")
    if conversa_id:
        conversa = repo.obter_conversa(conversa_id)
        if not conversa or conversa["crianca_id"] != crianca_id:
            raise KeyError("Conversa não encontrada.")
    else:
        conversa = repo.criar_conversa(crianca_id, autor, autor_id, titulo=texto[:60])

    historico = repo.listar_mensagens(conversa["id"], limite=HISTORICO_MENSAGENS)
    msg_usuario = repo.inserir_mensagem(conversa["id"], "usuario", texto)

    if autor == "professor":
        prof = repo.obter_professor(autor_id) or {}
        funcao = next((c["funcao"] for c in repo.listar_compartilhamentos(crianca_id) if c["professor_id"] == autor_id),
                      prof.get("funcao", "acompanhante"))
        quem = (f"{prof.get('nome', '')}, acompanhante da criança (função: {funcao}). Pode registrar observações, mas "
                "não altera perfil nem metas; o progresso das metas é registrado pelo responsável")
    else:
        quem = "o(a) responsável pelo perfil"
    mensagens = [{"role": "system", "content": f"{SISTEMA_CHAT}\nQuem está conversando agora: {quem}.\n"
                                                f"Data de hoje: {datetime.now().strftime('%d/%m/%Y')}.\n\n"
                                                f"=== RESUMO ATIVO DA CRIANÇA ===\n{contexto_crianca(crianca_id)}"}]
    mensagens += [{"role": "user" if m["papel"] == "usuario" else "assistant", "content": m["conteudo"]} for m in historico]
    mensagens.append({"role": "user", "content": texto})

    llm = llm or ClienteFeatherless()
    fontes: dict[str, dict] = {}
    ferramentas_usadas: list[str] = []
    buscas = 0
    resposta_final = None
    for passo in range(MAX_PASSOS_CHAT):
        tools = [BUSCAR_REGISTROS]
        if not config.RAG_DESATIVADO and buscas < MAX_BUSCAS_CHAT:
            tools.append(BUSCAR_BASE)
        if passo == MAX_PASSOS_CHAT - 1:
            tools = []  # último passo: obriga a responder
        r = llm.completar(mensagens, tools)
        r.pop("uso", None)
        mensagens.append(r)
        chamadas = r.get("tool_calls") or []
        if not chamadas:
            resposta_final = (r.get("content") or "").strip()
            break
        for tc in chamadas:
            nome = tc["function"]["name"]
            try:
                args = json.loads(tc["function"]["arguments"] or "{}")
            except json.JSONDecodeError:
                args = {}
            if nome == "consultar_base_conhecimento" and buscas < MAX_BUSCAS_CHAT:
                buscas += 1
                ferramentas_usadas.append(f"base: {args.get('consulta', '')}")
                resultado, novas = buscar_base(args.get("consulta", ""), len(fontes) + 1, top_k=3)
                fontes.update(novas)
            elif nome == "buscar_registros":
                ferramentas_usadas.append("registros: " + ", ".join(f"{k}={v}" for k, v in args.items()))
                desde = None
                if args.get("dias"):
                    desde = (datetime.now(timezone.utc) - timedelta(days=int(args["dias"]))).isoformat()
                regs = repo.listar_registros(crianca_id, tipo=args.get("tipo"), dominio=args.get("dominio"),
                                             texto=args.get("texto"), desde=desde, limite=40)
                resultado = "\n".join(_linha_registro(x) for x in regs) or "Nenhum registro encontrado com esses filtros."
            else:
                resultado = "Ferramenta indisponível agora."
            mensagens.append({"role": "tool", "tool_call_id": tc["id"], "content": resultado})

    if not resposta_final:
        resposta_final = "Desculpe, não consegui formular uma resposta agora. Pode reformular a pergunta?"
    msg_assistente = repo.inserir_mensagem(conversa["id"], "assistente", resposta_final, {
        "fontes": [{"id": k, "documento": v["documento"], "secao": v["secao"]} for k, v in fontes.items()],
        "ferramentas": ferramentas_usadas,
    })
    return {"conversa": repo.obter_conversa(conversa["id"]), "mensagem_usuario": msg_usuario, "mensagem_assistente": msg_assistente}
