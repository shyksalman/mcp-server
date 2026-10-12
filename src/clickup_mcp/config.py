from pydantic_settings import BaseSettings, SettingsConfigDict


class ClickUpSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    clickup_api_token: str | None = None
    clickup_workspace_id: str | None = None
    clickup_user_id: str | None = None
    clickup_base_url: str = "https://api.clickup.com/api/v2"


def load_settings() -> ClickUpSettings:
    return ClickUpSettings()
