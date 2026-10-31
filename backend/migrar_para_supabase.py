"""Copia os dados do SQLite local para o Postgres do Supabase (DATABASE_URL do .env).

    .venv/bin/python -m backend.migrar_para_supabase            # copia e confere
    .venv/bin/python -m backend.migrar_para_supabase --conferir # só compara as contagens

- Pré-requisito: tabelas criadas com supabase/schema.sql.
- Idempotente: linhas que já existem (mesma chave) são ignoradas (ON CONFLICT DO NOTHING).
- Ordem das tabelas respeita as chaves estrangeiras; avaliações vão em ordem de criação
  (uma reavaliação aponta para a anterior).
- Conversões: 0/1 → booleano; texto JSON → jsonb; datas ISO → date/timestamptz (o Postgres converte).
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time

from src.agente_perfil import config

ORDEM = ["escola", "conta", "sessao_login", "professor", "turma", "responsavel", "crianca", "responsavel_crianca",
         "compartilhamento", "formulario", "sessao_agente", "avaliacao", "conversa", "mensagem", "registro",
         "canal_mensagem", "notificacao"]
CHAVE = {"responsavel_crianca": "(responsavel_id, crianca_id)", "sessao_login": "(token_hash)"}
BOOLEANOS = {("responsavel_crianca", "principal")}
ORDENAR = {"avaliacao": "criado_em", "mensagem": "criado_em", "registro": "criado_em"}


def _sqlite(caminho) -> sqlite3.Connection:
    db = sqlite3.connect(caminho)
    db.row_factory = sqlite3.Row
    return db


def contagens(pg, lite) -> list[tuple[str, int, int]]:
    out = []
    for t in ORDEM:
        n_lite = lite.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        n_pg = pg.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        out.append((t, n_lite, n_pg))
    return out


def migrar(pg, lite) -> None:
    for t in ORDEM:
        cols = [r[1] for r in lite.execute(f"PRAGMA table_info({t})")]
        ordem = f" ORDER BY {ORDENAR[t]}" if t in ORDENAR else ""
        linhas = lite.execute(f"SELECT {', '.join(cols)} FROM {t}{ordem}").fetchall()
        if not linhas:
            print(f"  {t:20s} vazio")
            continue
        valores = [tuple(bool(r[c]) if (t, c) in BOOLEANOS and r[c] is not None else r[c] for c in cols) for r in linhas]
        sql = (f"INSERT INTO {t} ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))}) "
               f"ON CONFLICT {CHAVE.get(t, '(id)')} DO NOTHING")
        inicio = time.time()
        with pg.cursor() as cur:
            cur.executemany(sql, valores)
        print(f"  {t:20s} {len(valores):5d} linha(s) em {time.time() - inicio:.1f}s")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--conferir", action="store_true", help="Só compara as contagens, sem copiar")
    a = ap.parse_args()
    url = os.getenv("DATABASE_URL")
    if not url:
        print("Defina DATABASE_URL no .env (connection string do Supabase).")
        return 1
    import psycopg

    caminho = config.FORM_DB
    print(f"SQLite de origem: {caminho}")
    lite = _sqlite(caminho)
    with psycopg.connect(url, connect_timeout=15) as pg:
        if not a.conferir:
            print("Copiando para o Supabase…")
            with pg.transaction():  # tudo ou nada
                migrar(pg, lite)
        print("\nConferência (SQLite → Supabase):")
        ok = True
        for t, n_lite, n_pg in contagens(pg, lite):
            marca = "ok" if n_pg >= n_lite else "FALTANDO"
            ok &= n_pg >= n_lite
            print(f"  {t:20s} {n_lite:5d} → {n_pg:5d}  {marca}")
    print("\nTudo copiado." if ok else "\nHá diferenças: confira as linhas marcadas.")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
