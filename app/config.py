from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "dev"
    log_level: str = "INFO"

    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "qwen2.5:7b"

    openclaw_data_dir: str = "/data"
    openclaw_db_path: str = "/data/db/openclaw.sqlite3"

    ebay_app_id: str = ""
    ebay_dev_id: str = ""
    ebay_cert_id: str = ""
    ebay_env: str = "production"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()
