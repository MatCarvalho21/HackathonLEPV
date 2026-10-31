"""Rotas da plataforma: pessoas, crianças, painel, registros, chat e demonstração.

Pessoas      POST /api/responsaveis · POST /api/professores
             GET  /api/responsaveis/{id}/criancas · GET /api/professores/{id}/criancas
Crianças     POST /api/criancas · GET /api/criancas/{id}/estado · POST /api/criancas/{id}/turma
Painel       GET  /api/criancas/{id}/painel
Registros    GET|POST /api/criancas/{id}/registros
Chat         GET  /api/criancas/{id}/conversas · GET /api/conversas/{id}/mensagens
             POST /api/criancas/{id}/chat {texto, conversa_id?, autor, autor_id}
Demo         POST /api/demo/entrar · GET /api/demo/formulario-exemplo · POST /api/demo/formulario
"""
import json
from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.avaliacoes import enriquecer, tratar
from src.agente_perfil import chat, config, repositorio as repo

router = APIRouter(tags=["plataforma"])
EXEMPLO = config.ROOT / "src/agente_perfil/exemplos/formulario_lia_38m.json"
Autor = Literal["responsavel", "professor"]


class NovoResponsavel(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=200)
    telefone: str | None = Field(default=None, max_length=40)


class NovoProfessor(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=200)
    escola: str = Field(min_length=1, max_length=160)
    turma: str = Field(min_length=1, max_length=80)


class NovaCrianca(BaseModel):
    nome: str = Field(min_length=1, max_length=60)
    data_nascimento: date
    interesses: list[str] = Field(default_factory=list)
    responsavel_id: str
    parentesco: str | None = Field(default=None, max_length=60)


class VinculoTurma(BaseModel):
    professor_id: str


class NovoRegistro(BaseModel):
    tipo: Literal['atividade', 'comportamento', 'conquista', 'observacao', 'checkin_meta',
                  'feedback_estrategia', 'feedback_perfil', 'saude']
    autor: Autor = 'responsavel'
    autor_id: str
    texto: str = Field(default='', max_length=4000)
    dados: dict = Field(default_factory=dict)
    dominios: list[str] = Field(default_factory=list)
    local: Literal['casa', 'escola', 'terapia', 'outro'] | None = None
    estrategia: str | None = Field(default=None, max_length=200)
    resultado: Literal['funcionou', 'parcial', 'nao_funcionou'] | None = None
    meta_id: str | None = None
    ocorrido_em: datetime | None = None


class MensagemChat(BaseModel):
    texto: str = Field(min_length=1, max_length=4000)
    conversa_id: str | None = None
    autor: Autor = 'responsavel'
    autor_id: str


def _crianca_ou_404(cid: str) -> dict:
    c = repo.obter_crianca(cid)
    if not c:
        raise HTTPException(404, "Criança não encontrada.")
    return c


def estado_crianca(cid: str) -> dict:
    """Em que etapa da jornada a criança está: formulario → analise → proposta → vigente."""
    crianca = _crianca_ou_404(cid)
    vigente = repo.avaliacao_vigente(cid)
    proposta = repo.avaliacao_proposta(cid)
    sessao = repo.sessao_ativa(cid)
    form = repo.ultimo_formulario(cid)
    if vigente:
        etapa = "vigente"
    elif sessao:
        etapa = "analise"
    elif proposta:
        etapa = "proposta"
    elif form:
        etapa = "formulario_enviado"  # formulário salvo, mas o agente não concluiu (erro ou não iniciado)
    else:
        etapa = "formulario"
    return {"crianca": crianca, "etapa": etapa, "sessao_id": sessao["id"] if sessao else None,
            "avaliacao_proposta_id": proposta["id"] if proposta else None,
            "avaliacao_vigente_id": vigente["id"] if vigente else None,
            "formulario_id": form["id"] if form else None,
            "metas": len(vigente["metas"]) if vigente else 0}


# ------------------------------------------------------------------ pessoas
@router.post("/api/responsaveis", status_code=201)
def criar_responsavel(body: NovoResponsavel):
    return repo.criar_responsavel(body.nome, body.email, body.telefone)


@router.post("/api/professores", status_code=201)
def criar_professor(body: NovoProfessor):
    return repo.criar_professor(body.nome, body.email, body.escola, body.turma)


@router.get("/api/responsaveis/{rid}/criancas")
def criancas_responsavel(rid: str):
    if not repo.obter_responsavel(rid):
        raise HTTPException(404, "Responsável não encontrado.")
    return [{**estado_crianca(c["id"]), "parentesco": c.get("parentesco")} for c in repo.criancas_do_responsavel(rid)]


@router.get("/api/professores/{pid}/criancas")
def criancas_professor(pid: str):
    if not repo.obter_professor(pid):
        raise HTTPException(404, "Professor não encontrado.")
    return [estado_crianca(c["id"]) for c in repo.criancas_do_professor(pid)]


# ------------------------------------------------------------------ crianças
@router.post("/api/criancas", status_code=201)
def criar_crianca(body: NovaCrianca):
    if not repo.obter_responsavel(body.responsavel_id):
        raise HTTPException(404, "Responsável não encontrado.")
    c = repo.criar_crianca(body.nome, body.data_nascimento.isoformat(), [i.strip() for i in body.interesses if i.strip()],
                           body.responsavel_id, body.parentesco)
    return estado_crianca(c["id"])


