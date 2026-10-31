# Aplicação ligada ao Supabase, com RAG ativo

## O que foi feito
- **`src/agente_perfil/repositorio.py`**:
  - usa o Postgres do Supabase quando a `DATABASE_URL` existe no `.env`; sem ela, continua no SQLite local;
  - o resto do backend não mudou;
  - as linhas voltam no mesmo formato nos dois bancos: ids e datas em texto, JSON já convertido;
  - id malformado vira "não encontrado" (404), como antes.
- **SQL portável:** `sum(condição)` virou `CASE`, `LIKE` em JSON ganhou `CAST`, o alias no `ORDER BY` foi para uma subconsulta e `principal` passou a ser booleano.
- **Desempenho:** pool de conexões, leituras em *autocommit* (uma ida e volta), estado da criança com 4 consultas em paralelo (eram 9 em sequência), painel e listas em paralelo e cache de 60s da sessão de login. Medido em regime estável: lista 9,6s → 0,3s, painel 9,9s → 0,9s, canal 3,2s → 0,6s. O que resta é a distância até `us-east-1`; com o deploy na AWS na mesma região, cai para poucos milissegundos por consulta.
- **Limite de conexões:** o Session pooler gratuito aceita 15 conexões no total. O pool ficou com 2 a 5 por processo (`PG_POOL_MIN` / `PG_POOL_MAX`). Para vários processos no deploy, o Transaction pooler (porta 6543) já é compatível.
- **`backend/migrar_para_supabase.py`:** copiou todos os dados do SQLite (17 tabelas; contagens conferidas, todas iguais). É idempotente.
- **Testes:**
  - novo `backend/banco_teste.py`: SQLite temporário por padrão; com `TESTE_PG=1`, Supabase num schema temporário apagado no fim;
  - 20/20 passam no SQLite;
  - no Supabase, os 9 que rodaram passaram, sem erro de conexão (interrompido a pedido, por demora).
- **RAG:** a linha `RAG_DESATIVADO = 1` saiu do `.env`. Teste real no chat: duas buscas na base, com trechos da Caderneta da Criança citados.
- **Navegador:** o fluxo completo (cadastro → convite → aceite → canal → login → PDF → revogação) passou com o app ligado ao Supabase. Os dados de teste foram removidos; ficaram só os reais (Ana, Carla, Rafael, Lia, Nina, Paulo).
- **Dependências** adicionadas a `backend/requirements.txt`: `psycopg[binary]` e `psycopg-pool`. O README ganhou a seção de banco.
