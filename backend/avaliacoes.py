"""Rotas do agente de mapeamento de perfil (roda em segundo plano; o frontend acompanha a sessão).

  POST /api/avaliacoes                         {formulario_id, demo?}  → 202 {sessao_id}
  GET  /api/avaliacoes/sessoes/{id}                                    → status, eventos, perguntas ou avaliação
  POST /api/avaliacoes/sessoes/{id}/respostas  {respostas: {id: txt}}  → 202, retoma o loop
  GET  /api/avaliacoes/{id}                                            → avaliação (com evidências legíveis)
  POST /api/avaliacoes/{id}/ajustes            {comentario}            → 202, nova proposta
  POST /api/avaliacoes/{id}/aprovar                                    → proposta vira vigente

Todas exigem login. Ler (sessão, avaliação) vale para quem tem acesso à criança; disparar o agente,
responder às perguntas dele, pedir ajuste e aprovar é só do responsável pelo perfil.
"""
import threading

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.auth import Ator, acesso, ator_atual, so_responsavel

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
    if av["perfil"].get("reavaliacao"):
        for r in repo.listar_registros(av["crianca_id"], limite=1000):
            from backend.auth import rotulo_funcao
            quem = f"{r.get('autor_nome') or ''} ({rotulo_funcao(r.get('autor_funcao')).lower()})"
            ev[f"reg:{r['id'][:8]}"] = {"tipo": "registro", "texto": f"{r['ocorrido_em'][:10]} · {quem}: "
                                        f"{r.get('texto') or r.get('estrategia') or r['tipo']}"}
    return {**av, "evidencias_legiveis": ev, "crianca": formulario.get("perfil"),
            "crianca_cadastro": repo.obter_crianca(av["crianca_id"])}


def _avaliacao_ou_404(avaliacao_id: str) -> dict:
    av = repo.obter_avaliacao(avaliacao_id)
    if not av:
        raise HTTPException(404, "Avaliação não encontrada.")
    return av


def _sessao_ou_404(sessao_id: str) -> dict:
    sessao = repo.obter_sessao(sessao_id)
    if not sessao:
        raise HTTPException(404, "Sessão não encontrada.")
    return sessao


def _em_segundo_plano(sessao: dict) -> dict:
    threading.Thread(target=agente.executar, args=(sessao,), daemon=True).start()
    return agente.resumo_sessao(sessao)


@router.post("/api/avaliacoes", status_code=202)
def criar(body: NovaAvaliacao, ator: Ator = Depends(ator_atual)):
    form = repo.obter_formulario(body.formulario_id)
    if not form:
        raise HTTPException(404, "Formulário não encontrado.")
    so_responsavel(ator, form["crianca_id"])
    return _em_segundo_plano(tratar(agente.preparar_inicio, body.formulario_id, body.demo))


@router.get("/api/avaliacoes/sessoes/{sessao_id}")
def ver_sessao(sessao_id: str, ator: Ator = Depends(ator_atual)):
    sessao = _sessao_ou_404(sessao_id)
    acesso(ator, sessao["crianca_id"])
    return agente.resumo_sessao(sessao)


@router.post("/api/avaliacoes/sessoes/{sessao_id}/respostas", status_code=202)
def responder(sessao_id: str, body: RespostasExtras, ator: Ator = Depends(ator_atual)):
    so_responsavel(ator, _sessao_ou_404(sessao_id)["crianca_id"])
    return _em_segundo_plano(tratar(agente.preparar_retomada, sessao_id, body.respostas))


@router.get("/api/avaliacoes/{avaliacao_id}")
def ver(avaliacao_id: str, ator: Ator = Depends(ator_atual)):
    av = _avaliacao_ou_404(avaliacao_id)
    acesso(ator, av["crianca_id"])
    return enriquecer(av)


@router.post("/api/avaliacoes/{avaliacao_id}/ajustes", status_code=202)
def ajustar(avaliacao_id: str, body: Ajuste, ator: Ator = Depends(ator_atual)):
    so_responsavel(ator, _avaliacao_ou_404(avaliacao_id)["crianca_id"])
    return _em_segundo_plano(tratar(agente.preparar_ajuste, avaliacao_id, body.comentario))


@router.post("/api/avaliacoes/{avaliacao_id}/aprovar")
def aprovar(avaliacao_id: str, ator: Ator = Depends(ator_atual)):
    so_responsavel(ator, _avaliacao_ou_404(avaliacao_id)["crianca_id"])
    av = tratar(repo.aprovar_avaliacao, avaliacao_id)
    from backend.notificacoes import notificar_perfil_aprovado
    notificar_perfil_aprovado(av)
    return av


def aquecer_rag() -> None:
    """Carrega o modelo de embedding ao subir o servidor, para a 1ª busca não esperar."""
    if config.RAG_DESATIVADO:
        return
    from src.agente_perfil.ferramentas import _funcao_busca
    threading.Thread(target=_funcao_busca, daemon=True).start()
