from pathlib import Path
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    host: str = "0.0.0.0"
    port: int = 8094
    # --- secrets & endpoints you actually need --------------------
    postgres_password: SecretStr
    postgres_url: str = "localhost"
    langfuse_secret_key: SecretStr
    langfuse_public_key: SecretStr
    langfuse_host: str

    # --- convenience ---------------------------------------------
    @property
    def postgres_dsn(self) -> str:
        return f"postgresql://postgres:{self.postgres_password.get_secret_value()}@{self.postgres_url}:5432/langgraph"


settings = Settings()
