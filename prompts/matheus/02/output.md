# Sistema de acompanhamento infantil — mapa do conhecimento teórico

Oct 30, 2026 · @Matheus

## Visão geral

A base teórica entra em quatro momentos — formulário, geração do perfil, chatbot e reavaliação — e todos usam a mesma língua: a taxonomia de domínios da seção 1. Os registros de pais e professores fecham o ciclo, alimentando o chat e a próxima versão do perfil.

&#91;embedded content: fluxo do sistema · 7 etapas, 2 ciclos de negociação\]

O feedback do professor sobre o perfil entra como registro na linha do tempo: não altera o perfil vigente, mas é lido na reavaliação (seção 8).

## 1. Taxonomia de domínios: a espinha dorsal dos dados

Tudo no sistema — pergunta do formulário, nível do perfil, meta, registro, ficha de estratégia e mensagem do chat — recebe **uma ou mais etiquetas de domínio** desta lista. É isso que permite cruzar "o que o pai respondeu" com "o que o professor registrou" e "o que o chat sugeriu". A taxonomia segue a CIF da OMS (que incorporou a versão para crianças e jovens), o modelo adotado pela Lei Brasileira de Inclusão.

| ID | Domínio | O que cobre | Códigos CIF de referência | Escala principal (seção 3) |
| --- | --- | --- | --- | --- |
| COM\_R | Compreensão | Entender palavras, gestos, instruções, rotinas | d310, d315 | Marcos por idade |
| COM\_E | Comunicação expressiva | Formas e funções: pedir, recusar, comentar, chamar atenção (com ou sem fala) | d330–d349 | Communication Matrix, 7 níveis |
| FAL | Fala e verbalização | Sons, palavras, frases, inteligibilidade | b320, b330, d330 | Estágio de linguagem oral (0–6) |
| SOC | Interação social | Atenção compartilhada, imitação, interação com adultos e pares | b122, d710–d729 | Estados de engajamento |
| BRI | Brincadeira | Exploratória, funcional, simbólica, com regras | d880 | Níveis de brincadeira (1–7) |
| COG | Cognição e aprendizagem | Resolução de problemas, conceitos, pré-alfabetização e pré-matemática | b117, d130–d179 | Marcos por idade |
| MOT\_A | Motor amplo | Sentar, andar, correr, pular, equilíbrio | d410–d469 | Marcos; GMFCS se paralisia cerebral |
| MOT\_F | Motor fino | Pegar, encaixar, rabiscar, usar talheres e tesoura | d440, d445 | Marcos; MACS / Mini-MACS se PC |
| AUT | Autonomia e autocuidado | Comer, beber, vestir, higiene, uso do banheiro | d510–d571 | Nível de ajuda (0–4) |
| REG | Regulação e comportamento | Emoções, frustração, transições, comportamentos desafiadores | b152, d240, d250 | Frequência, intensidade, tempo para acalmar |
| ATE | Atenção e funções executivas | Tempo de engajamento, seguir rotinas, flexibilidade | b140, b164, d160, d230 | Nível de ajuda + tempo de engajamento |
| SEN | Processamento sensorial | Busca, evitação, sensibilidade, baixo registro | b156, b210–b270 | 4 quadrantes de Dunn (menos / igual / mais que outras crianças) |
| SAU | Saúde e corpo | Sono, alimentação, convulsões, visão, audição, medicações | b134, b510, b210, b230 | Registro factual (sem escala) |
| CTX | Contexto e participação | Rotinas, família, escola, terapias, barreiras e facilitadores | d-participação, fatores ambientais (e) | Qualificador CIF de barreira/facilitador |

**Regra de implementação:** a lista é uma tabela fixa no banco (`domains`), versionada. O modelo de IA nunca cria domínio novo; ele só escolhe entre os IDs existentes ao etiquetar textos livres.

## 2. Formulário inicial do responsável

O formulário deve ser **adaptativo por idade, em linguagem simples e com perguntas próprias** escritas a partir de fontes públicas. Instrumentos validados com direitos autorais não podem ser copiados, adaptados ou recortados dentro do app sem licença. Meta de tempo: 15–20 minutos, com possibilidade de salvar e continuar.

**Blocos do formulário**

