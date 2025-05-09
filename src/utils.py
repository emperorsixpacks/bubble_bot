from __future__ import annotations

import asyncio
import io
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
import imgkit
from jinja2 import Environment, FileSystemLoader
from PIL import Image

from logger import get_logger
from service_types import CHAIN_MAPPING, Chain, Error, error

if TYPE_CHECKING:
    from ibm_storage import IBMStorage
    from service_types import TokenCoinData, TokenMetrics

# Set up logging
logger = get_logger()


def to_chain(value: str) -> tuple[Chain | None, error]:
    try:
        chain = Chain(value)
    except ValueError:
        return None, Error(f"{value} is not a valid chain")
    return chain, None


def get_chain_full_name(value) -> tuple[str | None, error]:
    chain_name = CHAIN_MAPPING.get(value, None)
    if chain_name is None:
        return None, Error(f"{value} not found")
    return chain_name, None


def return_base_dir():
    logger.debug("Getting base directory")
    base_dir = os.path.dirname(os.path.dirname(__file__))
    logger.debug(f"Base directory: {base_dir}")
    return base_dir


class AsyncRequestSession:
    def __init__(self, headers: dict = None):
        self.headers = headers or {}
        self.client = None

    async def __aenter__(self):
        self.client = httpx.AsyncClient(headers=self.headers)
        logger.info("[Session] Client created.")
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.client.aclose()
        logger.info("[Session] Client closed.")

    async def get(self, url: str):
        logger.info(f"[Session] Sending GET request to: {url}")
        try:
            response = await self.client.get(url)
            logger.debug(f"[Session] Response status: {response.status_code}")
            return response
        except Exception as e:
            logger.error(f"[Session] Error sending request to {url}: {str(e)}")
            raise


class CoinGeckoRateLimiter:
    """Strict 30 requests/minute rate limiter for CoinGecko API"""

    __instance = None

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
            cls.__instance.reset()
        return cls.__instance

    def reset(self):
        self.request_times = []
        self.limit = 30
        self.period = 60  # seconds
        self.last_burst = time.time()

    async def acquire(self):
        now = time.time()

        # Remove expired requests (older than 1 minute)
        self.request_times = [t for t in self.request_times if now - t < self.period]

        # If we've hit the limit, wait until the oldest request expires
        if len(self.request_times) >= self.limit:
            oldest = self.request_times[0]
            wait_time = self.period - (now - oldest)
            await asyncio.sleep(wait_time)
            now = time.time()  # Update time after waiting
            self.request_times = [
                t for t in self.request_times if now - t < self.period
            ]

        self.request_times.append(now)


# TODO close the connection
async def send_request(url: str):
    logger.info(f"Sending request to: {url}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            logger.debug(f"Received response with status code: {response.status_code}")
            return response
    except Exception as e:
        logger.error(f"Error sending request to {url}: {str(e)}")
        raise


async def image_from_url(url) -> tuple[io.BytesIO | None, error]:
    res = await send_request(url)
    if res.status_code != 200:
        return None, error(f"Request error: {res.json()}")
    content = res.content
    if not isinstance(content, bytes):
        return None, Error("This is not a url")
    return io.BytesIO(content), None


def render_html_template(template_path: str, **kwargs) -> str:
    logger.info(f"Rendering HTML template: {template_path}")
    # Verify template exists
    if not Path(template_path).exists():
        logger.error(f"Template file not found: {template_path}")
        raise FileNotFoundError(f"Template file not found: {template_path}")

    # Set up Jinja environment
    template_dir = str(Path(template_path).parent)
    template_file = Path(template_path).name
    logger.debug(f"Template directory: {template_dir}, file: {template_file}")

    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # Render template with context
    try:
        template = env.get_template(template_file)
        logger.debug(f"Template loaded successfully: {template_file}")
        rendered = template.render(**kwargs)
        logger.debug("Template rendered successfully")
        return rendered
    except Exception as e:
        logger.error(f"Error rendering template: {str(e)}")
        raise


def save_html_as_screenshot(
    ibm_storage: IBMStorage,
    /,
    save_file_name: str,
    html_parsed: str = None,
    **kwargs,
):
    try:
        options = {
            "format": "png",
            "encoding": "UTF-8",
            "enable-local-file-access": None,
        }
        logger.debug(f"Using imgkit options: {options}")

        img_bytes = imgkit.from_string(html_parsed, False, options=options)
        logger.debug(f"Generated image bytes: {len(img_bytes)} bytes")

        logger.info(f"Uploading screenshot as: {save_file_name}")
        result, err = ibm_storage.upload_bytes(img_bytes, save_file_name, "screenshots")
        if err:
            logger.error("Error generating or saving screenshot: %s", err.message)
            return

        logger.info("Screenshot uploaded successfully")
        return result
    except Exception as e:
        logger.error(f"Error generating or saving screenshot: {str(e)}")
        raise


def reduce_image_size(image_bytes, max_size=(1024, 1024), quality=85):
    logger.info("Size before compression %smb", len(image_bytes) * (1024**2))
    # Open image from bytes
    img = Image.open(io.BytesIO(image_bytes))

    # Convert to RGB if necessary (e.g., for PNG or RGBA images)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # Resize image while maintaining aspect ratio
    img.thumbnail(max_size, Image.Resampling.LANCZOS)

    # Save to bytes with compression
    output = io.BytesIO()
    img.save(output, format="JPEG", quality=quality, optimize=True)
    bytes_obj = output.getvalue()
    logger.info("Size after compression %smb", len(bytes_obj) * (1024**2))
    return bytes_obj


def generate_token_description_text(token: TokenCoinData, metrics: TokenMetrics) -> str:
    """Generates descriptive text from all available token data"""
    logger.info(
        f"Generating token description for: {token.name if hasattr(token, 'name') else 'unknown token'}"
    )

    sections = []

    # Basic Info Section
    logger.debug("Adding basic info section")
    basic_info = [f"📝 **Description:**\n{token.description}"]
    sections.append("\n".join(filter(None, basic_info)))

    # Community Links Section
    logger.debug("Adding community links section")
    community_links = []

    if token.community_data.home_page_url:
        logger.debug(f"Added homepage: {token.community_data.home_page_url}")
        community_links.append(f"🌐 [Website]({token.community_data.home_page_url})")

    if token.community_data.twitter_handle:
        handle = token.community_data.twitter_handle.lstrip("@")
        twitter_link = f"🐦 [Twitter](https://twitter.com/{handle})"

        if token.community_data.twitter_followers:
            twitter_link += f" ({token.community_data.twitter_followers:,} followers)"
            logger.debug(
                f"Added Twitter with {token.community_data.twitter_followers} followers"
            )
        else:
            logger.debug(f"Added Twitter without follower count")

        community_links.append(twitter_link)

    if token.community_data.telegram_channel:
        logger.debug(f"Added Telegram: {token.community_data.telegram_channel}")
        community_links.append(
            f"📢 [Telegram](https://t.me/{token.community_data.telegram_channel})"
        )

    if token.community_data.repo:
        logger.debug(f"Added repository: {token.community_data.repo}")
        community_links.append(f"💻 [GitHub]({token.community_data.repo})")

    if token.community_data.white_paper:
        logger.debug(f"Added whitepaper: {token.community_data.white_paper}")
        community_links.append(f"📄 [Whitepaper]({token.community_data.white_paper})")

    if community_links:
        sections.append("\n🔗 **Community Links:**\n" + " | ".join(community_links))

    result = "\n\n".join(filter(None, sections))
    logger.debug(f"Generated description text of length: {len(result)}")
    return result
