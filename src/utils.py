import os

import imgkit
import httpx


def return_base_dir():
    return os.path.dirname(os.path.dirname(__file__))


async def send_request(url: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response


def ensure_screenshots_directory():
    base_dir = return_base_dir()
    upload_dir = os.path.join(base_dir, "screenshots")
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    return upload_dir


def save_html_as_screenshot(html_file, output_image="screenshot.png"):
    options = {
        "format": "png",
        "encoding": "UTF-8",
    }
    imgkit.from_file(html_file, output_image, options=options)
    print(f"Screenshot saved to {output_image}")


# Usage
save_html_as_screenshot("/home/adavid/Documents/GitHub/bubble_telegram_bot/static/token.html")
