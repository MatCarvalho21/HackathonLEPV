# Push recusado: chroma_db/chroma.sqlite3 com 112 MB

## Diagnóstico
- O arquivo cresceu de 58 MB para 112 MB no commit `bbbf47d` (depois, merge `2ca7a83`), ambos ainda não enviados. O `chroma.sqlite3` passou a guardar **duas coleções completas**: a antiga (`desenvolvimento_infantil_kb`, bge-m3, 1024 dimensões) e a nova (`desenvolvimento_infantil_kb_e5small`, 384 dimensões, 6.422 chunks).
- O GitHub recusa arquivos acima de 100 MB. O Git LFS não está instalado no servidor.
- A coleção leve está completa e funcionando. Reiniciei o backend e ele já a usa, sem o fallback para o bge-m3.

## O que tentei
Apagar a coleção antiga (que deixou de ser necessária) e compactar o SQLite. O classificador de permissões bloqueou a operação por ser destrutiva, então nada foi alterado. Perguntei ao usuário qual caminho seguir:
1. **Apagar a coleção antiga e compactar (recomendado):** o arquivo deve cair bem abaixo de 100 MB. Depois, reescrevo só os 2 commits não enviados, trocando o arquivo, e faço o push normal (sem force).
2. **Tirar `chroma_db/` do git:** cada pessoa reindexa localmente (cerca de 1 minuto na GPU, 10 a 15 minutos em CPU).
3. **Git LFS:** exige instalar o git-lfs aqui e em cada máquina do time, e consome a cota de LFS do GitHub.

## Resolução (opção 1, escolhida pelo usuário)
1. Fiz backup do `chroma_db` no scratchpad e apaguei a coleção antiga (`desenvolvimento_infantil_kb`, bge-m3). Rodei `VACUUM` no SQLite e removi as duas pastas de segmento órfãs (`25c545b7…`, `e01d09a9…`), que nenhum segmento referenciava. O `chroma.sqlite3` caiu de 112 MB para 76 MB, e o `chroma_db` de 160 MB para 87 MB. O que sobrou é tudo da coleção ativa (índice de texto, metadados e trechos).
2. Recriei só os 2 commits não enviados (`bbbf47d` e o merge `2ca7a83`) com o mesmo autor, data e mensagem, trocando apenas a árvore `chroma_db/`. Conferi que nenhum arquivo fora de `chroma_db/` mudou e que o `origin/main` continuava ancestral.
3. Fiz o push normal, sem force: `c97f6c5..29de35f main -> main`. O GitHub agora só avisa que o arquivo passa dos 50 MB recomendados.
4. O backend foi reiniciado e usa a coleção leve (`intfloat/multilingual-e5-small`). Validei a busca, inclusive em CPU.

A ponta antiga ficou no branch local `backup/antes-do-fix-chroma` (não enviado). Pode ser apagada com `git branch -D backup/antes-do-fix-chroma`.
