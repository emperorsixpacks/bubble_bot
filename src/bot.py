import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from handlers import token_router
from service_types import TokenSelection
from settings import TelegramSettings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
telegram_settings = TelegramSettings()

dp = Dispatcher()


@dp.message(Command("start"))
async def start_handler(message: Message) -> None:
    await message.answer("🚀 Welcome to the Bubble Bot!\n\n")


@dp.message(Command("help"))
async def help_handler(message: Message) -> None:
    await start_handler(message)


async def main() -> None:
    bot = Bot(token=telegram_settings.telegram_bot_token)
    dp.include_router(token_router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
