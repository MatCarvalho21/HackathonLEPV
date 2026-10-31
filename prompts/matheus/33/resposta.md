# Conexão com o Supabase testada

## Tentativas
1. **Primeira tentativa:** `password authentication failed`. A URL estava bem formada (usuário, host do pooler, porta e banco certos; sem colchetes do modelo; sem caracteres especiais), ou seja, a senha no `.env` não era a do banco.
2. **Depois do primeiro reset:** a mesma falha.
3. **Com a senha nova:** conectou em ~1s pelo Session pooler (`aws-0-us-east-1.pooler.supabase.com:5432`), PostgreSQL 17.

## Verificação do banco
- **17 tabelas** criadas pelo `supabase/schema.sql`, mais a visão `historico_estrategias` e 30 índices.
- **RLS ligado em todas as tabelas e 0 políticas:** a API pública (chave anon) não acessa nada.
- **Escrita e leitura testadas dentro de uma transação desfeita no fim:** uuid gerado pelo banco, jsonb lido de volta como lista. O banco continua vazio.
- O driver `psycopg[binary]` foi instalado no `.venv`.

## Próximo passo
Adaptar o `repositorio.py` para usar o Postgres quando a `DATABASE_URL` existir, copiar os dados do SQLite (contas, crianças, formulários, avaliações, registros, canal, notificações) e rodar os testes contra o Supabase.

Pendente: o `.env` ainda tem `RAG_DESATIVADO = 1`, que desliga a base de conhecimento do agente.
