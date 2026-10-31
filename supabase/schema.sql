-- =============================================================================
-- AjudaP.ai: Acompanhamento e Suporte — esquema do banco no Supabase (Postgres)
--
-- Espelha src/agente_perfil/schema_local.sql (SQLite) com tipos nativos do Postgres:
--   TEXT de id → uuid · TEXT ISO-8601 → timestamptz · TEXT com JSON → jsonb · nascimento → date
--
-- Como usar: Supabase → SQL Editor → New query → cole este arquivo inteiro → Run.
-- Pode rodar de novo sem erro (create ... if not exists).
--
-- Segurança: o backend (FastAPI) conecta direto no Postgres e faz a própria autenticação
-- (tabelas conta/sessao_login). Por isso o RLS fica LIGADO em todas as tabelas e SEM políticas:
-- a API pública do Supabase (PostgREST, chave anon) não lê nem escreve nada. Só o backend acessa.
-- =============================================================================

create extension if not exists pgcrypto;  -- gen_random_uuid()

-- ------------------------------------------------------------------ escolas e pessoas
create table if not exists escola (
  id     uuid primary key default gen_random_uuid(),
  nome   text not null,
  cidade text
);

-- Contas de login (e-mail + senha com hash PBKDF2). Uma conta pode ter perfil de responsável e/ou de acompanhante.
create table if not exists conta (
  id         uuid primary key default gen_random_uuid(),
  nome       text not null,
  email      text not null unique,
  senha_hash text not null,
  criado_em  timestamptz not null default now()
);

create table if not exists sessao_login (
  token_hash text primary key,                       -- sha256 do token; o token em si nunca é guardado
  conta_id   uuid not null references conta(id) on delete cascade,
  criado_em  timestamptz not null default now(),
  expira_em  timestamptz not null
);

-- "professor" guarda todos os ACOMPANHANTES (professor, pedagogo, médico, terapeuta, familiar...).
create table if not exists professor (
  id          uuid primary key default gen_random_uuid(),
  escola_id   uuid references escola(id),
  nome        text not null,
  email       text not null unique,
  conta_id    uuid references conta(id),
  funcao      text not null default 'professor'
              check (funcao in ('professor','pedagogo','medico','terapeuta','familiar','outro')),
  instituicao text
);

create table if not exists turma (
  id           uuid primary key default gen_random_uuid(),
  escola_id    uuid not null references escola(id),
  professor_id uuid references professor(id),
  nome         text not null,
  ano          integer not null
);

create table if not exists responsavel (
  id       uuid primary key default gen_random_uuid(),
  nome     text not null,
  email    text not null unique,
  telefone text,
  conta_id uuid references conta(id)
);

create table if not exists crianca (
  id                uuid primary key default gen_random_uuid(),
  turma_id          uuid references turma(id),
  nome              text not null,
  data_nascimento   date not null,
  prematuro_semanas integer,
  interesses        jsonb not null default '[]',
  criado_em         timestamptz not null default now()
);

create table if not exists responsavel_crianca (
  responsavel_id uuid references responsavel(id),
  crianca_id     uuid references crianca(id) on delete cascade,
  parentesco     text,
  principal      boolean not null default false,
  primary key (responsavel_id, crianca_id)
);

-- Responsável compartilha o perfil com um acompanhante (convite por e-mail → aceito ou recusado).
create table if not exists compartilhamento (
  id             uuid primary key default gen_random_uuid(),
  crianca_id     uuid not null references crianca(id) on delete cascade,
  email          text not null,
  funcao         text not null,
  professor_id   uuid references professor(id),
  responsavel_id uuid not null references responsavel(id),
  status         text not null default 'pendente' check (status in ('pendente','ativo','recusado','revogado')),
  criado_em      timestamptz not null default now(),
  respondido_em  timestamptz
);

-- ------------------------------------------------------------------ formulário, agente e avaliações
create table if not exists formulario (
  id             uuid primary key default gen_random_uuid(),
  crianca_id     uuid not null references crianca(id) on delete cascade,
  responsavel_id uuid references responsavel(id),
  professor_id   uuid references professor(id),
  versao         text not null,
  payload        jsonb not null,                     -- pacote completo do formulário (14 domínios)
  criado_em      timestamptz not null default now()
);

create table if not exists sessao_agente (
  id            uuid primary key default gen_random_uuid(),
  crianca_id    uuid references crianca(id) on delete cascade,
  formulario_id uuid not null references formulario(id),
  status        text not null check (status in ('executando','aguardando_responsavel','concluida','erro')),
  estado        jsonb not null,                      -- conversa com o modelo, dossiê, perguntas pendentes...
  criado_em     timestamptz not null default now(),
  atualizado_em timestamptz not null default now()
);

create table if not exists avaliacao (
  id                     uuid primary key default gen_random_uuid(),
  crianca_id             uuid not null references crianca(id) on delete cascade,
  formulario_id          uuid references formulario(id),
  sessao_id              uuid references sessao_agente(id),
  avaliacao_anterior_id  uuid references avaliacao(id),
  tipo                   text not null check (tipo in ('inicial','reavaliacao')),
  status                 text not null default 'proposta' check (status in ('proposta','vigente','substituida','descartada')),
  respostas_formulario   jsonb not null default '{}',
  perfil                 jsonb not null default '{}', -- relatório, fontes, evolução (reavaliação)
  niveis                 jsonb not null default '{}', -- cor de cada uma das 14 áreas
  metas                  jsonb not null default '[]',
  comentario_responsavel text,
  criado_em              timestamptz not null default now(),
  aceita_em              timestamptz
);
create unique index if not exists uma_vigente_por_crianca on avaliacao (crianca_id) where status = 'vigente';

