"""Rotas da plataforma: crianças, painel, registros, chat com IA, canal, compartilhamento, PDF e demonstração.

Todas exigem login (`Authorization: Bearer <token>`, ver backend/auth.py). Quem age e o papel dele
em cada criança vêm do token, nunca do corpo da requisição.

Crianças         GET  /api/eu/criancas?papel=responsavel|professor · POST /api/criancas
                 GET  /api/criancas/{id}/estado · GET /api/criancas/{id}/painel
                 GET  /api/criancas/{id}/formulario-atual · GET /api/criancas/{id}/resumo.pdf
Registros        GET|POST /api/criancas/{id}/registros
Chat (IA)        GET  /api/criancas/{id}/conversas · GET /api/conversas/{id}/mensagens · POST /api/criancas/{id}/chat
Canal            GET|POST /api/criancas/{id}/canal  (responsável ↔ acompanhantes)
Compartilhar     GET|POST /api/criancas/{id}/compartilhamentos · DELETE /api/compartilhamentos/{id}
                 GET  /api/eu/convites · POST /api/compartilhamentos/{id}/aceitar|recusar
Reavaliação      POST /api/criancas/{id}/reavaliacoes {comentario?, formulario_id?} → 202 {sessao_id}
Demo             POST /api/demo/entrar · POST /api/demo/entrar-professor (devolvem sessão de login)
                 GET  /api/demo/formulario-exemplo

Papéis:
- RESPONSÁVEL pelo perfil (mãe, pai, avó, tutor legal...): tudo — formulário, agente, ajustes,
  aprovação, reavaliação, progresso de metas, saúde, compartilhar e revogar acesso.
- ACOMPANHANTE (professor, pedagogo, médico, terapeuta, familiar...), só nas crianças compartilhadas
  com ele: lê o perfil, registra o dia a dia (atividade, comportamento, conquista, observação, estratégia
  testada), usa o canal e o chat. Não mexe no perfil, nas metas nem em quem tem acesso.
  (Internamente o acompanhante é o papel "professor", nome herdado do modelo original.)
"""
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from backend.auth import EMAIL, FUNCOES, Ator, Funcao, abrir_sessao, acesso, ator_atual, rotulo_funcao, so_responsavel
from backend import notificacoes as notif
from backend.avaliacoes import _em_segundo_plano, enriquecer, tratar
from src.agente_perfil import agente, chat, config, repositorio as repo

router = APIRouter(tags=["plataforma"])
EXEMPLO = config.ROOT / "src/agente_perfil/exemplos/formulario_lia_38m.json"
TIPOS_ACOMPANHANTE = {'atividade', 'comportamento', 'conquista', 'observacao', 'feedback_estrategia'}


class NovaCrianca(BaseModel):
    nome: str = Field(min_length=1, max_length=60)
    data_nascimento: date
    interesses: list[str] = Field(default_factory=list)
    parentesco: str | None = Field(default=None, max_length=60)


class NovoRegistro(BaseModel):
    tipo: Literal['atividade', 'comportamento', 'conquista', 'observacao', 'checkin_meta',
                  'feedback_estrategia', 'feedback_perfil', 'saude']
    texto: str = Field(default='', max_length=4000)
    dados: dict = Field(default_factory=dict)
    dominios: list[str] = Field(default_factory=list)
    local: Literal['casa', 'escola', 'terapia', 'outro'] | None = None
    estrategia: str | None = Field(default=None, max_length=200)
    resultado: Literal['funcionou', 'parcial', 'nao_funcionou'] | None = None
    meta_id: str | None = None
    ocorrido_em: datetime | None = None


class PedidoReavaliacao(BaseModel):
    comentario: str = Field(default='', max_length=2000)
    formulario_id: str | None = Field(default=None, description="Formulário atualizado (opcional)")


class MensagemChat(BaseModel):
    texto: str = Field(min_length=1, max_length=4000)
    conversa_id: str | None = None


class MensagemCanal(BaseModel):
    texto: str = Field(min_length=1, max_length=4000)


class Convite(BaseModel):
    email: str = Field(pattern=EMAIL, max_length=200)
    funcao: Funcao = "professor"


def em_paralelo(**tarefas):
    """Roda consultas independentes ao mesmo tempo (o banco remoto custa ~160 ms por ida e volta)."""
    with ThreadPoolExecutor(max_workers=len(tarefas)) as ex:
        futuros = {k: ex.submit(f) for k, f in tarefas.items()}
        return {k: f.result() for k, f in futuros.items()}


