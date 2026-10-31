# Acesso à aplicação a partir de um workspace remoto (SSH)

Dá para acessar sem clonar nada, com um túnel SSH, e essa é a opção recomendada: a GPU, a base vetorial e os modelos já estão no servidor. Só a porta **5173** precisa ser encaminhada, porque o Vite no servidor repassa `/api` para a porta 8000 lá mesmo.

- **VS Code Remote-SSH:** abra o painel *Ports*, escolha *Forward a Port*, digite `5173` e abra http://localhost:5173.
- **Terminal local:** rode `ssh -N -L 5173:127.0.0.1:5173 matheus@10.23.20.12` (ou o alias que você usa no ssh) e abra http://localhost:5173.

Para rodar localmente, é preciso clonar o repositório, criar o `.env` com `API_KEY`, criar o venv e instalar `backend/requirements.txt` (mais o torch para CPU e `src/rag/requirements.txt`, se quiser o RAG), rodar `npm install` em `frontend/` e subir uvicorn e vite em dois terminais. Na primeira busca, o RAG baixa cerca de 2 a 3 GB de modelos; é possível subir sem ele com `RAG_DESATIVADO=1`. O código precisa estar commitado e enviado ao GitHub antes de clonar.

Tudo isso está documentado no README principal, seção "Como acessar e subir a aplicação": os dois caminhos, comandos para Linux e PowerShell, variáveis de ambiente, problemas comuns e um roteiro de demonstração. Também atualizei a parte de validação para incluir os testes do agente.
