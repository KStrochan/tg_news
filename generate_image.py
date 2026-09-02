"""Генерація ілюстрації до новини. Підтримує безкоштовний Pollinations.ai та OpenAI Images API."""
import base64
import random
import urllib.parse

import requests

from config import config


def _generate_pollinations(prompt: str) -> bytes:
    """Безкоштовний сервіс генерації зображень, ключ не потрібен."""
    encoded = urllib.parse.quote(prompt)
    seed = random.randint(1, 1_000_000)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width=1024&height=1024&seed={seed}&nologo=true"
    )
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return resp.content


def _generate_openai(prompt: str) -> bytes:
    headers = {"Authorization": f"Bearer {config.openai_api_key}"}
    payload = {"model": "gpt-image-1", "prompt": prompt, "size": "1024x1024"}
    resp = requests.post(
        "https://api.openai.com/v1/images/generations",
        headers=headers,
        json=payload,
        timeout=90,
    )
    resp.raise_for_status()
    b64 = resp.json()["data"][0]["b64_json"]
    return base64.b64decode(b64)


def generate_image(prompt: str) -> bytes:
    if config.image_provider == "openai":
        return _generate_openai(prompt)
    return _generate_pollinations(prompt)
