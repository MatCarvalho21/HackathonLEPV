# HackathonLEPV — Primeiros Passos

Primeira etapa da aplicação: formulário do responsável, em React, e backend FastAPI. A fonte é `prompts/matheus/07/ouput.json` (nome original preservado), com 14 domínios. Nenhum modelo externo é chamado nesta etapa.

## Executar localmente

Requer Python 3.10+ e Node.js 20+.

Backend, a partir da raiz:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r backend/requirements.txt
.venv\Scripts\python -m uvicorn backend.main:app --reload --host 127.0.0.1
```

Frontend, em outro terminal:

```powershell
cd frontend
npm install
npm run dev
```

Abra http://localhost:5173. A interface encaminha `/api` para a API na porta 8000. Documentação interativa: http://127.0.0.1:8000/docs.

## Fluxo e contrato

- Perfil: apelido, idade em meses, ano escolar, vínculo do informante, idiomas, interesses, prioridade familiar, prematuridade e perda de habilidades relatada.
- 14 áreas com perguntas do JSON, referência visível, resposta, exemplos e contexto. “Não sei” e “não se aplica” são opções distintas de “ainda não”.
- Seleção: última faixa disponível de cada domínio até a idade informada. Para COG, COM_R e COM_E a partir de 6 anos, usa o final do ano escolar anterior; sem ano informado, coleta relato aberto. Para 0–1 mês, nenhum marco de 2 meses é antecipado.
- Perguntas abertas complementares são conteúdo do produto, não itens de um instrumento validado. Não há escores, cores ou diagnóstico automático. SAU e CTX permanecem contextuais. Idade corrigida não é calculada automaticamente.
- Revisão, edição, consentimento, registro SQLite e download do JSON completo. Rascunho apenas na memória da página; atualizar/fechar a página perde respostas ainda não enviadas.

`GET /api/questionario?idade_meses=84&ano_escolar=2` retorna versão, opções e domínios. `POST /api/formularios` valida os IDs esperados e as 14 áreas, persiste e retorna o pacote do agente. O pacote inclui fontes, perguntas, respostas, relato, identidade do informante, timestamp, versão e instruções para avaliação descritiva e planos revisáveis. `status=aguardando_agente` é explícito: metas e plano ainda dependem da implementação do agente/RAG.

O banco padrão fica em `backend/data/forms.sqlite3`; configure `FORM_DB` para outro caminho. Não há listagem pública de formulários. Este MVP é local e deve usar dados fictícios. Autenticação, vínculo responsável-criança, autorização, política de retenção e integração com a modelagem SQL dos prompts precisam ser implementados antes de uso com famílias reais. As referências e regras propostas nos prompts ainda exigem revisão profissional.

## Validação

```powershell
.venv\Scripts\python -m unittest backend.test_main -v
cd frontend
npm run build
```

Os testes cobrem todas as idades aceitas, seleção escolar, envio, preservação de evidências, versão, consentimento e rejeição de respostas incompletas.
