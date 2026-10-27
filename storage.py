"""Просте JSON-сховище посилань на вже опубліковані новини.

Зберігаємо список у порядку публікації, щоб при обрізанні історії
відкидались саме найстаріші посилання (а не випадкові, як було з set).
"""
import json
import os

from config import config

MAX_HISTORY = 1500  # скільки останніх посилань пам'ятати (опубліковані + відсіяні)


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
    data = {}
    if os.path.exists(config.storage_path):
        try:
            with open(config.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {}
    data["posted_links"] = list(dict.fromkeys(posted))[-MAX_HISTORY:]
    with open(config.storage_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


MAX_TITLES = 40  # скільки останніх заголовків пам'ятати для перевірки «та сама подія»


def load_recent_titles() -> list:
    if not os.path.exists(config.storage_path):
        return []
    try:
        with open(config.storage_path, "r", encoding="utf-8") as f:
            return json.load(f).get("recent_titles", [])
    except (json.JSONDecodeError, OSError):
        return []


def save_recent_titles(titles: list):
    data = {}
    if os.path.exists(config.storage_path):
        try:
            with open(config.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {}
    data["recent_titles"] = titles[-MAX_TITLES:]
    with open(config.storage_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


MAX_SCORES = 400  # кеш оцінок цікавості (link → score), щоб не оцінювати ту саму новину двічі


def load_scores() -> dict:
    if not os.path.exists(config.storage_path):
        return {}
    try:
        with open(config.storage_path, "r", encoding="utf-8") as f:
            return json.load(f).get("scores", {})
    except (json.JSONDecodeError, OSError):
        return {}


def save_scores(scores: dict):
    data = {}
    if os.path.exists(config.storage_path):
        try:
            with open(config.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {}
    data["scores"] = dict(list(scores.items())[-MAX_SCORES:])
    with open(config.storage_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
