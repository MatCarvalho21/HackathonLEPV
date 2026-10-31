# Caminho do professor, permissões por papel e reavaliação com evolução

Tudo está implementado, testado (14 testes, eram 11) e rodando em http://localhost:5173. A reavaliação também foi testada com o modelo real (DeepSeek), numa cópia do banco.

## 1. O "problema de caracteres" no cadastro do professor
- **Causa:** o campo de e-mail do navegador aceita `carla@gmail` (sem ponto depois do @), mas o backend exige `nome@dominio.com`. O backend devolvia a mensagem crua do Pydantic, em inglês e com a regex: `String should match pattern '^[^@\s]+@[^@\s]+\.[^@\s]+$'`.
- **Correção:**
  - Os erros de validação agora chegam em português, para todos os formulários (`backend/main.py`). Exemplos: "E-mail inválido. Use o formato nome@dominio.com" e "Turma: não pode ficar vazio."
  - O campo de e-mail do cadastro passou a usar a mesma regra do backend, com explicação.
- **Entrada rápida:** na tela inicial há "**Entrar como professora (demo)**". Ela entra como a Prof. Carla, com a **Lia e a Nina** na turma.

## 2. Papéis: o que o professor pode e não pode fazer
O backend confere o papel e o vínculo e responde **403** quando não pode. A interface esconde o que não se aplica.

| Ação | Responsável | Professor(a) |
| --- | --- | --- |
| Ver as crianças vinculadas e abrir uma por uma | as suas | as da própria turma |
| Ler perfil, metas, dicas e linha do tempo | sim | sim (somente leitura) |
| Registrar atividade, comportamento, conquista, observação, estratégia testada | sim | sim |
| Registrar **progresso de meta** (check-in GAS) | sim | **não** |
| Registro de saúde, comentário sobre o perfil | sim | **não** |
| Chat com o assistente | sim | sim |
| Preencher formulário, rodar o agente, responder às perguntas dele | sim | **não** |
| Pedir ajuste, aprovar, **solicitar reavaliação** | sim | **não** |

- Professor de outra turma recebe 403 ao registrar ou conversar sobre a criança.
- Também recebe 403 quem tenta se passar por responsável com o id de um professor.
- Criança sem perfil aprovado: o professor vê "Perfil em construção pela família" e não cai no formulário. Ele ainda pode registrar no diário.
- Proposta aguardando a família: o professor lê em modo somente leitura.
- No painel, o professor vê um aviso do que pode fazer. A aba Metas mostra o progresso sem o botão de check-in.

**Limite:** não há login real na demonstração. O frontend informa quem age (`autor` e `autor_id`, ou `responsavel_id`), e o backend confere o vínculo. As rotas de leitura (painel, estado) continuam abertas.

## 3. Reavaliação
**Como funciona para o responsável:**
1. No painel (Visão geral ou "Perfil e versões"), clicar em **Solicitar reavaliação**. O card mostra há quantos dias o perfil foi aprovado e quantos registros entraram desde então. Dá para escrever uma sugestão opcional (ex.: "quero focar no sono"); ela vira a evidência `extra:pedido`.
2. O agente roda em segundo plano, com a mesma tela de acompanhamento. Se faltar algo, ele faz **perguntas** ao responsável (1 rodada, até 5 perguntas).
3. Sai uma **nova proposta**. O responsável pode **pedir ajustes** (a nova versão continua comparada com o mesmo perfil vigente) ou **aprovar**. Ao aprovar, a versão anterior vira "substituída".

**O que o agente recebe** (montado em código em `src/agente_perfil/reavaliacao.py`):
- o perfil vigente: cores, justificativas, foco, metas com a escala GAS, dicas e alertas;
- **todos os registros**, um por linha, com ID citável, data, nome e papel de quem registrou, tipo, local, áreas e conteúdo. Ficam separados em "desde a última avaliação" e "anteriores";
- o histórico de check-ins de cada meta e o placar das estratégias testadas (funcionou, em parte, não funcionou);
- a idade atual e as prioridades do formulário original.

