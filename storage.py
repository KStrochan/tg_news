"""Просте JSON-сховище посилань на вже опубліковані новини."""
import json
import os
from config import config

MAX_HISTORY = 500  # скільки останніх посилань пам'ятати, щоб файл не ріс безмежно


def load_posted() -> set:
    if not os.path.exists(config.storage_path):
        return set()
    try:
        with open(config.storage_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return set(data.get("posted_links", []))
    except (json.JSONDecodeError, OSError):
        return set()


def save_posted(posted: set):
    trimmed = list(posted)[-MAX_HISTORY:]
    with open(config.storage_path, "w", encoding="utf-8") as f:
        json.dump({"posted_links": trimmed}, f, ensure_ascii=False, indent=2)