def _reavaliacao_em_andamento(vigente: dict | None, proposta: dict | None, sessoes: list[dict]) -> dict | None:
    """Com perfil vigente, uma reavaliação pode estar rodando (sessão) ou aguardando aprovação (proposta)."""
    if not vigente:
        return None
    sessao = next((x for x in sessoes if x.get("tipo") == "reavaliacao"), None)
    if sessao:
        return {"etapa": "analise", "sessao_id": sessao["id"], "status": sessao["status"]}
    if proposta and proposta["tipo"] == "reavaliacao":
        return {"etapa": "proposta", "avaliacao_id": proposta["id"]}
    return None


def estado_crianca(cid: str, crianca: dict | None = None) -> dict:
    """Em que etapa da jornada a criança está: formulario → analise → proposta → vigente.
    Quatro consultas, em paralelo (antes eram nove, em sequência)."""
    d = em_paralelo(crianca=lambda: crianca or repo.obter_crianca(cid), avaliacoes=lambda: repo.avaliacoes_resumo(cid),
                    sessoes=lambda: repo.sessoes_ativas(cid), formulario_id=lambda: repo.ultimo_formulario_id(cid))
    if not d["crianca"]:
        raise HTTPException(404, "Criança não encontrada.")
    avs, sessoes = d["avaliacoes"], d["sessoes"]
    vigente = next((a for a in avs if a["status"] == "vigente"), None)
    proposta = next((a for a in reversed(avs) if a["status"] == "proposta"), None)
    sessao = sessoes[0] if sessoes else None
    if vigente:
        etapa = "vigente"
    elif sessao:
        etapa = "analise"
    elif proposta:
        etapa = "proposta"
    elif d["formulario_id"]:
        etapa = "formulario_enviado"  # formulário salvo, mas o agente não concluiu (erro ou não iniciado)
    else:
        etapa = "formulario"
    return {"crianca": d["crianca"], "etapa": etapa, "sessao_id": sessao["id"] if sessao else None,
            "avaliacao_proposta_id": proposta["id"] if proposta else None,
            "avaliacao_vigente_id": vigente["id"] if vigente else None,
            "vigente_desde": vigente["aceita_em"] if vigente else None,
            "versoes_aprovadas": sum(1 for a in avs if a["status"] in ("vigente", "substituida")),
            "reavaliacao": _reavaliacao_em_andamento(vigente, proposta, sessoes),
            "formulario_id": d["formulario_id"],
            "metas": len(vigente["metas"]) if vigente else 0}


def _estados(criancas: list[dict], extra) -> list[dict]:
    """Estado de várias crianças ao mesmo tempo, na ordem da lista."""
    if not criancas:
        return []
    campos = ("id", "turma_id", "nome", "data_nascimento", "prematuro_semanas", "interesses", "criado_em")
    with ThreadPoolExecutor(max_workers=min(len(criancas), 6)) as ex:
        estados = list(ex.map(lambda c: estado_crianca(c["id"], {k: c.get(k) for k in campos}), criancas))
    return [{**e, **extra(c)} for e, c in zip(estados, criancas)]


# ------------------------------------------------------------------ crianças
@router.get("/api/eu/criancas")
def minhas_criancas(papel: Literal["responsavel", "professor"] = "responsavel", ator: Ator = Depends(ator_atual)):
    """Crianças do perfil escolhido: as do responsável, ou as compartilhadas com o acompanhante."""
    if papel == "responsavel":
        if not ator.responsavel:
            return []
        return _estados(repo.criancas_do_responsavel(ator.responsavel["id"]),
                        lambda c: {"papel": "responsavel", "parentesco": c.get("parentesco")})
    if not ator.professor:
        return []
    return _estados(repo.criancas_do_professor(ator.professor["id"]),
                    lambda c: {"papel": "professor", "funcao": c.get("funcao"), "funcao_rotulo": rotulo_funcao(c.get("funcao"))})


@router.post("/api/criancas", status_code=201)
def criar_crianca(body: NovaCrianca, ator: Ator = Depends(ator_atual)):
    if not ator.responsavel:
        raise HTTPException(403, "Só um responsável pode cadastrar uma criança. Crie o perfil de responsável na sua conta.")
    c = repo.criar_crianca(body.nome, body.data_nascimento.isoformat(), [i.strip() for i in body.interesses if i.strip()],
                           ator.responsavel["id"], body.parentesco)
    return estado_crianca(c["id"])


@router.get("/api/criancas/{cid}/estado")
def ver_estado(cid: str, ator: Ator = Depends(ator_atual)):
    acesso(ator, cid)
    return estado_crianca(cid)


