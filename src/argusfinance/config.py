from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ARGUS_", env_file=".env")

    state_dir: Path = Path("data")
    database_url: str = "sqlite:///db/workspace.sqlite"
    api_host: str = "127.0.0.1"
    api_port: int = 8765


@lru_cache
def get_settings() -> Settings:
    return Settings()
