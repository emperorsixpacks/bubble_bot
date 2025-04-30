import os

from pydantic_settings import BaseSettings, SettingsConfigDict

from utils import return_base_dir

env_dir = os.path.join(return_base_dir(), ".env")


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=env_dir, env_file_encoding="utf-8", extra="ignore"
    )


class TelegramSettings(AppSettings):
    telegram_bot_token: str


class CoinGeckoAPISettings(AppSettings):
    coin_gecko_api_key: str


class IBMSettings(AppSettings):
    ibm_service_endpoint: str
    ibm_bucket_name: str
    ibm_bucket_instance_id: str
    ibm_api_key: str
