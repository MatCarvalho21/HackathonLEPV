# AjudaP.ai: Acompanhamento e Suporte

Projeto do HackathonLEPV.

Plataforma de acompanhamento do desenvolvimento infantil (0 a 10 anos). A jornada:

1. O responsável pelo perfil (mãe, pai, avó, tutor legal…) cria a conta com e-mail e senha e cadastra a criança.
2. Preenche o formulário inicial com 14 domínios. A fonte das perguntas é `prompts/matheus/07/ouput.json`.
3. Um agente de IA (DeepSeek via Featherless) gera uma **proposta de perfil**: semáforo por domínio, foco, metas de curto, médio e longo prazo e dicas. Ele consulta a base vetorial (`chroma_db/`) e pode fazer perguntas extras ao responsável.
4. O responsável pede ajustes ou aprova a proposta.
5. Com o perfil aprovado, a família entra no **painel da criança**: metas com progresso, dicas e estratégias, registros (conquista, atividade, comportamento, saúde, observação), linha do tempo, diário e o **chat** com um assistente que conhece o perfil e os últimos registros.
6. O responsável **compartilha** o perfil com quem acompanha a criança (professor, pedagogo, médico, terapeuta, familiar): convida pelo e-mail, a pessoa cria a conta de acompanhante e aceita. Cada criança tem um **canal da equipe** para responsável e acompanhantes conversarem, e um **resumo em PDF** para baixar.

**Notificações.** Quando alguém da equipe registra algo ou escreve no canal, os outros (responsável e acompanhantes) recebem uma notificação no sino da barra lateral. Também há avisos de perfil aprovado e de convites. Cada notificação fica até a pessoa abrir (vira lida e leva ao lugar certo) ou apagar.
7. Depois de um tempo, o responsável pede uma **reavaliação**: só com os registros ou atualizando o formulário, que vem pré-preenchido com as últimas respostas e tem as cores recalculadas. O agente recebe o perfil vigente e todos os registros (quem fez, função, quando e o quê), o progresso das metas e as estratégias testadas. Ele pode fazer perguntas e propõe uma nova versão com o balanço da evolução (cores antes → agora, situação de cada meta, conquistas). O responsável pede ajustes ou aprova. A partir da segunda versão, o painel mostra a evolução entre as versões.

**Login e papéis.** Contas com e-mail e senha (hash PBKDF2) e sessão por token (`Authorization: Bearer`). O backend descobre pelo token quem age e o papel dele em cada criança; o corpo da requisição não decide isso. Uma conta pode ter os dois perfis (por exemplo, a avó que é responsável por uma criança e acompanhante de outra) e alterna no menu do perfil.
- **Responsável pelo perfil:** faz tudo. Preenche o formulário, aprova, pede ajuste e reavaliação, registra progresso de metas e saúde, decide quem tem acesso.
- **Acompanhante** (professor, pedagogo, médico, terapeuta, familiar): só nas crianças compartilhadas com ele. Lê o perfil, registra o dia a dia (atividade, comportamento, conquista, observação, estratégia testada), usa o canal, o assistente e o PDF. Não mexe no perfil, nas metas nem em quem tem acesso (o backend responde 403). Internamente o papel se chama `professor`, nome herdado do modelo original.

Contas criadas antes do login (sem senha) são recuperadas criando a conta com o mesmo e-mail.

O app principal é o da **raiz** (`index.html`, `src/App.jsx`, `src/jornada/`). A pasta `frontend/` guarda o primeiro protótipo do formulário e não faz parte do app integrado.

Mais detalhes: agente e chat em [src/agente_perfil/README.md](src/agente_perfil/README.md); RAG em [src/rag/README.md](src/rag/README.md).

## Arquitetura

| Processo | Porta | Função |
| --- | --- | --- |
| Backend FastAPI (`uvicorn backend.main:app`) | 8000 | API, agentes (perfil e chat), banco local, base vetorial |
| Frontend Vite (React, raiz do repositório) | 5173 | Interface. Encaminha `/api` para `127.0.0.1:8000` |

**Banco de dados.** Toda a leitura e escrita passa por [src/agente_perfil/repositorio.py](src/agente_perfil/repositorio.py), que funciona com dois bancos:
- **Supabase (Postgres):** é o padrão quando a `DATABASE_URL` está no `.env`. O esquema fica em [supabase/schema.sql](supabase/schema.sql): 17 tabelas, RLS ligado e sem políticas, ou seja, a API pública do Supabase não acessa nada e só o backend lê e escreve.
- **SQLite local:** sem `DATABASE_URL`, usa `backend/data/plataforma.sqlite3`, criado sozinho a partir de [src/agente_perfil/schema_local.sql](src/agente_perfil/schema_local.sql).

Configurar o Supabase:
1. *SQL Editor* → cole e rode `supabase/schema.sql` (pode rodar de novo sem erro).
2. *Connect* → *Session pooler* → copie a URI para o `.env`: `DATABASE_URL=postgresql://postgres.<ref>:<senha>@aws-0-<região>.pooler.supabase.com:5432/postgres`.
3. Para trazer os dados do SQLite: `.venv/bin/python -m backend.migrar_para_supabase`. O script é idempotente e confere as contagens no fim.