@router.get("/api/criancas/{cid}/painel")
def painel(cid: str, ator: Ator = Depends(ator_atual)):
    papel, _ = acesso(ator, cid)
    d = em_paralelo(crianca=lambda: repo.obter_crianca(cid), registros=lambda: repo.listar_registros(cid),
                    formulario=lambda: repo.ultimo_formulario(cid), estado=lambda: estado_crianca(cid),
                    vigente=lambda: enriquecer(repo.avaliacao_vigente(cid)), avaliacoes=lambda: repo.listar_avaliacoes(cid),
                    estrategias=lambda: repo.historico_estrategias(cid), equipe=lambda: repo.equipe_da_crianca(cid))
    crianca, registros = d["crianca"], d["registros"]
    checkins: dict[str, list] = {}
    for r in reversed(registros):  # ordem cronológica
        if r["tipo"] == "checkin_meta" and r["meta_id"]:
            checkins.setdefault(r["meta_id"], []).append({"em": r["ocorrido_em"], "nivel": r["dados"].get("nivel_gas"),
                                                          "texto": r["texto"]})
    form = d["formulario"]
    return {
        "crianca_id": cid, "crianca": crianca, "perfil_formulario": form["perfil"] if form else None,
        "meu_papel": papel,
        "estado": d["estado"],
        "avaliacao_vigente": d["vigente"],
        "avaliacoes": d["avaliacoes"],
        "registros": registros,
        "checkins_metas": checkins,
        "estrategias": d["estrategias"],
        "equipe": d["equipe"],
    }


@router.get("/api/criancas/{cid}/formulario-atual")
def formulario_atual(cid: str, ator: Ator = Depends(ator_atual)):
    """Últimas respostas no formato do formulário, para pré-preencher a atualização na reavaliação."""
    so_responsavel(ator, cid)
    form = repo.ultimo_formulario(cid)
    if not form:
        raise HTTPException(404, "Esta criança ainda não tem formulário.")
    return {
        "formulario_id": form["id"], "criado_em": form.get("criado_em"), "perfil": form["perfil"],
        "respostas": {q["id"]: {"resposta": q["resposta"], "exemplo": q.get("exemplo") or ""}
                      for d in form["dominios"] for q in d["perguntas"]},
        "dominios": {d["id"]: d.get("contexto_responsavel") or {} for d in form["dominios"]},
    }


