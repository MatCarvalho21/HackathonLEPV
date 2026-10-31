"""Login: contas com e-mail e senha, sessão por token e identificação de quem age.

    POST /api/auth/cadastro   {tipo, nome, email, senha, ...}  → {token, conta, perfis}
    POST /api/auth/entrar     {email, senha}                     → {token, conta, perfis}
    GET  /api/auth/eu                                            → {conta, perfis}
    POST /api/auth/perfis     {tipo, ...}  (conta logada ganha o outro perfil)
    POST /api/auth/sair

Uma conta pode ter dois perfis: RESPONSÁVEL pelo perfil de uma criança e ACOMPANHANTE
(professor, pedagogo, médico, terapeuta, familiar...) de crianças compartilhadas com ela.
O token vai no cabeçalho `Authorization: Bearer <token>`. As rotas descobrem pelo token quem
está agindo e qual o papel dele em cada criança; o corpo das requisições não decide isso.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from src.agente_perfil import repositorio as repo

router = APIRouter(tags=["login"])
ITERACOES = int(os.getenv("SENHA_ITERACOES", "200000"))
DIAS_SESSAO = 30
EMAIL = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

FUNCOES = {"professor": "Professor(a)", "pedagogo": "Pedagogo(a)", "medico": "Médico(a)",
           "terapeuta": "Terapeuta", "familiar": "Familiar", "outro": "Acompanhante"}
Funcao = Literal["professor", "pedagogo", "medico", "terapeuta", "familiar", "outro"]


def rotulo_funcao(funcao: str | None) -> str:
    if funcao == "responsavel":
        return "Responsável"
    return FUNCOES.get(funcao or "", "Acompanhante")


# ------------------------------------------------------------------ senha e token
def hash_senha(senha: str) -> str:
    sal = secrets.token_bytes(16)
    h = hashlib.pbkdf2_hmac("sha256", senha.encode(), sal, ITERACOES)
    return f"pbkdf2${ITERACOES}${sal.hex()}${h.hex()}"


def conferir_senha(senha: str, guardado: str) -> bool:
    try:
        _, it, sal, h = guardado.split("$")
        calc = hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(sal), int(it))
        return hmac.compare_digest(calc.hex(), h)
    except (ValueError, TypeError):
        return False


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def abrir_sessao(conta: dict) -> dict:
    token = secrets.token_urlsafe(32)
    expira = (datetime.now(timezone.utc) + timedelta(days=DIAS_SESSAO)).isoformat()
    repo.criar_sessao_login(_hash_token(token), conta["id"], expira)
    return {"token": token, **resumo_conta(conta)}


def resumo_conta(conta: dict) -> dict:
    p = repo.perfis_da_conta(conta["id"])
    perfis = []
    if p["responsavel"]:
        perfis.append({"papel": "responsavel", "id": p["responsavel"]["id"], "nome": p["responsavel"]["nome"],
                       "rotulo": "Responsável pelo perfil"})
    if p["professor"]:
        perfis.append({"papel": "professor", "id": p["professor"]["id"], "nome": p["professor"]["nome"],
                       "funcao": p["professor"].get("funcao"), "rotulo": f"Acompanhante · {rotulo_funcao(p['professor'].get('funcao'))}"})
    return {"conta": {"id": conta["id"], "nome": conta["nome"], "email": conta["email"]}, "perfis": perfis}


# ------------------------------------------------------------------ quem está agindo
@dataclass
class Ator:
    conta: dict
    responsavel: dict | None
    professor: dict | None  # acompanhante

    def papel_em(self, crianca_id: str) -> tuple[str, str] | None:
        """('responsavel', id) se é responsável pela criança; ('professor', id) se ela foi compartilhada com ele."""
        if self.responsavel and repo.responsavel_tem_crianca(self.responsavel["id"], crianca_id):
            return "responsavel", self.responsavel["id"]
        if self.professor and repo.professor_tem_crianca(self.professor["id"], crianca_id):
            return "professor", self.professor["id"]
        return None


# Cache curto de "quem é este token": evita 3 consultas ao banco em toda requisição.
# Sair e criar perfil invalidam na hora; o resto expira em CACHE_SESSAO_S segundos.
CACHE_SESSAO_S = 60
_cache_sessao: dict[str, tuple[float, Ator]] = {}
_trava_cache = threading.Lock()


def esquecer_sessao(token_hash: str | None = None, conta_id: str | None = None) -> None:
    with _trava_cache:
        for k in [k for k, (_, a) in _cache_sessao.items() if k == token_hash or a.conta["id"] == conta_id]:
            _cache_sessao.pop(k, None)


def ator_atual(authorization: str | None = Header(default=None)) -> Ator:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Entre na sua conta para continuar.")
    th = _hash_token(authorization.split(" ", 1)[1].strip())
    with _trava_cache:
        guardado = _cache_sessao.get(th)
    if guardado and guardado[0] > time.monotonic():
        return guardado[1]
    conta = repo.conta_do_token(th)
    if not conta:
        raise HTTPException(401, "Sua sessão expirou. Entre de novo.")
    p = repo.perfis_da_conta(conta["id"])
    ator = Ator(conta, p["responsavel"], p["professor"])
    with _trava_cache:
        _cache_sessao[th] = (time.monotonic() + CACHE_SESSAO_S, ator)
    return ator


def acesso(ator: Ator, crianca_id: str) -> tuple[str, str]:
    """Papel de quem age nesta criança, ou 403/404."""
    if not repo.obter_crianca(crianca_id):
        raise HTTPException(404, "Criança não encontrada.")
    papel = ator.papel_em(crianca_id)
    if not papel:
        raise HTTPException(403, "Você não tem acesso a esta criança. Peça ao responsável para compartilhar o perfil.")
    return papel


def so_responsavel(ator: Ator, crianca_id: str) -> str:
    """Ações que mudam o perfil, as metas ou quem tem acesso: só o responsável. Devolve o id dele."""
    papel, pid = acesso(ator, crianca_id)
    if papel != "responsavel":
        raise HTTPException(403, "Só o responsável pelo perfil pode fazer isso. Como acompanhante, use os registros, "
                                 "o canal e o chat.")
    return pid


# ------------------------------------------------------------------ rotas
class Cadastro(BaseModel):
    tipo: Literal["responsavel", "acompanhante"]
    nome: str = Field(min_length=1, max_length=120)
    email: str = Field(pattern=EMAIL, max_length=200)
    senha: str = Field(min_length=6, max_length=200)
    telefone: str | None = Field(default=None, max_length=40)
    vinculo: str | None = Field(default=None, max_length=60, description="Responsável: mãe, pai, avó, tutor legal...")
    funcao: Funcao = "professor"
    instituicao: str | None = Field(default=None, max_length=160, description="Acompanhante: escola, clínica...")


class Entrada(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    senha: str = Field(min_length=1, max_length=200)


class NovoPerfil(BaseModel):
    tipo: Literal["responsavel", "acompanhante"]
    telefone: str | None = Field(default=None, max_length=40)
    vinculo: str | None = Field(default=None, max_length=60)
    funcao: Funcao = "professor"
    instituicao: str | None = Field(default=None, max_length=160)


def _criar_perfil(conta: dict, body: Cadastro | NovoPerfil) -> None:
    esquecer_sessao(conta_id=conta["id"])  # o próximo acesso já enxerga o perfil novo
    perfis = repo.perfis_da_conta(conta["id"])
    if body.tipo == "responsavel":
        if perfis["responsavel"]:
            raise HTTPException(409, "Esta conta já tem perfil de responsável.")
        # aproveita um responsável antigo (sem conta) com o mesmo e-mail
        antigo = repo._um("SELECT * FROM responsavel WHERE lower(email) = ? AND conta_id IS NULL", (conta["email"],))
        if antigo:
            repo.ligar_perfil("responsavel", antigo["id"], conta["id"])
        else:
            r = repo.criar_responsavel(conta["nome"], conta["email"], body.telefone)
            repo.ligar_perfil("responsavel", r["id"], conta["id"])
    else:
        if perfis["professor"]:
            raise HTTPException(409, "Esta conta já tem perfil de acompanhante.")
        antigo = repo._um("SELECT * FROM professor WHERE lower(email) = ? AND conta_id IS NULL", (conta["email"],))
        if antigo:
            repo.ligar_perfil("professor", antigo["id"], conta["id"])
        else:
            repo.criar_acompanhante(conta["nome"], conta["email"], body.funcao, body.instituicao, conta["id"])


@router.post("/api/auth/cadastro", status_code=201)
def cadastro(body: Cadastro):
    if repo.obter_conta_por_email(body.email):
        raise HTTPException(409, "Já existe uma conta com este e-mail. Use “Entrar”.")
    conta = repo.criar_conta(body.nome.strip(), body.email, hash_senha(body.senha))
    _criar_perfil(conta, body)
    return abrir_sessao(conta)


@router.post("/api/auth/entrar")
def entrar(body: Entrada):
    conta = repo.obter_conta_por_email(body.email)
    if not conta or not conferir_senha(body.senha, conta["senha_hash"]):
        raise HTTPException(401, "E-mail ou senha incorretos.")
    return abrir_sessao(conta)


@router.get("/api/auth/eu")
def eu(ator: Ator = Depends(ator_atual)):
    return resumo_conta(ator.conta)


@router.post("/api/auth/perfis", status_code=201)
def adicionar_perfil(body: NovoPerfil, ator: Ator = Depends(ator_atual)):
    _criar_perfil(ator.conta, body)
    return resumo_conta(ator.conta)


@router.post("/api/auth/sair")
def sair(authorization: str | None = Header(default=None)):
    if authorization and authorization.lower().startswith("bearer "):
        th = _hash_token(authorization.split(" ", 1)[1].strip())
        repo.apagar_sessao_login(th)
        esquecer_sessao(token_hash=th)
    return {"ok": True}
