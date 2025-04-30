import re
from warnings import resetwarnings

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputFile,
    Message,
)

from ibm_storage import IBMStorage
from logger import get_logger
from service_types import Chain, Error, TokenSelection, error
from services import run
from settings import IBMSettings
from utils import generate_token_description_text, to_chain

temp_token_data = {}
ibm_settings = IBMSettings()
ibm_storage = IBMStorage(ibm_settings)
token_router = Router(name=__name__)
logger = get_logger()


async def process_and_reply(
    message: Message, contract_address: str, chain: str
) -> error:
    """Helper function to process and send reply"""
    try:
        response = await run(
            contract_address=contract_address, chain=chain, ibm_storage=ibm_storage
        )
        response_text = generate_token_description_text(
            response.token_data, response.token_metrics
        )

        # photo, err = await image_from_url(response.screenshot_url)
        # if err:
        #   logger.error(err.message)
        #  return err
        send_photo_message = await message.reply_photo(
            photo=response.screenshot_url, caption=f"{contract_address}/{chain}"
        )
        await send_photo_message.reply(
            text=response_text,
            parse_mode="Markdown",
        )
        return
    except Exception as e:
        return Error(str(e))


@token_router.message(Command("bi"))
async def bm_command_handler(message: Message):
    contract_address_chain_pattern = (
        r"^(0x[a-fA-F0-9]{40}|[1-9A-HJ-NP-Za-km-z]{32,44})/([a-zA-Z]+)$"
    )
    token_chain_pattern = r"^\$([a-zA-Z0-9]+)/([a-zA-Z]+)$"

    _, token = message.text.split(" ")

    if match := re.match(token_chain_pattern, token.strip()):
        token, chain = match.groups()
        chain, err = to_chain(chain)
        if err:
            await message.reply(
                f"""
                {chain} is not a valid chain, chain must be {[chain.value for chain in Chain]}
                """
            )
            return

        err = await handle_token_name(message, token, chain)
    elif match := re.match(contract_address_chain_pattern, token.strip()):
        token, chain = match.groups()
        chain, err = to_chain(chain)
        if err:
            await message.reply(
                f"""
                {chain} is not a valid chain, chain must be {[chain.value for chain in Chain]}
                """
            )
            return

        err = await handle_contract_address(message, token, chain)

    else:
        await message.reply(
            """
            Please send contract address in format: contract_address/chain\nExample: 0x123...abc/eth, $usdt/eth
            """
        )
        return

    if err:
        logger.error(err.message)
        await message.reply(f"oops!! something went wrong {token}/{chain}")
        return
    return


async def handle_contract_address(message: Message, contract_address, chain) -> error:
    response_message = await message.reply(
        f"Getting info for {contract_address} on {chain.upper()}"
    )
    err = await process_and_reply(message, contract_address, chain)
    await response_message.delete()
    return err


async def handle_token_name(message: Message, state: FSMContext, token, chain):
    # Check if message matches $token_symbol/chain pattern

    # Fetch token options from API
    token_options = await fetch_token_options(symbol, chain)

    if not token_options:
        await message.reply(
            f"❌ No tokens found for ${token} on {chain.upper()} chain"
        )
        return

    if len(token_options) == 1:
        # Only one option - process immediately
        contract_address = token_options[0]["address"]
        await process_and_reply(message, contract_address, chain)
    else:
        # Multiple options - present selection
        keyboard = InlineKeyboardMarkup()
        for idx, token in enumerate(token_options):
            keyboard.add(
                InlineKeyboardButton(
                    text=f"{token['name']} ({token['address'][:6]}...{token['address'][-4:]})",
                    callback_data=f"select_token:{idx}",
                )
            )

        # Store options in temporary storage
        temp_token_data[message.from_user.id] = {
            "options": token_options,
            "chain": chain,
            "original_message_id": message.message_id,
        }

        await message.reply(
            f"🔍 Multiple tokens found for ${symbol} on {chain.upper()} chain:",
            reply_markup=keyboard,
        )
        await TokenSelection.waiting_for_selection.set()


async def handle_token_selection(callback_query: CallbackQuery, state: FSMContext):
    """Handle user's token selection from inline keyboard"""
    user_id = callback_query.from_user.id
    if user_id not in temp_token_data:
        await callback_query.answer("Session expired. Please try again.")
        return

    # Get selected token
    selected_idx = int(callback_query.data.split(":")[1])
    token_data = temp_token_data[user_id]
    selected_token = token_data["options"][selected_idx]

    # Delete the original message with token options
    try:
        await callback_query.bot.delete_message(
            chat_id=callback_query.message.chat.id,
            message_id=token_data["original_message_id"],
        )
        await callback_query.bot.delete_message(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
        )
    except:
        pass  # Don't fail if message can't be deleted

    # Process the selected token
    await process_and_reply(
        callback_query.message, selected_token["address"], token_data["chain"]
    )

    # Clean up
    del temp_token_data[user_id]
    await state.finish()
