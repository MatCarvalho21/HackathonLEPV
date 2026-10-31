# Banco local, integração com o app do Otavio, chat da criança e RAG leve

Tudo está implementado, testado e rodando em http://localhost:5173.

## 1. Banco de dados local
- **Esquema:** SQLite em `backend/data/plataforma.sqlite3` com o **mesmo modelo do Supabase** (`prompts/matheus/04/output.sql` + `migracao_postgres.sql`): escola, professor, turma, responsável, criança, responsavel_crianca, formulário, avaliação, registro, conversa, mensagem e sessao_agente. O esquema está em `src/agente_perfil/schema_local.sql` e é criado quando o backend sobe.
- **Acesso:** todo acesso passa por `src/agente_perfil/repositorio.py`. Migrar para o Supabase = trocar essa camada.
- **Seed:** `python -m backend.seed` (ou o botão "Entrar na demonstração") cria:
  - a Ana (mãe);
  - a **Lia**, com perfil aprovado (o relatório real da rodada 21) e 14 registros em 2 semanas;
  - a **Nina**, sem formulário, para rodar a jornada;
  - a Prof. Carla, com a Lia na turma.

## 2. Integração com o app do Otavio (raiz)
- O app da raiz virou o principal. As telas dele foram mantidas (boas-vindas, cadastro, painel, formulário, diário), e o **localStorage foi trocado pela API**: no navegador fica só a sessão.
- As metas geradas localmente e a tela `Goals` saíram. Em seu lugar entram o agente ao vivo, a proposta com ajuste e aprovação, e o painel com abas. Os componentes novos estão em `src/jornada/`, com CSS prefixado `pp-` e usando as variáveis e classes dele (`btn-primary`, `panel`, `section-kicker`).
- O formulário ganhou **"Preencher com respostas de exemplo"**, que liga o modo demo (o agente faz uma pergunta extra).
- O diário grava no banco (`registro`). A aba "Dúvida sobre a criança", que dizia "aguardando integração do modelo", agora é o chat.
- `frontend/` voltou ao original do Igor (protótipo).
- **Ambiente:** o Vite 8 da raiz exige Node 20+, então instalei o Node 22 em `~/.local/node22`. O `node_modules` versionado estava quebrado (o `.gitignore` ignorava `dist/`): tirei-o do git (`git rm --cached`) e coloquei `node_modules/` no `.gitignore`. Cada pessoa roda `npm install`.

## 3. Chat no perfil da criança
- Fica na aba **Conversar** do painel (atalho na barra lateral) e também no Diário.
- **Contexto:** o prompt recebe o **resumo ativo**, gerado por código: perfil vigente, semáforo, foco, metas com o último check-in, dicas, estratégias que funcionaram ou não, e os 15 registros mais recentes.
- **Ferramentas:** `buscar_registros` (SQL) e `consultar_base_conhecimento` (RAG).
- **Teste real:** à pergunta *"teve outra crise com o tablet, o que eu tento hoje?"*, ele buscou os registros sobre o tablet, lembrou que o aviso único não funcionou e que o cantinho da calma funcionou, e propôs uma variação usando a música da creche. Para *"o que a pediatra disse?"*, filtrou os registros de saúde.
- Endureci a regra de citação: só cita um documento se o trecho veio da busca.

## 4. RAG leve
- **Padrão novo:** `intfloat/multilingual-e5-small` (cerca de 470 MB, roda em CPU), com prefixos `query:`/`passage:`, numa coleção nova `desenvolvimento_infantil_kb_e5small`. O modelo fica gravado na metadata da coleção.
- **Reranker:** agora é opcional (`RAG_RERANKER=1`).
- **Fallback:** até você reindexar, o sistema usa a coleção antiga com bge-m3.
- **Para reindexar** (os Markdowns são reaproveitados): `RAG_DEVICE=cuda:1 python -m src.rag.indexer` (cerca de 1 minuto na GPU). Depois, reinicie o backend.

## Validação
- **Testes:** 11 testes passando (jornada da plataforma, registros, turma do professor, contexto e ferramentas do chat, seed).
- **Interface:** navegação completa com Playwright, sem erros no console. A Nina foi do formulário à pergunta extra (15 s), à proposta (75 s) e ao painel aprovado.
