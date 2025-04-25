import os
from io import BytesIO
from pathlib import Path

import httpx
import imgkit
from jinja2 import Environment, FileSystemLoader


def return_base_dir():
    return os.path.dirname(os.path.dirname(__file__))


async def send_request(url: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response


def save_html_as_screenshot(html_file):
    options = {
        "format": "png",
        "encoding": "UTF-8",
        "enable-local-file-access": None,
    }
    img_bytes = imgkit.from_file(html_file, False, options=options)
    return BytesIO(img_bytes)


def render_html_template(template_path: str, token: dict, metrics) -> str:
    # Verify template exists
    if not Path(template_path).exists():
        raise FileNotFoundError(f"Template file not found: {template_path}")

    # Set up Jinja environment
    template_dir = str(Path(template_path).parent)
    template_file = Path(template_path).name

    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # Render template with context
    template = env.get_template(template_file)
    return template.render(token=token, metrics=metrics)
