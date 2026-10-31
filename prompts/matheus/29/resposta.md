# Login, compartilhamento, canal, PDF, reavaliação com formulário e revisão visual

Os 13 itens estão implementados e rodando em http://localhost:5173.
- **Backend:** 19 testes passando (eram 14).
- **Navegador:** as telas foram conferidas por screenshot no Chrome. Um fluxo automatizado percorreu: cadastro → criança → convite → aceite → canal → login → PDF → revogação, sem erros.

## Item por item
| Pedido | O que foi feito |
| --- | --- |
| Fonte +50% | Textos de 8–11px subiram 50% (8→12, 10→15, 11→16,5). Acima disso o aumento diminui aos poucos, e os títulos grandes sobem ~18% para manter a hierarquia. O ajuste foi feito por script nos dois CSS. Textos de leitura têm piso de ~14px. |
| Info sobre o sistema no formulário | Bloco "Antes de começar · Como funciona" no início, com 3 etapas: você responde (15–25 min), a IA organiza, você decide. |
| Alinhamento dos inputs | Grades de formulário com *subgrid*: o rótulo ocupa a mesma altura nos campos lado a lado, e os inputs ficam na mesma linha mesmo quando um rótulo quebra ou tem dica embaixo. Todos os campos têm a mesma altura (46px), o mesmo raio e a mesma fonte. |
| Espaçamento e formatação | Escala única de espaçamento (4/8/12/16/24/32px) aplicada a cartões, blocos, botões e grades. Também foi corrigida a ordem dos CSS: o `styles.css` carregava depois do `pp.css` e anulava os ajustes. |
| Avisar sobre respostas completas | Aviso "Quanto mais completo, melhor o resultado" no início. Lembrete com exemplo concreto a cada 4 áreas. Na revisão, o aviso de que "Não informado" deixa o perfil menos preciso. |
| Formulário na reavaliação + PDF | **Reavaliação:** duas opções, "Atualizar o formulário e reavaliar" (recomendado) e "Só com os registros". O formulário volta pré-preenchido com as últimas respostas, com a idade de hoje; as perguntas novas da idade aparecem em branco. Com o formulário novo, as cores das áreas por idade são recalculadas pelas regras e o agente é obrigado a usá-las. **PDF:** botão "Resumo em PDF" na visão geral e no painel. O resumo tem cerca de 2 páginas: quem é a criança, o que vai bem, as 14 áreas com cor e motivo, foco, metas com o último progresso, dicas, evolução, lembretes e o aviso de que não é diagnóstico. |
| Generalizar o responsável | "Responsável pelo perfil" (mãe, pai, avó, tutor legal, cuidador…), com o vínculo escolhido numa lista ao criar a conta e ao cadastrar a criança. |
| Generalizar o professor | "Acompanhante", com função: professor, pedagogo, médico, terapeuta, familiar ou outro. A função aparece nos registros, no canal, no chat e no dossiê da reavaliação. Os poderes são os que o professor tinha. |
| Ícone da aba | `public/favicon.svg`: o mesmo coração verde da marca. |
| Saiba mais | Janela de verdade (antes era um alerta do navegador): os 5 passos da plataforma e o que ela não faz. Acessível na tela inicial, na barra lateral, na visão geral e no rodapé. |
| Login | Contas com e-mail e senha (hash PBKDF2) e sessão por token. O backend descobre pelo token quem age e o papel em cada criança; o `autor_id` do corpo não vale mais. Uma conta pode ter os dois perfis e alternar no menu. Telas novas de Entrar e Criar conta. |
| Compartilhar (do zero) | O responsável convida pelo e-mail com a função; o convite fica pendente até a pessoa entrar e aceitar ou recusar. O responsável vê quem tem acesso, cancela convites e remove acessos. Remover corta o acesso na hora. O vínculo por turma deixou de dar acesso. |
| Canal direto por criança | "Canal da equipe" na barra lateral e no painel: mensagens entre o responsável e os acompanhantes, com nome e função, atualizando a cada 6s. Fica separado do assistente de IA. Cada pessoa vê só as próprias conversas com a IA. |

## Arquivos principais
- **Backend:**
  - novos: `backend/auth.py` (login, sessão, papéis) e `backend/resumo_pdf.py` (PDF com reportlab);
  - `backend/plataforma.py` reescrito: rotas com login, compartilhamento, canal, PDF, formulário atual e reavaliação com formulário.
- **Banco:**
  - tabelas `conta`, `sessao_login`, `compartilhamento` e `canal_mensagem`;
  - colunas `conta_id`, `funcao` e `instituicao`, com migração automática do banco existente.
- **Agente:** `reavaliacao.py`, `agente.py` e `prompts.py` aceitam o formulário atualizado; o chat e o dossiê mostram a função de quem registrou.
- **Frontend:**
  - novos: `Acesso.jsx`, `Canal.jsx`, `Compartilhar.jsx` e `SaibaMais.jsx`;
  - alterados: `App.jsx`, `Painel.jsx`, `api.js` (token em toda chamada) e `pp.css` (ajustes globais);
  - `styles.css` com as fontes escaladas.

## Demonstração
- Senha de todas as contas demo: `demo1234`.
  - `ana@demo.primeirospassos`: responsável da Lia e da Nina.
  - `carla@demo.primeirospassos`: professora da Lia e da Nina.
  - `rafael@demo.primeirospassos`: pediatra da Lia.
- Na tela inicial, "Família da Lia" e "Professora Carla" entram direto.
- Contas criadas antes do login ficaram sem senha. Para recuperar, crie a conta com o mesmo e-mail: o perfil antigo e as crianças são reaproveitados.

## Observações
- O backend agora depende do `reportlab` (adicionado em `backend/requirements.txt`). No servidor, rode `pip install -r backend/requirements.txt`.
- Internamente o papel de acompanhante continua se chamando `professor` (tabela e API), para não reescrever o modelo de dados; a interface usa "acompanhante" e a função de cada pessoa.
