"""Rotas do agente de mapeamento de perfil, dos registros do dia a dia e do painel.

Agente (roda em segundo plano; o frontend acompanha por GET /sessoes/{id}):
  POST /api/avaliacoes                         {formulario_id, demo?}  → 202 {sessao_id}
  GET  /api/avaliacoes/sessoes/{id}                                    → status, eventos, perguntas ou avaliação
  POST /api/avaliacoes/sessoes/{id}/respostas  {respostas: {id: txt}}  → 202, retoma o loop
  GET  /api/avaliacoes/{id}                                            → avaliação
  POST /api/avaliacoes/{id}/ajustes            {comentario}            → 202, nova proposta
  POST /api/avaliacoes/{id}/aprovar                                    → proposta vira vigente
Criança (no MVP local a criança é identificada pelo id do formulário):
  GET  /api/criancas/{formulario_id}/painel
  GET  /api/criancas/{formulario_id}/registros?tipo=
  POST /api/criancas/{formulario_id}/registros
Demo:
  POST /api/demo/formulario                                            → envia o formulário sintético da Lia
"""
import json
import threading
from datetime import datetime
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.agente_perfil import agente, config, repositorio as repo

router = APIRouter(tags=["avaliações"])
EXEMPLO_DEMO = config.ROOT / "src/agente_perfil/exemplos/formulario_lia_38m.json"


class NovaAvaliacao(BaseModel):
    formulario_id: str
    demo: bool = Field(default=False, description="Força uma rodada de perguntas extras (para demonstração)")


class RespostasExtras(BaseModel):
    respostas: dict[str, str] = Field(default_factory=dict, description="{id_pergunta: resposta}; omitir = não respondeu")


class Ajuste(BaseModel):
    comentario: str = Field(min_length=3, max_length=2000)


class NovoRegistro(BaseModel):
    tipo: Literal['atividade', 'comportamento', 'conquista', 'observacao', 'checkin_meta',
                  'feedback_estrategia', 'feedback_perfil', 'saude']
    autor: Literal['responsavel', 'professor'] = 'responsavel'
    texto: str = Field(default='', max_length=4000)
    dados: dict = Field(default_factory=dict)
    dominios: list[str] = Field(default_factory=list)
    local: Literal['casa', 'escola', 'terapia', 'outro'] | None = None
    estrategia: str | None = Field(default=None, max_length=200)
    resultado: Literal['funcionou', 'parcial', 'nao_funcionou'] | None = None
    meta_id: str | None = None
    ocorrido_em: datetime | None = None


def _tratar(fn, *args):
    try:
        return fn(*args)
    except KeyError as e:
        raise HTTPException(404, str(e).strip("'"))
    except (agente.ErroAgente, ValueError) as e:
        raise HTTPException(409, str(e))


def _enriquecer(av: dict | None) -> dict | None:
    """Anexa o texto de cada marco e relato citável, para o frontend mostrar as evidências legíveis."""
    if not av:
        return av
    formulario = repo.obter_formulario(av["formulario_id"]) or {"dominios": []}
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
    return {**av, "evidencias_legiveis": ev, "crianca": formulario.get("perfil")}


def _em_segundo_plano(sessao: dict) -> dict:
    threading.Thread(target=agente.executar, args=(sessao,), daemon=True).start()
    return agente.resumo_sessao(sessao)


# ------------------------------------------------------------------ agente
@router.post("/api/avaliacoes", status_code=202)
def criar(body: NovaAvaliacao):
    return _em_segundo_plano(_tratar(agente.preparar_inicio, body.formulario_id, body.demo))


@router.get("/api/avaliacoes/sessoes/{sessao_id}")
def ver_sessao(sessao_id: str):
    sessao = repo.obter_sessao(sessao_id)
    if not sessao:
        raise HTTPException(404, "Sessão não encontrada.")
    return agente.resumo_sessao(sessao)


@router.post("/api/avaliacoes/sessoes/{sessao_id}/respostas", status_code=202)
def responder(sessao_id: str, body: RespostasExtras):
    return _em_segundo_plano(_tratar(agente.preparar_retomada, sessao_id, body.respostas))


