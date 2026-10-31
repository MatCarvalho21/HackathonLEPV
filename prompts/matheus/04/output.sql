-- =====================================================================
-- Sistema de acompanhamento infantil — versão hackathon (PostgreSQL / Supabase)
-- 10 tabelas. Relações:
--   escola 1—N turma · professor 1—N turma · turma 1—N crianca
--   responsavel N—N crianca (responsavel_crianca)
--   crianca 1—N avaliacao · crianca 1—N registro · crianca 1—N conversa 1—N mensagem
-- O professor vê as crianças das turmas dele.
-- =====================================================================

create extension if not exists pgcrypto;

create table escola (
  id         uuid primary key default gen_random_uuid(),
  nome       text not null,
  cidade     text
);

create table professor (
  id         uuid primary key default gen_random_uuid(),
  escola_id  uuid references escola(id),
  nome       text not null,
  email      text unique not null
);

create table turma (                               -- a "classe"
  id           uuid primary key default gen_random_uuid(),
  escola_id    uuid not null references escola(id),
  professor_id uuid references professor(id),
  nome         text not null,                     -- ex.: "Pré I B"
  ano          int  not null
);

create table responsavel (
  id         uuid primary key default gen_random_uuid(),
  nome       text not null,
  email      text unique not null,
  telefone   text
);

create table crianca (
  id              uuid primary key default gen_random_uuid(),
  turma_id        uuid references turma(id),        -- null enquanto não tiver escola
  nome            text not null,
  data_nascimento date not null,
  prematuro_semanas int,                            -- idade gestacional, se prematuro
  interesses      text[],
  criado_em       timestamptz not null default now()
);

-- Um responsável pode ter várias crianças e uma criança vários responsáveis
create table responsavel_crianca (
  responsavel_id uuid references responsavel(id),
  crianca_id     uuid references crianca(id),
  parentesco     text,                              -- mãe, pai, avó...
  principal      boolean not null default false,    -- quem aceita a avaliação
  primary key (responsavel_id, crianca_id)
);

-- Avaliação inicial e reavaliações. Cada versão proposta pela IA é uma linha;
-- a que o responsável aceita vira 'vigente' (só uma por criança).
create table avaliacao (
  id                    uuid primary key default gen_random_uuid(),
  crianca_id            uuid not null references crianca(id),
  avaliacao_anterior_id uuid references avaliacao(id),
  tipo                  text not null check (tipo in ('inicial', 'reavaliacao')),
  status                text not null default 'proposta'
                        check (status in ('proposta', 'vigente', 'substituida', 'descartada')),
  respostas_formulario  jsonb not null default '{}', -- {"E7": "as_vezes", "G3": ["aponta"], ...}
  perfil                jsonb not null default '{}', -- pontos fortes, dificuldades, características, resumo
  niveis                jsonb not null default '{}', -- {"COM_E": 4, "FAL": 3, "REG": 2}
  metas                 jsonb not null default '[]', -- [{"id":"m1","horizonte":"curto","dominio":"COM_E","texto":"...","gas":{...}}]
  comentario_responsavel text,                      -- pedido de ajuste que gerou esta versão
  criado_em             timestamptz not null default now(),
  aceita_em             timestamptz
);
create unique index uma_vigente_por_crianca on avaliacao (crianca_id) where status = 'vigente';

-- Todos os registros do dia a dia, de pais e professores
create table registro (
  id             uuid primary key default gen_random_uuid(),
  crianca_id     uuid not null references crianca(id),
  responsavel_id uuid references responsavel(id),   -- preenche um dos dois autores
  professor_id   uuid references professor(id),
  tipo           text not null check (tipo in ('atividade', 'comportamento', 'conquista', 'observacao',
                                               'checkin_meta', 'feedback_estrategia', 'feedback_perfil', 'saude')),
  texto          text,
  dados          jsonb not null default '{}',       -- campos específicos do tipo (ABC, nível de ajuda, nível da meta...)
  dominios       text[],                            -- etiquetas: {COM_E, REG}
  local          text check (local in ('casa', 'escola', 'terapia', 'outro')),
  -- usados pelo chat para não repetir o que não funcionou
  estrategia     text,                              -- ex.: 'aviso_visual'
  resultado      text check (resultado in ('funcionou', 'parcial', 'nao_funcionou')),
  meta_id        text,                              -- id da meta dentro de avaliacao.metas
  avaliacao_id   uuid references avaliacao(id),     -- feedback do professor sobre o perfil
  mensagem_id    uuid,                              -- registro criado pelo atalho do chat
  ocorrido_em    timestamptz not null default now(),
  criado_em      timestamptz not null default now(),
  check (num_nonnulls(responsavel_id, professor_id) = 1),
  check (tipo <> 'saude' or responsavel_id is not null),
  check (tipo <> 'feedback_estrategia' or (estrategia is not null and resultado is not null))
);

create table conversa (
  id             uuid primary key default gen_random_uuid(),
  crianca_id     uuid not null references crianca(id),
  responsavel_id uuid references responsavel(id),
  professor_id   uuid references professor(id),
  titulo         text,
  criado_em      timestamptz not null default now(),
  check (num_nonnulls(responsavel_id, professor_id) = 1)
);

create table mensagem (
  id          uuid primary key default gen_random_uuid(),
  conversa_id uuid not null references conversa(id),
  papel       text not null check (papel in ('usuario', 'assistente')),
  conteudo    text not null,
  sugestoes   jsonb,                               -- cartões: [{"estrategia":"aviso_visual","titulo":"...","passos":[...]}]
  criado_em   timestamptz not null default now()
);

alter table registro add foreign key (mensagem_id) references mensagem(id);

create index on registro (crianca_id, ocorrido_em desc);
create index on registro (crianca_id, estrategia) where estrategia is not null;
create index on mensagem (conversa_id, criado_em);
create index on avaliacao (crianca_id, criado_em desc);

-- Crianças que cada professor vê
create view professor_alunos as
select t.professor_id, c.*
from crianca c join turma t on t.id = c.turma_id;

-- O que já foi tentado com cada criança (vai no contexto do chat)
create view historico_estrategias as
select crianca_id, estrategia, local,
       count(*)                                              as tentativas,
       count(*) filter (where resultado = 'funcionou')        as funcionou,
       count(*) filter (where resultado = 'nao_funcionou')    as nao_funcionou,
       (array_agg(resultado order by ocorrido_em desc))[1]   as ultimo_resultado,
       (array_agg(texto order by ocorrido_em desc))[1]       as ultimo_comentario,
       max(ocorrido_em)                                      as ultima_vez
from registro
where tipo = 'feedback_estrategia'
group by crianca_id, estrategia, local;
