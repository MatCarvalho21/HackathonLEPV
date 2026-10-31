# Migração para o Supabase: passo a passo, DDL e credenciais

## O que foi preparado
- `supabase/schema.sql`: DDL completo do banco atual em Postgres nativo (uuid, jsonb, timestamptz, date).
  - Tem as 17 tabelas, os índices e a visão `historico_estrategias`, e pode ser rodado mais de uma vez sem erro.
  - Validado com o parser oficial do Postgres (pglast): 31 comandos válidos.
  - Bate coluna por coluna com o banco SQLite atual.
  - O DDL antigo do prompt 04 tinha só 10 tabelas e não tinha login, compartilhamento, canal, notificações, formulário nem sessão do agente.
- O DDL liga o RLS em todas as tabelas, sem políticas: a API pública do Supabase (chave anon) não acessa nada, e só o backend lê e escreve.

## Passo a passo
1. **Criar o projeto:** em supabase.com → New project. Escolha o nome (ex.: ajudapai), uma senha forte para o banco (guarde: ela vai no `.env`) e a região South America (São Paulo).
2. **Criar as tabelas:** SQL Editor → New query → colar `supabase/schema.sql` → Run. Em Table Editor devem aparecer as 17 tabelas. Alternativa pelo terminal: `psql "$DATABASE_URL" -f supabase/schema.sql`.
3. **Pegar a conexão:** botão **Connect** no topo do projeto → aba de connection string → **Session pooler** (porta 5432, funciona em IPv4). Copie a URI e troque `[YOUR-PASSWORD]` pela senha. A conexão direta (`db.<ref>.supabase.co`) é só IPv6 no plano gratuito, por isso o pooler.
4. **Preencher o `.env`** (ele já está no `.gitignore`):
   ```
   DATABASE_URL=postgresql://postgres.<project-ref>:<senha>@aws-0-sa-east-1.pooler.supabase.com:5432/postgres
   # opcionais, só se um dia o front/back usar a API REST do Supabase:
   SUPABASE_URL=https://<project-ref>.supabase.co
   SUPABASE_SECRET_KEY=<secret / service_role: só no servidor>
   ```
   Se a senha tiver caracteres especiais (`@ : / # ?`), codifique-os na URL (`@` vira `%40`).

## Sobre "deixar aberto via API"
- **Recomendado:** o backend conecta direto no Postgres com a `DATABASE_URL`. Nada precisa ficar aberto. O login do app é próprio (tabelas `conta` e `sessao_login`), não o Supabase Auth, então abrir as tabelas para a chave pública exporia os dados das crianças.
- **API REST (PostgREST):** só faria sentido com a chave secreta no servidor, e exigiria reescrever o `repositorio.py` com o cliente do Supabase. Não compensa: já temos SQL.

## Próximo passo (código)
Com o projeto criado e a `DATABASE_URL` no `.env`, adaptar o `repositorio.py` para Postgres (psycopg) quando `DATABASE_URL` existir, mantendo o SQLite como padrão local. Também um script para copiar os dados atuais do SQLite para o Supabase e testes rodando contra os dois.

## Achado
O `.env` tem `RAG_DESATIVADO = 1`, alterado hoje às 01:38, antes desta sessão. O `config.py` lê o `.env`, então o agente e o chat estavam sem a base de conhecimento, apesar de o backend ter sido subido "com RAG". Remover a linha (ou trocar para 0) e reiniciar o backend reativa.
