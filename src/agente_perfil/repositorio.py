"""Persistência local (SQLite) espelhando a tabela `avaliacao` de prompts/matheus/04/output.sql.

`sessao_agente` guarda o estado do loop (histórico de mensagens, perguntas pendentes,
fontes consultadas) para pausar enquanto o responsável responde e retomar depois.
Na migração para Postgres/Supabase, ver src/agente_perfil/migracao_postgres.sql.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from src.agente_perfil import config

DDL = """
CREATE TABLE IF NOT EXISTS submissions (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessao_agente (
  id TEXT PRIMARY KEY,
  formulario_id TEXT NOT NULL,
  status TEXT NOT NULL,          -- executando | aguardando_responsavel | concluida | erro
  estado TEXT NOT NULL,          -- JSON com mensagens, perguntas pendentes, fontes, uso de tokens
  criado_em TEXT NOT NULL,
  atualizado_em TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS avaliacao (
  id TEXT PRIMARY KEY,
  crianca_id TEXT,
  formulario_id TEXT NOT NULL,
  sessao_id TEXT,
  avaliacao_anterior_id TEXT,
  tipo TEXT NOT NULL CHECK (tipo IN ('inicial','reavaliacao')),
  status TEXT NOT NULL DEFAULT 'proposta' CHECK (status IN ('proposta','vigente','substituida','descartada')),
  respostas_formulario TEXT NOT NULL DEFAULT '{}',
  perfil TEXT NOT NULL DEFAULT '{}',
  niveis TEXT NOT NULL DEFAULT '{}',
  metas TEXT NOT NULL DEFAULT '[]',
  comentario_responsavel TEXT,
  criado_em TEXT NOT NULL,
  aceita_em TEXT
);
CREATE TABLE IF NOT EXISTS registro (       -- mesmo desenho de prompts/matheus/04/output.sql
  id TEXT PRIMARY KEY,
  formulario_id TEXT NOT NULL,                -- identifica a criança no MVP local
  autor TEXT NOT NULL DEFAULT 'responsavel' CHECK (autor IN ('responsavel','professor')),
  tipo TEXT NOT NULL CHECK (tipo IN ('atividade','comportamento','conquista','observacao',
                                     'checkin_meta','feedback_estrategia','feedback_perfil','saude')),
  texto TEXT,
  dados TEXT NOT NULL DEFAULT '{}',
  dominios TEXT NOT NULL DEFAULT '[]',
  local TEXT CHECK (local IN ('casa','escola','terapia','outro')),
  estrategia TEXT,
  resultado TEXT CHECK (resultado IN ('funcionou','parcial','nao_funcionou')),
  meta_id TEXT,
  avaliacao_id TEXT,
  ocorrido_em TEXT NOT NULL,
  criado_em TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS registro_crianca ON registro (formulario_id, ocorrido_em DESC);
CREATE UNIQUE INDEX IF NOT EXISTS uma_vigente_por_formulario ON avaliacao (formulario_id) WHERE status = 'vigente';
"""

JSON_COLS = ("respostas_formulario", "perfil", "niveis", "metas")


def agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _caminho() -> Path:
    import os
    return Path(os.getenv("FORM_DB", str(config.FORM_DB)))


@contextmanager
def conexao():
    caminho = _caminho()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(caminho)
    db.row_factory = sqlite3.Row
    db.executescript(DDL)
    try:
        yield db
        db.commit()
    finally:
        db.close()


def obter_formulario(formulario_id: str) -> dict | None:
    with conexao() as db:
        row = db.execute("SELECT payload FROM submissions WHERE id = ?", (formulario_id,)).fetchone()
    return json.loads(row["payload"]) if row else None


def salvar_formulario(payload: dict) -> None:
    with conexao() as db:
        db.execute("INSERT OR REPLACE INTO submissions VALUES (?, ?)", (payload["id"], json.dumps(payload, ensure_ascii=False)))


def salvar_sessao(sessao: dict) -> None:
    sessao["atualizado_em"] = agora()
    with conexao() as db:
        db.execute(
            "INSERT INTO sessao_agente (id, formulario_id, status, estado, criado_em, atualizado_em) VALUES (?,?,?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET status=excluded.status, estado=excluded.estado, atualizado_em=excluded.atualizado_em",
            (sessao["id"], sessao["formulario_id"], sessao["status"], json.dumps(sessao, ensure_ascii=False),
             sessao["criado_em"], sessao["atualizado_em"]))


def obter_sessao(sessao_id: str) -> dict | None:
    with conexao() as db:
        row = db.execute("SELECT estado FROM sessao_agente WHERE id = ?", (sessao_id,)).fetchone()
    return json.loads(row["estado"]) if row else None


def inserir_avaliacao(av: dict) -> None:
    cols = list(av)
    vals = [json.dumps(av[c], ensure_ascii=False) if c in JSON_COLS else av[c] for c in cols]
    with conexao() as db:
        db.execute(f"INSERT INTO avaliacao ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})", vals)


def obter_avaliacao(avaliacao_id: str) -> dict | None:
    with conexao() as db:
        row = db.execute("SELECT * FROM avaliacao WHERE id = ?", (avaliacao_id,)).fetchone()
    if not row:
        return None
    av = dict(row)
    for c in JSON_COLS:
        av[c] = json.loads(av[c])
    return av


def atualizar_status_avaliacao(avaliacao_id: str, status: str) -> None:
    with conexao() as db:
        db.execute("UPDATE avaliacao SET status = ? WHERE id = ?", (status, avaliacao_id))


def aprovar_avaliacao(avaliacao_id: str) -> dict:
    """A proposta vira 'vigente'; a vigente anterior da mesma criança vira 'substituida'."""
    with conexao() as db:
        row = db.execute("SELECT formulario_id, status FROM avaliacao WHERE id = ?", (avaliacao_id,)).fetchone()
        if not row:
            raise KeyError(avaliacao_id)
        if row["status"] != "proposta":
            raise ValueError(f"Só é possível aprovar uma proposta (status atual: {row['status']}).")
        db.execute("UPDATE avaliacao SET status='substituida' WHERE formulario_id=? AND status='vigente'",
                   (row["formulario_id"],))
        db.execute("UPDATE avaliacao SET status='vigente', aceita_em=? WHERE id=?", (agora(), avaliacao_id))
    return obter_avaliacao(avaliacao_id)


# ------------------------------------------------------------------ registros e painel
def inserir_registro(reg: dict) -> dict:
    reg = {**reg, "dados": json.dumps(reg.get("dados") or {}, ensure_ascii=False),
           "dominios": json.dumps(reg.get("dominios") or [], ensure_ascii=False)}
    cols = list(reg)
    with conexao() as db:
        db.execute(f"INSERT INTO registro ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})", [reg[c] for c in cols])
    return listar_registros(reg["formulario_id"], id_=reg["id"])[0]


def listar_registros(formulario_id: str, tipo: str | None = None, id_: str | None = None, limite: int = 200) -> list[dict]:
    sql, args = "SELECT * FROM registro WHERE formulario_id = ?", [formulario_id]
    if tipo:
        sql, args = sql + " AND tipo = ?", args + [tipo]
    if id_:
        sql, args = sql + " AND id = ?", args + [id_]
    with conexao() as db:
        rows = db.execute(sql + " ORDER BY ocorrido_em DESC, criado_em DESC LIMIT ?", args + [limite]).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["dados"], d["dominios"] = json.loads(d["dados"]), json.loads(d["dominios"])
        out.append(d)
    return out


def listar_avaliacoes(formulario_id: str) -> list[dict]:
    with conexao() as db:
        rows = db.execute("SELECT id, status, tipo, avaliacao_anterior_id, comentario_responsavel, criado_em, aceita_em "
                          "FROM avaliacao WHERE formulario_id = ? ORDER BY criado_em", (formulario_id,)).fetchall()
    return [dict(r) for r in rows]


def avaliacao_vigente(formulario_id: str) -> dict | None:
    with conexao() as db:
        row = db.execute("SELECT id FROM avaliacao WHERE formulario_id = ? AND status = 'vigente'", (formulario_id,)).fetchone()
    return obter_avaliacao(row["id"]) if row else None


def historico_estrategias(formulario_id: str) -> list[dict]:
    """Equivalente à view historico_estrategias do .sql."""
    with conexao() as db:
        rows = db.execute("""
            SELECT estrategia, local, count(*) AS tentativas,
                   sum(resultado = 'funcionou') AS funcionou, sum(resultado = 'parcial') AS parcial,
                   sum(resultado = 'nao_funcionou') AS nao_funcionou, max(ocorrido_em) AS ultima_vez
            FROM registro WHERE formulario_id = ? AND estrategia IS NOT NULL AND resultado IS NOT NULL
            GROUP BY estrategia, local ORDER BY ultima_vez DESC""", (formulario_id,)).fetchall()
    return [dict(r) for r in rows]