| Bloco | O que perguntar | Fundamentação | Alimenta |
| --- | --- | --- | --- |
| A. Identificação e contexto | Data de nascimento, prematuridade (usar idade corrigida até 2 anos), línguas em casa, quem cuida, escola, terapias atuais, diagnósticos já informados ou "em investigação", upload de laudos | Caderneta da Criança; CIF fatores contextuais | CTX, SAU |
| B. Preocupações da família | Uma pergunta aberta por domínio ("Você tem alguma preocupação com a forma como seu filho…?") | Preocupação parental tem valor preditivo (AAP, 2020) | Todos; peso alto na priorização |
| C. Prioridades | "O que mais ajudaria a rotina de vocês nos próximos 3 meses?" (escolher até 3) | Routines-Based Model (McWilliam); "F-words" | Metas de curto prazo |
| D. Pontos fortes e interesses | Do que gosta, o que faz bem, como se acalma, pessoas e objetos favoritos | Perspectiva baseada em forças / neuroafirmativa | Perfil; ranqueamento de estratégias |
| E. Marcos do desenvolvimento | Checklist adaptativo por faixa etária (abaixo) | Marcos do CDC revisados em 2022 (domínio público) + marcos da Caderneta da Criança | COM\_R, COM\_E, FAL, SOC, BRI, COG, MOT\_A, MOT\_F |
| F. Rotinas e autonomia | Para cada rotina (acordar, refeição, banho, vestir, brincar, sair de casa, dormir, escola): quanto de ajuda precisa e quanto é difícil | CIF (qualificadores); entrevista baseada em rotinas | AUT, ATE, CTX |
| G. Comunicação em detalhe | Como pede, recusa, chama atenção e comenta (choro, puxar, gesto, figura, sinal, palavra, frase) | Níveis da Communication Matrix (Rowland) | COM\_E, FAL |
| H. Sensorial, sono e alimentação | Reações a sons, texturas, movimento, luz; padrão de sono; seletividade alimentar | Modelo de Dunn (conceitual, sem itens do Perfil Sensorial) | SEN, SAU |
| I. Comportamento e regulação | Comportamentos que preocupam, frequência, gatilhos, o que acalma | Lógica ABC da análise funcional; Pyramid Model | REG |
| J. Sinais de alerta | Regra fixa, fora da IA (abaixo) | AAP / CDC / SBP | Alertas |

**Bloco E — checklist adaptativo de marcos**

- Faixas: 2, 4, 6, 9, 12, 15, 18, 24 e 30 meses; 3, 4 e 5 anos (as 12 listas do CDC).
- Começa na faixa da idade (corrigida); se a criança não atinge a maioria dos marcos, desce uma faixa; se atinge todos, sobe uma. Para quando encontrar uma faixa toda atingida (base) e uma faixa pouco atingida (teto).
- Respostas: **faz com frequência** / **às vezes ou com ajuda** / **ainda não** / **não sei**. Guarde cada resposta com ID do marco, domínio e faixa.
- Os marcos do CDC indicam o que **75% ou mais** das crianças fazem em cada idade; por isso um marco ausente já justifica conversar com o pediatra (Zubler et al., 2022).

**Instrumentos validados: o que pode e o que não pode**

