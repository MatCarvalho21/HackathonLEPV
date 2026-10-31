# Descrição do projeto, conferência das entregas e ajuste do README

## Descrição em 500 caracteres
> Quem cuida de uma criança junta observações soltas: o que a creche contou, o que a pediatra pediu, a crise de ontem. Cada um vê só um pedaço. O AjudaP.ai reúne família, escola e saúde em torno de cada criança de 0 a 10 anos. A família preenche um formulário e a IA, apoiada em fontes oficiais, propõe um perfil com semáforo por área, metas e dicas personalizadas. Todos registram o dia a dia, tiram dúvidas com um assistente e veem a evolução. Não diagnostica: orienta e indica quando procurar ajuda.

Exatamente 500 caracteres com espaços. Para encurtar, tire "de 0 a 10 anos".

## Conferência das entregas
**Precisava resolver:**
- **Repositório:** o link do GitHub, aberto sem login, respondeu 404. Parece estar privado e precisa ficar público para a banca (isso só dá para mudar no GitHub).
- **Nome da pasta:** o edital pede `/PROMPTS`, e a pasta se chama `prompts/`. O código importa `prompts/matheus/07/ouput.json` em `src/questionnaire.js`; se renomear, é preciso trocar esse caminho.

**Valia ajustar:**
- **Como rodar:** o README começava por uma opção com túnel SSH para um servidor interno, que a banca não consegue usar.
- **Entregas:** o README não apontava para o plano de negócio nem para a pasta de prompts.

**Estava ok:**
- **Deploy:** respondeu 200, e os botões de demonstração entram sem senha.
- **Plano de negócio:** o PDF está em `plano_de_negocio/plano.pdf`.
- **Como rodar:** o README tem as instruções local e Docker.
- **Segredos:** o `.env` e os venvs não estão versionados.
- **Git:** o `main` estava em dia com o `origin`.

## O que foi feito no README
- **Opção A removida:** saiu a opção do túnel SSH para o servidor interno. "Clonar e rodar" virou a Opção A e "Docker" virou a Opção B.
- **Clone por HTTPS:** o `git clone` passou a usar HTTPS em vez de SSH, para funcionar sem chave cadastrada no GitHub.
- **Verificação de saúde:** a verificação rápida (`/api/health`) foi para o fim da nova Opção A.
- **Seção "Entregas do hackathon":** entrou no topo do README, com a tabela de vídeo, plano de negócio, aplicação no ar, repositório e sessões de IA. O link do vídeo ficou como _link do vídeo_ para ser preenchido.
