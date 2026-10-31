"""Notificações da equipe de cada criança.

Quem recebe (por conta de login; quem fez a ação nunca recebe):
- novo registro do dia a dia          → responsável e acompanhantes da criança
- mensagem no canal                    → idem
- nova versão do perfil aprovada       → acompanhantes
- convite para acompanhar              → a pessoa convidada (se já tiver conta)
- convite aceito                       → o responsável que convidou

Ficam até a pessoa abrir (vira "lida") ou apagar.

    GET    /api/eu/notificacoes                 → {nao_lidas, notificacoes}
    POST   /api/notificacoes/{id}/lida
    DELETE /api/notificacoes/{id}
    POST   /api/eu/notificacoes/ler-todas       {crianca_id?, tipo?}
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.auth import Ator, ator_atual, rotulo_funcao
from src.agente_perfil import repositorio as repo

router = APIRouter(tags=["notificações"])

TIPOS_REGISTRO = {"atividade": "uma atividade", "comportamento": "um comportamento", "conquista": "uma conquista",
                  "observacao": "uma observação", "checkin_meta": "o progresso de uma meta",
                  "feedback_estrategia": "uma estratégia testada", "feedback_perfil": "um comentário sobre o perfil",
                  "saude": "um registro de saúde"}


def _autor(papel: str, perfil_id: str, crianca_id: str) -> tuple[str, str]:
    """(nome, função legível) de quem agiu."""
    if papel == "responsavel":
        r = repo.obter_responsavel(perfil_id) or {}
        vinculo = next((c.get("parentesco") for c in repo.criancas_do_responsavel(perfil_id) if c["id"] == crianca_id), None)
        return r.get("nome", "Responsável"), vinculo or "Responsável"
    p = repo.obter_professor(perfil_id) or {}
    funcao = next((c["funcao"] for c in repo.listar_compartilhamentos(crianca_id) if c["professor_id"] == perfil_id),
                  p.get("funcao"))
    return p.get("nome", "Acompanhante"), rotulo_funcao(funcao)


def _equipe_menos(crianca_id: str, conta_autor: str | None, so_acompanhantes: bool = False) -> list[str]:
    return [e["conta_id"] for e in repo.contas_da_equipe(crianca_id)
            if e["conta_id"] != conta_autor and (not so_acompanhantes or e["papel"] == "professor")]


def _resumo(texto: str | None, limite: int = 140) -> str | None:
    if not texto:
        return None
    t = " ".join(texto.split())
    return t if len(t) <= limite else t[: limite - 1].rsplit(" ", 1)[0] + "…"


def notificar_registro(reg: dict, papel: str, perfil_id: str) -> None:
    crianca = repo.obter_crianca(reg["crianca_id"])
    nome, funcao = _autor(papel, perfil_id, reg["crianca_id"])
    d = reg.get("dados") or {}
    corpo = reg.get("texto") or " → ".join(x for x in (d.get("antecedente"), d.get("comportamento")) if x) or reg.get("estrategia")
    repo.inserir_notificacoes(
        _equipe_menos(reg["crianca_id"], repo.conta_do_perfil(papel, perfil_id)), reg["crianca_id"], "registro",
        f"{nome}, {funcao.lower()}, registrou {TIPOS_REGISTRO.get(reg['tipo'], 'algo')} sobre {crianca['nome']}",
        _resumo(corpo), reg["id"], {"registro_tipo": reg["tipo"], "autor": nome, "funcao": funcao})


def notificar_canal(msg: dict, papel: str, perfil_id: str) -> None:
    crianca = repo.obter_crianca(msg["crianca_id"])
    nome, funcao = _autor(papel, perfil_id, msg["crianca_id"])
    repo.inserir_notificacoes(
        _equipe_menos(msg["crianca_id"], repo.conta_do_perfil(papel, perfil_id)), msg["crianca_id"], "canal",
        f"{nome}, {funcao.lower()}, escreveu no canal de {crianca['nome']}", _resumo(msg["texto"]), msg["id"],
        {"autor": nome, "funcao": funcao})


def notificar_perfil_aprovado(av: dict) -> None:
    crianca = repo.obter_crianca(av["crianca_id"])
    nova = av.get("tipo") == "reavaliacao"
    repo.inserir_notificacoes(
        _equipe_menos(av["crianca_id"], None, so_acompanhantes=True), av["crianca_id"], "perfil",
        f"{'Nova versão do perfil' if nova else 'Perfil'} de {crianca['nome']} aprovado pela família",
        "Veja as áreas, o foco e as metas atualizadas." if nova else "As metas e dicas já estão no painel.", av["id"])


def notificar_convite(cp: dict) -> None:
    conta = repo.obter_conta_por_email(cp["email"])
    if not conta:
        return  # a pessoa vê o convite quando criar a conta
    crianca = repo.obter_crianca(cp["crianca_id"])
    resp = repo.obter_responsavel(cp["responsavel_id"]) or {}
    repo.inserir_notificacoes([conta["id"]], cp["crianca_id"], "convite",
                              f"{resp.get('nome', 'Um responsável')} convidou você para acompanhar {crianca['nome']}",
                              f"Função: {rotulo_funcao(cp['funcao']).lower()}. Aceite na sua visão geral.", cp["id"])


def notificar_convite_aceito(cp: dict, professor_id: str) -> None:
    crianca = repo.obter_crianca(cp["crianca_id"])
    p = repo.obter_professor(professor_id) or {}
    repo.inserir_notificacoes([repo.conta_do_perfil("responsavel", cp["responsavel_id"])], cp["crianca_id"], "acesso",
                              f"{p.get('nome', 'Um acompanhante')} aceitou acompanhar {crianca['nome']}",
                              f"Função: {rotulo_funcao(cp['funcao']).lower()}.", cp["id"])


# ------------------------------------------------------------------ rotas
class LerTodas(BaseModel):
    crianca_id: str | None = None
    tipo: str | None = None


@router.get("/api/eu/notificacoes")
def minhas_notificacoes(ator: Ator = Depends(ator_atual)):
    return {"nao_lidas": repo.contar_nao_lidas(ator.conta["id"]), "notificacoes": repo.listar_notificacoes(ator.conta["id"])}


def _minha(nid: str, ator: Ator) -> dict:
    n = repo.obter_notificacao(nid)
    if not n or n["conta_id"] != ator.conta["id"]:
        raise HTTPException(404, "Notificação não encontrada.")
    return n


@router.post("/api/notificacoes/{nid}/lida")
def marcar_lida(nid: str, ator: Ator = Depends(ator_atual)):
    _minha(nid, ator)
    repo.marcar_notificacoes_lidas(ator.conta["id"], ids=[nid])
    return {"nao_lidas": repo.contar_nao_lidas(ator.conta["id"])}


@router.delete("/api/notificacoes/{nid}")
def apagar(nid: str, ator: Ator = Depends(ator_atual)):
    _minha(nid, ator)
    repo.apagar_notificacao(ator.conta["id"], nid)
    return {"nao_lidas": repo.contar_nao_lidas(ator.conta["id"])}


@router.post("/api/eu/notificacoes/ler-todas")
def ler_todas(body: LerTodas, ator: Ator = Depends(ator_atual)):
    repo.marcar_notificacoes_lidas(ator.conta["id"], crianca_id=body.crianca_id, tipo=body.tipo)
    return {"nao_lidas": repo.contar_nao_lidas(ator.conta["id"])}
