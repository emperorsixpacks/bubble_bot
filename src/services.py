import asyncio

import httpx
from playwright.async_api import async_playwright

BUBBLE_MAPS_API_URL = "https://api-legacy.bubblemaps.io/map-data"
ElementsToRemove = [".mdc-top-app-bar", "div.buttons-row:nth-child(6)", ".buttons-row"]


async def get_token_bubble_map(contract_addres: str, chain: str) -> dict[str, any]:
    async with httpx.AsyncClient() as client:
        url = BUBBLE_MAPS_API_URL
        params = {
            "chain": chain,
            "token": contract_addres,
        }
        response = await client.get(url, params=params)
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
                ",".join(ElementsToRemove)
            )
        )
        await page.locator(".graph-view").screenshot(path="screenshot.png")
        await browser.close()