-- ------------------------------------------------------------------ chat com a IA
create table if not exists conversa (
  id             uuid primary key default gen_random_uuid(),
  crianca_id     uuid not null references crianca(id) on delete cascade,
  responsavel_id uuid references responsavel(id),
  professor_id   uuid references professor(id),
  titulo         text,
  criado_em      timestamptz not null default now(),
  check (num_nonnulls(responsavel_id, professor_id) = 1)
);

create table if not exists mensagem (
  id          uuid primary key default gen_random_uuid(),
  conversa_id uuid not null references conversa(id) on delete cascade,
  papel       text not null check (papel in ('usuario','assistente')),
  conteudo    text not null,
  sugestoes   jsonb,                                 -- fontes consultadas, ferramentas usadas
  criado_em   timestamptz not null default now()
);

-- ------------------------------------------------------------------ registros do dia a dia
create table if not exists registro (
  id             uuid primary key default gen_random_uuid(),
  crianca_id     uuid not null references crianca(id) on delete cascade,
  responsavel_id uuid references responsavel(id),
  professor_id   uuid references professor(id),
  tipo           text not null check (tipo in ('atividade','comportamento','conquista','observacao',
                                               'checkin_meta','feedback_estrategia','feedback_perfil','saude')),
  texto          text,
  dados          jsonb not null default '{}',
  dominios       jsonb not null default '[]',
  local          text check (local in ('casa','escola','terapia','outro')),
  estrategia     text,
  resultado      text check (resultado in ('funcionou','parcial','nao_funcionou')),
  meta_id        text,
  avaliacao_id   uuid references avaliacao(id),
  mensagem_id    uuid references mensagem(id),
  ocorrido_em    timestamptz not null default now(),
  criado_em      timestamptz not null default now(),
  check (num_nonnulls(responsavel_id, professor_id) = 1),
  check (tipo <> 'saude' or responsavel_id is not null),
  check (tipo <> 'feedback_estrategia' or (estrategia is not null and resultado is not null))
);

-- ------------------------------------------------------------------ canal e notificações
create table if not exists canal_mensagem (
  id             uuid primary key default gen_random_uuid(),
  crianca_id     uuid not null references crianca(id) on delete cascade,
  responsavel_id uuid references responsavel(id),
  professor_id   uuid references professor(id),
  texto          text not null,
  criado_em      timestamptz not null default now(),
  check (num_nonnulls(responsavel_id, professor_id) = 1)
);

create table if not exists notificacao (
  id         uuid primary key default gen_random_uuid(),
  conta_id   uuid not null references conta(id) on delete cascade,
  crianca_id uuid references crianca(id) on delete cascade,
  tipo       text not null check (tipo in ('registro','canal','perfil','convite','acesso')),
  titulo     text not null,
  texto      text,
  ref_id     text,
  dados      jsonb not null default '{}',
  criado_em  timestamptz not null default now(),
  lida_em    timestamptz
);

-- ------------------------------------------------------------------ índices
create index if not exists registro_crianca_data       on registro (crianca_id, ocorrido_em desc);
create index if not exists registro_crianca_estrategia on registro (crianca_id, estrategia);
create index if not exists mensagem_conversa           on mensagem (conversa_id, criado_em);
create index if not exists avaliacao_crianca           on avaliacao (crianca_id, criado_em desc);
create index if not exists compartilhamento_crianca    on compartilhamento (crianca_id, status);
create index if not exists canal_crianca_data          on canal_mensagem (crianca_id, criado_em);
create index if not exists notificacao_conta           on notificacao (conta_id, lida_em, criado_em desc);
create index if not exists sessao_login_expira         on sessao_login (expira_em);
create unique index if not exists conta_email_minusculo on conta (lower(email));

-- ------------------------------------------------------------------ visão usada pelo painel
create or replace view historico_estrategias as
select crianca_id, estrategia, local, count(*) as tentativas,
       count(*) filter (where resultado = 'funcionou')     as funcionou,
       count(*) filter (where resultado = 'parcial')       as parcial,
       count(*) filter (where resultado = 'nao_funcionou') as nao_funcionou,
       max(ocorrido_em) as ultima_vez
from registro
where estrategia is not null and resultado is not null
group by crianca_id, estrategia, local;

-- ------------------------------------------------------------------ segurança: fecha a API pública
-- RLS ligado e nenhuma política = PostgREST (chaves anon/authenticated) não acessa nada.
-- O backend conecta como "postgres" pela connection string, que ignora o RLS.
do $$
declare t text;
begin
  foreach t in array array['escola','conta','sessao_login','professor','turma','responsavel','crianca',
                           'responsavel_crianca','compartilhamento','formulario','sessao_agente','avaliacao',
                           'conversa','mensagem','registro','canal_mensagem','notificacao']
  loop
    execute format('alter table %I enable row level security', t);
  end loop;
end $$;
alter view historico_estrategias set (security_invoker = true);
