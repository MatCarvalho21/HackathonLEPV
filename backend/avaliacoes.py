"""Rotas do agente de mapeamento de perfil.

POST /api/avaliacoes                         {formulario_id}       → roda o agente
POST /api/avaliacoes/sessoes/{id}/respostas  {respostas: {id: txt}} → responde perguntas extras e retoma
GET  /api/avaliacoes/sessoes/{id}                                  → estado da sessão
GET  /api/avaliacoes/{id}                                          → avaliação (proposta/vigente)
POST /api/avaliacoes/{id}/ajustes            {comentario}          → nova proposta com o pedido do responsável
POST /api/avaliacoes/{id}/aprovar                                  → proposta vira vigente

As chamadas ao modelo são síncronas (30 s a 2 min). Para o MVP é aceitável; em produção,
rodar em background e o frontend consultar GET /sessoes/{id}.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.agente_perfil import agente, repositorio as repo

router = APIRouter(prefix="/api/avaliacoes", tags=["avaliações"])


class NovaAvaliacao(BaseModel):
    formulario_id: str


class RespostasExtras(BaseModel):
    respostas: dict[str, str] = Field(default_factory=dict, description="{id_pergunta: resposta}; omitir = não respondeu")


class Ajuste(BaseModel):
    comentario: str = Field(min_length=3, max_length=2000)


def _ou_404(fn, *args):
    try:
        return fn(*args)
    except KeyError as e:
        raise HTTPException(404, str(e))
    except agente.ErroAgente as e:
        raise HTTPException(409, str(e))
    except ValueError as e:
        raise HTTPException(409, str(e))


@router.post("", status_code=201)
def criar(body: NovaAvaliacao):
    return _ou_404(agente.iniciar, body.formulario_id)


@router.post("/sessoes/{sessao_id}/respostas")
def responder(sessao_id: str, body: RespostasExtras):
    return _ou_404(agente.retomar, sessao_id, body.respostas)


@router.get("/sessoes/{sessao_id}")
def ver_sessao(sessao_id: str):
    sessao = repo.obter_sessao(sessao_id)
    if not sessao:
        raise HTTPException(404, "Sessão não encontrada.")
    return agente.resumo_sessao(sessao)


@router.get("/{avaliacao_id}")
def ver(avaliacao_id: str):
    av = repo.obter_avaliacao(avaliacao_id)
    if not av:
        raise HTTPException(404, "Avaliação não encontrada.")
    return av


@router.post("/{avaliacao_id}/ajustes", status_code=201)
def ajustar(avaliacao_id: str, body: Ajuste):
    return _ou_404(agente.ajustar, avaliacao_id, body.comentario)


@router.post("/{avaliacao_id}/aprovar")
def aprovar(avaliacao_id: str):
    return _ou_404(repo.aprovar_avaliacao, avaliacao_id)
