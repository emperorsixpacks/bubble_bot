import os

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
