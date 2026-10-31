-- Complemento a prompts/matheus/04/output.sql para o agente de mapeamento de perfil.
-- A tabela `avaliacao` já atende: respostas_formulario, perfil (relatório completo + fontes),
-- niveis ({"COM_E": "amarelo", ...}) e metas. Falta guardar o formulário bruto e o estado do loop.

create table formulario (
  id          uuid primary key default gen_random_uuid(),
  crianca_id  uuid references crianca(id),
  responsavel_id uuid references responsavel(id),
  versao      text not null,
  payload     jsonb not null,                       -- pacote de POST /api/formularios
  criado_em   timestamptz not null default now()
);

-- Estado do loop agêntico: permite pausar quando o agente faz perguntas ao responsável
-- e auditar cada passo (buscas na base, perguntas, erros de validação).
create table sessao_agente (
  id                  uuid primary key default gen_random_uuid(),
  formulario_id       uuid not null references formulario(id),
  avaliacao_id        uuid references avaliacao(id),           -- preenchido ao concluir
  status              text not null check (status in ('executando', 'aguardando_responsavel', 'concluida', 'erro')),
  estado              jsonb not null,                           -- mensagens, perguntas pendentes, fontes kb, uso de tokens
  criado_em           timestamptz not null default now(),
  atualizado_em       timestamptz not null default now()
);

alter table avaliacao add column formulario_id uuid references formulario(id);
alter table avaliacao add column sessao_id uuid references sessao_agente(id);
