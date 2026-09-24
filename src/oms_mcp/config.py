from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    oms_email: str = Field(min_length=1)
    oms_password: str = Field(min_length=1)
    oms_tenant: str = Field(min_length=1)
    oms_auth_base_url: str = Field(min_length=1)
    oms_employee_base_url: str = Field(min_length=1)
    oms_refresh_path: str
    ollama_base_url: str = Field(min_length=1)
    ollama_model: str = Field(min_length=1)
    max_tool_iterations: int = Field(ge=1, le=50)

    def require_credentials(self) -> None:
        if not self.oms_email or not self.oms_password:
            raise ValueError("Set OMS_EMAIL and OMS_PASSWORD in .env")


def load_settings() -> Settings:
    """Report configuration field names without exposing secret values."""
    try:
        return Settings()
    except ValidationError as exc:
        fields = ", ".join(sorted({str(error["loc"][0]).upper() for error in exc.errors()}))
        raise ValueError(f"Check required .env settings: {fields}") from None
