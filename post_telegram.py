"""Публікація посту у Telegram-канал через Bot API."""
import html

import requests

from config import config

API_BASE = "https://api.telegram.org/bot{token}/{method}"

CAPTION_LIMIT = 1024   # ліміт підпису до фото
MESSAGE_LIMIT = 4096   # ліміт звичайного текстового повідомлення


def _build_text(title: str, post_text: str, source: str, link: str, limit: int) -> str:
    # Екрануємо текст, інакше символи < > & ламають parse_mode=HTML
    title_h = html.escape(title or "")
    source_h = html.escape(source or "")
    footer = f'\n\n🔗 <a href="{html.escape(link, quote=True)}">{source_h}</a>' if link else f"\n\n🔗 {source_h}"

    body = html.escape(post_text or "")
    head = f"<b>{title_h}</b>\n\n"
    room = limit - len(head) - len(footer)
    if len(body) > room:
        body = body[: max(room - 1, 0)].rstrip() + "…"
    return head + body + footer


def _call(method: str, data: dict, files: dict | None = None) -> dict:
    url = API_BASE.format(token=config.telegram_bot_token, method=method)
    resp = requests.post(url, data=data, files=files, timeout=60)
    if not resp.ok:
        raise RuntimeError(f"Telegram API ({method}) помилка: {resp.status_code} {resp.text}")
    return resp.json()


def post_to_channel(image_bytes: bytes | None, title: str, post_text: str, source: str, link: str):
    """Постить фото з підписом. Якщо картинки немає або Telegram її не прийняв — постить текстом."""
    if image_bytes:
        try:
            caption = _build_text(title, post_text, source, link, CAPTION_LIMIT)
            return _call(
                "sendPhoto",
                data={"chat_id": config.telegram_channel_id, "caption": caption, "parse_mode": "HTML"},
                files={"photo": ("news.jpg", image_bytes)},
            )
        except RuntimeError as e:
            # Помилки доступу/ID каналу не лікуються текстовим постом — прокидуємо далі
            if any(code in str(e) for code in (" 401 ", " 403 ", "chat not found")):
                raise
            print(f"   [telegram] Фото не надіслалось ({e}), публікую текстом.")

    text = _build_text(title, post_text, source, link, MESSAGE_LIMIT)
    return _call(
        "sendMessage",
        data={
            "chat_id": config.telegram_channel_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        },
    )
