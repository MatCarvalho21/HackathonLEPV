"""Rotas do agente de mapeamento de perfil (roda em segundo plano; o frontend acompanha a sessão).

  POST /api/avaliacoes                         {formulario_id, demo?}  → 202 {sessao_id}
  GET  /api/avaliacoes/sessoes/{id}                                    → status, eventos, perguntas ou avaliação
  POST /api/avaliacoes/sessoes/{id}/respostas  {respostas: {id: txt}}  → 202, retoma o loop
  GET  /api/avaliacoes/{id}                                            → avaliação (com evidências legíveis)
  POST /api/avaliacoes/{id}/ajustes            {comentario}            → 202, nova proposta
  POST /api/avaliacoes/{id}/aprovar                                    → proposta vira vigente
"""
import threading

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.agente_perfil import agente, config, repositorio as repo

router = APIRouter(tags=["avaliações"])


class NovaAvaliacao(BaseModel):
    formulario_id: str
    demo: bool = Field(default=False, description="Força uma rodada de perguntas extras (para demonstração)")


class RespostasExtras(BaseModel):
    respostas: dict[str, str] = Field(default_factory=dict, description="{id_pergunta: resposta}; omitir = não respondeu")


class Ajuste(BaseModel):
    comentario: str = Field(min_length=3, max_length=2000)


def tratar(fn, *args, **kwargs):
    """Converte erros de domínio em HTTP (404/409/422)."""
    try:
        return fn(*args, **kwargs)
    except KeyError as e:
        raise HTTPException(404, str(e).strip("'"))
    except (agente.ErroAgente, ValueError) as e:
        raise HTTPException(409, str(e))


def enriquecer(av: dict | None) -> dict | None:
    """Anexa o texto de cada marco/relato/fonte citável, para o frontend mostrar as evidências legíveis."""
    if not av:
        return av
    formulario = repo.obter_formulario(av["formulario_id"]) if av.get("formulario_id") else None
    formulario = formulario or {"dominios": []}
    ev = {}
    for d in formulario["dominios"]:
        for q in d["perguntas"]:
            ev[q["id"]] = {"tipo": "marco", "texto": q["texto"], "resposta": q["resposta"], "exemplo": q.get("exemplo")}
        ctx = d.get("contexto_responsavel") or {}
        relato = " · ".join(v for k, v in ctx.items() if isinstance(v, str) and v.strip() and k != "contexto")
        if relato:
            ev[f"ctx:{d['id']}"] = {"tipo": "relato", "texto": relato}
    for k, v in av["perfil"].get("respostas_complementares", {}).items():
        ev[k] = {"tipo": "extra", "texto": f"{v['pergunta']} → {v['resposta']}"}
    for k, v in av["perfil"].get("fontes", {}).items():
        ev[k] = {"tipo": "fonte", "texto": f"{v['documento']} · {v['secao']}"}
    return {**av, "evidencias_legiveis": ev, "crianca": formulario.get("perfil"),
            "crianca_cadastro": repo.obter_crianca(av["crianca_id"])}


def _em_segundo_plano(sessao: dict) -> dict:
    threading.Thread(target=agente.executar, args=(sessao,), daemon=True).start()
    return agente.resumo_sessao(sessao)


@router.post("/api/avaliacoes", status_code=202)
def criar(body: NovaAvaliacao):
    return _em_segundo_plano(tratar(agente.preparar_inicio, body.formulario_id, body.demo))


@router.get("/api/avaliacoes/sessoes/{sessao_id}")
def ver_sessao(sessao_id: str):
    sessao = repo.obter_sessao(sessao_id)
    if not sessao:
        raise HTTPException(404, "Sessão não encontrada.")
    return agente.resumo_sessao(sessao)


@router.post("/api/avaliacoes/sessoes/{sessao_id}/respostas", status_code=202)
def responder(sessao_id: str, body: RespostasExtras):
    return _em_segundo_plano(tratar(agente.preparar_retomada, sessao_id, body.respostas))


@router.get("/api/avaliacoes/{avaliacao_id}")
def ver(avaliacao_id: str):
    av = repo.obter_avaliacao(avaliacao_id)
    if not av:
        raise HTTPException(404, "Avaliação não encontrada.")
    return enriquecer(av)


@router.post("/api/avaliacoes/{avaliacao_id}/ajustes", status_code=202)
def ajustar(avaliacao_id: str, body: Ajuste):
    return _em_segundo_plano(tratar(agente.preparar_ajuste, avaliacao_id, body.comentario))


@router.post("/api/avaliacoes/{avaliacao_id}/aprovar")
def aprovar(avaliacao_id: str):
    return tratar(repo.aprovar_avaliacao, avaliacao_id)


def aquecer_rag() -> None:
    """Carrega o modelo de embedding ao subir o servidor, para a 1ª busca não esperar."""
    if config.RAG_DESATIVADO:
        return
    from src.agente_perfil.ferramentas import _funcao_busca
    threading.Thread(target=_funcao_busca, daemon=True).start()
