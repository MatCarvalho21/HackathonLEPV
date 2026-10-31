# Espaçamento em "Perfil e versões" e linha do tempo no estilo do Diário

## Perfil e versões (e Metas)
- **Causa:** os blocos eram renderizados lado a lado, sem contêiner nem espaço entre eles. O mesmo acontecia com os três horizontes da aba Metas.
- **Correção:** um contêiner `pp-pilha` (grade com 16px de espaço, a escala usada no resto do app) nas duas abas.
- As versões do perfil viraram cartões: ícone, "Versão N" com selo (Vigente, Substituída, Ajustada), datas de criação e aprovação, pedido de ajuste (se houver) e o botão "Ver esta versão". A versão vigente fica destacada em verde.
- A lista de próximos passos ganhou espaço entre os itens.

## Linha do tempo
Reescrita com os mesmos cartões do Diário (`journal-entry`):
- **Topo:** selo com ícone e tipo do registro, e a data e hora.
- **Corpo:** o texto. Em estratégias testadas, o título traz a estratégia com o ícone do resultado.
- **Etiquetas:** onde aconteceu, áreas relacionadas, estratégia usada e se funcionou, intensidade, duração e nível de ajuda.
- **Rodapé:** quem registrou e a função.
- Os registros ficam agrupados por dia ("Hoje", "Ontem", "29 de out.") com um separador.
- Uma borda colorida à esquerda indica o tipo: conquista, comportamento, saúde, meta ou estratégia.
- Os filtros por tipo quebram linha, e o estado vazio tem mensagem.

Arquivos: `src/jornada/Painel.jsx` (`Metas`, `Linha`, `Historico`) e `src/jornada/pp.css`. Conferido por screenshot no Chrome, sem erros no console.
