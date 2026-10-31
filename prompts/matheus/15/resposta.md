# Resposta sobre o aviso `fontTools`

**Não é erro!** Trata-se apenas de um **aviso informativo (warning)** da biblioteca `pypdf`.

### Por que esse aviso aparece?
Alguns arquivos PDF antigos ou diagramados com certas ferramentas usam fontes vetoriais no formato `Type1/CFF`. O `pypdf` emite esse aviso para informar que uma biblioteca opcional chamada `fontTools` poderia ajudar a decodificar caracteres muito específicos dessas fontes caso houvesse algum caractere corrompido.

### Prova de que deu tudo certo:
Como mostram os logs seguintes do seu terminal:
1. `Processando PDFs: 100% | 74/74 [01:11<00:00]` ➔ **Todos os 74 PDFs foram lidos e processados com sucesso!**
2. `Total de novos chunks gerados: 7760` ➔ O texto foi fatiado perfeitamente em 7.760 blocos.
3. `[Etapa 2/2] Vetorizando e salvando no ChromaDB (Lotes de 64)...` ➔ Ele já estava gerando os vetores e salvando no banco.

O tempo estimado para concluir a gravação dos vetores é de apenas **~3 minutos**! Você pode deixar o processo terminar naturalmente.
