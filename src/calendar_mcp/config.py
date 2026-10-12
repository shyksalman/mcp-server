from pydantic_settings import BaseSettings, SettingsConfigDict


class CalendarSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    calendar_provider: str = "local"
    calendar_timezone: str = "Asia/Karachi"
    calendar_client_id: str | None = None
    calendar_client_secret: str | None = None


def load_settings() -> CalendarSettings:
    return CalendarSettings()
