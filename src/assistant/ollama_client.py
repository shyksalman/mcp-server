from typing import Any

import httpx
from ollama import AsyncClient, ResponseError


class OllamaClient:
    def __init__(self, base_url: str, model: str):
        self.model = model
        self.client = AsyncClient(host=base_url)

    async def chat(self, messages: list[Any], tools: list[dict[str, Any]]) -> Any:
        try:
            return await self.client.chat(model=self.model, messages=messages, tools=tools)
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise RuntimeError("Ollama is unavailable. Start it with `ollama serve` and check OLLAMA_BASE_URL.") from exc
        except ResponseError as exc:
            raise RuntimeError(f"Ollama request failed (HTTP {exc.status_code}). Check OLLAMA_MODEL and run `ollama pull {self.model}`.") from exc
