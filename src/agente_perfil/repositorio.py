"""Acesso ao banco local da plataforma (SQLite com o esquema de schema_local.sql).

Espelha o modelo Postgres/Supabase de prompts/matheus/04/output.sql para que a troca
por um banco na nuvem seja só trocar esta camada. O arquivo é criado ao primeiro uso
(padrão: backend/data/plataforma.sqlite3; configurável por FORM_DB).
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from src.agente_perfil import config

SCHEMA = (Path(__file__).parent / "schema_local.sql").read_text(encoding="utf-8")
JSON_COLS = {"respostas_formulario", "perfil", "niveis", "metas", "dados", "dominios", "interesses", "sugestoes"}


def agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def novo_id() -> str:
    return str(uuid4())


def caminho_banco() -> Path:
    return Path(os.getenv("FORM_DB", str(config.FORM_DB)))


# Colunas novas em tabelas que já existiam: entram por ALTER TABLE no banco antigo.
MIGRACOES = {
    "responsavel": {"conta_id": "TEXT REFERENCES conta(id)"},
    "professor": {"conta_id": "TEXT REFERENCES conta(id)", "funcao": "TEXT NOT NULL DEFAULT 'professor'",
                  "instituicao": "TEXT"},
}


def _migrar(db) -> None:
    for tabela, colunas in MIGRACOES.items():
        existentes = {r[1] for r in db.execute(f"PRAGMA table_info({tabela})")}
        for col, tipo in colunas.items():
            if col not in existentes:
                db.execute(f"ALTER TABLE {tabela} ADD COLUMN {col} {tipo}")


@contextmanager
def conexao():
    caminho = caminho_banco()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(caminho, timeout=30)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    _migrar(db)
    try:
        yield db
        db.commit()
    finally:
        db.close()


def _linha(row) -> dict | None:
    if row is None:
        return None
    d = dict(row)
    for k in JSON_COLS & d.keys():
        if isinstance(d[k], str):
            d[k] = json.loads(d[k])
    return d


def _inserir(db, tabela: str, valores: dict) -> None:
    vals = {k: json.dumps(v, ensure_ascii=False) if k in JSON_COLS and not isinstance(v, str) else v
            for k, v in valores.items()}
    db.execute(f"INSERT INTO {tabela} ({', '.join(vals)}) VALUES ({', '.join('?' * len(vals))})", list(vals.values()))


def _um(sql: str, args=()) -> dict | None:
    with conexao() as db:
        return _linha(db.execute(sql, args).fetchone())


def _todos(sql: str, args=()) -> list[dict]:
    with conexao() as db:
        return [_linha(r) for r in db.execute(sql, args).fetchall()]


# ------------------------------------------------------------------ pessoas e crianças
def criar_responsavel(nome: str, email: str, telefone: str | None = None) -> dict:
    existente = _um("SELECT * FROM responsavel WHERE lower(email) = lower(?)", (email,))
    if existente:
        return existente
    r = {"id": novo_id(), "nome": nome, "email": email, "telefone": telefone}
    with conexao() as db:
        _inserir(db, "responsavel", r)
    return r


def obter_responsavel(rid: str) -> dict | None:
    return _um("SELECT * FROM responsavel WHERE id = ?", (rid,))


def criar_professor(nome: str, email: str, escola: str, turma: str) -> dict:
    existente = _um("SELECT * FROM professor WHERE lower(email) = lower(?)", (email,))
    if existente:
        return existente
    with conexao() as db:
        esc = db.execute("SELECT id FROM escola WHERE lower(nome) = lower(?)", (escola,)).fetchone()
        escola_id = esc["id"] if esc else novo_id()
        if not esc:
            _inserir(db, "escola", {"id": escola_id, "nome": escola})
        p = {"id": novo_id(), "escola_id": escola_id, "nome": nome, "email": email}
        _inserir(db, "professor", p)
        _inserir(db, "turma", {"id": novo_id(), "escola_id": escola_id, "professor_id": p["id"],
                               "nome": turma, "ano": datetime.now().year})
    return p


def obter_professor(pid: str) -> dict | None:
    return _um("SELECT * FROM professor WHERE id = ?", (pid,))


def criar_crianca(nome: str, data_nascimento: str, interesses: list[str] | None = None,
                  responsavel_id: str | None = None, parentesco: str | None = None,
                  prematuro_semanas: int | None = None, turma_id: str | None = None) -> dict:
    c = {"id": novo_id(), "turma_id": turma_id, "nome": nome, "data_nascimento": data_nascimento,
         "prematuro_semanas": prematuro_semanas, "interesses": interesses or [], "criado_em": agora()}
    with conexao() as db:
        _inserir(db, "crianca", c)
        if responsavel_id:
            _inserir(db, "responsavel_crianca", {"responsavel_id": responsavel_id, "crianca_id": c["id"],
                                                 "parentesco": parentesco, "principal": 1})
    return c


def obter_crianca(cid: str) -> dict | None:
    return _um("SELECT * FROM crianca WHERE id = ?", (cid,))


def criancas_do_responsavel(rid: str) -> list[dict]:
    return _todos("SELECT c.*, rc.parentesco FROM crianca c JOIN responsavel_crianca rc ON rc.crianca_id = c.id "
                  "WHERE rc.responsavel_id = ? ORDER BY c.criado_em", (rid,))


def criancas_do_professor(pid: str) -> list[dict]:
    """Crianças compartilhadas com o acompanhante, com a função dele em cada uma."""
    return _todos("SELECT c.*, cp.funcao FROM crianca c JOIN compartilhamento cp ON cp.crianca_id = c.id "
                  "WHERE cp.professor_id = ? AND cp.status = 'ativo' ORDER BY c.nome", (pid,))


def responsavel_tem_crianca(responsavel_id: str, crianca_id: str) -> bool:
    return _um("SELECT 1 AS ok FROM responsavel_crianca WHERE responsavel_id = ? AND crianca_id = ?",
               (responsavel_id, crianca_id)) is not None


def professor_tem_crianca(professor_id: str, crianca_id: str) -> bool:
    """Acompanhante só acessa crianças compartilhadas com ele (compartilhamento ativo; revogar corta o acesso)."""
    return _um("SELECT 1 AS ok FROM compartilhamento WHERE crianca_id = ? AND professor_id = ? AND status = 'ativo'",
               (crianca_id, professor_id)) is not None


def vincular_turma(crianca_id: str, professor_id: str) -> None:
    with conexao() as db:
        t = db.execute("SELECT id FROM turma WHERE professor_id = ? LIMIT 1", (professor_id,)).fetchone()
        if not t:
            raise ValueError("Professor sem turma.")
        db.execute("UPDATE crianca SET turma_id = ? WHERE id = ?", (t["id"], crianca_id))


def _nascimento_aproximado(idade_meses: int) -> str:
    return (date.today() - timedelta(days=int(idade_meses * 30.44))).isoformat()


# ------------------------------------------------------------------ formulário
def salvar_formulario(payload: dict, crianca_id: str | None = None, autor_id: str | None = None) -> str:
    """Guarda o pacote do formulário. Sem criança informada (CLI, testes), cria uma a partir do perfil."""
    if not crianca_id:
        crianca_id = criar_crianca(payload["perfil"]["apelido"], _nascimento_aproximado(payload["perfil"]["idade_meses"]))["id"]
    payload["crianca_id"] = crianca_id
    professor = payload.get("informante") == "professor"
    with conexao() as db:
        _inserir(db, "formulario", {"id": payload["id"], "crianca_id": crianca_id,
                                    "responsavel_id": None if professor else autor_id,
                                    "professor_id": autor_id if professor else None,
                                    "versao": payload["versao"], "payload": json.dumps(payload, ensure_ascii=False),
                                    "criado_em": payload.get("criado_em") or agora()})
    return crianca_id


def obter_formulario(formulario_id: str) -> dict | None:
    row = _um("SELECT payload, crianca_id FROM formulario WHERE id = ?", (formulario_id,))
    if not row:
        return None
    payload = json.loads(row["payload"])
    payload["crianca_id"] = row["crianca_id"]
    return payload


def ultimo_formulario(crianca_id: str) -> dict | None:
    row = _um("SELECT id FROM formulario WHERE crianca_id = ? ORDER BY criado_em DESC LIMIT 1", (crianca_id,))
    return obter_formulario(row["id"]) if row else None


# ------------------------------------------------------------------ sessões do agente
def salvar_sessao(sessao: dict) -> None:
    sessao["atualizado_em"] = agora()
    with conexao() as db:
        db.execute(
            "INSERT INTO sessao_agente (id, crianca_id, formulario_id, status, estado, criado_em, atualizado_em) "
            "VALUES (?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET status=excluded.status, estado=excluded.estado, "
            "atualizado_em=excluded.atualizado_em",
            (sessao["id"], sessao.get("crianca_id"), sessao["formulario_id"], sessao["status"],
             json.dumps(sessao, ensure_ascii=False), sessao["criado_em"], sessao["atualizado_em"]))


def obter_sessao(sessao_id: str) -> dict | None:
    row = _um("SELECT estado FROM sessao_agente WHERE id = ?", (sessao_id,))
    return json.loads(row["estado"]) if row else None


def sessoes_ativas(crianca_id: str) -> list[dict]:
    return [json.loads(r["estado"]) for r in _todos(
        "SELECT estado FROM sessao_agente WHERE crianca_id = ? AND status IN ('executando','aguardando_responsavel') "
        "ORDER BY atualizado_em DESC", (crianca_id,))]


def sessao_ativa(crianca_id: str) -> dict | None:
    return _um("SELECT id, status, atualizado_em FROM sessao_agente WHERE crianca_id = ? "
               "AND status IN ('executando','aguardando_responsavel') ORDER BY atualizado_em DESC LIMIT 1", (crianca_id,))


# ------------------------------------------------------------------ avaliações
def inserir_avaliacao(av: dict) -> None:
    with conexao() as db:
        _inserir(db, "avaliacao", av)


def obter_avaliacao(avaliacao_id: str) -> dict | None:
    return _um("SELECT * FROM avaliacao WHERE id = ?", (avaliacao_id,))


def atualizar_status_avaliacao(avaliacao_id: str, status: str) -> None:
    with conexao() as db:
        db.execute("UPDATE avaliacao SET status = ? WHERE id = ?", (status, avaliacao_id))


def aprovar_avaliacao(avaliacao_id: str) -> dict:
    """A proposta vira 'vigente'; a vigente anterior da mesma criança vira 'substituida'."""
    with conexao() as db:
        row = db.execute("SELECT crianca_id, status FROM avaliacao WHERE id = ?", (avaliacao_id,)).fetchone()
        if not row:
            raise KeyError(avaliacao_id)
        if row["status"] != "proposta":
            raise ValueError(f"Só é possível aprovar uma proposta (status atual: {row['status']}).")
        db.execute("UPDATE avaliacao SET status='substituida' WHERE crianca_id=? AND status='vigente'", (row["crianca_id"],))
        db.execute("UPDATE avaliacao SET status='vigente', aceita_em=? WHERE id=?", (agora(), avaliacao_id))
    return obter_avaliacao(avaliacao_id)


def listar_avaliacoes(crianca_id: str) -> list[dict]:
    return _todos("SELECT id, status, tipo, avaliacao_anterior_id, comentario_responsavel, niveis, criado_em, aceita_em "
                  "FROM avaliacao WHERE crianca_id = ? ORDER BY criado_em", (crianca_id,))


def avaliacao_vigente(crianca_id: str) -> dict | None:
    return _um("SELECT * FROM avaliacao WHERE crianca_id = ? AND status = 'vigente'", (crianca_id,))


def avaliacao_proposta(crianca_id: str) -> dict | None:
    return _um("SELECT * FROM avaliacao WHERE crianca_id = ? AND status = 'proposta' ORDER BY criado_em DESC LIMIT 1",
               (crianca_id,))


# ------------------------------------------------------------------ registros
def inserir_registro(reg: dict) -> dict:
    reg = {"id": novo_id(), "criado_em": agora(), **reg}
    reg.setdefault("ocorrido_em", reg["criado_em"])
    with conexao() as db:
        _inserir(db, "registro", reg)
    return _um("SELECT * FROM registro WHERE id = ?", (reg["id"],))


def listar_registros(crianca_id: str, tipo: str | None = None, dominio: str | None = None,
                     texto: str | None = None, desde: str | None = None, limite: int = 200) -> list[dict]:
    sql = ("SELECT r.*, coalesce(resp.nome, prof.nome) AS autor_nome, "
           "CASE WHEN r.professor_id IS NOT NULL THEN 'professor' ELSE 'responsavel' END AS autor, "
           "CASE WHEN r.professor_id IS NOT NULL THEN coalesce((SELECT cp.funcao FROM compartilhamento cp "
           "  WHERE cp.crianca_id = r.crianca_id AND cp.professor_id = r.professor_id AND cp.status = 'ativo' LIMIT 1), "
           "  prof.funcao, 'professor') ELSE 'responsavel' END AS autor_funcao "
           "FROM registro r LEFT JOIN responsavel resp ON resp.id = r.responsavel_id "
           "LEFT JOIN professor prof ON prof.id = r.professor_id WHERE r.crianca_id = ?")
    args: list = [crianca_id]
    if tipo:
        sql, args = sql + " AND r.tipo = ?", args + [tipo]
    if dominio:
        sql, args = sql + " AND r.dominios LIKE ?", args + [f'%"{dominio}"%']
    if texto:
        sql, args = sql + " AND (r.texto LIKE ? OR r.dados LIKE ? OR r.estrategia LIKE ?)", args + [f"%{texto}%"] * 3
    if desde:
        sql, args = sql + " AND r.ocorrido_em >= ?", args + [desde]
    return _todos(sql + " ORDER BY r.ocorrido_em DESC, r.criado_em DESC LIMIT ?", args + [limite])


def historico_estrategias(crianca_id: str) -> list[dict]:
    """Equivalente à view historico_estrategias do .sql (inclui comportamentos em que uma dica foi usada)."""
    return _todos("""
        SELECT estrategia, local, count(*) AS tentativas,
               sum(resultado = 'funcionou') AS funcionou, sum(resultado = 'parcial') AS parcial,
               sum(resultado = 'nao_funcionou') AS nao_funcionou, max(ocorrido_em) AS ultima_vez
        FROM registro WHERE crianca_id = ? AND estrategia IS NOT NULL AND resultado IS NOT NULL
        GROUP BY estrategia, local ORDER BY ultima_vez DESC""", (crianca_id,))


# ------------------------------------------------------------------ conversas
def criar_conversa(crianca_id: str, autor: str, autor_id: str, titulo: str | None = None) -> dict:
    c = {"id": novo_id(), "crianca_id": crianca_id, "titulo": titulo, "criado_em": agora(),
         "responsavel_id": autor_id if autor == "responsavel" else None,
         "professor_id": autor_id if autor == "professor" else None}
    with conexao() as db:
        _inserir(db, "conversa", c)
    return c


def obter_conversa(conversa_id: str) -> dict | None:
    return _um("SELECT * FROM conversa WHERE id = ?", (conversa_id,))


def listar_conversas(crianca_id: str) -> list[dict]:
    return _todos("SELECT c.*, (SELECT count(*) FROM mensagem m WHERE m.conversa_id = c.id) AS mensagens, "
                  "(SELECT max(criado_em) FROM mensagem m WHERE m.conversa_id = c.id) AS ultima "
                  "FROM conversa c WHERE c.crianca_id = ? ORDER BY coalesce(ultima, c.criado_em) DESC", (crianca_id,))


def inserir_mensagem(conversa_id: str, papel: str, conteudo: str, sugestoes: dict | None = None) -> dict:
    m = {"id": novo_id(), "conversa_id": conversa_id, "papel": papel, "conteudo": conteudo,
         "sugestoes": sugestoes, "criado_em": agora()}
    with conexao() as db:
        _inserir(db, "mensagem", m)
    return m


def listar_mensagens(conversa_id: str, limite: int = 200) -> list[dict]:
    return _todos("SELECT * FROM (SELECT * FROM mensagem WHERE conversa_id = ? ORDER BY criado_em DESC LIMIT ?) "
                  "ORDER BY criado_em", (conversa_id, limite))


def atualizar_titulo_conversa(conversa_id: str, titulo: str) -> None:
    with conexao() as db:
        db.execute("UPDATE conversa SET titulo = ? WHERE id = ? AND titulo IS NULL", (titulo, conversa_id))


# ------------------------------------------------------------------ contas e login
def obter_conta_por_email(email: str) -> dict | None:
    return _um("SELECT * FROM conta WHERE lower(email) = lower(?)", (email.strip(),))


def obter_conta(conta_id: str) -> dict | None:
    return _um("SELECT * FROM conta WHERE id = ?", (conta_id,))


def criar_conta(nome: str, email: str, senha_hash: str) -> dict:
    c = {"id": novo_id(), "nome": nome, "email": email.strip().lower(), "senha_hash": senha_hash, "criado_em": agora()}
    with conexao() as db:
        _inserir(db, "conta", c)
    return c


def perfis_da_conta(conta_id: str) -> dict:
    """{'responsavel': dict|None, 'professor': dict|None} (professor = acompanhante)."""
    return {"responsavel": _um("SELECT * FROM responsavel WHERE conta_id = ?", (conta_id,)),
            "professor": _um("SELECT * FROM professor WHERE conta_id = ?", (conta_id,))}


def ligar_perfil(tabela: str, perfil_id: str, conta_id: str) -> None:
    assert tabela in ("responsavel", "professor")
    with conexao() as db:
        db.execute(f"UPDATE {tabela} SET conta_id = ? WHERE id = ?", (conta_id, perfil_id))


def criar_acompanhante(nome: str, email: str, funcao: str, instituicao: str | None, conta_id: str | None) -> dict:
    p = {"id": novo_id(), "nome": nome, "email": email.strip().lower(), "funcao": funcao,
         "instituicao": instituicao, "conta_id": conta_id}
    with conexao() as db:
        _inserir(db, "professor", p)
    return _um("SELECT * FROM professor WHERE id = ?", (p["id"],))


def criar_sessao_login(token_hash: str, conta_id: str, expira_em: str) -> None:
    with conexao() as db:
        _inserir(db, "sessao_login", {"token_hash": token_hash, "conta_id": conta_id, "criado_em": agora(),
                                      "expira_em": expira_em})


def conta_do_token(token_hash: str) -> dict | None:
    return _um("SELECT c.* FROM sessao_login s JOIN conta c ON c.id = s.conta_id "
               "WHERE s.token_hash = ? AND s.expira_em > ?", (token_hash, agora()))


def apagar_sessao_login(token_hash: str) -> None:
    with conexao() as db:
        db.execute("DELETE FROM sessao_login WHERE token_hash = ?", (token_hash,))


# ------------------------------------------------------------------ compartilhamento
def listar_compartilhamentos(crianca_id: str) -> list[dict]:
    return _todos("SELECT cp.*, p.nome AS acompanhante_nome FROM compartilhamento cp "
                  "LEFT JOIN professor p ON p.id = cp.professor_id "
                  "WHERE cp.crianca_id = ? AND cp.status IN ('pendente','ativo') ORDER BY cp.criado_em", (crianca_id,))


def obter_compartilhamento(cid: str) -> dict | None:
    return _um("SELECT * FROM compartilhamento WHERE id = ?", (cid,))


def criar_compartilhamento(crianca_id: str, email: str, funcao: str, responsavel_id: str) -> dict:
    email = email.strip().lower()
    existente = _um("SELECT * FROM compartilhamento WHERE crianca_id = ? AND email = ? AND status IN ('pendente','ativo')",
                    (crianca_id, email))
    if existente:
        raise ValueError("Este e-mail já tem acesso ou um convite pendente para esta criança.")
    prof = _um("SELECT p.id FROM professor p LEFT JOIN conta c ON c.id = p.conta_id "
               "WHERE lower(p.email) = ? OR lower(c.email) = ? LIMIT 1", (email, email))
    cp = {"id": novo_id(), "crianca_id": crianca_id, "email": email, "funcao": funcao,
          "professor_id": prof["id"] if prof else None, "responsavel_id": responsavel_id,
          "status": "pendente", "criado_em": agora()}
    with conexao() as db:
        _inserir(db, "compartilhamento", cp)
    return cp


def convites_do_acompanhante(professor_id: str, email: str) -> list[dict]:
    return _todos("SELECT cp.*, c.nome AS crianca_nome, r.nome AS responsavel_nome FROM compartilhamento cp "
                  "JOIN crianca c ON c.id = cp.crianca_id JOIN responsavel r ON r.id = cp.responsavel_id "
                  "WHERE cp.status = 'pendente' AND (cp.professor_id = ? OR (cp.professor_id IS NULL AND cp.email = ?)) "
                  "ORDER BY cp.criado_em DESC", (professor_id, email.strip().lower()))


def responder_compartilhamento(cid: str, professor_id: str, status: str) -> None:
    with conexao() as db:
        db.execute("UPDATE compartilhamento SET status = ?, professor_id = ?, respondido_em = ? WHERE id = ?",
                   (status, professor_id, agora(), cid))


def revogar_compartilhamento(cid: str) -> None:
    with conexao() as db:
        db.execute("UPDATE compartilhamento SET status = 'revogado', respondido_em = ? WHERE id = ?", (agora(), cid))


def equipe_da_crianca(crianca_id: str) -> list[dict]:
    """Responsáveis + acompanhantes com acesso ativo (para o canal e a tela de compartilhamento)."""
    resp = _todos("SELECT r.id, r.nome, 'responsavel' AS papel, coalesce(rc.parentesco, 'Responsável') AS funcao "
                  "FROM responsavel r JOIN responsavel_crianca rc ON rc.responsavel_id = r.id WHERE rc.crianca_id = ?",
                  (crianca_id,))
    acomp = _todos("SELECT p.id, p.nome, 'professor' AS papel, cp.funcao FROM compartilhamento cp "
                   "JOIN professor p ON p.id = cp.professor_id WHERE cp.crianca_id = ? AND cp.status = 'ativo'",
                   (crianca_id,))
    return resp + acomp


# ------------------------------------------------------------------ canal da criança
def inserir_mensagem_canal(crianca_id: str, papel: str, autor_id: str, texto: str) -> dict:
    m = {"id": novo_id(), "crianca_id": crianca_id, "texto": texto, "criado_em": agora(),
         "responsavel_id": autor_id if papel == "responsavel" else None,
         "professor_id": autor_id if papel == "professor" else None}
    with conexao() as db:
        _inserir(db, "canal_mensagem", m)
    return listar_canal(crianca_id, ids=[m["id"]])[0]


def listar_canal(crianca_id: str, depois: str | None = None, ids: list[str] | None = None, limite: int = 300) -> list[dict]:
    sql = ("SELECT m.*, coalesce(r.nome, p.nome) AS autor_nome, "
           "CASE WHEN m.professor_id IS NOT NULL THEN 'professor' ELSE 'responsavel' END AS autor, "
           "CASE WHEN m.professor_id IS NOT NULL THEN coalesce((SELECT cp.funcao FROM compartilhamento cp WHERE "
           "  cp.crianca_id = m.crianca_id AND cp.professor_id = m.professor_id ORDER BY cp.criado_em DESC LIMIT 1), p.funcao) "
           "  ELSE 'responsavel' END AS autor_funcao "
           "FROM canal_mensagem m LEFT JOIN responsavel r ON r.id = m.responsavel_id "
           "LEFT JOIN professor p ON p.id = m.professor_id WHERE m.crianca_id = ?")
    args: list = [crianca_id]
    if depois:
        sql, args = sql + " AND m.criado_em > ?", args + [depois]
    if ids:
        sql, args = sql + f" AND m.id IN ({','.join('?' * len(ids))})", args + ids
    return _todos(f"SELECT * FROM ({sql} ORDER BY m.criado_em DESC LIMIT ?) ORDER BY criado_em", args + [limite])
