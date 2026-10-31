# HackathonLEPV — Primeiros Passos

Plataforma de acompanhamento do desenvolvimento infantil (0 a 10 anos). A jornada tem cinco etapas:

1. A família preenche o formulário inicial com 14 domínios. A fonte das perguntas é `prompts/matheus/07/ouput.json`.
2. Um agente de IA (DeepSeek via Featherless) gera uma proposta de perfil: semáforo por domínio, foco, metas de curto, médio e longo prazo e dicas. Ele consulta a base vetorial (`chroma_db/`) e pode fazer perguntas extras ao responsável.
3. O responsável pede ajustes ou aprova a proposta.
4. Com o perfil aprovado, a família entra no painel da criança, onde registra metas, estratégias, conquistas, atividades, comportamento e saúde.
5. Detalhes do agente estão em [src/agente_perfil/README.md](src/agente_perfil/README.md). Detalhes do RAG estão em [src/rag/README.md](src/rag/README.md).

## Como acessar e subir a aplicação

São dois processos, e o navegador só precisa acessar a porta **5173**:

| Processo | Porta | Função |
| --- | --- | --- |
| Backend FastAPI (`uvicorn`) | 8000 | API, agente, SQLite, base vetorial |
| Frontend Vite (React) | 5173 | Interface. Encaminha `/api` para `127.0.0.1:8000` |

### Opção A — Rodar no servidor remoto e acessar por túnel SSH (recomendado)

O servidor tem GPU, a base vetorial e os modelos de embedding já baixados. Se a aplicação já estiver rodando nele, basta encaminhar a porta 5173 para a sua máquina.

**VS Code com Remote-SSH:** abra o painel **Ports** (`Ctrl+J`, aba *Ports*), clique em **Forward a Port**, digite `5173` e abra http://localhost:5173 no seu navegador. Em geral o VS Code já encaminha a porta sozinho quando o Vite sobe.

**Terminal da sua máquina, sem VS Code.** Rode o comando no seu computador. Não use o terminal integrado do VS Code, que está no servidor: lá a porta 5173 já está ocupada pelo Vite e o comando falha com `Address already in use`.

```bash
# Mantenha este terminal aberto enquanto usa a aplicação
ssh -N -L 5173:127.0.0.1:5173 matheus@10.23.20.12   # ou o mesmo host/alias que você usa no ssh
```

Depois, abra http://localhost:5173. Se quiser também a documentação da API (http://localhost:8000/docs), adicione `-L 8000:127.0.0.1:8000`.

**Para subir os dois processos no servidor**, a partir da raiz do repositório, use dois terminais. Também dá para rodar dentro de `tmux`, assim os processos sobrevivem se o SSH cair.

```bash
# Terminal 1: backend. RAG_DEVICE escolhe a GPU, e a base vetorial carrega ao subir.
cd /mnt/diskSSD2TB/matheus_2/HackathonLEPV
RAG_DEVICE=cuda:1 .venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

# Terminal 2: frontend
cd /mnt/diskSSD2TB/matheus_2/HackathonLEPV/frontend
npx vite --host 127.0.0.1 --port 5173
```

Verificação rápida: `curl http://127.0.0.1:5173/api/health` deve responder `{"status":"ok"}`.

### Opção B — Clonar e rodar na sua máquina

Requisitos:
- Python 3.10+ e Node.js 18+;
- cerca de 5 GB livres. Na primeira busca na base, os modelos `BAAI/bge-m3` e `bge-reranker-v2-m3` são baixados do Hugging Face.

GPU não é obrigatória. Em CPU, cada busca na base fica mais lenta. Se quiser pular o RAG, defina `RAG_DESATIVADO=1`.

> O código precisa estar no GitHub. Faça commit e push no servidor antes de clonar.

**Linux / macOS:**

```bash
git clone git@github.com:MatCarvalho21/HackathonLEPV.git
cd HackathonLEPV

# 1. Chave da API (o .env não vai para o git)
echo "API_KEY=sua-chave-featherless" > .env

# 2. Python
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
# RAG (opcional): em máquina sem GPU, instale antes o torch para CPU
.venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu
.venv/bin/pip install -r src/rag/requirements.txt

# 3. Frontend
cd frontend && npm install && cd ..

# 4. Subir (dois terminais, a partir da raiz)
RAG_DEVICE=cpu .venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
#   ou sem RAG:  RAG_DESATIVADO=1 .venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
cd frontend && npx vite --host 127.0.0.1 --port 5173
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
cd frontend; npm install; cd ..

# Terminal 1
$env:RAG_DEVICE="cpu"          # ou: $env:RAG_DESATIVADO="1"
.venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
# Terminal 2
cd frontend; npx vite --host 127.0.0.1 --port 5173
```