Limite de conexões: o Session pooler gratuito aceita 15 conexões no total, somando todos os processos. Cada processo do backend usa de 2 a 5 (`PG_POOL_MIN` / `PG_POOL_MAX`). Com vários processos no deploy, use o *Transaction pooler* (porta 6543), que já é compatível. Para latência baixa, rode o backend na mesma região AWS do projeto Supabase.

Testes: `.venv/bin/python -m unittest backend.test_agente backend.test_main` usa um SQLite temporário. Com `TESTE_PG=1`, os mesmos testes rodam no Supabase, num schema temporário que é apagado no fim, sem tocar nos dados reais.

**Dados de demonstração.** Gere com `python -m backend.seed`, ou clique em "Família da Lia (responsável)" na tela inicial. A família criada:
- Ana (mãe), responsável.
- **Lia**, com perfil aprovado (relatório real gerado pelo agente) e duas semanas de registros. Serve para testar o painel e o chat na hora.
- **Nina**, só com o cadastro. Serve para rodar a jornada completa: formulário → agente → aprovação.
- Acompanhantes: Prof. Carla (Lia e Nina) e Dr. Rafael, pediatra (Lia). O canal da Lia já tem algumas mensagens.
- Senha de todas as contas de demonstração: `demo1234` (`ana@`, `carla@` e `rafael@demo.primeirospassos`). Na tela inicial, "Família da Lia" e "Professora Carla" entram direto.

## Como acessar e subir a aplicação

### Opção A — Rodar no servidor remoto e acessar por túnel SSH (recomendado)

O servidor tem GPU, a base vetorial e os modelos já baixados. Se a aplicação já estiver rodando nele, basta encaminhar a porta 5173.

**VS Code com Remote-SSH:** abra o painel **Ports** (`Ctrl+J`, aba *Ports*), clique em **Forward a Port**, digite `5173` e abra http://localhost:5173 no seu navegador.

**Terminal da sua máquina, sem VS Code.** Rode o comando no seu computador. Não use o terminal integrado do VS Code, que está no servidor: lá a porta 5173 já está ocupada pelo Vite e o comando falha com `Address already in use`.

```bash
ssh -N -L 5173:127.0.0.1:5173 matheus@10.23.20.12   # ou o mesmo host/alias que você usa no ssh
```

**Para subir no servidor**, use dois terminais a partir da raiz. Também dá para rodar dentro de `tmux`, assim os processos sobrevivem se o SSH cair. O Vite 8 exige Node 20+, e no servidor há um Node 22 em `~/.local/node22`.

```bash
cd /mnt/diskSSD2TB/matheus_2/HackathonLEPV

# (uma vez) dependências do frontend e dados de demonstração
export PATH=$HOME/.local/node22/bin:$PATH
npm install
.venv/bin/python -m backend.seed            # --zerar apaga o banco local e recria

# Terminal 1: backend
RAG_DEVICE=cuda:1 .venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

# Terminal 2: frontend (raiz do repositório)
export PATH=$HOME/.local/node22/bin:$PATH
npx vite --host 127.0.0.1 --port 5173
```

Verificação rápida: `curl http://127.0.0.1:5173/api/health` deve responder `{"status":"ok"}`.

### Opção B — Clonar e rodar na sua máquina

Requisitos:
- Python 3.10+ e **Node.js 20+**;
- cerca de 1 GB livre para o modelo de embedding leve (`intfloat/multilingual-e5-small`, baixado na primeira busca).

GPU não é obrigatória. Se quiser pular o RAG, defina `RAG_DESATIVADO=1`.

> O código precisa estar no GitHub. Faça commit e push no servidor antes de clonar.

**Linux / macOS:**

```bash
git clone git@github.com:MatCarvalho21/HackathonLEPV.git
cd HackathonLEPV
echo "API_KEY=sua-chave-featherless" > .env        # o .env não vai para o git

python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
.venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu   # RAG em CPU (opcional)
.venv/bin/pip install -r src/rag/requirements.txt                               # RAG (opcional)
npm install                                        # frontend (na raiz)
.venv/bin/python -m backend.seed                   # dados de demonstração

# dois terminais, a partir da raiz
RAG_DEVICE=cpu .venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
npx vite --host 127.0.0.1 --port 5173
```

**Windows (PowerShell):**

```powershell
git clone git@github.com:MatCarvalho21/HackathonLEPV.git
cd HackathonLEPV
Set-Content .env "API_KEY=sua-chave-featherless"
python -m venv .venv
.venv\Scripts\python -m pip install -r backend/requirements.txt
.venv\Scripts\python -m pip install torch --index-url https://download.pytorch.org/whl/cpu   # opcional (RAG)
.venv\Scripts\python -m pip install -r src/rag/requirements.txt                             # opcional (RAG)
npm install
.venv\Scripts\python -m backend.seed

# Terminal 1
$env:RAG_DEVICE="cpu"          # ou: $env:RAG_DESATIVADO="1"
.venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
# Terminal 2
npx vite --host 127.0.0.1 --port 5173
```

