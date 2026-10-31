Montei o esquema completo em PostgreSQL, compatível com Supabase, e o diagrama de relacionamentos: acompanhamento_schema.sql e modelo_er.png. Rodei o esquema num Postgres 16 local e simulei o fluxo inteiro:

Perfil: o responsável aceita a segunda proposta do perfil; ela vira a vigente e a primeira é descartada.
Chat: a IA sugere uma estratégia e o pai toca em “Fiz → não funcionou”. A sugestão fica marcada como feita e o histórico registra a tentativa, o que baixa a prioridade dessa estratégia nas próximas respostas.
Restrições: o banco recusou um registro de saúde feito por professor e um registro de chat sem mensagem de origem.

Como as entidades de vocês viraram tabelas

Professor e Responsável: os dois são um usuario (o login). Ser professor ou responsável vem do vínculo. Assim a mesma pessoa pode ser as duas coisas, e qualquer um pode ter várias crianças:
crianca_responsavel liga responsáveis e crianças, em qualquer quantidade, com parentesco e um “titular” que dá os consentimentos;
turma_professor liga professores a turmas e guarda o papel (regente, auxiliar, AEE);
professor_escola liga professores às escolas onde trabalham.
Classe: virou turma, sempre de um ano letivo. matricula guarda o histórico da criança quando ela muda de turma ou de escola.
Avaliação: separei em duas tabelas.
avaliacao é o evento (inicial ou reavaliação).
perfil_versao guarda cada proposta da IA durante a negociação com o pai. O banco garante que só existe um perfil vigente por criança.
Os níveis de cada área ficam em nivel_dominio, uma linha por área, e é dali que saem os gráficos de evolução.
Reports: os 8 tipos ficam numa tabela só, registro. Os campos comuns são colunas. Os campos usados em filtros e no ranqueamento do chat também são colunas: meta, estratégia, resultado, nível de ajuda e nível de meta. O que é específico de cada tipo fica num campo dados. Regras no banco obrigam cada tipo a ter seus campos (um check-in de meta sem meta é recusado).

Chat: todo o gerenciamento passa pelo banco.

conversa: pertence a um usuário e a uma criança. Guarda um resumo das mensagens antigas para não reenviar a conversa inteira ao modelo.
mensagem: cada mensagem tem ordem, status (gerando, concluída, erro) e blocos estruturados para os cartões e botões. Também guarda modelo, tokens consumidos e tempo de resposta.
mensagem_contexto: registra quais perfis, metas e registros foram enviados ao modelo em cada resposta. Isso permite explicar por que o chat sugeriu algo e auditar quais dados da criança saíram do banco.
sugestao_estrategia: cada cartão de estratégia que o chat oferece. O atalho “Fiz” cria um registro ligado à sugestão e à mensagem de origem.
Outras tabelas do chat: chamada_ferramenta (quando o agente busca registros ou propõe um registro), mensagem_feedback (útil / não útil) e a busca semântica com pgvector, tanto na base teórica quanto nos registros da criança.

O que estava faltando no modelo de vocês

Acesso autorizado: o professor estar na turma não deveria bastar para ver a criança. acesso_crianca guarda a autorização do responsável, que pode ser revogada, e uma permissão separada para ver dados de saúde. A tabela também cobre quem não está na turma, como o professor de AEE.
Consentimentos da LGPD: consentimento separa os tipos e guarda a versão do termo. log_acesso registra quem leu o quê.
Metas como entidade própria: os check-ins precisam apontar para algo que continua existindo depois da reavaliação.
Base teórica no banco: áreas do desenvolvimento, escalas, marcos, perguntas do formulário, biblioteca de metas e fichas de estratégia. O formulário e o chat leem dali.
Operação do dia a dia:
convite vincula professores e outros responsáveis;
notificacao cobra o feedback depois de um “vou tentar” e lembra do check-in semanal;
alerta guarda os sinais de alerta;
anexo guarda laudos, fotos e vídeos;
a view linha_do_tempo junta tudo em ordem.

Ficaram de fora as regras de acesso do Supabase (RLS), que limitam o que cada usuário lê no banco. Sem elas, qualquer usuário logado poderia ler dados de outras crianças. Também falta fixar o tamanho do vetor de busca: deixei 1536, que precisa bater com o modelo de embedding escolhido. Se quiserem, escrevo as regras de RLS e um script com dados de exemplo da Lia para a demo de amanhã.