@router.get("/api/criancas/{cid}/resumo.pdf")
def resumo_pdf(cid: str, ator: Ator = Depends(ator_atual)):
    acesso(ator, cid)
    from backend.resumo_pdf import gerar_resumo
    conteudo, nome = gerar_resumo(cid)
    return Response(conteudo, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{nome}"'})


# ------------------------------------------------------------------ registros
@router.get("/api/criancas/{cid}/registros")
def listar_registros(cid: str, tipo: str | None = None, ator: Ator = Depends(ator_atual)):
    acesso(ator, cid)
    return repo.listar_registros(cid, tipo)


@router.post("/api/criancas/{cid}/registros", status_code=201)
def criar_registro(cid: str, body: NovoRegistro, ator: Ator = Depends(ator_atual)):
    papel, autor_id = acesso(ator, cid)
    if papel == "professor" and body.tipo not in TIPOS_ACOMPANHANTE:
        motivo = {"checkin_meta": "O progresso das metas é registrado pelo responsável.",
                  "saude": "Registros de saúde são feitos pelo responsável.",
                  "feedback_perfil": "Comentários que mudam o perfil são do responsável."}.get(body.tipo, "Tipo não permitido.")
        raise HTTPException(403, motivo + " Como acompanhante, registre como observação.")
    if body.tipo == "feedback_estrategia" and not (body.estrategia and body.resultado):
        raise HTTPException(422, "Informe a estratégia e o resultado.")
    if body.tipo == "checkin_meta" and (not body.meta_id or body.dados.get("nivel_gas") not in (-2, -1, 0, 1, 2)):
        raise HTTPException(422, "Informe a meta e o nível (de -2 a +2).")
    if body.tipo not in ("checkin_meta", "feedback_estrategia") and not body.texto.strip() and not body.dados:
        raise HTTPException(422, "Descreva o registro.")
    vigente = repo.avaliacao_vigente(cid)
    reg = repo.inserir_registro({
        "crianca_id": cid, "tipo": body.tipo,
        "responsavel_id": autor_id if papel == "responsavel" else None,
        "professor_id": autor_id if papel == "professor" else None,
        "texto": body.texto.strip() or None, "dados": body.dados, "dominios": body.dominios, "local": body.local,
        "estrategia": body.estrategia, "resultado": body.resultado, "meta_id": body.meta_id,
        "avaliacao_id": vigente["id"] if vigente else None,
        **({"ocorrido_em": body.ocorrido_em.isoformat()} if body.ocorrido_em else {}),
    })
    notif.notificar_registro(reg, papel, autor_id)  # avisa o resto da equipe
    return reg


# ------------------------------------------------------------------ chat com o assistente (IA)
def _minha_conversa(conversa: dict, papel: str, autor_id: str) -> bool:
    return conversa.get("responsavel_id" if papel == "responsavel" else "professor_id") == autor_id


@router.get("/api/criancas/{cid}/conversas")
def conversas(cid: str, ator: Ator = Depends(ator_atual)):
    papel, autor_id = acesso(ator, cid)
    return [c for c in repo.listar_conversas(cid) if _minha_conversa(c, papel, autor_id)]  # cada um vê as suas


@router.get("/api/conversas/{conversa_id}/mensagens")
def mensagens(conversa_id: str, ator: Ator = Depends(ator_atual)):
    conversa = repo.obter_conversa(conversa_id)
    if not conversa:
        raise HTTPException(404, "Conversa não encontrada.")
    papel, autor_id = acesso(ator, conversa["crianca_id"])
    if not _minha_conversa(conversa, papel, autor_id):
        raise HTTPException(403, "Esta conversa é de outra pessoa.")
    return repo.listar_mensagens(conversa_id)


@router.post("/api/criancas/{cid}/chat")
def conversar(cid: str, body: MensagemChat, ator: Ator = Depends(ator_atual)):
    papel, autor_id = acesso(ator, cid)
    if body.conversa_id:
        conversa = repo.obter_conversa(body.conversa_id)
        if conversa and not _minha_conversa(conversa, papel, autor_id):
            raise HTTPException(403, "Esta conversa é de outra pessoa.")
    return tratar(chat.responder, cid, body.texto, papel, autor_id, body.conversa_id)


@router.get("/api/criancas/{cid}/contexto-chat", include_in_schema=False)
def contexto_chat(cid: str, ator: Ator = Depends(ator_atual)):
    """Depuração: o resumo ativo que o chat recebe."""
    acesso(ator, cid)
    return {"contexto": tratar(chat.contexto_crianca, cid)}


# ------------------------------------------------------------------ canal da criança (pessoas)
@router.get("/api/criancas/{cid}/canal")
def ver_canal(cid: str, depois: str | None = Query(default=None), ator: Ator = Depends(ator_atual)):
    papel, autor_id = acesso(ator, cid)
    tarefas = {"msgs": lambda: repo.listar_canal(cid, depois=depois), "equipe": lambda: repo.equipe_da_crianca(cid)}
    if not depois:  # abriu o canal: as mensagens dele contam como lidas
        tarefas["lidas"] = lambda: repo.marcar_notificacoes_lidas(ator.conta["id"], crianca_id=cid, tipo="canal")
    d = em_paralelo(**tarefas)
    msgs = d["msgs"]
    for m in msgs:
        m["funcao_rotulo"] = rotulo_funcao(m["autor_funcao"])
        m["minha"] = (m["responsavel_id"] if papel == "responsavel" else m["professor_id"]) == autor_id
    return {"mensagens": msgs, "equipe": [{**e, "funcao_rotulo": e["funcao"] if e["papel"] == "responsavel"
                                           else rotulo_funcao(e["funcao"])} for e in d["equipe"]]}


@router.post("/api/criancas/{cid}/canal", status_code=201)
def escrever_canal(cid: str, body: MensagemCanal, ator: Ator = Depends(ator_atual)):
    papel, autor_id = acesso(ator, cid)
    if not body.texto.strip():
        raise HTTPException(422, "Escreva uma mensagem.")
    m = repo.inserir_mensagem_canal(cid, papel, autor_id, body.texto.strip())
    notif.notificar_canal(m, papel, autor_id)
    return {**m, "funcao_rotulo": rotulo_funcao(m["autor_funcao"]), "minha": True}


# ------------------------------------------------------------------ compartilhamento
@router.get("/api/criancas/{cid}/compartilhamentos")
def compartilhamentos(cid: str, ator: Ator = Depends(ator_atual)):
    so_responsavel(ator, cid)
    return [{**c, "funcao_rotulo": rotulo_funcao(c["funcao"])} for c in repo.listar_compartilhamentos(cid)]


@router.post("/api/criancas/{cid}/compartilhamentos", status_code=201)
def compartilhar(cid: str, body: Convite, ator: Ator = Depends(ator_atual)):
    rid = so_responsavel(ator, cid)
    if body.email.strip().lower() == ator.conta["email"]:
        raise HTTPException(422, "Use o e-mail da pessoa que vai acompanhar a criança, não o seu.")
    cp = tratar(repo.criar_compartilhamento, cid, body.email, body.funcao, rid)
    notif.notificar_convite(cp)
    return cp


@router.delete("/api/compartilhamentos/{comp_id}")
def revogar(comp_id: str, ator: Ator = Depends(ator_atual)):
    cp = repo.obter_compartilhamento(comp_id)
    if not cp:
        raise HTTPException(404, "Compartilhamento não encontrado.")
    so_responsavel(ator, cp["crianca_id"])
    repo.revogar_compartilhamento(comp_id)
    return {"ok": True}


@router.get("/api/eu/convites")
def meus_convites(ator: Ator = Depends(ator_atual)):
    if not ator.professor:
        return []
    return [{**c, "funcao_rotulo": rotulo_funcao(c["funcao"])}
            for c in repo.convites_do_acompanhante(ator.professor["id"], ator.conta["email"])]


def _meu_convite(comp_id: str, ator: Ator) -> dict:
    cp = repo.obter_compartilhamento(comp_id)
    if not cp or cp["status"] != "pendente":
        raise HTTPException(404, "Convite não encontrado ou já respondido.")
    if not ator.professor:
        raise HTTPException(403, "Crie o perfil de acompanhante na sua conta para aceitar convites.")
    if cp["professor_id"] not in (None, ator.professor["id"]) or (cp["professor_id"] is None and cp["email"] != ator.conta["email"]):
        raise HTTPException(403, "Este convite foi enviado para outra pessoa.")
    return cp


@router.post("/api/compartilhamentos/{comp_id}/aceitar")
def aceitar_convite(comp_id: str, ator: Ator = Depends(ator_atual)):
    cp = _meu_convite(comp_id, ator)
    repo.responder_compartilhamento(comp_id, ator.professor["id"], "ativo")
    notif.notificar_convite_aceito(cp, ator.professor["id"])
    return {"ok": True}


@router.post("/api/compartilhamentos/{comp_id}/recusar")
def recusar_convite(comp_id: str, ator: Ator = Depends(ator_atual)):
    _meu_convite(comp_id, ator)
    repo.responder_compartilhamento(comp_id, ator.professor["id"], "recusado")
    return {"ok": True}


# ------------------------------------------------------------------ reavaliação
@router.post("/api/criancas/{cid}/reavaliacoes", status_code=202)
def pedir_reavaliacao(cid: str, body: PedidoReavaliacao, ator: Ator = Depends(ator_atual)):
    """O agente recebe o perfil vigente + todos os registros (quem, quando, o quê) e, se houver,
    o formulário atualizado; propõe uma nova versão comparada com a vigente."""
    so_responsavel(ator, cid)
    vigente = repo.avaliacao_vigente(cid)
    if not vigente:
        raise HTTPException(409, "A reavaliação parte de um perfil aprovado. Conclua a primeira avaliação antes.")
    if _reavaliacao_em_andamento(vigente, repo.avaliacao_proposta(cid), repo.sessoes_ativas(cid)):
        raise HTTPException(409, "Já existe uma reavaliação em andamento para esta criança.")
    if body.formulario_id:
        form = repo.obter_formulario(body.formulario_id)
        if not form or form["crianca_id"] != cid:
            raise HTTPException(404, "Formulário não encontrado para esta criança.")
    return _em_segundo_plano(tratar(agente.preparar_reavaliacao, cid, body.comentario.strip() or None, body.formulario_id))


# ------------------------------------------------------------------ demo
@router.post("/api/demo/entrar")
def demo_entrar():
    """Cria (uma vez) a família de demonstração e devolve a sessão de login da Ana (responsável)."""
    from backend.seed import EMAIL_DEMO, semear_demo
    semear_demo()
    return abrir_sessao(repo.obter_conta_por_email(EMAIL_DEMO))


@router.post("/api/demo/entrar-professor")
def demo_entrar_professor():
    """Entra como a Prof. Carla, acompanhante da Lia e da Nina."""
    from backend.seed import EMAIL_PROFESSORA, semear_demo
    semear_demo()
    return abrir_sessao(repo.obter_conta_por_email(EMAIL_PROFESSORA))


@router.get("/api/demo/formulario-exemplo")
def formulario_exemplo():
    """Respostas fictícias (criança de 38 meses) para preencher o formulário sem digitar."""
    return json.loads(EXEMPLO.read_text(encoding="utf-8"))


@router.get("/api/funcoes", include_in_schema=False)
def funcoes():
    return FUNCOES
