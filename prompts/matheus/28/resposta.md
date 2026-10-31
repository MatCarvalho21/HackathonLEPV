# Erro 500 ao gerar o mapeamento (criança de 131 meses)

## Causa
O formulário foi salvo, mas `POST /api/avaliacoes` falhava ao montar o dossiê para o agente:

```
File "src/agente_perfil/dossie.py", line 93, in montar_dossie
    "fontes_referencia": sorted({q["fonte"] for q in d.get("perguntas", []) if q.get("fonte")}),
TypeError: unhashable type: 'list'
```

Nos marcos de algumas faixas (como os de 6 a 10 anos, BNCC), a `fonte` é uma **lista** de referências, e não um texto. O frontend já tratava os dois casos, mas o dossiê não. O exemplo pré-preenchido (38 meses) só tem fontes em texto, por isso os testes não pegaram o caso.

## Correção
- `src/agente_perfil/dossie.py`: `fontes_referencia` aceita fonte em texto ou em lista.
- Verificação: montei o dossiê para **todas as 792 combinações** de idade (0 a 131 meses) e ano escolar (nenhum, 1º a 5º), sem nenhum erro. Os testes continuam passando (14).
- O formulário que você já enviou (Paulo, 131 meses) agora monta o dossiê normalmente. Ele ficou salvo duas vezes, uma por tentativa; o agente usa o mais recente.

## Como continuar
Na visão geral, selecione o Paulo e clique em **Gerar mapeamento**. O formulário já está salvo, então não precisa preencher de novo.
