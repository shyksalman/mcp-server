from assistant.mcp_client import MultiMCPClient
from assistant.ollama_client import OllamaClient
from backend.agent.memory import ConversationMemory
from backend.config import BackendSettings


def build_chat(settings: BackendSettings, mcp: MultiMCPClient) -> ConversationMemory:
    return ConversationMemory(
        OllamaClient(settings.ollama_base_url, settings.ollama_model),
        mcp,
        database_path=settings.chat_memory_path,
        max_iterations=settings.max_tool_iterations,
        max_context_messages=settings.chat_max_context_messages,
        max_conversations=settings.chat_max_conversations,
    )
