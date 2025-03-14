"""Configuration settings for the Plato client."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="PLATO_", extra="ignore")
    base_url: str = Field(
        default="https://plato.so/api",
        description="Base URL for the Plato API",
        validation_alias="PLATO_BASE_URL",
    )
    api_key: str = Field(
        default="",
        description="API key for the Plato API",
        validation_alias="PLATO_API_KEY",
    )

@lru_cache
def get_config() -> Config:
    return Config()
