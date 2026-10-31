-- Banco LOCAL (SQLite) da plataforma, espelhando prompts/matheus/04/output.sql (Postgres/Supabase)
-- + as tabelas de src/agente_perfil/migracao_postgres.sql (formulario, sessao_agente).
-- É criado automaticamente quando o backend sobe. Diferenças para o Postgres:
-- uuid → TEXT, jsonb/text[] → TEXT com JSON, timestamptz → TEXT ISO-8601.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS escola (
  id     TEXT PRIMARY KEY,
  nome   TEXT NOT NULL,
  cidade TEXT
);

-- Contas de login (e-mail + senha). Uma conta pode ter perfil de responsável e/ou de acompanhante.
CREATE TABLE IF NOT EXISTS conta (
  id         TEXT PRIMARY KEY,
  nome       TEXT NOT NULL,
  email      TEXT UNIQUE NOT NULL,
  senha_hash TEXT NOT NULL,
  criado_em  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessao_login (
  token_hash TEXT PRIMARY KEY,
  conta_id   TEXT NOT NULL REFERENCES conta(id),
  criado_em  TEXT NOT NULL,
  expira_em  TEXT NOT NULL
);

-- "professor" guarda todos os ACOMPANHANTES (professor, pedagogo, médico, terapeuta, familiar...);
-- o nome da tabela segue o modelo original. A função fica em `funcao`.
CREATE TABLE IF NOT EXISTS professor (
  id        TEXT PRIMARY KEY,
  escola_id TEXT REFERENCES escola(id),
  nome      TEXT NOT NULL,
  email     TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS turma (
  id           TEXT PRIMARY KEY,
  escola_id    TEXT NOT NULL REFERENCES escola(id),
  professor_id TEXT REFERENCES professor(id),
  nome         TEXT NOT NULL,
  ano          INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS responsavel (
  id       TEXT PRIMARY KEY,
  nome     TEXT NOT NULL,
  email    TEXT UNIQUE NOT NULL,
  telefone TEXT
);

CREATE TABLE IF NOT EXISTS crianca (
  id                TEXT PRIMARY KEY,
  turma_id          TEXT REFERENCES turma(id),
  nome              TEXT NOT NULL,
  data_nascimento   TEXT NOT NULL,
  prematuro_semanas INTEGER,
  interesses        TEXT NOT NULL DEFAULT '[]',
  criado_em         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS responsavel_crianca (
  responsavel_id TEXT REFERENCES responsavel(id),
  crianca_id     TEXT REFERENCES crianca(id),
  parentesco     TEXT,
  principal      INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (responsavel_id, crianca_id)
);

CREATE TABLE IF NOT EXISTS formulario (
  id             TEXT PRIMARY KEY,
  crianca_id     TEXT NOT NULL REFERENCES crianca(id),
  responsavel_id TEXT REFERENCES responsavel(id),
  professor_id   TEXT REFERENCES professor(id),
  versao         TEXT NOT NULL,
  payload        TEXT NOT NULL,
  criado_em      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessao_agente (
  id            TEXT PRIMARY KEY,
  crianca_id    TEXT REFERENCES crianca(id),
  formulario_id TEXT NOT NULL REFERENCES formulario(id),
  status        TEXT NOT NULL CHECK (status IN ('executando','aguardando_responsavel','concluida','erro')),
  estado        TEXT NOT NULL,
  criado_em     TEXT NOT NULL,
  atualizado_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS avaliacao (
  id                     TEXT PRIMARY KEY,
  crianca_id             TEXT NOT NULL REFERENCES crianca(id),
  formulario_id          TEXT REFERENCES formulario(id),
  sessao_id              TEXT REFERENCES sessao_agente(id),
  avaliacao_anterior_id  TEXT REFERENCES avaliacao(id),
  tipo                   TEXT NOT NULL CHECK (tipo IN ('inicial','reavaliacao')),
  status                 TEXT NOT NULL DEFAULT 'proposta' CHECK (status IN ('proposta','vigente','substituida','descartada')),
  respostas_formulario   TEXT NOT NULL DEFAULT '{}',
  perfil                 TEXT NOT NULL DEFAULT '{}',
  niveis                 TEXT NOT NULL DEFAULT '{}',
  metas                  TEXT NOT NULL DEFAULT '[]',
  comentario_responsavel TEXT,
  criado_em              TEXT NOT NULL,
  aceita_em              TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS uma_vigente_por_crianca ON avaliacao (crianca_id) WHERE status = 'vigente';

CREATE TABLE IF NOT EXISTS conversa (
  id             TEXT PRIMARY KEY,
  crianca_id     TEXT NOT NULL REFERENCES crianca(id),
  responsavel_id TEXT REFERENCES responsavel(id),
  professor_id   TEXT REFERENCES professor(id),
  titulo         TEXT,
  criado_em      TEXT NOT NULL,
  CHECK ((responsavel_id IS NOT NULL) + (professor_id IS NOT NULL) = 1)
);

CREATE TABLE IF NOT EXISTS mensagem (
  id          TEXT PRIMARY KEY,
  conversa_id TEXT NOT NULL REFERENCES conversa(id),
  papel       TEXT NOT NULL CHECK (papel IN ('usuario','assistente')),
  conteudo    TEXT NOT NULL,
  sugestoes   TEXT,                       -- JSON: fontes consultadas, ferramentas usadas
  criado_em   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS registro (
  id             TEXT PRIMARY KEY,
  crianca_id     TEXT NOT NULL REFERENCES crianca(id),
  responsavel_id TEXT REFERENCES responsavel(id),
  professor_id   TEXT REFERENCES professor(id),
  tipo           TEXT NOT NULL CHECK (tipo IN ('atividade','comportamento','conquista','observacao',
                                               'checkin_meta','feedback_estrategia','feedback_perfil','saude')),
  texto          TEXT,
  dados          TEXT NOT NULL DEFAULT '{}',
  dominios       TEXT NOT NULL DEFAULT '[]',
  local          TEXT CHECK (local IN ('casa','escola','terapia','outro')),
  estrategia     TEXT,
  resultado      TEXT CHECK (resultado IN ('funcionou','parcial','nao_funcionou')),
  meta_id        TEXT,
  avaliacao_id   TEXT REFERENCES avaliacao(id),
  mensagem_id    TEXT REFERENCES mensagem(id),
  ocorrido_em    TEXT NOT NULL,
  criado_em      TEXT NOT NULL,
  CHECK ((responsavel_id IS NOT NULL) + (professor_id IS NOT NULL) = 1),
  CHECK (tipo <> 'saude' OR responsavel_id IS NOT NULL),
  CHECK (tipo <> 'feedback_estrategia' OR (estrategia IS NOT NULL AND resultado IS NOT NULL))
);

-- Responsável compartilha o perfil com um acompanhante (convite por e-mail → aceito ou recusado).
CREATE TABLE IF NOT EXISTS compartilhamento (
  id             TEXT PRIMARY KEY,
  crianca_id     TEXT NOT NULL REFERENCES crianca(id),
  email          TEXT NOT NULL,
  funcao         TEXT NOT NULL,
  professor_id   TEXT REFERENCES professor(id),
  responsavel_id TEXT NOT NULL REFERENCES responsavel(id),
  status         TEXT NOT NULL DEFAULT 'pendente' CHECK (status IN ('pendente','ativo','recusado','revogado')),
  criado_em      TEXT NOT NULL,
  respondido_em  TEXT
);

-- Canal direto da criança: responsável e acompanhantes conversam entre si.
CREATE TABLE IF NOT EXISTS canal_mensagem (
  id             TEXT PRIMARY KEY,
  crianca_id     TEXT NOT NULL REFERENCES crianca(id),
  responsavel_id TEXT REFERENCES responsavel(id),
  professor_id   TEXT REFERENCES professor(id),
  texto          TEXT NOT NULL,
  criado_em      TEXT NOT NULL,
  CHECK ((responsavel_id IS NOT NULL) + (professor_id IS NOT NULL) = 1)
);

CREATE INDEX IF NOT EXISTS compartilhamento_crianca ON compartilhamento (crianca_id, status);
CREATE INDEX IF NOT EXISTS canal_crianca_data ON canal_mensagem (crianca_id, criado_em);
CREATE INDEX IF NOT EXISTS registro_crianca_data ON registro (crianca_id, ocorrido_em DESC);
CREATE INDEX IF NOT EXISTS registro_crianca_estrategia ON registro (crianca_id, estrategia);
CREATE INDEX IF NOT EXISTS mensagem_conversa ON mensagem (conversa_id, criado_em);
CREATE INDEX IF NOT EXISTS avaliacao_crianca ON avaliacao (crianca_id, criado_em DESC);
