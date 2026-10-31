# Túnel SSH: erro "Address already in use"

O comando foi rodado **no próprio servidor** (o prompt mostra `matheus@ERJ0700`, que é a máquina remota). Ou seja, foi um SSH do servidor para ele mesmo. Lá, a porta 5173 já está ocupada pelo Vite, daí o `Address already in use`.

O túnel precisa ser aberto **na sua máquina local**: num terminal do seu computador, não no terminal integrado do VS Code conectado ao servidor.

Como você usa VS Code Remote-SSH, o mais simples é encaminhar a porta pelo painel **Ports**:
1. `Ctrl+Shift+P` → "Ports: Focus on Ports View" (ou `Ctrl+J`, aba *Ports*);
2. **Forward a Port** → `5173`;
3. abrir http://localhost:5173 no navegador da sua máquina.

Encerre com `Ctrl+C` o ssh que ficou aberto no servidor.
