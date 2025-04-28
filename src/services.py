from __future__ import annotations

import asyncio
from urllib.parse import urlencode

from playwright.async_api import async_playwright

from logger import get_logger
from service_types import (
    TelegramCommand,
    TokenCoinData,
    TokenCommunityData,
    TokenMetrics,
)
from utils import reduce_image_size, render_html_template, return_base_dir, send_request

# Set up logging
logger = get_logger()


BUBBLE_MAPS_API_URL = "https://api-legacy.bubblemaps.io"
ELEMENTS_TO_REMOVE = [
    ".mdc-top-app-bar",
    "div.buttons-row:nth-child(6)",
    ".buttons-row",
    ".wallets-table > h3:nth-child(1)",
]
TOKEN_TEMPLATE_PATH = "../static/token.html"
BUBBLE_MAP_TEMPLATE = "../static/bubble_map.html"


async def bubble_map(path: str, *, contract_address: str, chain: str) -> dict[str, any]:
    logger.info(f"Requesting bubble map data for {path}: {chain}/{contract_address}")
    qparams = {
        "chain": chain,
        "token": contract_address,
    }
    query_string = urlencode(qparams)

    url = f"{BUBBLE_MAPS_API_URL}/{path}?{query_string}"
    logger.debug(f"Built URL: {url}")

    try:
        response = await send_request(url)
        data = response.json()
        if data.get("message") == "Data not available for this token":
            logger.warning(f"No data available for token {contract_address} on {chain}")
            return None
        logger.debug(f"Received bubble map data from {path}: {len(str(data))} bytes")
        return data
    except Exception as e:
        logger.error(f"Error getting bubble map data for {path}: {str(e)}")
        raise


async def get_token_bubble_map(*, contract_address: str, chain: str):
    logger.info(f"Getting token bubble map: {chain}/{contract_address}")
    try:
        data = await bubble_map(
            "map-data", contract_address=contract_address, chain=chain
        )
        if data:
            logger.info(
                f"Successfully retrieved bubble map for {chain}/{contract_address}"
            )
        else:
            logger.warning(f"No bubble map available for {chain}/{contract_address}")
        return data
    except Exception as e:
        logger.error(f"Failed to get token bubble map: {str(e)}")
        raise


async def get_decentralization_score(
    *, contract_address: str, chain: str
) -> TokenMetrics:
    logger.info(f"Getting decentralization score for {chain}/{contract_address}")
    try:
        data = await bubble_map(
            "map-metadata", contract_address=contract_address, chain=chain
        )
        if data:
            logger.info(
                f"Retrieved decentralization metrics for {chain}/{contract_address}"
            )
            return TokenMetrics(**data)
        logger.warning(
            f"No decentralization metrics available for {chain}/{contract_address}"
        )
        return None
    except Exception as e:
        logger.error(f"Error getting decentralization score: {str(e)}")
        raise


async def get_token_data(*, contract_address: str, chain: str):
    logger.info(f"Getting token data from CoinGecko: {chain}/{contract_address}")
    url = f"https://api.coingecko.com/api/v3/coins/{chain}/contract/{contract_address}"
    logger.debug(f"CoinGecko URL: {url}")

    try:
        response = await send_request(url)
        if response.status_code != 200:
            logger.warning(f"Failed to get token data: HTTP {response.status_code}")
            return None

        data = response.json()
        logger.debug(f"Received token data: {len(str(data))} bytes")

        # Extract community data
        logger.debug("Extracting community data")
        community_data = TokenCommunityData(
            home_page_url=data.get("links", {}).get("homepage", [None])[0],
            white_paper=data.get("links", {}).get("whitepaper", None),
            twitter_handle=data.get("links", {}).get("twitter_screen_name", None),
            twitter_followers=data.get("community_data", {}).get(
                "twitter_followers", None
            ),
            token_image_url=data.get("image", {}).get("large", ""),
            telegram_channel=data.get("links", {}).get(
                "telegram_channel_identifier", None
            ),
            repo=(
                data.get("links", {}).get("repos_url", {}).get("github", [None])[0]
                if data.get("links", {}).get("repos_url", {}).get("github")
                else None
            ),
        )

        # Extract market data
        logger.debug("Extracting market data")
        market_data = data.get("market_data", {})

        token_data = TokenCoinData(
            symbol=data.get("symbol", "").upper(),
            name=data.get("name", ""),
            description=data.get("description", {}).get("en", ""),
            bubble_screenshot_url=None,  # Not available in the API response
            market_cap=int(market_data.get("market_cap", {}).get("usd", 0)),
            volume=int(market_data.get("total_volume", {}).get("usd", 0)),
            price=float(market_data.get("current_price", {}).get("usd", 0)),
            total_supply=data.get("market_data", {}).get("total_supply", None),
            circulating_supply=data.get("market_data", {}).get(
                "circulating_supply", None
            ),
            community_data=community_data,
        )

        logger.info(
            f"Successfully extracted token data for {token_data.name} ({token_data.symbol})"
        )
        return token_data

    except Exception as e:
        logger.error(f"Error getting token data: {str(e)}")
        raise


