from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="PLATO_")
    base_url: str = Field(
        default="https://api.plato.so",
        description="Base URL for the Plato API",
        validation_alias="PLATO_BASE_URL    ",
    )
    api_key: str = Field(
        default="",
        description="API key for the Plato API",
        validation_alias="PLATO_API_KEY",
    )


config = Config()