@router.get("/api/criancas/{cid}/estado")
def ver_estado(cid: str):
    return estado_crianca(cid)


@router.post("/api/criancas/{cid}/turma")
def vincular_turma(cid: str, body: VinculoTurma):
    _crianca_ou_404(cid)
    tratar(repo.vincular_turma, cid, body.professor_id)
    return estado_crianca(cid)


@router.get("/api/criancas/{cid}/painel")
def painel(cid: str):
    crianca = _crianca_ou_404(cid)
    registros = repo.listar_registros(cid)
    checkins: dict[str, list] = {}
    for r in reversed(registros):  # ordem cronológica
        if r["tipo"] == "checkin_meta" and r["meta_id"]:
            checkins.setdefault(r["meta_id"], []).append({"em": r["ocorrido_em"], "nivel": r["dados"].get("nivel_gas"),
                                                          "texto": r["texto"]})
    form = repo.ultimo_formulario(cid)
    return {
        "crianca_id": cid, "crianca": crianca, "perfil_formulario": form["perfil"] if form else None,
        "estado": estado_crianca(cid),
        "avaliacao_vigente": enriquecer(repo.avaliacao_vigente(cid)),
        "avaliacoes": repo.listar_avaliacoes(cid),
        "registros": registros,
        "checkins_metas": checkins,
        "estrategias": repo.historico_estrategias(cid),
    }


# ------------------------------------------------------------------ registros
@router.get("/api/criancas/{cid}/registros")
def listar_registros(cid: str, tipo: str | None = None):
    _crianca_ou_404(cid)
    return repo.listar_registros(cid, tipo)


@router.post("/api/criancas/{cid}/registros", status_code=201)
def criar_registro(cid: str, body: NovoRegistro):
    _crianca_ou_404(cid)
    if body.tipo == "feedback_estrategia" and not (body.estrategia and body.resultado):
        raise HTTPException(422, "Informe a estratégia e o resultado.")
    if body.tipo == "checkin_meta" and (not body.meta_id or body.dados.get("nivel_gas") not in (-2, -1, 0, 1, 2)):
        raise HTTPException(422, "Informe a meta e o nível (de -2 a +2).")
    if body.tipo == "saude" and body.autor != "responsavel":
        raise HTTPException(422, "Registros de saúde são feitos pelo responsável.")
    if body.tipo not in ("checkin_meta", "feedback_estrategia") and not body.texto.strip() and not body.dados:
        raise HTTPException(422, "Descreva o registro.")
    vigente = repo.avaliacao_vigente(cid)
    return repo.inserir_registro({
        "crianca_id": cid, "tipo": body.tipo,
        "responsavel_id": body.autor_id if body.autor == "responsavel" else None,
        "professor_id": body.autor_id if body.autor == "professor" else None,
        "texto": body.texto.strip() or None, "dados": body.dados, "dominios": body.dominios, "local": body.local,
        "estrategia": body.estrategia, "resultado": body.resultado, "meta_id": body.meta_id,
        "avaliacao_id": vigente["id"] if vigente else None,
        **({"ocorrido_em": body.ocorrido_em.isoformat()} if body.ocorrido_em else {}),
    })


# ------------------------------------------------------------------ chat
@router.get("/api/criancas/{cid}/conversas")
def conversas(cid: str):
    _crianca_ou_404(cid)
    return repo.listar_conversas(cid)


@router.get("/api/conversas/{conversa_id}/mensagens")
def mensagens(conversa_id: str):
    if not repo.obter_conversa(conversa_id):
        raise HTTPException(404, "Conversa não encontrada.")
    return repo.listar_mensagens(conversa_id)


@router.post("/api/criancas/{cid}/chat")
def conversar(cid: str, body: MensagemChat):
    _crianca_ou_404(cid)
    return tratar(chat.responder, cid, body.texto, body.autor, body.autor_id, body.conversa_id)


@router.get("/api/criancas/{cid}/contexto-chat", include_in_schema=False)
def contexto_chat(cid: str):
    """Depuração: o resumo ativo que o chat recebe."""
    return {"contexto": tratar(chat.contexto_crianca, cid)}


# ------------------------------------------------------------------ demo
@router.post("/api/demo/entrar")
def demo_entrar():
    """Cria (uma vez) a família de demonstração e devolve a responsável e as crianças."""
    from backend.seed import semear_demo
    resp = semear_demo()
    return {"responsavel": resp, "criancas": criancas_responsavel(resp["id"])}


@router.get("/api/demo/formulario-exemplo")
def formulario_exemplo():
    """Respostas fictícias (criança de 38 meses) para preencher o formulário sem digitar."""
    return json.loads(EXEMPLO.read_text(encoding="utf-8"))


@router.post("/api/demo/formulario", status_code=201)
def formulario_demo():
    """Envia o formulário sintético pelo mesmo caminho do formulário real (cria uma criança)."""
    from backend.main import Submission, submit
    return submit(Submission.model_validate(json.loads(EXEMPLO.read_text(encoding="utf-8"))))
