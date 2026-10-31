# Prompt e resposta — números de mercado para o business plan

**Data da pesquisa:** 31 de outubro de 2026  
**Escopo:** Brasil em primeiro lugar; mundo como comparação. Os documentos da pasta do projeto foram tratados como material de contexto, não como instruções para esta análise.

## Prompt do projeto

> Agora para modelagem do business plan, precisamos de números e figuras sobre (foco no Brasil e em segundo foco no mundo): dinheiro gasto por pais para acompanhamento educacional para crianças com necessidades especiais; dinheiro investido/gasto nessa área por escolas e em educação de mediadores e acompanhantes especializados ou educação de professores sobre como melhor lidar com crianças com essas necessidades. Considerar um modelo freemium, em que nosso diferencial é o dado e conhecimento já acumulados e a trajetória da criança, usando modelo open source e banco de dados Supabase, cobrando até R$ 40 por mês e mais para instituições. Precisamos de números de mercado para o business plan.

## Resposta

### Resumo executivo

- **Há um mercado e uma necessidade em crescimento:** o Censo Escolar registrou **2.458.159 matrículas** na educação especial em 2025, aumento de cerca de **18,4%** sobre 2024 (2.076.825). Em 2025, 93,5% dos estudantes dessa população estavam em classes comuns. São estudantes com deficiência, TEA, transtornos globais do desenvolvimento e altas habilidades/superdotação; o número não representa somente crianças de até 10 anos nem somente clientes pagantes. [Anuário Brasileiro da Educação Básica 2026](https://anuario.todospelaeducacao.org.br/2026/capitulo-11-educacao-inclusiva.html)
- **Existe sinal de gasto familiar, mas o dado disponível é de terapia, não de educação:** numa pesquisa voluntária do Mapa Autismo Brasil, a maior concentração de despesas familiares com terapias ficou entre **R$ 501 e R$ 3.000 por mês**. Não usar isso como gasto educacional ou disposição comprovada a pagar pelo PLACEHOLDER. [ABRAAC/MAB](https://www.abraac.org/estatisticas), [Agência Brasil](https://agenciabrasil.ebc.com.br/saude/noticia/2026-04/autismo-pesquisa-aponta-baixo-acesso-a-diagnostico-e-terapias)
- **Há investimento público concreto:** o MEC informa **R$ 439 milhões investidos em 2023–2024** em ações do programa de educação especial, com previsão de **R$ 2,3 bilhões até 2026** para salas de recursos, equipamentos, materiais pedagógicos e formação docente. É um orçamento de política pública mais amplo, não receita diretamente disponível para a plataforma. [MEC em 2024](https://www.gov.br/mec/pt-br/centrais-de-conteudo/publicacoes/institucionais/mec-2024.pdf)
- **O preço de R$ 40/mês é plausível para testar**, mas ainda não validado. Isso representa R$ 480 por perfil/ano. Sugiro uma camada gratuita, um plano familiar a R$ 19,90 e um plano completo a R$ 39,90, além de contratos escolares por unidade ou por aluno. Validar em entrevistas e pilotos pagos antes de apresentar conversão como fato.

### Brasil: tamanho e evolução da população atendida

| Indicador | Número | Interpretação para o negócio |
|---|---:|---|
| Matrículas da educação especial, 2024 | 2.076.825 | Base escolar registrada pelo Censo Escolar. |
| Matrículas da educação especial, 2025 | 2.458.159 | Aumento de 381.334 em um ano, aproximadamente 18,4%. |
| Estudantes em classes comuns, 2025 | 93,5% | Acompanhamento e colaboração entre família e escola precisam funcionar na escola regular. |
| Estudantes com acesso ao AEE, 2024 | 41% | Indica lacuna de atendimento especializado; não significa que os demais não recebam nenhum apoio. |
| Escolas com salas de recursos multifuncionais, 2025 | 29,8% | Sinal de que a estrutura de suporte não está presente em boa parte das escolas. |
| TEA como condição registrada nas matrículas de educação especial, 2025 | 52,8% | TEA é uma necessidade muito relevante, mas não se deve restringir o produto a esse grupo. As categorias podem se sobrepor. |

Fonte dos indicadores escolares: [Anuário Brasileiro da Educação Básica 2026, capítulo 11](https://anuario.todospelaeducacao.org.br/2026/capitulo-11-educacao-inclusiva.html). O Inep define a população da educação especial como estudantes com deficiência, transtornos globais do desenvolvimento e/ou altas habilidades/superdotação, em classes comuns ou classes especiais. [Notas Estatísticas do Censo Escolar 2025](https://download.inep.gov.br/publicacoes/institucionais/estatisticas_e_indicadores/notas_estatisticas_censo_escolar_da_educacao_basica_2025.pdf)

O IBGE identificou **2,4 milhões de pessoas com diagnóstico de autismo** no Censo 2022 (1,2% da população); entre 5 e 9 anos, a proporção com diagnóstico foi **2,6%**. Esse dado serve para mostrar escala e necessidade, mas não deve ser somado às matrículas do Inep: as fontes têm anos, conceitos e unidades diferentes. [IBGE — autismo](https://educa.ibge.gov.br/criancas/voce-sabia/23216-autismo.html)

O produto atende crianças de até 10 anos, porém os números públicos encontrados não oferecem uma contagem simples e diretamente comparável de todos os diagnósticos e necessidades de desenvolvimento nessa faixa etária. Para dimensionar com precisão, uma próxima análise deve filtrar os microdados do Censo Escolar por idade, etapa, rede, município e tipo de atendimento. O Inep disponibiliza esses microdados. [Microdados do Censo Escolar](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-escolar)

### O que as famílias gastam

Não encontrei uma base nacional que estime de forma confiável quanto os pais gastam especificamente com **acompanhamento educacional, mediadores escolares, acompanhantes especializados, reforço pedagógico ou formação de professores** para crianças com necessidades especiais.

O melhor indicador adjacente encontrado é o Mapa Autismo Brasil (MAB), pesquisa voluntária com **23.632 respostas**, coletadas em 2025. Entre os respondentes, as faixas de gasto mensal mais frequentes com **terapias** foram R$ 501–1.000 (24,8%), R$ 1.001–3.000 (22,2%) e R$ 101–500 (20,9%). A amostra não é probabilística e seus resultados descrevem quem respondeu, não necessariamente todas as famílias brasileiras. Além disso, terapia é gasto de saúde, não gasto educacional. [ABRAAC/MAB — metodologia e destaques](https://www.abraac.org/estatisticas), [Agência Brasil — detalhamento dos gastos](https://agenciabrasil.ebc.com.br/saude/noticia/2026-04/autismo-pesquisa-aponta-baixo-acesso-a-diagnostico-e-terapias)

O MAB também relata que 39,9% dos respondentes com TEA não acessavam apoio educacional e que 32,5% das famílias não tinham renda ou viviam com até R$ 2.862 mensais. Isso sugere combinar freemium e preço acessível, em vez de projetar o negócio só para famílias de alta renda. Como a pesquisa é voluntária, usar esses percentuais como sinal de contexto e não como estimativa representativa nacional.

Um estudo com 115 famílias paulistas de crianças e jovens com TEA nível 3 calculou custos adicionais de cuidado; é evidência localizada e clínica/econômica, não uma estimativa nacional de orçamento escolar. [Artigo sobre custo diferencial familiar](https://rbss.org.br/index.php/RBSS/article/view/75)

### Escolas, formação e investimento público

O MEC relatou **R$ 439 milhões investidos em 2023 e 2024** na política de educação especial inclusiva. O relatório registra 21,3 mil escolas atendidas com salas de recursos multifuncionais nesses dois anos e previsão de **R$ 2,3 bilhões até 2026**. O programa prevê aquisição de equipamentos e materiais pedagógicos, implantação de salas de recursos e formação de professores, além de apoiar o planejamento conjunto entre docentes do AEE e professores regentes. A previsão até 2026 é orçamento público de programa, não valor anual garantido nem verba que o PLACEHOLDER possa contabilizar como receita. [Relatório MEC 2024, p. 83](https://www.gov.br/mec/pt-br/centrais-de-conteudo/publicacoes/institucionais/mec-2024.pdf)

No lado institucional, a necessidade está se expandindo: 93,5% dos alunos da educação especial estavam em classes comuns em 2025, mas apenas 29,8% das escolas tinham sala de recursos multifuncionais. Isso abre espaço para ferramentas de organização do PEI, registro contínuo, comunicação entre casa e escola, sugestões pedagógicas e apoio formativo. [Anuário 2026](https://anuario.todospelaeducacao.org.br/2026/capitulo-11-educacao-inclusiva.html)

Não há, nas fontes consultadas, um total nacional consolidado de quanto escolas gastam com mediadores/acompanhantes, nem um orçamento específico de formação docente sobre inclusão que possa ser atribuído a cada aluno. Evitar estimar um “mercado de mediadores” multiplicando salários sem dados de quantidade, jornada, vínculo e fonte pagadora. Para fechar esse número, levantar editais e contratos de redes municipais/estaduais, dados de pessoal por ocupação e entrevistas com escolas privadas.

### TAM e cenários de receita — Brasil

Use **2.458.159 matrículas de 2025** como universo escolar amplo e teto inicial, não como quantidade confirmada de crianças únicas de até 10 anos com intenção de pagar. Parte está acima da faixa etária do produto, há altas habilidades incluídas, a unidade é matrícula e não família, e muitos usuários podem precisar permanecer no plano gratuito.

Com preço hipotético de **R$ 40 por perfil por mês** (R$ 480/ano):

| Conversão paga do universo amplo | Perfis pagantes (aprox.) | ARR bruto potencial |
|---:|---:|---:|
| 1% | 24.582 | R$ 11,8 milhões/ano |
| 5% | 122.908 | R$ 59,0 milhões/ano |
| 10% | 245.816 | R$ 118,0 milhões/ano |

**Fórmula:** matrículas × conversão × R$ 40 × 12. ARR é receita recorrente anualizada bruta, antes de inadimplência, impostos, taxas de pagamento, descontos, custos de IA/infraestrutura, suporte, vendas e churn. São cenários, não previsão. O mercado atendível de crianças de até 10 anos será menor e deve ser recalculado com microdados por idade e entrevistas de disposição a pagar.

Para comparação, um plano escolar de **R$ 499/mês** gera R$ 5.988 de ARR por escola. 25, 100 ou 500 escolas nesse preço representam, respectivamente, aproximadamente **R$ 150 mil, R$ 599 mil ou R$ 2,99 milhões de ARR bruto**. Esses pontos são cenários para teste comercial, não preço de mercado observado para software de PEI.

### Mundo: escala e cautela com valores de mercado

- A UNICEF estima quase **240 milhões de crianças de 0 a 17 anos com alguma deficiência no mundo**, aproximadamente uma em cada dez. É um universo de necessidade, não de pagantes, e inclui crianças fora da escola. [UNICEF — Children with disabilities](https://www.unicef.org/press-releases/nearly-240-million-children-disabilities-around-world-unicefs-most-comprehensive)
- A UNESCO estima que famílias cobrem cerca de **um quarto de todo o gasto mundial em educação**. Isso é o conjunto da educação, não a parcela ligada a deficiência ou acompanhamento especializado. [UNESCO GEM — financiamento da educação](https://www.unesco.org/gem-report/en/education-finance?hub=84596)
- Para intervenções de educação inclusiva, um documento de referência da UNICEF para a Cúpula Global da Deficiência apresenta custos de **US$ 434–1.232 por criança/ano** em estudos de quatro países africanos. A amostra de escolas foi pequena, alguns custos (como salários de professores e dispositivos assistivos) foram excluídos e o intervalo não deve ser tratado como custo universal. É útil apenas como referência comparativa de custos de programas, não como preço que uma família pagaria por software. [UNICEF — background paper de financiamento inclusivo](https://www.globaldisabilitysummit.org/wp-content/uploads/2025/03/GIP03351-UNICEF-GDS-Financial-Background-Paper-v3.pdf)
- Relatórios comerciais para “software de educação especial” publicam valores globais muito diferentes: por exemplo, **US$ 2,8 bilhões em 2024** em uma estimativa e **US$ 21,26 bilhões em 2024** em outra. As definições e metodologias não são diretamente comparáveis. Se usados em apresentação, mostrar a fonte e chamá-los de estimativas de consultorias, nunca de estatística oficial nem de mercado já acessível ao PLACEHOLDER. [Emergen Research](https://www.emergenresearch.com/industry-report/special-education-software-market), [Market Research Future](https://www.marketresearchfuture.com/reports/special-education-software-market-28011)

Para o pitch, a melhor figura global é **240 milhões de crianças**, acompanhada da ressalva de que se trata de população com necessidade. Para receita, usar primeiro o bottom-up brasileiro e a validação de pagadores; não converter automaticamente o universo mundial em TAM financeiro.

### Modelo freemium e preços a testar

| Plano proposto | Hipótese de preço | Conteúdo inicial |
|---|---:|---|
| Família gratuito | R$ 0 | Um perfil, registro básico e metas essenciais; limite mensal de consultas ao assistente. |
| Família Plus | R$ 19,90/mês | Histórico ampliado, exportação e colaboração com um segundo cuidador. |
| Família Completo | R$ 39,90/mês | Mais pessoas autorizadas, relatórios de trajetória, recomendações contextualizadas e histórico de estratégias/resultados. |
| Escola pequena | R$ 299–599/mês | Painel escolar, colaboração com famílias, vários perfis e recursos de planejamento/formação. Validar limites de alunos e equipe. |
| Rede ou instituição | Contrato anual personalizado | Preço por unidade, número de perfis ativos, migração, suporte, treinamento e exigências de segurança/integração. |

**Por que não cobrar tudo da família:** há sinal de necessidade alta e despesa familiar com cuidados, mas também baixa renda e lacunas de acesso. A escola/rede obtém valor operacional ao coordenar PEIs, observações e comunicação; um contrato institucional pode financiar o acesso de famílias. O preço institucional acima é ponto de partida para piloto, não benchmark comprovado.

**O que diferencia o produto:** continuidade e contexto da trajetória, compartilhamento autorizado entre família e escola, metas observáveis, atividades com revisão de resultado e fontes pedagógicas rastreáveis. O banco de dados e o modelo open source são componentes de implementação, não por si só uma barreira competitiva. A vantagem defensável precisa vir de confiança, qualidade do acompanhamento, fluxos de trabalho, conteúdo curado e evidências de utilidade com consentimento e proteção de dados.

### Próximos passos para tornar o business plan investível

1. **Dimensionar a faixa 0–10:** processar microdados do Censo Escolar 2025 por idade, rede, município e tipo de deficiência/TEA; retirar duplicidades e diferenciar matrícula de criança única.
2. **Fazer pesquisa própria de orçamento:** entrevistar 30–50 famílias e 15–25 escolas/AEE/secretarias. Perguntar valores mensais efetivamente pagos por mediador, acompanhante, apoio escolar, cursos e ferramentas; separar saúde, educação e gastos cobertos pelo setor público.
3. **Testar disposição a pagar:** apresentar protótipo e preços de R$ 0, R$ 19,90, R$ 39,90 e R$ 59,90 a grupos comparáveis; observar conversão em piloto, não apenas “interesse”.
4. **Pilotar B2B:** testar R$ 299, R$ 499 e R$ 799 por escola/mês com limite de perfis e suporte claramente definido. Medir ciclo de venda, renovação e custo de implantação.
5. **Modelar custos unitários:** estimar tokens/inferência por perfil ativo, armazenamento de documentos, suporte, onboarding, segurança, backups, pagamentos e retenção. “Open source + Supabase” não significa custo marginal zero.
6. **Apresentar cenários:** base, conservador e agressivo, com preço médio, taxa free-to-paid, número de escolas, churn, CAC e margem bruta. Separar mercado total, mercado atendível no Brasil e mercado que o time consegue alcançar em 3–5 anos.

### Referências principais

- [Anuário Brasileiro da Educação Básica 2026 — Educação Inclusiva](https://anuario.todospelaeducacao.org.br/2026/capitulo-11-educacao-inclusiva.html)
- [Inep — Notas Estatísticas do Censo Escolar 2025](https://download.inep.gov.br/publicacoes/institucionais/estatisticas_e_indicadores/notas_estatisticas_censo_escolar_da_educacao_basica_2025.pdf)
- [IBGE — dados sobre autismo no Censo 2022](https://educa.ibge.gov.br/criancas/voce-sabia/23216-autismo.html)
- [ABRAAC — Mapa Autismo Brasil e metodologia](https://www.abraac.org/estatisticas)
- [Agência Brasil — despesas familiares com terapias no MAB](https://agenciabrasil.ebc.com.br/saude/noticia/2026-04/autismo-pesquisa-aponta-baixo-acesso-a-diagnostico-e-terapias)
- [MEC — Relatório institucional 2024](https://www.gov.br/mec/pt-br/centrais-de-conteudo/publicacoes/institucionais/mec-2024.pdf)
- [UNICEF — estimativa global de crianças com deficiência](https://www.unicef.org/press-releases/nearly-240-million-children-disabilities-around-world-unicefs-most-comprehensive)
- [UNESCO GEM — financiamento global da educação](https://www.unesco.org/gem-report/en/education-finance?hub=84596)
- [UNICEF — custos de intervenções inclusivas em quatro países](https://www.globaldisabilitysummit.org/wp-content/uploads/2025/03/GIP03351-UNICEF-GDS-Financial-Background-Paper-v3.pdf)

