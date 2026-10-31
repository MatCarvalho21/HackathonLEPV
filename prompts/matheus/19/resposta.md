Sim, mas só para as fontes oficiais. Para os dados da criança, RAG é a ferramenta errada: eles são poucos, estruturados e já estão no banco, então o melhor é SQL mais um resumo fixo no prompt. E a avaliação não deve "ler as regras": as regras viram código, e o modelo recebe o resultado já calculado.

### 1. Chat: cada tipo de informação no seu lugar

| Informação | Como chega ao modelo | Por quê |
| --- | --- | --- |
| Regras de comportamento do agente + as 20–30 fichas de estratégia | **Prompt de sistema fixo, com cache** | Cabem inteiras (cerca de 15 mil tokens); com cache saem baratas e a busca nunca "erra" a ficha |
| Resumo da criança | **Injetado sempre**, depois do bloco fixo | Responde a maioria das perguntas sem nenhuma busca |
| Detalhes da criança (registros, histórico, marcos) | **Ferramentas SQL** que o modelo chama quando precisa | Dado estruturado: filtro por data, domínio e tipo é mais preciso que busca semântica |
| Documentos oficiais (OMS, EEF, Caderneta, decretos) | **RAG como ferramenta** (`buscar_base_conhecimento`), não a cada mensagem | São centenas de páginas, não cabem; e "obrigado!" não precisa de busca |

O resumo injetado, gerado por código a cada conversa, teria uns 600 tokens:

```
Criança: Lia, 3a2m (38 meses). Quem pergunta: mãe (Ana).
Semáforo: COM_E amarelo (faixa 30m) · FAL vermelho (18m→24m) · REG vermelho (6 crises/sem) · demais verdes
Pontos fortes: música, quebra-cabeças. Interesses: dinossauros, água.
Metas ativas: m1 pedir com figura no lanche (GAS -1) · m2 transição do banho (GAS -2)
Estratégias: aviso_transicao = não funcionou em casa (12/10) · pausa_com_expectativa = funcionou 3/4
Alertas: nenhum. Últimos registros: 3 nesta semana (2 escola, 1 casa).
```

Ferramentas da criança, todas consultas SQL simples:
- `buscar_registros(periodo, dominios, tipo, local, texto)`
- `historico_estrategia(ficha_id | dominio)`
- `ver_marcos(dominio)`
- `ver_avaliacao(versao)`

### 2. Avaliação inicial: regras em código, modelo só para redigir

O modelo não deve receber "o formulário + as regras" e calcular. Ele erra conta, pula marco e não é auditável. O caminho é um pipeline em etapas:

1. **Código** lê as respostas e o `marcos_referencia.json` e calcula:
   - cor e faixa consolidada de cada domínio;
   - alertas;
   - domínios com informação insuficiente.

   O resultado é um **dossiê em JSON**, com o ID de cada resposta usada.
2. **Modelo** recebe o dossiê, as prioridades da família e a biblioteca de metas, e devolve um **JSON com esquema fixo**: resumo, pontos a favor e de atenção por domínio, 2 ou 3 metas escolhidas da biblioteca e 2 ou 3 fichas iniciais. Cada afirmação cita IDs (`form:E7`).
3. **Código valida** antes de mostrar:
   - o esquema está correto;
   - as metas e fichas existem;
   - a cor do texto bate com a calculada;
   - nenhuma palavra de diagnóstico aparece.

   Se a validação falhar, o modelo tenta de novo com o erro apontado.
4. **Negociação com os pais:** o comentário é classificado primeiro.
   - "Ela já aponta" é correção de resposta: o código recalcula e o modelo só reescreve aquele domínio.
   - "Quero focar no sono" é preferência: o modelo refaz as metas.

### 3. Reavaliação: o "mar de anotações"

**Primeiro, o tamanho do problema.** São uns 5 registros por semana, por 3 a 6 meses, com cerca de 80 palavras cada: 100 a 130 registros, por volta de 15 mil tokens. **Cabe no contexto.** Para o hackathon, o mais simples funciona: todos os registros da janela em formato compacto, uma linha cada (`[reg:812] 12/10 escola prof REG ABC: tirou o tablet → jogou o prato → acalmou em 15min`), mais os números agregados por SQL.

**Em produção**, com vários informantes, anos de histórico e custo importando, use memória em camadas:

1. **Na hora do registro**, um modelo pequeno e barato extrai campos estruturados: domínios, qual marco o registro evidencia (presente ou ausente), intensidade, estratégia e resultado. Isso alimenta direto as regras e os gráficos.
2. **SQL agrega** a janela por domínio: crises por semana com a tendência, nível de ajuda médio, evolução das metas, marcos evidenciados em 2 datas ou mais (a regra para mudar de faixa) e a divergência entre casa e escola.
3. **Resumo por domínio, atualizado aos poucos** (por exemplo, a cada semana): resumo anterior + registros novos geram um resumo novo. Na reavaliação, o modelo lê 14 resumos curtos, não 500 registros.
4. **A reavaliação** recebe: o perfil anterior, o mini-formulário, os agregados, os resumos por domínio e a ferramenta `buscar_registros`, caso precise conferir um caso específico. O código recalcula as cores e o modelo redige, citando `reg:` como prova de cada mudança.

### O que eu faria para amanhã

- Fichas no prompt fixo e o resumo da criança injetado em todo chat.
- RAG como ferramenta só para os documentos.
- Avaliação em 3 etapas: código → modelo com JSON de saída → validação.
- Reavaliação com todos os registros da janela em linhas compactas, mais os agregados. A camada de resumos fica para depois.

O pitch fica claro: regras clínicas em código auditável, IA para explicar e personalizar, e fontes oficiais citadas.

Posso escrever agora o gerador do resumo da criança, o esquema JSON da saída da avaliação com o prompt e o validador. São as três peças que mais aparecem na demo.