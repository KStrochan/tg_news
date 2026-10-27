"""Генерація ілюстрації до новини. Підтримує безкоштовний Pollinations.ai та OpenAI Images API."""
import base64
import random
import time
import urllib.parse

import requests

from config import config


def _generate_pollinations(prompt: str) -> bytes:
    """Безкоштовний сервіс генерації зображень, ключ не потрібен. 3 спроби, бо сервіс іноді віддає 503."""
    encoded = urllib.parse.quote(prompt[:900])
    variants = [
        "width=1280&height=720&model=flux&enhance=true",
        "width=1280&height=720&model=flux",
        "width=1024&height=576",
    ]
    last_error = None
    for params in variants:
        seed = random.randint(1, 1_000_000)
        url = f"https://image.pollinations.ai/prompt/{encoded}?{params}&seed={seed}&nologo=true"
        try:
            resp = requests.get(url, timeout=90)
            resp.raise_for_status()
            if not resp.headers.get("Content-Type", "").startswith("image/"):
                raise RuntimeError(f"не картинка: {resp.headers.get('Content-Type')}")
            return resp.content
        except Exception as e:
            last_error = e
            time.sleep(5)
    raise RuntimeError(f"Pollinations недоступний: {last_error}")


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


def generate_image(prompt: str) -> bytes | None:
    """Повертає байти картинки або None — тоді пост піде без фото, але піде."""
    try:
        if config.image_provider == "openai":
            return _generate_openai(prompt)
        return _generate_pollinations(prompt)
    except Exception as e:
        print(f"   [image] Не вдалося згенерувати картинку ({e}), пост буде без фото.")
        return None
