Vou checar o conteúdo e a licença de cada um dos 7 documentos antes de montar o catálogo e o pipeline de indexação.

Os documentos que você listou estão confirmados. Antes de escrever o código, crio uma aba no documento para o catálogo e o desenho da indexação.

Pipeline testado. Agora preencho as seções restantes da aba Base de conhecimento.

Montei a base de conhecimento e o pipeline de indexação. Testei com documentos de exemplo, porque os PDFs reais ainda precisam ser baixados; o desenho completo está na nova aba **Base de conhecimento** do [mapa do conhecimento](https://claude.ai/artifact/RcR4fTyifhwAdYN35fJQ3g).

**Sobre os seus 7 documentos:** 5 entram no RAG e 2 não.

- **Entram:**
  - os dois guias da OMS: o de visitas domiciliares (usado para definir metas) e o dos participantes (o principal para o chat dos pais);
  - a Caderneta da Criança, só a parte da família;
  - os dois relatórios da EEF (alfabetização e matemática).
- **Ficam fora:**
  - **SWYC:** é um questionário de triagem e o site não informa a licença. Serve para conferir as perguntas do formulário inicial, não para o agente usar.
  - **SDQ:** a versão eletrônica precisa de autorização dos autores. O app aceita o upload do resultado feito por um profissional.

Para fechar 10, sugiro três documentos que cobrem lacunas dos seus:

- **EEF, alunos com necessidades especiais na escola comum:** é o mais próximo do tema do produto.
- **Pyramid Model, materiais em português para famílias:** crises, mordidas, emoções.
- **Política Nacional de Educação Especial Inclusiva** (decretos e portaria do MEC): estudo de caso, PEI, apoio sem laudo. Atos oficiais são de domínio público.

Deixei dois opcionais: o guia de Harvard sobre funções executivas e a EEF de 7 a 11 anos, porque os seus documentos escolares param nos 7.

**Como organizei:** separei o conhecimento em três camadas, porque nem tudo deve ir para o banco vetorial.

1. **Marcos e regras do semáforo:** ficam estruturados e nunca passam pelo RAG. Assim a cor de um domínio não depende do trecho que a busca trouxe.
2. **Fichas de estratégia:** escritas pela equipe, cada uma com um identificador fixo. É isso que permite registrar "Fiz, não funcionou" e não repetir a sugestão.
3. **Documentos:** recortados em trechos, servem para fundamentar e detalhar as respostas.

**O que está no zip:**

- **`catalogo.json`:** licença, público, idade e citação pronta de cada documento.
- **`schema_kb.sql`:** tabelas no Postgres com busca vetorial (pgvector, funciona no Supabase). A busca combina sentido e palavras exatas, para achar termos como "PEI" e "laudo", filtra por idade, público e domínio e registra cada consulta.
- **`ingest.py`:**
  - extrai PDF, HTML e as fichas;
  - recorta trechos de cerca de 350 palavras por seção;
  - etiqueta domínio e idade;
  - gera os vetores;
  - só reindexa o arquivo que mudou.
- **`buscar.py`:** a ferramenta `buscar_base_conhecimento` pronta para o agente, com as instruções de citação.
- **`fichas_estrategia.json`:** 4 fichas de exemplo. Para a demo, o ideal são umas 20.

**No teste local, com Postgres e pgvector, funcionaram:**

- seções e páginas corretas;
- a faixa de idade estreitada pelo próprio texto;
- o filtro de idade excluindo fichas fora da faixa;
- a busca por "laudo" encontrando o decreto.

Usei vetores falsos no teste. A qualidade real da busca só dá para medir com o modelo de verdade e os PDFs completos; a aba traz 6 perguntas de teste para isso.

**Para rodar:**

1. Baixe os PDFs para a pasta `docs/` com os nomes do catálogo.
2. Ajuste no `catalogo.json` os títulos das seções da Caderneta que devem ficar de fora (os que deixei são suposição) e o nome dos 5 PDFs do Pyramid Model.
3. Escolha um modelo de embedding multilíngue, porque metade do acervo está em inglês.
4. Rode a indexação conforme o `README.md`.

**Licenças:** o material da OMS permite uso não comercial com citação. Serve para o hackathon, mas um produto comercial precisaria de autorização. Os termos da EEF, do Pyramid Model e de Harvard precisam ser confirmados antes de lançar.