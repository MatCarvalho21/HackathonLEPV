# HackathonLEPV — Primeiros Passos

Plataforma de acompanhamento do desenvolvimento infantil (0 a 10 anos). A jornada:

1. O responsável (ou professor) cria a conta e cadastra a criança.
2. Preenche o formulário inicial com 14 domínios. A fonte das perguntas é `prompts/matheus/07/ouput.json`.
3. Um agente de IA (DeepSeek via Featherless) gera uma **proposta de perfil**: semáforo por domínio, foco, metas de curto, médio e longo prazo e dicas. Ele consulta a base vetorial (`chroma_db/`) e pode fazer perguntas extras ao responsável.
4. O responsável pede ajustes ou aprova a proposta.
5. Com o perfil aprovado, a família entra no **painel da criança**: metas com progresso, dicas e estratégias, registros (conquista, atividade, comportamento, saúde, observação), linha do tempo, diário e o **chat** com um assistente que conhece o perfil e os últimos registros.
6. Depois de um tempo, o responsável pede uma **reavaliação**. O agente recebe o perfil vigente e todos os registros (quem fez, quando e o quê), o progresso das metas e as estratégias testadas. Ele pode fazer perguntas e propõe uma nova versão com o balanço da evolução (cores antes → agora, situação de cada meta, conquistas). O responsável pede ajustes ou aprova. A partir da segunda versão, o painel mostra a evolução entre as versões.

**Papéis.** O **responsável** faz tudo. O **professor** vê as crianças da própria turma, lê o perfil, registra o dia a dia (atividade, comportamento, conquista, observação, estratégia testada) e usa o chat. Ele não preenche o formulário, não mexe no perfil nem nas metas e não registra progresso de meta nem saúde. O backend confere o papel e o vínculo e responde 403. Não há login real na demonstração.

O app principal é o da **raiz** (`index.html`, `src/App.jsx`, `src/jornada/`). A pasta `frontend/` guarda o primeiro protótipo do formulário e não faz parte do app integrado.

Mais detalhes: agente e chat em [src/agente_perfil/README.md](src/agente_perfil/README.md); RAG em [src/rag/README.md](src/rag/README.md).

## Arquitetura

| Processo | Porta | Função |
| --- | --- | --- |
| Backend FastAPI (`uvicorn backend.main:app`) | 8000 | API, agentes (perfil e chat), banco local, base vetorial |
| Frontend Vite (React, raiz do repositório) | 5173 | Interface. Encaminha `/api` para `127.0.0.1:8000` |

**Banco de dados local.** É um SQLite em `backend/data/plataforma.sqlite3` com o mesmo modelo do Postgres/Supabase (`prompts/matheus/04/output.sql` + `src/agente_perfil/migracao_postgres.sql`). As tabelas são escola, professor, turma, responsável, criança, responsável_criança, formulário, avaliação, registro, conversa, mensagem e sessão do agente. O esquema fica em [src/agente_perfil/schema_local.sql](src/agente_perfil/schema_local.sql) e é criado sozinho quando o backend sobe. Toda a leitura e escrita passa por [src/agente_perfil/repositorio.py](src/agente_perfil/repositorio.py). Para ir para o Supabase, basta trocar essa camada.

**Dados de demonstração.** Gere com `python -m backend.seed`, ou clique em "Entrar na demonstração" na tela inicial. A família criada:
- Ana (mãe), responsável.
- **Lia**, com perfil aprovado (relatório real gerado pelo agente) e duas semanas de registros. Serve para testar o painel e o chat na hora.
- **Nina**, só com o cadastro. Serve para rodar a jornada completa: formulário → agente → aprovação.
- Prof. Carla, com a Lia e a Nina na turma dela. Entre por "Entrar como professora (demo)" na tela inicial.

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
