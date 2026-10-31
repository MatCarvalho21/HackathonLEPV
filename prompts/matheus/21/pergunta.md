Agora que eu processei os documentos e salvei no banco de dados vetorial, vamos pensar na primeira parte agentica. O pai entrou no sistema, vai preencher um formulário sobre a criança (esse formulário os meus colegas já implementaram e tudo mais). Um agente de IA vai receber o resultado desse formulário e com base no que ele tem de contexto sobre lá os 14 domínios gerar uma classificação/avaliação da criança + metas de curto/médio/longo prazo + onde focar + dicas e tal. Um report completo para o pai (um mapeamento de perfil). É em cima desse agente que eu quero trabalhar. 

Eu entendo que ele vai receber um prompt fixo explicando como interpretar os dados do formulário, como deve ser o relatório e tudo mais. Ele vai receber a saída do formulário estruturada ali no formato de JSON. Se considerar necessário, ele pode consultar a base de conhecimento usando uma skill de RAG e tal e até mesmo solicitar novas perguntas para o pai (ele pode pedir que o pai responde novas perguntas) no meio do loop agêntico se ele considerar que foi insuficiente. 

Para esse agente, vamos usar: 

curl -N -X POST 'https://api.featherless.ai/v1/chat/completions' \
  -H 'Authorization: Bearer your-featherless-api-key' \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "deepseek-ai/DeepSeek-V4.1-Flash-1017",
    "max_tokens": 4096,
    "messages": [
      { "role": "system", "content": "You are a helpful assistant." },
      { "role": "user", "content": "What is the fastest way to get to the airport?" }
    ]
  }'

Tenho aqui no repo um .env com a chave de API que vamos usar para chamar o agente. 

Estou participando de um hackathon e toda interação com IA é monitorada como você pode ver na pasta prompts. Então para toda mensagem que eu enviar, quero que você salve lá a pergunta e a resposta em uma pasta numerada. 

Sobre o banco de dados, onde vamos salvar grande parte do que formos produzindo, temos um .sql ali na pasta de prompts mapeando as tabelas também e tal. 

Após o responsável aprovar o perfil gerado pelo agente, ele vai de fato entrar na plataforma, com uma página dedicada, personalizada e tal.

---
(mensagem enviada durante a execução)

from openai import OpenAI

client = OpenAI(
    base_url="https://api.featherless.ai/v1",
    api_key="your-featherless-api-key",
)

response = client.chat.completions.create(
    model="deepseek-ai/DeepSeek-V4.1-Flash-1017",
    max_tokens=4096,
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the fastest way to get to the airport?"},
    ],
)

print(response.choices[0].message.content)
