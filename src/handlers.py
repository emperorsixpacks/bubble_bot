import re
from warnings import resetwarnings

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, InputFile, Message)
from httpx import delete

from ibm_storage import IBMStorage
from logger import get_logger
from service_types import Chain, Error, TokenSelection, error
from services import run, search_token, top_traders_page_url
from settings import CoinGeckoAPISettings, IBMSettings
from utils import (generate_token_description_text, get_chain_full_name,
                   to_chain)

temp_token_data = {}
ibm_settings = IBMSettings()
coin_gecko_settings = CoinGeckoAPISettings()
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


@token_router.message(Command("bm"))
async def bm_command_handler(message: Message):
    contract_address_chain_pattern = (
        r"^(0x[a-fA-F0-9]{40}|[1-9A-HJ-NP-Za-km-z]{32,44})/([a-zA-Z]+)$"
    )

    user_q = message.text.split(" ")
    if len(user_q) != 2:
        await message.reply(
            """
            Please send contract address in format: contract_address/chain\nExample: 0x123...abc/eth, $usdt/eth
            """
        )
        return
    _, token = user_q
    match = re.match(contract_address_chain_pattern, token.strip())
    if match is None:
        await message.reply(
            """
            Please send contract address in format: contract_address/chain\nExample: 0x123...abc/eth
            """
        )
        return

    contract_address, chain = match.groups()
    chain, err = to_chain(chain)
    if err:
        await message.reply(
            f"""
            {chain} is not a valid chain, chain must be {[chain.value for chain in Chain]}
            """
        )
        return
    response_message = await message.reply(
        f"Getting info for {contract_address} on {chain.upper()}"
    )
    visualization_url = await top_traders_page_url(
        ibm_storage=ibm_storage, chain=chain, contract_address=contract_address
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Open Interactive Visualization", url=visualization_url
                )
            ]
        ]
    )
    await response_message.delete()
    await message.reply(
        "Here's your token network visualization:", reply_markup=keyboard
    )


@token_router.message(Command("bi"))
async def bi_command_handler(message: Message):
    contract_address_chain_pattern = (
        r"^(0x[a-fA-F0-9]{40}|[1-9A-HJ-NP-Za-km-z]{32,44})/([a-zA-Z]+)$"
    )
    token_chain_pattern = r"^\$([a-zA-Z0-9]+)/([a-zA-Z]+)$"

    user_q = message.text.split(" ")
    if len(user_q) != 2:
        await message.reply(
            """
            Please send contract address in format: contract_address/chain\nExample: 0x123...abc/eth, $usdt/eth
            """
        )
        return
    _, token = user_q

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


async def handle_token_name(message: Message, token, chain):
    response_message = await message.reply(
        f"Getting info for {token} on {chain.upper()}"
    )
    chain_full_name, _ = get_chain_full_name(chain)
    # Fetch token options from API
    token_options, err = await search_token(
        coin_gecko_settings.coin_gecko_api_key, symbol=token, chain=chain_full_name
    )
    if len(token_options) == 0 or err:
        logger.error("Handler error %s", err.message)
        await response_message.edit_text(
            f"❌ No tokens found for ${token} on {chain.upper()} chain"
        )
        return

    if len(token_options) == 1:
        await process_and_reply(message, token_options[0].contract_address, chain)
        await response_message.delete()
        return
    # Multiple options - present selection
    keyboard = InlineKeyboardMarkup()
    for idx, tkn in enumerate(token_options):
        keyboard.add(
            InlineKeyboardButton(
                text=f"{tkn.name} ({tkn.contract_address[:6]}...{tkn.contract_address[-4:]})",
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
        f"🔍 Multiple tokens found for ${token} on {chain.upper()} chain:",
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


# TODO add a disclaimer for the $token/chain handler
