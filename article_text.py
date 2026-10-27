"""Повний текст статті зі сторінки новини — щоб пост мав конкретні деталі, а не лише анонс з RSS."""
import html
import re

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    )
}


def get_article_text(url: str, max_chars: int = 4000) -> str:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        page = resp.text
    except Exception:
        return ""
    page = re.sub(r"(?is)<(script|style|nav|header|footer|aside|form)[^>]*>.*?</\1>", " ", page)
    paragraphs = []
    for raw in re.findall(r"(?is)<p[^>]*>(.*?)</p>", page):
        text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
        text = re.sub(r"\s+", " ", text).strip()
        # відкидаємо службові рядки: копірайти, «читайте також», підписи
        if len(text) < 40 or re.search(r"(©|читайте також|підписуйтес|cookie|всі права)", text, re.I):
            continue
        paragraphs.append(text)
    return "\n".join(paragraphs)[:max_chars]
