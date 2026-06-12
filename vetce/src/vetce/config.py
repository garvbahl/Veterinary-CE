from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    log_level: str = "INFO"
    user_agent: str = "VetCEBot/0.1"
    scheduler_mode: str = "prod"  # "prod" or "dev"
    admin_password: str = "changeme"  # set via ADMIN_PASSWORD env var


settings = Settings()