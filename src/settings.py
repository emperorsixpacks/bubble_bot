import os
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.utils import return_base_dir

env_dir = os.path.join(return_base_dir(), ".env")


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=env_dir, env_file_encoding="utf-8", extra="ignore"
    )


class TelegramSettings(AppSettings):
    telegram_bot_token: str