Abra http://localhost:5173.

### Roteiro de demonstração

1. Na tela inicial, clique em **"Usar o formulário da Lia, já preenchido"**. Também dá para preencher o formulário do zero.
2. Acompanhe o agente ao vivo. No modo demo, ele sempre faz uma rodada de perguntas extras. Responda.
3. Leia a proposta e peça um ajuste, por exemplo: *"Quero focar primeiro no sono"*.
4. Aprove a nova versão para entrar no painel. As abas são: Visão geral, Metas (progresso de -2 a +2), Dicas e estratégias, Novo registro (conquista, atividade, comportamento ABC, saúde, observação), Linha do tempo e Perfil e versões.

Cada etapa do agente leva de 1 a 2 minutos.

### Variáveis de ambiente úteis

| Variável | Padrão | Uso |
| --- | --- | --- |
| `API_KEY` (no `.env`) | — | Chave do Featherless |
| `RAG_DEVICE` | GPU com mais memória livre | `cuda:0`, `cuda:1` ou `cpu` |
| `RAG_DESATIVADO` | `0` | `1` sobe sem a base vetorial |
| `FORM_DB` | `backend/data/forms.sqlite3` | Banco SQLite local |
| `LLM_MODELO` | `deepseek-ai/DeepSeek-V4.1-Flash-1017` | Modelo do agente |

### Problemas comuns

- **A página abre, mas as ações falham:** o backend não está rodando na porta 8000 da mesma máquina do Vite.
- **`Address already in use`:** já existe um processo na porta. Veja com `ss -ltnp | grep -E '8000|5173'` e encerre o processo antigo.
- **Agente com erro `RuntimeError: Defina API_KEY`:** falta o `.env` na raiz.
- **CUDA out of memory:** use outra GPU (`RAG_DEVICE=cuda:1`) ou `cpu`.

## Fluxo e contrato do formulário

- Perfil: apelido, idade em meses, ano escolar, vínculo do informante, idiomas, interesses, prioridade familiar, prematuridade e perda de habilidades relatada.
- 14 áreas com perguntas do JSON, referência visível, resposta, exemplos e contexto. "Não sei" e "não se aplica" são opções distintas de "ainda não".
- Seleção: última faixa disponível de cada domínio até a idade informada. Para COG, COM_R e COM_E a partir de 6 anos, usa o final do ano escolar anterior; sem ano informado, coleta relato aberto. Para 0–1 mês, nenhum marco de 2 meses é antecipado.
- Perguntas abertas complementares são conteúdo do produto, não itens de um instrumento validado. O formulário não calcula escore nem diagnóstico. O semáforo é calculado depois, pelo agente de perfil, com regras em código (ver `src/agente_perfil/dossie.py`). SAU e CTX permanecem contextuais. Idade corrigida não é calculada automaticamente.
- Revisão, edição, consentimento, registro SQLite e download do JSON completo. O rascunho fica apenas na memória da página: atualizar ou fechar a página perde respostas ainda não enviadas.

Endpoints do formulário:
- `GET /api/questionario?idade_meses=84&ano_escolar=2` retorna versão, opções e domínios.
- `POST /api/formularios` valida os IDs esperados e as 14 áreas, persiste e retorna o pacote para o agente.

Endpoints do agente e do painel: `/api/avaliacoes/*`, `/api/criancas/{id}/painel`, `/api/criancas/{id}/registros` e `/api/demo/formulario`. Estão descritos em [backend/avaliacoes.py](backend/avaliacoes.py).

O banco padrão fica em `backend/data/forms.sqlite3` (configurável por `FORM_DB`). Este MVP é local e deve usar dados fictícios. Antes de qualquer uso com famílias reais, ainda é preciso implementar:
- autenticação;
- vínculo responsável-criança;
- autorização;
- política de retenção;
- migração para o Postgres modelado em `prompts/matheus/04/output.sql`.

As referências e regras propostas nos prompts ainda exigem revisão profissional.

## Validação

```bash
.venv/bin/python -m unittest backend.test_main backend.test_agente -v   # Windows: .venv\Scripts\python ...
cd frontend && npm run build
```

Os testes do formulário cobrem idades, seleção escolar, envio, evidências, versão, consentimento e rejeição de respostas incompletas. Os testes do agente usam um LLM falso e cobrem:
- regras do semáforo;
- validação (linguagem diagnóstica, metas);
- pausa e retomada com perguntas;
- ajuste e aprovação;
- registros e painel.
