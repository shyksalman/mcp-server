from fastapi import Request

from assistant.mcp_client import MultiMCPClient
from backend.agent.memory import ConversationMemory
from backend.config import BackendSettings


def settings(request: Request) -> BackendSettings:
    return request.app.state.settings


def mcp(request: Request) -> MultiMCPClient:
    return request.app.state.mcp


def chat(request: Request) -> ConversationMemory:
    return request.app.state.chat
