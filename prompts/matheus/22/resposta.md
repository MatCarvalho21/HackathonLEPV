# Jornada completa no navegador: formulário demo → agente → ajuste → aprovação → painel

A aplicação está rodando em http://localhost:5173. O backend está em :8000, com a base vetorial carregada na GPU 1.

## Roteiro de teste
1. Na tela inicial, clique em **"Usar o formulário da Lia, já preenchido"**. É o mesmo formulário fictício da rodada anterior, enviado pelo mesmo caminho do formulário real.
2. Você acompanha o agente trabalhar **ao vivo**: cada busca na base e os documentos encontrados aparecem na tela. No modo demo, o agente é obrigado a fazer **uma rodada de perguntas extras** (de 1 a 3, geralmente de múltipla escolha).
3. Depois que você responde, ele termina e mostra a **proposta**: resumo, pontos fortes, alertas, semáforo das 14 áreas (clique em cada área para ver detalhes e evidências; passe o mouse nos selos para ver a origem), foco, metas com escala GAS, dicas com fontes, próximos passos e limitações.
4. Escreva um comentário, por exemplo "Ela já fala o próprio nome sempre. Quero focar primeiro no sono", e clique em **Pedir ajuste**. O agente gera uma nova versão ligada à anterior.
5. Clique em **Aprovar**. Você entra no **painel da criança**, com estas abas:
   - **Visão geral**: resumo, foco, as 14 áreas, metas de curto prazo com mini-gráfico de progresso, últimos registros e lembretes.
   - **Metas**: check-in semanal na escala GAS (de -2 a +2), com histórico.
   - **Dicas e estratégias**: "funcionou / em parte / não funcionou", por local, com contagem acumulada.
   - **Novo registro**: Conquista, Atividade (duração, nível de ajuda, engajamento), Comportamento (registro ABC, com intensidade, duração e qual dica foi usada e se funcionou), Saúde (consulta, exame, medicação, vacina, sono, alimentação, terapia; profissional e retorno) e Observação. Todos têm as áreas relacionadas, onde, quando e quem registrou (responsável ou professor).
   - **Linha do tempo**: todos os registros, com filtro por tipo.
   - **Perfil e versões**: histórico das versões (descartada → vigente), fontes e limitações.

## O que mudou no código
- **Agente** (`src/agente_perfil/agente.py`): roda em segundo plano (thread) e registra **eventos** de progresso. `demo=true` obriga uma rodada de perguntas.
- **API** (`backend/avaliacoes.py`):
  - `POST /api/avaliacoes` agora retorna 202 e o frontend consulta a sessão periodicamente;
  - rotas novas: `POST /api/demo/formulario`, `GET /api/criancas/{id}/painel`, `GET|POST /api/criancas/{id}/registros`;
  - as evidências chegam com o texto legível (marcos, relatos, fontes).
- **Banco** (`repositorio.py`): tabela `registro` igual à do `.sql` e agregação equivalente à view `historico_estrategias`. Registros de comportamento em que uma dica foi usada também contam como teste de estratégia.
- **Base vetorial**: carregada ao subir o servidor (`lifespan`), para a primeira busca não esperar.
- **Frontend** (`frontend/src/jornada/`): `Jornada.jsx` (rotas por hash, início, agente ao vivo, proposta), `Relatorio.jsx`, `Painel.jsx` e `jornada.css`, com a mesma identidade visual do formulário. No `main.jsx` dos colegas mudou pouco: ele renderiza `<Jornada Formulario={App} />` e ganhou o botão "Gerar mapeamento de perfil com IA" depois do envio.
- **Testes:** 10 passando, incluindo registros e painel.

## Validação
Rodei a jornada inteira pela API com o modelo real:
- o agente fez 3 perguntas de múltipla escolha (frequência do choro na creche, tempo para se acalmar, impacto dos barulhos);
- com as respostas, REG passou de amarelo para **vermelho**;
- o ajuste "focar no sono" mudou o foco para SAU → FAL → REG e trouxe metas de sono;
- na aprovação, a proposta virou `vigente` e a versão anterior ficou como `descartada`.