async def capture_screenshot(page, selector: str | None = None) -> bytes:
    """Capture a high-resolution 4K screenshot of the page or specific element."""
    try:
        # Try to capture screenshot of a specific element
        if selector and page.locator(str(selector)):
            screenshot_bytes = await page.locator(selector).screenshot(
                type="png",
                omit_background=True,  # Transparent background if needed
                scale="css",  # Use CSS pixels for consistent sizing
            )
            logger.info(f"Screenshot captured: {len(screenshot_bytes)} bytes")
            return screenshot_bytes
        else:
            # If element not found, capture full page screenshot
            screenshot_bytes = await page.screenshot(
                type="png",
                omit_background=True,  # Transparent background if needed
                scale="css",  # Use CSS pixels for consistent sizing
            )
            logger.info(
                f"Screenshot captured (full page): {len(screenshot_bytes)} bytes"
            )
            return screenshot_bytes
    except Exception as e:
        logger.error(f"Error during screenshot capture: {str(e)}")
        raise


async def get_page_screenshot(
    url, sleep: int | None = None, selector: str | None = None
) -> bytes:
    """Generate a high-resolution 4K screenshot of the bubble map and return as bytes"""
    logger.info("Generating bubble map screenshot for %s", url)

    try:
        async with async_playwright() as p:
            logger.debug("Launching Playwright browser")
            # Launch browser with higher default viewport for better quality
            browser = await p.chromium.launch(channel="chromium", headless=True)
            context = await browser.new_context(
                viewport={
                    "width": 1080,
                    "height": 1080,
                    "deviceScaleFactor": 2,  # Higher pixel density
                }
            )
            page = await context.new_page()

            try:
                # Navigate to the page
                logger.debug(f"Navigating to: {url}")
                await page.goto(
                    url,
                    timeout=60000,  # Longer timeout for high-res loading
                )

                # Wait for the page to load before proceeding (sleep)
                if sleep:
                    await asyncio.sleep(sleep)

                # Capture the screenshot of the page or element
                screenshot_bytes = await capture_screenshot(page, selector=selector)

                return screenshot_bytes

            except Exception as e:
                logger.error(f"Error during screenshot capture: {str(e)}")
                raise

            finally:
                # Ensure browser is closed even if errors occur
                logger.debug("Closing browser")
                await context.close()
                await browser.close()
    except Exception as e:
        logger.error(f"Playwright error: {str(e)}")
        raise


async def run(contract_address: str, chain: str, ibm_storage: IBMStorage):
    logger.info(f"Starting bubble map generation for {chain}/{contract_address}")
    try:
        token = {"contract_address": contract_address, "chain": chain}

        logger.info("Getting token data")
        token_data = await get_token_data(**token)
        if not token_data:
            logger.error("Failed to get token data, aborting")
            return None, None, None

        logger.info("Getting decentralization metrics")
        token_metrics = await get_decentralization_score(**token)
        if not token_metrics:
            logger.warning("Decentralization metrics not available")

        logger.info("Generating and uploading bubble map screenshot")
        token_chart = await get_token_bubble_map(
            contract_address=contract_address, chain=chain
        )
        html_data = render_html_template(BUBBLE_MAP_TEMPLATE, chart_data=token_chart)
        url, _ = ibm_storage.upload_bytes(
            html_data.encode(), f"{chain}-{contract_address}.html", "bubble-map-pages"
        )
        screenshot_bytes = await get_page_screenshot(url, sleep=15)
        screenshot_bytes_reduced = reduce_image_size(screenshot_bytes)
        screenshot_filename = f"{chain}-{contract_address}.png"
        logger.debug(f"Uploading screenshot as {screenshot_filename}")
        bubble_map_screenshot_url, err = ibm_storage.upload_bytes(
            screenshot_bytes_reduced,
            screenshot_filename,
            "bubble-map-image",
        )
        if err:
            logger.info(err.message)

        logger.info(f"Screenshot uploaded successfully: {bubble_map_screenshot_url}")

        token_data.bubble_screenshot_url = bubble_map_screenshot_url

        logger.info("Generating HTML page screenshot")
        token_html = render_html_template(
            "../static/token.html",
            token=token_data,
            metrics=token_metrics,
            root_dir=return_base_dir(),
        )
        page_url, _ = ibm_storage.upload_bytes(
            token_html.encode(),
            f"{chain}-{contract_address}.html",
            "bubble-map-screenshot",
        )
        # _ = save_html_as_screenshot(
        #   ibm_storage,
        #  data=token_data,
        # metrics=token_metrics,
        # html_parsed=token_html,
        # save_file_name=screenshot_filename,
        # )
        page_screenshot = await get_page_screenshot(page_url, selector=".token-card")
        screenshot_bytes_reduced = reduce_image_size(page_screenshot)
        screenshot_filename = f"{chain}-{contract_address}.png"
        logger.debug(f"Uploading screenshot as {screenshot_filename}")
        token_page_screenshot_url, err = ibm_storage.upload_bytes(
            screenshot_bytes_reduced,
            screenshot_filename,
            "bubble-map-screenshots",
        )
        if err:
            logger.info(err.message)
        logger.info(f"HTML page screenshot generated: {token_page_screenshot_url}")

        logger.info(
            f"Successfully completed bubble map processing for {chain}/{contract_address}"
        )
        return TelegramCommand(token_data, token_metrics, token_page_screenshot_url)

    except Exception as e:
        logger.error(f"Error during bubble map generation: {str(e)}")
        raise


if __name__ == "__main__":
    from ibm_storage import IBMStorage
    from settings import IBMSettings

    settings = IBMSettings()
    ibm_storage = IBMStorage(settings)
    token = {
        "contract_address": "F28UWka8PSyG1jUtVZ2CfFdF1dkLEA4rw7GkFBW7pump",
        "chain": "sol",
        "ibm_storage": ibm_storage,
    }

    # asyncio.run(run(**token))
