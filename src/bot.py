import asyncio

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from services import (
    get_bubble_map_screenshot,
    get_decentralization_score,
    get_token_bubble_map,
    get_token_data,
    save_html_as_screenshot,
)
from settings import TelegramSettings

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
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
