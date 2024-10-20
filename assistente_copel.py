import os
import google.generativeai as genai
from google.ai.generativelanguage_v1beta.types import content
from flask import Flask, request
import random, string
from dataclasses import dataclass
from typing import Literal
import json

app = Flask(__name__)

genai.configure(api_key=os.environ["GEMINI_API_KEY"])


@dataclass
class InfoCliente:
    nome: str
    endereco: str
    status_pagamento: Literal["em dia", "pendente", "atrasado"]
    status_ligacao: Literal["operando", "cortado"]

    def __str__(self) -> str:
        return json.dumps(
            {
                "nome": self.nome,
                "endereço": self.endereco,
                "status_pagamento": self.status_pagamento,
                "status_ligação": self.status_ligacao,
            }
        )


def random_token() -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=16))


# Create the model
generation_config: genai.types.GenerationConfigDict = {
    "temperature": 1,
    # "top_p": 0.95,
    # "top_k": 64,
    "max_output_tokens": 8192,
    "response_schema": content.Schema(
        type=content.Type.OBJECT,
        # enum="[]",
        required=["pensamento", "movimento1", "resposta", "linksSugeridos"],
        properties={
            "pensamento": content.Schema(
                type=content.Type.STRING,
            ),
            "movimento1": content.Schema(
                type=content.Type.STRING,
            ),
            "movimento2": content.Schema(
                type=content.Type.STRING,
            ),
            "movimento3": content.Schema(
                type=content.Type.STRING,
            ),
            "movimento4": content.Schema(
                type=content.Type.STRING,
            ),
            "resposta": content.Schema(
                type=content.Type.STRING,
            ),
            "linksSugeridos": content.Schema(
                type=content.Type.ARRAY,
                items=content.Schema(
                    type=content.Type.STRING,
                ),
            ),
        },
    ),
    "response_mime_type": "application/json",
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    # model_name="gemini-1.5-pro",
    generation_config=generation_config,
    # safety_settings = Adjust safety settings
    # See https://ai.google.dev/gemini-api/docs/safety-settings
    system_instruction='Você é um sistema de suporte da Copel (assistente virtual da Copel), uma empresa fornecedora de energia elétrica. Você só pode ajudar com coisas mencionadas no MENUAJUDA. Não tente ajudar com nada que não esteja listado no MENUAJUDA, nunquinha.\nSua meta é encaminhar o cliente ao link de suporte mais relevante depois de entender com o quê ele precisa de ajuda.\nEm caso de dúvidas sobre qual link recomendar, peça mais detalhes ao cliente.\n\nformato MENUAJUDA: Descrição (códigoAjuda)\nMENUAJUDA:\nPagar conta (pgConta)\nPagar conta atrasada (pgConta2)\nConfigurar débito automático (pgContaAuto)\nNova ligação (nvLig)\nDesligamento (rmLig)\nAlterar data de vencimento (mudVenc)\n\nEm cada turno, realize um ou mais movimentos entre os listados:\nchecarMenu: Verificar se o que foi pedido corresponde com algo no MENUAJUDA\nsugerirLink: Sugerir um tópico de ajuda listado no MENUAJUDA\ncumprimentar: Se o cliente enviar um cumprimento como "oi", "qual a boa?", "como vai você?", responda naturalmente e então pergunte o como você pode ajudá-lo.\nclarificar: Caso o link de ajuda não seja óbvio ou múltiplos se aplicarem, \nredirecionar: Se a pergunta ou problema do cliente não faz sentido no contexto ou falarem de qualquer coisa que não esteja no MENUAJUDA, não converse sobre o tópico.\n\nResponda no seguinte formato:\n```json\n{\n "pensamento": "iniciando com um sumário do que já foi realizado, uma string descrevendo como o assistente decide seu próximo movimento dado o que foi realizado nos turnos anteriores.",\n "movimento1": "uma string com um dos seguintes valores: checarMenu|sugerirLink|cumprimentar|clarificar|redirecionar",\n "movimento2": "uma string com um dos seguintes valores: checarMenu|sugerirLink|cumprimentar|clarificar|redirecionar",\n "movimento3": "uma string com um dos seguintes valores: checarMenu|sugerirLink|cumprimentar|clarificar|redirecionar",\n "resposta": "uma string com a resposta dada do assistente ao cliente",\n "linksSugeridos": ["códigoAjuda"]\n}\n```\n\nExemplos\n==\nCliente: preciso de ajuda\n```json\n{\n "pensamento":  "O cliente não deixou claro com o quê ele precisa de ajuda, vou pedir clarificação.",\n "movimento1": "clarificar",\n "resposta": "Oi! Sou o assistente virtual da Copel 😊\\nCom o quê você precisa de ajuda?",\n  "linksSugeridos": []\n}\n```\n==\nCliente: quero pagar uma conta\n```json\n{\n "pensamento":  "Um problema foi especificado, vou checarMenu procurando itens relevantes, e pedir clarificação caso eu não encontre um item que se aplique.",\n "movimento1": "checarMenu",\n "resposta": "Para pagar uma conta, você pode utilizar um dos links de ajuda a seguir 😊",\n  "linksSugeridos": ["pgConta", "pgConta2"]\n}\n```\n==\nCliente: me dê uma receita\n```json\n{\n "pensamento":  "Como sou o assistente da Copel, não devo conversar sobre coisas que não estejam no MENUAJUDA. Receitas não estão no MENUAJUDA. Vou redirecionar a conversa a um tópico relevante.",\n "movimento1": "checarMenu",\n "movimento2": "redirecionar",\n "resposta": "Infelizmente, como o assistente virtual da Copel, não posso te dar uma receita. Você precisa de ajuda com nossos serviços?",\n  "linksSugeridos": []\n}\n```',
)

chat_session = model.start_chat(
    history=[
        {
            "role": "model",
            "parts": [
                '{\n "pensamento": "Para iniciar a conversa, vou cumprimentar o cliente.",\n "movimento1": "cumprimentar",\n "resposta": "Oi, sou o assistente virtual da Copel, como posso te ajudar? 😊",\n "linksSugeridos": []\n}',
            ],
        },
    ]
)

clientes: dict[str, InfoCliente] = {
    "123456": InfoCliente(
        "Geraldo Silva",
        "Rua das Oliveiras, 94, Jardim Roldini, Pato Loiro - PR",
        "atrasado",
        "operando",
    )
}

chats: dict[str, tuple[genai.ChatSession, str]] = {}


@app.route("/new_session", methods=["GET"])
def new_session():
    id_cliente = request.form["id_cliente"]
    if id_cliente not in clientes.keys():
        raise KeyError
    token = random_token()
    chat_session = model.start_chat(
        history=[
            {
                "role": "model",
                "parts": [
                    '{\n "pensamento": "Para iniciar a conversa, vou cumprimentar o cliente.",\n "movimento1": "cumprimentar",\n "resposta": "Oi, sou o assistente virtual da Copel, como posso te ajudar? 😊",\n "linksSugeridos": []\n}',
                ],
            },
        ]
    )
    chats[token] = (chat_session, id_cliente)
    return token


@app.route("/send_message", methods=["POST"])
def send_message():
    token = request.form["token"]
    message = request.form["message"]
    chat_session, id_cliente = chats[token]

    response = chat_session.send_message(
        content=f"message\n{str(clientes[id_cliente])}"
    )
    return response.text
