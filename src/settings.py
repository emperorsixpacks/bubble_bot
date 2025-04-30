import os

from dotenv import load_dotenv

from utils import return_base_dir

# Load the .env file manually
# env_path = os.path.join(return_base_dir(), ".env")
# load_dotenv(env_path)


class TelegramSettings:
    def __init__(self):
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")


class CoinGeckoAPISettings:
    def __init__(self):
        self.coin_gecko_api_key = os.getenv("COIN_GECKO_API_KEY")


class IBMSettings:
    def __init__(self):
        self.ibm_service_endpoint = os.getenv("IBM_SERVICE_ENDPOINT")
        self.ibm_bucket_name = os.getenv("IBM_BUCKET_NAME")
        self.ibm_bucket_instance_id = os.getenv("IBM_BUCKET_INSTANCE_ID")
        self.ibm_api_key = os.getenv("IBM_API_KEY")
