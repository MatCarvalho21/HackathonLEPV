"""Banco dos testes.

Padrão: SQLite temporário (rápido, sem rede) — a DATABASE_URL do .env é ignorada.
Com TESTE_PG=1: Postgres da DATABASE_URL (Supabase), num schema temporário criado a partir de
supabase/schema.sql e apagado no fim. Assim os testes nunca tocam nos dados reais.

    .venv/bin/python -m unittest backend.test_agente backend.test_main            # SQLite
    TESTE_PG=1 .venv/bin/python -m unittest backend.test_agente backend.test_main # Supabase
"""
import os
import tempfile
from pathlib import Path
from uuid import uuid4

USAR_PG = os.getenv("TESTE_PG") == "1"
if not USAR_PG:
    os.environ["DATABASE_URL"] = ""  # vazio vence o .env (o config só preenche o que não existe)

RAIZ = Path(__file__).resolve().parents[1]
TABELAS = ["notificacao", "canal_mensagem", "registro", "mensagem", "conversa", "avaliacao", "sessao_agente",
           "formulario", "compartilhamento", "responsavel_crianca", "crianca", "responsavel", "turma", "professor",
           "sessao_login", "conta", "escola"]


class BancoTeste:
    """Uso: preparar() no setUpClass, limpar() no setUp, encerrar() no tearDownClass."""

    def __init__(self):
        self.schema = None
        self.tmp = None

    def preparar(self):
        if not USAR_PG:
            return
        import psycopg
        from src.agente_perfil import config  # noqa: F401  (carrega o .env)
        self.schema = f"teste_{uuid4().hex[:10]}"
        with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as c:
            c.execute(f'CREATE SCHEMA "{self.schema}"')
            c.execute(f'SET search_path TO "{self.schema}", public')
            c.execute((RAIZ / "supabase/schema.sql").read_text(encoding="utf-8"))
        os.environ["PG_SCHEMA"] = self.schema

    def limpar(self):
        """Cada teste começa com o banco vazio."""
        if USAR_PG:
            from src.agente_perfil import repositorio as repo
            with repo.conexao() as db:
                db.execute(f"TRUNCATE {', '.join(TABELAS)} CASCADE")
        else:
            self.tmp = tempfile.TemporaryDirectory(dir=str(RAIZ / "backend"))
            os.environ["FORM_DB"] = self.tmp.name + "/t.sqlite3"

    def depois(self):
        if self.tmp:
            self.tmp.cleanup()
            self.tmp = None
            os.environ.pop("FORM_DB", None)

    def encerrar(self):
        if not USAR_PG:
            return
        import psycopg
        from src.agente_perfil import repositorio as repo
        repo.fechar_pools()
        with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as c:
            c.execute(f'DROP SCHEMA IF EXISTS "{self.schema}" CASCADE')
        os.environ.pop("PG_SCHEMA", None)
