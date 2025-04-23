import asyncio
from urllib.parse import urlencode, urlunparse

import httpx
from playwright.async_api import async_playwright

BUBBLE_MAPS_API_URL = "https://api-legacy.bubblemaps.io"
ELEMENTS_TO_REMOVE = [
    ".mdc-top-app-bar",
    "div.buttons-row:nth-child(6)",
    ".buttons-row",
]


async def get_token_bubble_map(*, contract_addres: str, chain: str) -> dict[str, any]:
    path = "map-data"
    qparams = {
        "chain": chain,
        "token": contract_addres,
    }
    query_string = urlencode(qparams)

    url = f"{BUBBLE_MAPS_API_URL}/{path}?{query_string}"

    response = await send_requet(url)
    if response.get("message") == "Data not available for this token":
        return None
    return response


async def get_decentralization_score(
    *, contract_addres: str, chain: str
) -> dict[str, any]:
    path = "map-metadata"
    qparams = {
        "chain": chain,
        "token": contract_addres,
    }
    query_string = urlencode(qparams)

    url = f"{BUBBLE_MAPS_API_URL}/{path}?{query_string}"
    response = await send_requet(url)
    if response.get("message") == "Data not available for this token":
        return None
    return response


async def send_requet(url: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()
        return data


async def get_bubble_map_screenshot(chain: str, contract_addres: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chromium", headless=True)
        page = await browser.new_page()
        await page.goto(
            f"https://app.bubblemaps.io/{chain}/token/{contract_addres}?mode=0"
        )
        await asyncio.sleep(3)
        await page.evaluate(
            "document.querySelectorAll('{0}').forEach(el => el.remove());".format(
                ",".join(ELEMENTS_TO_REMOVE)
            )
        )
        await page.locator(".graph-view").screenshot(path="screenshot.png")
        await browser.close()
