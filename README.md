# API para Assistente para sistema de atendimento:

## Como rodar

```
poetry shell
export GEMINI_API_KEY=<insira chave aqui>
flask --app assistente_copel run
```

## Métodos

`/new_session` (POST)

entradas (via form data):

`id_cliente`: string

saída:

token da sessão (string simples)

---

`/send_message` (POST)

entradas (via form data):

`token`: string

`mensagem`: multiline string

saída:

resposta do bot (em json) (ver formato de resposta)