| Instrumento | Situação de licença | Recomendação para o app |
| --- | --- | --- |
| Marcos do CDC (Learn the Signs. Act Early.) | Material do governo dos EUA, uso livre | Base do bloco E; citar a fonte |
| Marcos da Caderneta da Criança (MS) | Publicação pública do Ministério da Saúde | Complementar o bloco E com a referência brasileira |
| M-CHAT-R/F | Uso livre em papel; **software que distribui a versão eletrônica precisa de acordo de licença**, e os itens não podem ser alterados ([mchatscreen.com](https://www.mchatscreen.com/map/)) | No hackathon: não embutir; oferecer link oficial para os pais (16–30 meses) e um campo para registrar o resultado. Em produção: pedir licença |
| SWYC (Tufts) | Formulários gratuitos, com versão brasileira validada | Verificar termos para uso eletrônico antes de embutir |
| ASQ-3, Perfil Sensorial 2, Vineland-3, Bayley | Comerciais / uso profissional | Não reproduzir; permitir **upload do resultado** feito por profissional |
| Communication Matrix | Gratuita, online | Usar os 7 níveis como referência conceitual; linkar para a avaliação oficial |
| GMFCS / MACS | Descritores públicos (CanChild) | Perguntar o nível já informado pelo fisioterapeuta |

**Bloco J — sinais de alerta (regras determinísticas)**

Estes itens disparam uma mensagem fixa recomendando avaliação médica, sem bloquear o cadastro e sem a IA reinterpretar:

- **Perda de habilidades já adquiridas** (fala, interação, motor) em qualquer idade.
- Sem balbucio, apontar ou gestos aos 12 meses; nenhuma palavra aos 16 meses; nenhuma frase espontânea de duas palavras aos 24 meses.
- Não responde a sons ou parece não enxergar bem; teste da orelhinha ou do olhinho alterado ou não feito.
- Episódios sugestivos de convulsão; perda de peso ou recusa alimentar importante.
- Comportamentos que colocam a criança em risco (bater a cabeça com força, fugas frequentes) ou suspeita de maus-tratos.

## 3. Como quantificar necessidades e progresso

Use **três camadas de medida**, cada uma respondendo a uma pergunta diferente. Isso evita o erro de tentar resumir a criança num único número e permite exatamente o tipo de leitura do exemplo de vocês: "subiu de nível em comunicação, mas a fala ficou parada".

| Camada | Pergunta que responde | Como calcular | Atualiza com |
| --- | --- | --- | --- |
| 1. Desenvolvimento por domínio | Em que ponto do desenvolvimento típico a criança está neste domínio? | Faixa de marcos atingida (nível 1–12) | Formulário inicial e reavaliação |
| 2. Nível funcional por domínio | Como ela funciona no dia a dia e quanto apoio precisa? | Escalas ordinais específicas + qualificador CIF 0–4 | Formulário, registros, reavaliação |
| 3. Metas individuais | As metas combinadas estão sendo alcançadas? | Goal Attainment Scaling (−2 a +2) | Registros e check-ins de meta |
|  |  |  |  |

**Camada 1 — nível de desenvolvimento (determinístico, sem IA)**

- Nível do domínio = maior faixa do CDC (1 = 2 meses … 12 = 5 anos) em que a criança faz pelo menos 80% dos marcos daquele domínio, com todas as faixas anteriores também atingidas. "Às vezes / com ajuda" conta como meio ponto.
- Mostre também a **idade de desenvolvimento estimada** do domínio comparada à idade cronológica (corrigida). Ex.: 36 meses de idade, comunicação na faixa de 18 meses.
- Deixe explícito na interface: é um **indicador de acompanhamento**, não um escore normatizado nem um diagnóstico.

**Camada 2 — escalas funcionais por domínio**

| Domínio | Escala | Níveis | Origem |
| --- | --- | --- | --- |
| COM\_E | Communication Matrix | I comportamento pré-intencional · II comportamento intencional · III comunicação pré-simbólica não convencional · IV comunicação pré-simbólica convencional (gestos, apontar) · V símbolos concretos (objetos, fotos) · VI símbolos abstratos (palavra, sinal, figura isolada) · VII linguagem (combinação de símbolos) | [Rowland; gratuita](https://communicationmatrix.org/Matrix/Pages/ResearchBasis). Vale para fala, sinais e CAA |
| FAL | Estágio de linguagem oral | 0 sem vocalização intencional · 1 balbucio · 2 aproximações de palavras · 3 palavras isoladas · 4 combinações de 2 palavras · 5 frases simples · 6 frases complexas e narrativa | Escala do produto, baseada nos marcos de linguagem; não validada |
| SOC | Estados de engajamento | não engajado · observa · engajado só com objeto · engajado com pessoa · engajamento coordenado (atenção compartilhada) · engajamento simbólico | Bakeman & Adamson; usado em JASPER |
| BRI | Níveis de brincadeira | 1 exploratória/sensorial · 2 causa e efeito · 3 funcional · 4 construção e combinação · 5 simbólica simples · 6 faz de conta em sequência/papéis · 7 jogos com regras com pares | Escala do produto, baseada na literatura de desenvolvimento do brincar |
| AUT e ATE | Nível de ajuda | 0 ajuda total · 1 ajuda física parcial · 2 dica verbal ou gestual · 3 supervisão · 4 independente | Hierarquia de ajudas (prática baseada em evidência) |
| REG | Indicadores de regulação | Episódios por semana · intensidade (1–3) · minutos para se acalmar | Registros ABC |
| SEN | Quadrantes de Dunn | Busca, evitação, sensibilidade, baixo registro: menos / igual / mais que outras crianças | Conceito de Dunn, perguntas próprias |
| MOT\_A, MOT\_F | GMFCS / MACS (quando há paralisia cerebral) | I a V (I = menor limitação) | CanChild; informado por profissional |
| Todos | Qualificador CIF de dificuldade | 0 nenhuma · 1 leve · 2 moderada · 3 grave · 4 completa | CIF/OMS; resume a necessidade de apoio por domínio |

**Camada 3 — metas com Goal Attainment Scaling**

| Horizonte | Prazo | Quantidade sugerida | Exemplo |
| --- | --- | --- | --- |
| Curto | 4–8 semanas | 2–3 | Pedir água usando figura ou palavra no lanche, 3 de 5 vezes |
| Médio | 3–6 meses (= ciclo de reavaliação, alinhado ao PEI semestral) | 3–5 | Passar do nível IV para o V da Communication Matrix |
| Longo | 12 meses | 1–3 | Participar da roda de conversa com apoio visual, sem sair da sala |

Cada meta é criada já com os 5 níveis descritos: −1 = situação atual, 0 = resultado esperado, +1 e +2 = acima do esperado, −2 = piora. Formato da meta: **quem + faz o quê + em que situação + com que critério + até quando**. O escore T do GAS (fórmula de Kiresuk & Sherman) resume o conjunto de metas: perto de 50 significa metas atingidas como esperado ([revisão sistemática, 2024](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10965877/)).

Para gerar metas, a IA escolhe de uma **biblioteca de metas** por domínio e nível (ex.: COM\_E nível IV → metas típicas do nível V), e personaliza com rotina, interesses e prioridades da família. Isso deixa a sugestão fundamentada e auditável.

## 4. Perfil gerado: esquema e regras para a IA

O perfil é metade **calculado por regras** (níveis, alertas) e metade **redigido pela IA** (síntese, metas, estratégias), sempre com referência às respostas que o sustentam. Essa divisão é o que torna o resultado defensável numa banca de hackathon e, depois, perante pais e escola.

```json
{
  "profile_id": "p_123", "child_id": "c_45", "version": 1,
  "status": "proposto | em_revisao | vigente | substituido",
  "idade_meses": 38, "idade_corrigida_meses": null,
  "contexto": { "linguas": ["pt"], "escola": "...", "terapias": ["fono 1x/sem"],
                "diagnosticos_informados": [{ "cid11": "6A02", "status": "informado_pela_familia" }] },
  "pontos_fortes": [{ "texto": "memoriza músicas", "fontes": ["form:D2"] }],
  "interesses": ["dinossauros", "água"],
  "dominios": [
    { "id": "COM_E", "nivel_desenvolvimento": 6, "escala": "communication_matrix",
      "nivel_funcional": "IV", "qualificador_cif": 2,
      "resumo": "Pede puxando o adulto e apontando...", "fontes": ["form:E7", "form:G3"] }
  ],
  "barreiras": [{ "texto": "instruções só orais na escola", "tipo": "comunicacional" }],
  "facilitadores": [{ "texto": "rotina visual em casa" }],
  "prioridades_familia": ["comunicar o que quer", "dormir melhor"],
  "metas": [
    { "id": "m1", "horizonte": "curto", "dominio": "COM_E", "rotina": "lanche",
      "texto": "...", "gas": { "-2": "...", "-1": "...", "0": "...", "+1": "...", "+2": "..." },
      "prazo": "2026-12-15", "origem": "biblioteca:COM_E_IV_03" }
  ],
  "estrategias_iniciais": ["estr:apoio_visual_escolha", "estr:pausa_com_expectativa"],
  "alertas": [{ "regra": "J1_regressao", "mensagem_fixa": true }],
  "criado_por": "ia+regras", "aceito_por": "responsavel:u_9", "aceito_em": "..."
}
```

**Regras de geração (para o prompt do sistema)**

1. Cada afirmação do perfil cita ao menos uma fonte (`form:<item>` ou `reg:<id>`). Sem fonte, não entra.
2. Níveis de desenvolvimento e alertas vêm do cálculo determinístico; a IA só os explica em linguagem simples.
3. A IA **não sugere nem nomeia diagnósticos**. Pode dizer "vale conversar com o pediatra sobre comunicação".
4. Começar pelos pontos fortes; usar linguagem descritiva e respeitosa, sem rótulos de déficit.
5. Metas: no máximo 3 de curto prazo, priorizando as prioridades da família e os domínios com qualificador CIF ≥ 2; sempre vindas da biblioteca de metas.
6. Estratégias iniciais: só IDs existentes na biblioteca de fichas (seção 6).

**Negociação com o responsável**

- O responsável comenta ou edita trechos; o sistema guarda o **diff** e o motivo.
- A IA reprocessa **apenas as seções afetadas** e explica o que mudou. Se a mudança contradiz uma resposta do formulário, a IA pergunta qual vale ("no formulário você marcou que ele ainda não aponta; quer corrigir essa resposta?") em vez de simplesmente aceitar.
- Campos **não negociáveis**: alertas de sinais de alerta e níveis calculados (o responsável pode corrigir a resposta de origem, o que recalcula o nível, mas não editar o nível diretamente).
- Ao aceitar, a versão vira `vigente` e a anterior `substituido`. Todas ficam no histórico.

## 5. Registros do dia a dia

Os registros só servem para medir evolução se tiverem **alguns campos estruturados**. O truque para não virar burocracia: o usuário escreve (ou dita) em texto livre e a IA propõe os campos estruturados, que ele confirma com um toque.

**Tipos de registro**

| Tipo | Quem registra | Campos específicos | Para que serve |
| --- | --- | --- | --- |
| Atividade | Pais e professor | Atividade (ou `estrategia_id`), duração, participação (0–4), nível de ajuda | Medir engajamento e nível de ajuda ao longo do tempo |
| Comportamento (ABC) | Pais e professor | Antecedente, comportamento, consequência, intensidade 1–3, minutos até acalmar | Identificar função e gatilhos; indicadores do domínio REG |
| Conquista / primeira vez | Pais e professor | Habilidade, marco relacionado (ID), espontâneo ou com ajuda | Atualizar níveis entre reavaliações |
| Observação livre | Pais e professor | Texto, foto ou vídeo curto | Contexto qualitativo |
| Check-in de meta | Pais e professor | `meta_id`, nível GAS atual (−2 a +2) | Progresso das metas |
| Feedback de estratégia | Pais e professor (via chat) | `estrategia_id`, funcionou (sim / parcial / não), comentário | Personalizar o chatbot (seção 6) |
| Feedback sobre o perfil | Professor | Concordo / discordo por domínio + comentário | Base para a reavaliação (seção 8) |
| Saúde | Só responsável | Consulta, terapia, exame, laudo, medicação em uso (só registro), sono, alimentação | Contexto clínico; visível ao professor só se o responsável autorizar |

**Campos comuns a todos os registros**

`child_id`, `autor_id`, `papel` (responsável / professor), `data_hora`, `contexto` (casa / escola / terapia / outro), `rotina` (refeição, roda, parque, banho…), `dominios` (IDs da seção 1, sugeridos pela IA e confirmáveis), `meta_id` e `estrategia_id` quando houver, `humor_regulacao` (1–5, opcional), `texto`, `anexos`, `visibilidade`.

**Boas práticas que vêm da literatura de monitoramento de progresso**

- Registrar o **nível de ajuda**, não só "fez / não fez": é onde o progresso aparece primeiro.
- Registrar **onde** aconteceu: generalização entre casa e escola é um resultado em si.
- Comportamento sempre no formato ABC, sem adjetivos ("jogou o prato quando tirei o tablet" em vez de "birra").
- Pedir check-ins de meta curtos, uma vez por semana, por notificação.

## 6. Chatbot: base de conhecimento, fichas de estratégia e memória do que funcionou

O chatbot deve responder a partir de **duas bases**: uma base teórica curada (igual para todas as crianças) e a base pessoal da criança (perfil, metas, registros e histórico de estratégias). A peça que liga as duas é a **ficha de estratégia**: cada sugestão do chat aponta para uma ficha com ID, e é esse ID que o atalho "feito" registra.

**Corpus teórico para o RAG**

| Fonte | Conteúdo útil para o chat | Uso / licença |
| --- | --- | --- |
| CDC Learn the Signs. Act Early. | Marcos e dicas de atividades por idade | Governo dos EUA, uso livre com citação |
| Caderneta da Criança (MS) | Marcos, orientações de estimulação em português | Público; citar |
| OMS — Caregiver Skills Training | Estratégias para pais: engajamento, comunicação, rotinas, comportamento, bem-estar do cuidador | Verificar licença (materiais da OMS costumam ser CC BY-NC-SA) |
| NCPMI — Pyramid Model | Rotinas visuais, ensino de emoções, prevenção de comportamento desafiador, materiais para famílias | Reprodução incentivada com citação da fonte |
| ECTA / DEC Recommended Practices | Guias práticos para famílias e profissionais (0–8 anos) | Gratuitos; citar |
| NCAEP / AFIRM | Passo a passo das 28 práticas focais (apoios visuais, CAA, modelação, análise de tarefas…) | Gratuitos; checar termos para reprodução |
| CAST — DUA 3.0 | Adaptações de aula para o professor | Gratuito; citar |
| Legislação (Decretos 12.686 e 12.773/2025, LBI) e SBP | Direitos, estudo de caso, PEI, quando procurar o pediatra | Público; citar |

Dica de implementação: em vez de jogar PDFs inteiros no vetor, **destile o corpus em fichas** (abaixo) e indexe as fichas. O texto original fica como referência de citação.

**Esquema da ficha de estratégia**

```json
{
  "id": "estr:pausa_com_expectativa",
  "nome": "Pausa com expectativa",
  "objetivo": "criar oportunidade para a criança pedir",
  "dominios": ["COM_E", "SOC"], "niveis_alvo": { "COM_E": ["II", "III", "IV"] },
  "idade_meses": [12, 72], "contextos": ["casa", "escola"], "publico": ["pais", "professor"],
  "situacoes": ["rotina", "brincadeira", "lanche"],
  "passos": ["..."], "materiais": ["..."],
  "sinais_de_que_funcionou": ["..."], "cuidados": ["..."],
  "variacoes": ["estr:pausa_com_expectativa_v_visual"],
  "evidencia": { "nivel": "alta", "fontes": ["NCAEP 2020: intervenção naturalista", "OMS CST"] }
}
```

Para o hackathon, 20–30 fichas bem escritas cobrindo COM\_E, REG, SOC/BRI e AUT bastam para uma demo convincente.

**Ranqueamento com o histórico da criança**

Para cada pergunta, o sistema seleciona fichas candidatas por domínio, idade, contexto e situação, e ordena por:

```latex
\text{score} = \text{relev\^ancia} \times \text{peso da evid\^encia} \times \frac{1 + \text{sucessos}}{2 + \text{tentativas}}
```

- "Funcionou" conta 1 sucesso, "parcial" conta 0,5, "não funcionou" conta 0. Sem histórico, o fator pessoal vale 0,5 (neutro).
- O histórico é guardado **por contexto**: o que falhou em casa pode funcionar na escola.
- Regras duras: se a última tentativa foi "não funcionou", a ficha **não pode ser a primeira opção** por 14 dias; o chat pode oferecer uma variação dela, dizendo explicitamente "da última vez X não funcionou; uma versão adaptada é…". Com duas falhas seguidas, só aparece se o usuário pedir.
- Entre 3 sugestões, mantenha 1 nunca testada, para o sistema continuar aprendendo.

**O que entra no contexto de cada resposta**

1. Política do sistema (limites da seção 9) e papel de quem pergunta (pai ou professor).
2. Resumo do perfil vigente e metas ativas.
3. Histórico de estratégias da criança (as 10 mais relevantes, com resultados e comentários).
4. Registros recentes relevantes à pergunta (busca semântica nos últimos 30–60 dias, filtrada por domínio).
5. Fichas candidatas já ranqueadas + trechos de fonte para citação.

**Atalho de registro dentro do chat**

- Cada estratégia sugerida aparece como um **cartão** com dois botões: "Vou tentar" e "Fiz".
- "Fiz" abre um mini-formulário de 3 toques: funcionou? (sim / parcial / não) → contexto (pré-preenchido) → comentário opcional (texto ou voz).
- Isso cria um registro `feedback_estrategia` com `estrategia_id`, `conversa_id` e `meta_id` (se a estratégia estava ligada a uma meta). "Vou tentar" gera um lembrete para pedir o feedback depois.
- Atalho por texto também: o usuário escreve "fiz a pausa, não funcionou, ele chorou mais" e a IA propõe o registro para confirmação.

**Política de resposta**

- Dar 2–3 opções práticas, com passos curtos, e dizer de onde vem a recomendação.
- Ajustar ao papel: para o professor, linguagem de sala (grupo, roda, PEI, DUA); para os pais, rotinas da casa.
- Usar os interesses da criança nas atividades sugeridas.
- Quando a pergunta envolve diagnóstico, remédio, regressão ou risco, aplicar as regras da seção 9.

## 7. Reavaliação

A reavaliação compara o perfil vigente com tudo o que aconteceu desde então e propõe uma nova versão **em que cada mudança de nível aponta para as evidências que a justificam**. Intervalo sugerido: a cada 3–6 meses (alinhado ao PEI semestral da escola), ou antes, a pedido do responsável.

**Gatilhos para sugerir uma reavaliação**

- 3 a 6 meses desde a última versão.
- Todas as metas de médio prazo em +1 ou mais no GAS, ou a maioria em −1 por mais de 8 semanas.
- Novo laudo ou mudança de escola ou terapia.
- Registro de perda de habilidade (dispara o alerta de regressão imediatamente, sem esperar).

**Pipeline**

1. **Pacote de evidências:** perfil vigente, formulário inicial, registros desde a última versão (agrupados por domínio), check-ins de meta, histórico de estratégias e feedbacks do professor.
2. **Mini-formulário de reavaliação:** marcos da faixa atual e da seguinte, rotinas (bloco F), comunicação (bloco G) e as perguntas abertas de preocupação. Menos de 10 minutos.
3. **Cálculo determinístico:** novos níveis das camadas 1 e 2, deltas por domínio, escore GAS de cada meta e tendências dos registros (nível de ajuda médio, episódios por semana, minutos para acalmar).
4. **Síntese pela IA:** o que avançou, o que ficou estável, o que piorou; quais estratégias funcionaram e quais abandonar; novas metas da biblioteca; ajuste de expectativas. Cada item cita `reg:` ou `form:`.
5. **Divergências:** mostrar lado a lado onde a visão do professor difere da visão da família (seção 8).
6. **Negociação** com o responsável, nas mesmas regras do perfil inicial.
7. **Versão vigente** + geração de um **resumo exportável para a escola**, no formato do estudo de caso (potencialidades, barreiras, necessidades de apoio, estratégias) previsto no Decreto 12.686/2025, que pode alimentar o PEI.

**Regras de evidência para mudar um nível**

- Subir um nível exige: resposta do mini-formulário **e** pelo menos 2 registros em datas diferentes que mostrem o comportamento, de preferência em contextos diferentes.
- Descer um nível exige o mesmo, e sempre gera recomendação de conversar com o pediatra.
- Sem evidência suficiente, o nível fica como está e o domínio é marcado "pouca informação"; a IA sugere o que observar no próximo ciclo.

**Como mostrar o progresso**

- Um gráfico por domínio com os níveis em cada versão do perfil (eixo do tempo = datas das versões).
- Uma linha do tempo com os registros de conquista e os pontos de reavaliação.
- Uma tabela de metas com o GAS no início e no fim do ciclo.

## 8. Feedback do professor e divergência entre informantes

A decisão de vocês de **não deixar o feedback do professor alterar o perfil** tem bom apoio na literatura: pais e professores concordam pouco ao descrever a mesma criança, em média uma correlação em torno de 0,28 entre informantes de contextos diferentes (Achenbach, McConaughy & Howell, 1987; De Los Reyes et al., 2015). A interpretação atual é que essa diferença **é informação, não erro**: a criança se comporta de modo diferente em casa e na escola.

**Como transformar isso em funcionalidade**

- O feedback do professor sobre o perfil é estruturado por domínio: **concordo / parcialmente / discordo** + "na escola eu observo que…".
- O sistema calcula, por domínio, um **índice de divergência** (ex.: nível percebido pela família menos nível percebido pela escola). Divergência ≥ 2 níveis vira um item destacado na reavaliação.
- Na reavaliação, a IA apresenta a divergência como pergunta, nunca como correção: "Na escola, João pede ajuda com figuras; em casa você relata que ele puxa a mão. O que pode estar diferente entre os dois ambientes?".
- O perfil pode guardar níveis **por contexto** quando a diferença for consistente ("COM\_E: casa III, escola IV"). Isso orienta o chat a sugerir para a família o que já funciona na escola, e vice-versa.

**Permissões do professor**

- Vê o perfil vigente, as metas e os registros escolares; vê registros de saúde só com autorização explícita do responsável.
- Registra atividades, comportamentos, conquistas, check-ins de meta e feedback sobre o perfil.
- Não edita o perfil nem as metas; pode **propor** uma meta escolar, que fica pendente até o responsável aceitar.

## 9. Limites clínicos, éticos e LGPD

O sistema deve se posicionar como **ferramenta de acompanhamento e apoio pedagógico e familiar**, não como triagem clínica ou diagnóstico. Além de ser o correto, isso simplifica a regulamentação: software que se apresenta como diagnóstico pode ser enquadrado como dispositivo médico pela Anvisa (RDC 657/2022), o que vale avaliar antes de qualquer lançamento.

**Regras fixas do chatbot e da IA de perfil**

- Não sugerir, confirmar nem descartar diagnósticos.
- Não orientar dose, troca ou suspensão de medicamentos; encaminhar ao médico.
- Não sugerir práticas punitivas, aversivas, de isolamento ou contenção física.
- Regressão de habilidades, suspeita de convulsão, perda auditiva ou visual: mensagem fixa recomendando avaliação médica.
- Risco imediato à criança: SAMU 192. Suspeita de violência ou maus-tratos: Conselho Tutelar ou Disque 100.
- Sofrimento intenso do cuidador: acolher, sugerir rede de apoio e, se houver risco, indicar o CVV (188) e serviços de saúde.
- Linguagem respeitosa e neuroafirmativa; respeitar a terminologia escolhida pela família.
- Sempre citar a fonte da recomendação e deixar claro quando algo é sugestão geral, e não orientação clínica.

**LGPD**

- Dados de saúde são **dados sensíveis** (art. 11) e dados de crianças exigem **consentimento específico e em destaque de pelo menos um dos pais ou responsável**, sempre no melhor interesse da criança (art. 14).
- Consentimentos separados: uso do app; compartilhamento com cada professor/escola; compartilhamento de registros de saúde; uso de dados para melhorar o modelo (opcional, desligado por padrão).
- O responsável controla quem vê o quê e pode revogar acesso e pedir exclusão.
- Minimização: não pedir o que não será usado; vídeos e fotos com retenção limitada.
- Registro de acesso (quem leu o perfil e quando) e criptografia em repouso e em trânsito.
- Contratos com o provedor de IA sem uso dos dados para treinamento.

**Direitos autorais de instrumentos**

Não embutir M-CHAT-R/F, ASQ-3, Perfil Sensorial, Vineland ou outros instrumentos protegidos sem licença; usar perguntas próprias baseadas em fontes públicas e permitir o upload de resultados feitos por profissionais (seção 2).

## 10. Recorte de MVP para o hackathon e roteiro de demo

Para amanhã, o que mais impressiona é mostrar o **ciclo fechado**: formulário → perfil fundamentado → registro → chat que aprende com o feedback → reavaliação com níveis que mudam. Melhor um ciclo completo com 3 domínios do que 14 domínios pela metade.

**Prioridades de construção**

- [ ] Tabela de domínios (seção 1) e biblioteca de metas para COM\_E, FAL e REG.
- [ ] Formulário com blocos A, B, C, D, G e I + marcos de 18 a 48 meses (cerca de 40 perguntas) + regras de sinais de alerta.
- [ ] Cálculo determinístico dos níveis de COM\_E (Communication Matrix), FAL (estágios 0–6) e REG (indicadores).
- [ ] Prompt de geração de perfil com citação de fontes e um ciclo de ajuste pelo responsável.
- [ ] Registro rápido em texto livre com etiquetagem automática de domínio.
- [ ] 20 fichas de estratégia + ranqueamento com o fator pessoal + cartão com botão "Fiz".
- [ ] Reavaliação simulada (com registros semeados) mostrando delta de níveis e gráfico por domínio.
- [ ] Tela de consentimento LGPD (mesmo que simples): mostra que vocês pensaram nisso.

**Roteiro de demo (5 minutos)**

1. **Cadastro:** mãe de Lia, 3 anos, preenche o formulário. Preocupação: "ela fala poucas palavras e fica muito brava quando não entendem".
2. **Perfil proposto:** COM\_E nível IV (aponta, puxa a mão), FAL estágio 3 (cerca de 10 palavras), REG com 6 episódios por semana. Pontos fortes: música e quebra-cabeças. Cada item mostra de qual resposta veio.
3. **Ajuste:** a mãe diz que Lia já usa figuras na terapia; a IA pergunta se quer corrigir a resposta, recalcula e o nível sobe para V. Perfil aceito.
4. **Professor:** registra um comportamento ABC na roda e dá feedback: "na escola ela usa mais gestos do que em casa".
5. **Chat:** a mãe pergunta como lidar com as crises na hora do banho. O chat sugere "aviso visual de transição". Ela toca em "Fiz" → "não funcionou". Na pergunta seguinte, o chat oferece outra opção primeiro e cita a tentativa anterior.
6. **Reavaliação (3 meses depois, dados semeados):** COM\_E de V para VI, FAL continua no estágio 3, episódios caem de 6 para 2 por semana; a IA propõe novas metas e mostra a divergência casa × escola.
7. **Fechamento:** exporta o resumo no formato do estudo de caso da política nacional, que a escola pode usar para o PEI sem exigir laudo.

**Frase de pitch:** "Transformamos o que pais e professores já observam todo dia em dados estruturados pela CIF, medidos com escalas reconhecidas e prontos para o estudo de caso que a nova política de educação especial exige."
