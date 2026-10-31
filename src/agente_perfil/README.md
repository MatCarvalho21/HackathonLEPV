# Agente de mapeamento de perfil

Este agente recebe o formulário inicial do responsável e gera uma **proposta** de perfil da criança: semáforo dos 14 domínios, pontos fortes, foco prioritário, metas de curto, médio e longo prazo (com escala GAS) e dicas. O responsável lê a proposta, pode pedir ajustes e depois a aprova.

```
formulário ─código─▶ dossiê ─▶ DeepSeek ⇄ ferramentas ─▶ entregar_relatorio ─código─▶ validação ─▶ avaliacao 'proposta'
   (POST /api/formularios)  │        ├ consultar_base_conhecimento (RAG, ChromaDB + reranker)     │ erro → volta ao modelo
                            │        └ solicitar_informacoes_responsavel → PAUSA até o responsável responder
                            └ semáforo calculado por regras, lacunas e alertas
```

## Divisão de trabalho

| Parte | Quem faz | Arquivo |
| --- | --- | --- |
| Cor dos 9 domínios por idade, alertas (perda de habilidades, prematuridade) e lacunas | Código, por regra auditável | `dossie.py` |
| Cor de REG, ATE e SEN (impacto no dia a dia) | Modelo, com justificativa | `prompts.py` |
| Texto, foco, metas, dicas e quando perguntar mais | Modelo | `prompts.py` |
| Esquema, 14 domínios, quantidade de metas por horizonte, evidências que existem, fontes `kb:N` reais e ausência de linguagem diagnóstica | Código | `relatorio.py` |

Cada afirmação do relatório cita os IDs que a sustentam: um marco (`M36_FAL_1`), um relato (`ctx:REG`), uma resposta complementar (`extra:r1q1`) ou um trecho da base (`kb:3`). O código remove os IDs inventados e corrige as cores calculadas. O que mudou fica registrado em `perfil.gerado_por.ajustes_automaticos`.

## Rodar

```bash
source .venv/bin/activate
pip install -r backend/requirements.txt        # inclui openai

# Terminal, com o formulário sintético da Lia (38 meses):
python -m src.agente_perfil.cli src/agente_perfil/exemplos/formulario_lia_38m.json --saida /tmp/av.json
python -m src.agente_perfil.cli <arquivo> --sem-rag              # sem carregar a base vetorial (mais rápido)
python -m src.agente_perfil.cli <arquivo> --ajuste "Quero focar no sono"

# API (o router é incluído em backend/main.py):
uvicorn backend.main:app --reload

# Testes (LLM falso, não chama a API):
python -m unittest backend.test_agente -v
```

A chave fica no `.env` da raiz (`API_KEY=...`). Variáveis opcionais: `LLM_MODELO`, `AGENTE_MAX_BUSCAS` (padrão 6), `AGENTE_MAX_RODADAS` (rodadas de perguntas ao responsável, padrão 1), `RAG_DESATIVADO=1` e `RAG_DEVICE=cuda:1`.

## API

| Rota | O que faz |
| --- | --- |
| `POST /api/avaliacoes` `{formulario_id}` | Roda o agente. Retorna `status` `concluida` com a avaliação, ou `aguardando_responsavel` com `perguntas` e `sessao_id`. |
| `POST /api/avaliacoes/sessoes/{sessao_id}/respostas` `{respostas: {r1q1: "..."}}` | Envia as respostas e retoma o loop. Uma resposta omitida conta como não respondida. |
| `GET /api/avaliacoes/sessoes/{sessao_id}` | Mostra o estado da sessão. |
| `GET /api/avaliacoes/{id}` | Mostra a avaliação. O relatório completo fica em `perfil.relatorio`. |
| `POST /api/avaliacoes/{id}/ajustes` `{comentario}` | Gera uma nova proposta ligada à anterior (`avaliacao_anterior_id`). A anterior vira `descartada`. |
| `POST /api/avaliacoes/{id}/aprovar` | A proposta vira `vigente` e a vigente anterior vira `substituida`. A partir daqui, a página personalizada usa esta avaliação. |

As chamadas são síncronas e levam de 30 s a 2 min. No frontend, mostre um estado de "analisando".

## Banco

O SQLite local usa `FORM_DB`, o mesmo banco do formulário. As tabelas são `submissions`, `sessao_agente` e `avaliacao`, esta última com as mesmas colunas de `prompts/matheus/04/output.sql`. A tabela `avaliacao` guarda o relatório completo e as fontes em `perfil`, as cores em `niveis` (`{"FAL": "vermelho", ...}`) e as metas com GAS em `metas`. Para levar ao Postgres/Supabase, aplique `migracao_postgres.sql`.

## Limitações conhecidas

- As regras de cor são propostas (ver `prompts/matheus/05` e `07`) e precisam de validação profissional.
- O formulário só pergunta os marcos da faixa da idade. Por isso, o vermelho usa a proporção de "ainda não", não a faixa anterior.
- A idade corrigida de prematuros não é calculada. Isso aparece como alerta.