### Roteiro de demonstração

1. Na tela inicial, clique em **"Entrar na demonstração (família da Lia)"**.
2. **Lia (perfil aprovado):** abra o painel e percorra as abas (Visão geral, Metas, Dicas, Novo registro, Linha do tempo, **Conversar**, Perfil e versões). No chat, pergunte por exemplo *"Ela teve outra crise com o tablet, o que eu tento hoje?"*. O assistente usa as metas, as estratégias que funcionaram ou não e os registros.
3. **Nina (do zero):**
   - clique em **Começar formulário** e depois em **"Preencher com respostas de exemplo"**;
   - clique em **Concluir e gerar mapeamento** e acompanhe o agente ao vivo. Com as respostas de exemplo, ele sempre faz uma pergunta extra;
   - leia a proposta, peça um ajuste (*"Quero focar primeiro no sono"*) e aprove.
4. **Diário e dúvidas:** a aba de dúvidas é o mesmo chat; as observações viram registros no banco.

Cada etapa do agente de perfil leva de 1 a 2 minutos. Uma resposta do chat leva de 3 a 10 segundos.

### Variáveis de ambiente úteis

| Variável | Padrão | Uso |
| --- | --- | --- |
| `API_KEY` (no `.env`) | — | Chave do Featherless |
| `FORM_DB` | `backend/data/plataforma.sqlite3` | Banco local |
| `RAG_DEVICE` | GPU com mais memória livre, ou CPU | `cuda:0`, `cuda:1` ou `cpu` |
| `RAG_DESATIVADO` | `0` | `1` sobe sem a base vetorial |
| `RAG_RERANKER` | `0` | `1` liga o reranker (pesado, ~2,2 GB) |
| `LLM_MODELO` | `deepseek-ai/DeepSeek-V4.1-Flash-1017` | Modelo dos agentes |

### Problemas comuns

- **A página abre, mas as ações falham:** o backend não está rodando na porta 8000 da mesma máquina do Vite.
- **`Address already in use`:** já existe um processo na porta. Veja com `ss -ltnp | grep -E '8000|5173'`.
- **Vite falha com erro de sintaxe ou `Cannot find module`:** use Node 20+ e rode `npm install` na raiz.
- **Agente com erro `RuntimeError: Defina API_KEY`:** falta o `.env` na raiz.
- **"Coleção ... e5small não existe" no log:** a base leve ainda não foi indexada. O sistema usa a coleção antiga (bge-m3) enquanto isso. Ver [src/rag/README.md](src/rag/README.md).

## Fluxo e contrato do formulário

- Perfil: apelido, idade em meses, ano escolar, vínculo do informante, idiomas, interesses, prioridade familiar, prematuridade e perda de habilidades relatada.
- 14 áreas com perguntas do JSON, referência visível, resposta, exemplos e contexto. "Não sei" e "não se aplica" são opções distintas de "ainda não".
- Seleção: última faixa disponível de cada domínio até a idade informada. Para COG, COM_R e COM_E a partir de 6 anos, usa o final do ano escolar anterior. O frontend (`src/questionnaire.js`) e o backend (`backend/main.py`) usam a mesma regra.
- O formulário não calcula escore nem diagnóstico. O semáforo é calculado depois, pelo agente de perfil, com regras em código (`src/agente_perfil/dossie.py`). SAU e CTX permanecem contextuais. Idade corrigida não é calculada.

Endpoints principais:
- **Formulário:** `GET /api/questionario`, `POST /api/formularios`.
- **Agente de perfil:** `/api/avaliacoes/*`, em [backend/avaliacoes.py](backend/avaliacoes.py).
- **Plataforma:** pessoas, crianças, painel, registros, chat e demo, em [backend/plataforma.py](backend/plataforma.py).
- **Documentação interativa:** http://localhost:8000/docs.

Este MVP é local e deve usar dados fictícios. Antes de qualquer uso com famílias reais, ainda é preciso implementar:
- autenticação (hoje o login é só a escolha de perfil, sem senha);
- autorização por vínculo responsável-criança e professor-turma;
- política de retenção;
- migração para o Supabase.

As referências e regras propostas nos prompts ainda exigem revisão profissional.

## Validação

```bash
.venv/bin/python -m unittest backend.test_main backend.test_agente -v   # Windows: .venv\Scripts\python ...
npm run build
```

Os testes do agente e da plataforma usam um LLM falso e cobrem:
- regras do semáforo e validação (linguagem diagnóstica, metas);
- pausa e retomada com perguntas;
- ajuste e aprovação;
- jornada da plataforma (conta → criança → formulário → proposta → vigente);
- registros, painel e turma do professor;
- contexto e ferramentas do chat;
- seed de demonstração.
