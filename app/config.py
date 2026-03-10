from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "dev"
    log_level: str = "INFO"

    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "qwen2.5:7b"

    openclaw_data_dir: str = "/data"
    openclaw_db_path: str = "/data/db/openclaw.sqlite3"

    web_host: str = "0.0.0.0"
    web_port: int = 8000
    web_base_url: str = "http://localhost:8000"
    web_support_email: str = "support@openclaw.local"

    ebay_client_id: str = Field(
        default="",
        validation_alias=AliasChoices("EBAY_CLIENT_ID", "EBAY_APP_ID"),
    )
    ebay_client_secret: str = Field(
        default="",
        validation_alias=AliasChoices("EBAY_CLIENT_SECRET", "EBAY_CERT_ID"),
    )
    ebay_dev_id: str = ""
    ebay_env: str = "production"
    ebay_marketplace_id: str = "EBAY_GB"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def ebay_app_id(self) -> str:
        return self.ebay_client_id

    @property
    def ebay_cert_id(self) -> str:
        return self.ebay_client_secret


settings = Settings()
