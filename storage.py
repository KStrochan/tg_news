"""Просте JSON-сховище посилань на вже опубліковані новини.

Зберігаємо список у порядку публікації, щоб при обрізанні історії
відкидались саме найстаріші посилання (а не випадкові, як було з set).
"""
import json
import os

from config import config

MAX_HISTORY = 500  # скільки останніх посилань пам'ятати, щоб файл не ріс безмежно


def load_posted() -> list:
    if not os.path.exists(config.storage_path):
        return []
    try:
        with open(config.storage_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        links = data.get("posted_links", [])
        # прибираємо дублікати, зберігаючи порядок
        return list(dict.fromkeys(links))
    except (json.JSONDecodeError, OSError):
        return []


def save_posted(posted: list):
    trimmed = list(dict.fromkeys(posted))[-MAX_HISTORY:]
    with open(config.storage_path, "w", encoding="utf-8") as f:
        json.dump({"posted_links": trimmed}, f, ensure_ascii=False, indent=2)
