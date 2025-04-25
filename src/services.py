import asyncio
from urllib.parse import urlencode

from playwright.async_api import async_playwright

from service_types import TokenCoinData, TokenCommunityData, TokenMetrics
from utils import render_html_template, send_request

BUBBLE_MAPS_API_URL = "https://api-legacy.bubblemaps.io"
ELEMENTS_TO_REMOVE = [
    ".mdc-top-app-bar",
    "div.buttons-row:nth-child(6)",
    ".buttons-row",
]


async def bubble_map(path: str, *, contract_address: str, chain: str) -> dict[str, any]:
    qparams = {
        "chain": chain,
        "token": contract_address,
    }
    query_string = urlencode(qparams)

    url = f"{BUBBLE_MAPS_API_URL}/{path}?{query_string}"

    response = await send_request(url)
    data = response.json()
    if data.get("message") == "Data not available for this token":
        return None
    return data


async def get_token_bubble_map(*, contract_address: str, chain: str):
    data = await bubble_map("map-data", contract_address=contract_address, chain=chain)
    return data


async def get_decentralization_score(
    *, contract_address: str, chain: str
) -> TokenMetrics:
    data = await bubble_map(
        "map-metadata", contract_address=contract_address, chain=chain
    )
    return TokenMetrics(**data)


async def get_token_data(*, contract_address: str, chain: str):
    url = f"https://api.coingecko.com/api/v3/coins/{chain}/contract/{contract_address}"

    response = await send_request(url)
    if response.status_code != 200:
        return None

    data = response.json()

    # Extract community data
    community_data = TokenCommunityData(
        home_page_url=data.get("links", {}).get("homepage", [None])[0],
        white_paper=data.get("links", {}).get("whitepaper", None),
        twitter_handle=data.get("links", {}).get("twitter_screen_name", None),
        twitter_followers=data.get("community_data", {}).get("twitter_followers", None),
        token_image_url=data.get("image", {}).get("large", ""),
        telegram_channel=data.get("links", {}).get("telegram_channel_identifier", None),
        repo=(
            data.get("links", {}).get("repos_url", {}).get("github", [None])[0]
            if data.get("links", {}).get("repos_url", {}).get("github")
            else None
        ),
    )

    # Extract market data
    market_data = data.get("market_data", {})

    return TokenCoinData(
        symbol=data.get("symbol", "").upper(),
        name=data.get("name", ""),
        description=data.get("description", {}).get("en", ""),
        bubble_screenshot_url=None,  # Not available in the API response
        market_cap=int(market_data.get("market_cap", {}).get("usd", 0)),
        volume=int(market_data.get("total_volume", {}).get("usd", 0)),
        price=float(market_data.get("current_price", {}).get("usd", 0)),
        total_supply=data.get("market_data", {}).get("total_supply", None),
        circulating_supply=data.get("market_data", {}).get("circulating_supply", None),
        community_data=community_data,
    )


async def get_bubble_map_screenshot(chain: str, contract_address: str):
    screenshot_location = f"{chain}-{contract_address}.png"
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chromium", headless=True)
        page = await browser.new_page()
        await page.goto(
            f"https://app.bubblemaps.io/{chain}/token/{contract_address}?mode=0"
        )
        await asyncio.sleep(5)
        await page.evaluate(
            "document.querySelectorAll('{0}').forEach(el => el.remove());".format(
                ",".join(ELEMENTS_TO_REMOVE)
            )
        )
        await page.locator(".graph-view").screenshot(
            path=f"../screenshots/{screenshot_location}"
        )
        await browser.close()
    return screenshot_location


token = {
    "contract_address": "F28UWka8PSyG1jUtVZ2CfFdF1dkLEA4rw7GkFBW7pump",
    "chain": "sol",
}


async def main():
    metrics = await get_decentralization_score(**token)
    token_data = await get_token_data(**token)
    print(
        render_html_template(
            "../static/token.html",
            token=token_data.model_dump(),
            metrics=metrics.model_dump(),
        )
    )


asyncio.run(main())
