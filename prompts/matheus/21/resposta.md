# Agente de mapeamento de perfil: implementado e testado com a API real

O agente está implementado em `src/agente_perfil/` e foi testado de ponta a ponta com o DeepSeek no Featherless e a base vetorial na GPU 1. O formulário sintético da Lia (38 meses) gerou a avaliação salva em `prompts/matheus/21/output_avaliacao_lia.json`.

## Como funciona

```
formulário ─código─▶ dossiê ─▶ DeepSeek ⇄ ferramentas ─▶ entregar_relatorio ─código─▶ validação ─▶ avaliacao 'proposta'
                       │         ├ consultar_base_conhecimento (RAG)                         │ erro → volta ao modelo
                       │         └ solicitar_informacoes_responsavel → PAUSA até o pai responder
                       └ semáforo por regra, alertas, lacunas
```

- **Prompt fixo** (`prompts.py`): explica como ler o dossiê, o que é cada cor, como escrever metas (curto de 2 a 6 semanas, médio de 8 a 16, longo de 16 a 52, todas com escala GAS) e dicas, e o tom. Também proíbe diagnóstico.
- **O modelo não decide a cor dos 9 domínios por idade.** O código calcula essa cor a partir das respostas (`dossie.py`) e o modelo explica. Nos domínios REG, ATE e SEN, o modelo propõe a cor pelo impacto no dia a dia. SAU e CTX ficam sem cor.
- **Três ferramentas**, por function calling nativo, que o modelo suporta:
  1. `consultar_base_conhecimento`: o RAG que você indexou, com até 6 buscas e corte de relevância do reranker;
  2. `solicitar_informacoes_responsavel`: pausa o loop, salva o estado e devolve as perguntas para o frontend. Quando o pai responde, o loop retoma. São no máximo 5 perguntas, em 1 rodada (configurável);
  3. `entregar_relatorio`: o relatório é validado em código antes de ser salvo. A validação confere o esquema, os 14 domínios, as cores calculadas, a quantidade de metas por horizonte, se as evidências e as fontes `kb:N` existem e se há linguagem diagnóstica. Se algo falhar, os erros voltam para o modelo corrigir.
- **Rastreabilidade:** cada afirmação cita IDs (`M36_FAL_1`, `ctx:REG`, `extra:r1q1`, `kb:3`). As fontes da base ficam salvas com documento, seção e consulta.

## Teste real (Lia, 38 meses)

O agente levou 4 passos e fez 6 buscas, com cerca de 59 mil tokens de entrada e 30 mil de saída. O semáforo ficou FAL vermelho, COM_E amarelo e REG/ATE/SEN amarelo; os demais domínios ficaram verdes. O foco foi FAL, COM_E e REG, alinhado com a prioridade da mãe. As 8 metas são observáveis e têm GAS. As 8 dicas aproveitam dinossauros e música. Há recomendação de fono e de exame de audição, e nenhum diagnóstico.

A primeira entrega veio incompleta e o validador barrou; o modelo corrigiu na segunda tentativa.

Nesse caso, o agente decidiu não fazer perguntas ao pai. Esse fluxo está coberto pelos testes com um LLM falso.

## Banco

`avaliacao` segue o `.sql` (`perfil`, `niveis` e `metas` em JSON; status `proposta` → `vigente`). A tabela nova `sessao_agente` guarda o estado do loop para pausar e retomar. Para o Postgres, use `src/agente_perfil/migracao_postgres.sql`.

## API (router em `backend/avaliacoes.py`)

- `POST /api/avaliacoes {formulario_id}`
- `POST /api/avaliacoes/sessoes/{id}/respostas`
- `POST /api/avaliacoes/{id}/ajustes {comentario}`: o pai pede ajuste e é gerada uma nova versão ligada à anterior
- `POST /api/avaliacoes/{id}/aprovar`: a proposta vira `vigente` e alimenta a página personalizada

## Pontos de atenção

- Os metadados de página no ChromaDB estão todos como `page: 1`, então as citações não mostram a página real. Isso precisa ser corrigido no indexador.
- A base retorna muitos trechos da Caderneta. Para REG e sono, a relevância foi baixa: faltam documentos sobre esses temas.
- As chamadas são síncronas (cerca de 1 a 2 minutos com RAG). O frontend precisa de um estado de "analisando".