**Regras e validação:**
- Uma área só muda de cor com evidência (`reg:` ou `extra:`). Área sem registro mantém a cor, porque falta de registro não é piora.
- Toda mudança de cor precisa estar explicada em `evolucao.areas`. O "antes" e o "depois" são preenchidos pelo código.
- O balanço precisa cobrir **cada meta anterior**, e o destino tem que bater com a lista nova:
  - meta mantida ou ajustada conserva o mesmo id (assim o histórico de progresso continua);
  - meta concluída ou substituída sai da lista.
- Uma meta com check-ins não pode ser marcada "sem dados".
- Uma meta "alcançada" precisa de nível ≥ 0 ou de evidência.
- Evidências inventadas são removidas, e o filtro de linguagem diagnóstica também cobre o texto da evolução.

## 4. Como a evolução aparece
- **Na proposta da reavaliação ("Como a Lia evoluiu"):**
  - o período com o total de registros, quantos são da família e quantos da escola;
  - o resumo da evolução e as conquistas, que citam os registros (passe o mouse no selo "registro");
  - **as 14 áreas antes → agora**, com setas (avançou, estável, pede mais atenção);
  - o balanço de cada meta anterior, com as barrinhas do progresso GAS;
  - o que funcionou e o que vale rever;
  - depois, a nova versão completa do perfil.
- **No painel:** um bloco "Evolução desde a versão anterior" na Visão geral, com o placar das áreas e das metas alcançadas.
- **Em "Perfil e versões":**
  - uma **matriz de cores por área ao longo de todas as versões aprovadas** (V1, V2, …), com destaque onde mudou;
  - o detalhe da última reavaliação.
- O cabeçalho do painel mostra a versão atual do perfil.

## 5. Teste com o modelo real
Rodei a reavaliação da Lia com o DeepSeek numa **cópia** do banco. O seu banco não foi alterado, e a Lia continua pronta para você testar.
- O agente juntou 17 registros (14 da família, 3 da escola).
- Fez 5 perguntas pertinentes: sono, que a família pediu, metas sem nenhum check-in e choro na entrada da creche.
- Na primeira entrega, o validador apontou 3 erros. O modelo corrigiu e a proposta foi aceita.
- O balanço cobriu as 8 metas, manteve os ids das que continuam e criou `meta_r2_1` para o sono. As 9 conquistas citam registros reais, inclusive os da professora.
- Custo: cerca de 90 mil tokens, alguns minutos.

## 6. Como testar
- **Responsável:** "Entrar na demonstração", depois Lia → Solicitar reavaliação → responder às perguntas → pedir um ajuste → aprovar. Por fim, veja "Perfil e versões".
- **Professor:** "Entrar como professora (demo)". Abra a Lia: dá para registrar uma observação ou conquista e conversar, mas não há check-in de meta nem botões de perfil. A Nina aparece como "perfil em construção".

## Arquivos
- Backend:
  - `backend/main.py`: erros em português, formulário só do responsável;
  - `backend/plataforma.py`: permissões, rota de reavaliação, demo da professora;
  - `backend/avaliacoes.py`: `responsavel_id` nas ações do agente, evidências de registros;
  - `backend/seed.py`.
- Agente:
  - `src/agente_perfil/reavaliacao.py` (novo);
  - `agente.py`, `relatorio.py` (esquema `evolucao`), `prompts.py`, `ferramentas.py`, `repositorio.py`.
- Frontend: `src/App.jsx`, `src/jornada/{Painel,Agente,Relatorio}.jsx`, `api.js`, `pp.css`.
- Testes:
  - `backend/test_agente.py`: permissões do professor, erro em português e o fluxo completo da reavaliação (pergunta, validação, ajuste, aprovação, matriz de versões);
  - as rotas que disparam o agente em segundo plano agora não chamam o LLM real nos testes.

**Observação:** o `chroma_db/chroma.sqlite3` aparece como modificado porque o Chroma escreve no arquivo ao abrir a base. Não é mudança de conteúdo, então vale não commitar.
