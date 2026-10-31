# Layout para a fonte maior, notificações, ícones no lugar de emojis e o nome AjudaP.ai

Tudo implementado e rodando em http://localhost:5173.
- **Backend:** 20 testes passando (eram 19).
- **Navegador:** todas as telas e abas do painel foram revisadas por screenshot no Chrome. O fluxo completo (cadastro → convite → aceite → canal → PDF → revogação) e o de notificações rodaram sem erros.

## Layout
- **Rodapé fixo removido.** "Saiba mais" e "Sair" continuam no cabeçalho da tela inicial, na barra lateral e no menu do perfil. A barra lateral e o conteúdo vão até o fim da tela.
- **Landing mais larga:** até 1520px (94% da tela), com hero maior e a ilustração ampliada.
- **Barra lateral:** de 248px para 300px (260px em telas médias).
- **Grades repensadas para a fonte maior:**
  - as 14 áreas passaram de 6 para 4 por linha;
  - a visão geral do painel passou de 3 para 2 colunas: resumo e "Foco agora" em faixas inteiras (os três focos lado a lado), e metas de curto prazo ao lado dos últimos registros;
  - metas, dicas e o comparativo de evolução ficaram com 2 por linha;
  - a lista de perfis da visão geral foi alargada;
  - campos do novo registro alinhados pela base;
  - abas do painel e filtros da linha do tempo quebram linha em vez de cortar.
- **Saiba mais:** modal largo (até 1280px), com os passos em 3 colunas e o "o que a plataforma não faz" ocupando a última célula. O botão "Entendi" foi para o cabeçalho. Não rola nem em 1366×768.

## Notificações (novo)
- **Quem recebe** (por conta de login; quem fez a ação nunca recebe):
  - novo registro e mensagem no canal → responsável e acompanhantes da criança;
  - perfil aprovado → acompanhantes;
  - convite novo → a pessoa convidada;
  - convite aceito → o responsável.
- **Sino na barra lateral** com contador. Ele abre um painel com:
  - ícone do tipo;
  - "Carla Mendes, professor(a), registrou uma conquista sobre Lia";
  - um trecho do conteúdo, a criança e "há 5 min".
- **Abrir** marca como lida e leva ao lugar: registro → linha do tempo; canal → canal da equipe; perfil → painel; convite → visão geral. A **lixeira** apaga, e há "Marcar todas como lidas". Abrir o canal marca como lidas as mensagens daquela criança.
- Quem perde o acesso deixa de receber. Os dados de demonstração já vêm com algumas notificações para a Ana e a equipe.
- **Arquivos:** `backend/notificacoes.py` (geração e rotas), tabela `notificacao`, `src/jornada/Notificacoes.jsx`.

## Ícones no lugar de emojis
Novo `src/jornada/icones.jsx`, com ícones lucide para:
- tipos de registro (conquista, comportamento, saúde…);
- resultado de estratégia (funcionou / em parte / não funcionou);
- as 14 áreas do formulário.

Também foram trocados os emojis da linha do tempo, das versões do perfil, da evolução, das dicas (relógio), dos estados vazios e da ilustração da tela inicial. Não sobrou nenhum emoji no código da interface.

## Nome: AjudaP.ai
- **Aba do navegador:** só "AjudaP.ai".
- **Tela inicial:** "AjudaP.ai | Acompanhamento e Suporte".
- **Barra lateral:** "AjudaP.ai".
- **Saiba mais:** título "AjudaP.ai: Acompanhamento e Suporte".
- **Também atualizados:** rodapé do PDF, título da API, prompts do agente e do chat, README.
- Os e-mails das contas de demonstração continuam `@demo.primeirospassos` (são dados).

## Problema encontrado no caminho
O Vite vigiava a pasta inteira do projeto (`.venv`, `chroma_db`, banco SQLite) e estourou o limite de *watchers* do sistema (`ENOSPC`). Arquivos novos não recarregavam no navegador. O `vite.config.js` agora ignora essas pastas.
