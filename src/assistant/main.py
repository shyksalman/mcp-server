import asyncio
import logging

from assistant.chat import ChatSession
from assistant.mcp_client import MultiMCPClient
from assistant.ollama_client import OllamaClient
from oms_mcp.config import load_settings


async def run() -> None:
    settings = load_settings()
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    async with MultiMCPClient() as mcp:
        chat = ChatSession(OllamaClient(settings.ollama_base_url, settings.ollama_model), mcp, settings.max_tool_iterations)
        print(f"Employee AI Copilot\nModel: {settings.ollama_model}\nType /tools, /clear, or /exit.")
        while True:
            try:
                message = await asyncio.to_thread(input, "\nYou: ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            command = message.strip().lower()
            if command in ("/exit", "/quit"):
                break
            if command == "/clear":
                chat.clear()
                print("Conversation cleared.")
                continue
            if command == "/tools":
                for tool in mcp.tools:
                    print(f"- {tool.name}: {tool.description or ''}")
                continue
            if not message.strip():
                continue
            try:
                print(f"Assistant: {await chat.ask(message)}")
            except RuntimeError as exc:
                print(f"Error: {exc}")


def main() -> None:
    try:
        asyncio.run(run())
    except (RuntimeError, ValueError) as exc:
        print(f"Error: {exc}")


if __name__ == "__main__":
    main()