@router.get("/api/avaliacoes/{avaliacao_id}")
def ver(avaliacao_id: str):
    av = repo.obter_avaliacao(avaliacao_id)
    if not av:
        raise HTTPException(404, "Avaliação não encontrada.")
    return _enriquecer(av)


@router.post("/api/avaliacoes/{avaliacao_id}/ajustes", status_code=202)
def ajustar(avaliacao_id: str, body: Ajuste):
    return _em_segundo_plano(_tratar(agente.preparar_ajuste, avaliacao_id, body.comentario))


@router.post("/api/avaliacoes/{avaliacao_id}/aprovar")
def aprovar(avaliacao_id: str):
    return _tratar(repo.aprovar_avaliacao, avaliacao_id)


# ------------------------------------------------------------------ criança: painel e registros
@router.get("/api/criancas/{formulario_id}/painel")
def painel(formulario_id: str):
    formulario = repo.obter_formulario(formulario_id)
    if not formulario:
        raise HTTPException(404, "Criança/formulário não encontrado.")
    registros = repo.listar_registros(formulario_id)
    checkins: dict[str, list] = {}
    for r in reversed(registros):  # ordem cronológica
        if r["tipo"] == "checkin_meta" and r["meta_id"]:
            checkins.setdefault(r["meta_id"], []).append({"em": r["ocorrido_em"], "nivel": r["dados"].get("nivel_gas"),
                                                          "texto": r["texto"]})
    return {
        "formulario_id": formulario_id,
        "crianca": formulario["perfil"],
        "avaliacao_vigente": _enriquecer(repo.avaliacao_vigente(formulario_id)),
        "avaliacoes": repo.listar_avaliacoes(formulario_id),
        "registros": registros,
        "checkins_metas": checkins,
        "estrategias": repo.historico_estrategias(formulario_id),
    }


@router.get("/api/criancas/{formulario_id}/registros")
def listar_registros(formulario_id: str, tipo: str | None = None):
    return repo.listar_registros(formulario_id, tipo)


@router.post("/api/criancas/{formulario_id}/registros", status_code=201)
def criar_registro(formulario_id: str, body: NovoRegistro):
    if not repo.obter_formulario(formulario_id):
        raise HTTPException(404, "Criança/formulário não encontrado.")
    if body.tipo == "feedback_estrategia" and not (body.estrategia and body.resultado):
        raise HTTPException(422, "Informe a estratégia e o resultado.")
    if body.tipo == "checkin_meta" and (not body.meta_id or body.dados.get("nivel_gas") not in (-2, -1, 0, 1, 2)):
        raise HTTPException(422, "Informe a meta e o nível (de -2 a +2).")
    if body.tipo not in ("checkin_meta", "feedback_estrategia") and not body.texto.strip() and not body.dados:
        raise HTTPException(422, "Descreva o registro.")
    vigente = repo.avaliacao_vigente(formulario_id)
    agora = repo.agora()
    return repo.inserir_registro({
        "id": str(uuid4()), "formulario_id": formulario_id, "autor": body.autor, "tipo": body.tipo,
        "texto": body.texto.strip() or None, "dados": body.dados, "dominios": body.dominios, "local": body.local,
        "estrategia": body.estrategia, "resultado": body.resultado, "meta_id": body.meta_id,
        "avaliacao_id": vigente["id"] if vigente else None,
        "ocorrido_em": body.ocorrido_em.isoformat() if body.ocorrido_em else agora, "criado_em": agora,
    })


# ------------------------------------------------------------------ demo
@router.post("/api/demo/formulario", status_code=201)
def formulario_demo():
    """Envia o formulário sintético da Lia (38 meses) pelo mesmo caminho do formulário real."""
    from backend.main import Submission, submit
    return submit(Submission.model_validate(json.loads(EXEMPLO_DEMO.read_text(encoding="utf-8"))))


def aquecer_rag() -> None:
    """Carrega bge-m3 + reranker na GPU ao subir o servidor, para a 1ª busca não esperar ~20 s."""
    if config.RAG_DESATIVADO:
        return
    from src.agente_perfil.ferramentas import _funcao_busca
    threading.Thread(target=_funcao_busca, daemon=True).start()
