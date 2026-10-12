from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BackendSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Employee AI Copilot"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:8b"
    max_tool_iterations: int = Field(default=10, ge=1, le=50)
    chat_memory_path: str = ".data/chat_memory.db"
    chat_max_context_messages: int = Field(default=100, ge=10, le=1000)
    chat_max_conversations: int = Field(default=500, ge=1, le=10000)
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    cors_origin_regex: str = r"^https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+):3000$"


def load_settings() -> BackendSettings:
    return BackendSettings()
