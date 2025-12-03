import os
from pydantic import BaseModel


class Settings(BaseModel):
    app_env: str = os.getenv("APP_ENV", "development")
    app_port: int = int(os.getenv("APP_PORT", 8000))

    db_user: str = os.getenv("DB_USER", "postgres")
    db_password: str = os.getenv("DB_PASSWORD", "postgres")
    db_host: str = os.getenv("DB_HOST", "db")
    db_port: int = int(os.getenv("DB_PORT", "5432"))
    db_name: str = os.getenv("DB_NAME", "aibench")

    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY")
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")
    grok_api_key: str | None = os.getenv("GROK_API_KEY")

    class Config:
        arbitrary_types_allowed = True


def get_settings() -> Settings:
    return Settings()
