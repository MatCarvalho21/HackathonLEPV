"""Cliente do modelo (Featherless, API compatível com OpenAI)."""
from typing import Any, Protocol

from src.agente_perfil import config


class ClienteLLM(Protocol):
    def completar(self, mensagens: list[dict], ferramentas: list[dict]) -> dict:
        """Recebe o histórico e devolve a mensagem do assistente como dict
        ({"role": "assistant", "content": ..., "tool_calls": [...]}) mais "uso"."""


class ClienteFeatherless:
    def __init__(self, modelo: str = config.MODELO):
        from openai import OpenAI

        if not config.API_KEY:
            raise RuntimeError("Defina API_KEY (ou FEATHERLESS_API_KEY) no .env da raiz.")
        self.modelo = modelo
        self.cliente = OpenAI(base_url=config.BASE_URL, api_key=config.API_KEY,
                              timeout=config.TIMEOUT_S, max_retries=2)

    def completar(self, mensagens: list[dict], ferramentas: list[dict]) -> dict:
        kwargs: dict[str, Any] = dict(model=self.modelo, messages=mensagens,
                                      max_tokens=config.MAX_TOKENS, temperature=config.TEMPERATURA)
        if ferramentas:
            kwargs.update(tools=ferramentas, tool_choice="auto")
        resp = self.cliente.chat.completions.create(**kwargs)
        msg = resp.choices[0].message
        saida: dict[str, Any] = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            saida["tool_calls"] = [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments or "{}"}}
                for tc in msg.tool_calls
            ]
        saida["uso"] = {
            "prompt_tokens": getattr(resp.usage, "prompt_tokens", None),
            "completion_tokens": getattr(resp.usage, "completion_tokens", None),
            "finish_reason": resp.choices[0].finish_reason,
        }
        return saida
