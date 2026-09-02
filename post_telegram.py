"""Публікація фото + підпису у Telegram-канал через Bot API."""
import requests

from config import config

TELEGRAM_API = f"https://api.telegram.org/bot{{token}}/sendPhoto"


def post_to_channel(image_bytes: bytes, title: str, post_text: str, source: str, link: str):
    caption = f"<b>{title}</b>\n\n{post_text}\n\n🔗 Джерело: {source}"
    if len(caption) > 1024:
        caption = caption[:1000] + "…"

    url = TELEGRAM_API.format(token=config.telegram_bot_token)
    files = {"photo": ("news.jpg", image_bytes)}
    data = {
        "chat_id": config.telegram_channel_id,
        "caption": caption,
        "parse_mode": "HTML",
    }
    resp = requests.post(url, data=data, files=files, timeout=60)
    if not resp.ok:
        raise RuntimeError(f"Telegram API помилка: {resp.status_code} {resp.text}")
    return resp.json()
