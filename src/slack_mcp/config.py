from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SlackSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    slack_bot_token: str | None = None
    slack_app_token: str | None = None
    slack_team_id: str | None = None
    slack_user_token: str | None = None
    slack_base_url: str = "https://slack.com/api"
    slack_max_bulk_recipients: int = Field(default=20, ge=1, le=100)


def load_settings() -> SlackSettings:
    return SlackSettings()
