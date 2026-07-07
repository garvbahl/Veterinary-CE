from pydantic_settings import BaseSettings, SettingsConfigDict

from pydantic import field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str
    log_level: str = "INFO"
    user_agent: str = "VetCEBot/0.1"
    scheduler_mode: str = "prod"  # "prod" or "dev"
    admin_password: str = "garvii"  # set via ADMIN_PASSWORD env var
    environment: str = "dev"  # "dev" or "production"
    frontend_url: str = ""  # set in production
    anthropic_api_key: str = ""

    @field_validator("database_url")
    @classmethod
    def _normalize_db_url(cls, v: str) -> str:
        """Managed Postgres hosts (Render, Heroku, Railway) hand out URLs with
        a bare `postgres://` or `postgresql://` scheme. SQLAlchemy + psycopg v3
        needs the explicit `postgresql+psycopg://` driver prefix, so normalize."""
        if v.startswith("postgres://"):
            v = "postgresql://" + v[len("postgres://"):]
        if v.startswith("postgresql://"):
            v = "postgresql+psycopg://" + v[len("postgresql://"):]
        return v

settings = Settings()