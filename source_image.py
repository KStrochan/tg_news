"""Фото з самого джерела новини: з RSS (enclosure / media / <img>) або головне фото статті (og:image).

Повертає JPEG-байти, готові для Telegram, або None — тоді бот згенерує ілюстрацію сам.
"""
import io
import re
from urllib.parse import urljoin

import requests
from PIL import Image

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    )
}

MIN_WIDTH = 300     # менші — це зазвичай іконки й мініатюри; справжнє фото навіть 320px краще за згенероване
MIN_HEIGHT = 200
MAX_BYTES = 9_500_000  # Telegram приймає фото до 10 МБ

# Картинки-заглушки та логотипи сайтів, які не варто ставити в пост
SKIP_PATTERNS = re.compile(r"(logo|favicon|icon|placeholder|default|no[-_]?image|avatar|banner|sprite)", re.I)


def _candidates_from_entry(entry, page_url: str) -> list[str]:
    urls = []
    for media in getattr(entry, "media_content", []) or []:
        if media.get("url") and "image" in (media.get("type") or "image"):
            urls.append(media["url"])
    for thumb in getattr(entry, "media_thumbnail", []) or []:
        if thumb.get("url"):
            urls.append(thumb["url"])
    for enc in getattr(entry, "enclosures", []) or []:
        if enc.get("href") and (enc.get("type") or "").startswith("image"):
            urls.append(enc["href"])
    html_parts = [getattr(entry, "summary", "") or ""]
    for c in getattr(entry, "content", []) or []:
        html_parts.append(c.get("value", ""))
    for part in html_parts:
        urls += re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', part, re.I)
    return [urljoin(page_url, u) for u in urls]


def _og_image(page_url: str) -> list[str]:
    try:
        resp = requests.get(page_url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception:
        return []
    html_text = resp.text[:300_000]
    found = []
    for prop in ("og:image", "twitter:image"):
        for pattern in (
            rf'<meta[^>]+(?:property|name)=["\']{prop}["\'][^>]+content=["\']([^"\']+)["\']',
            rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']{prop}["\']',
        ):
            found += re.findall(pattern, html_text, re.I)
    return [urljoin(page_url, u) for u in found]


def _download_as_jpeg(url: str) -> bytes | None:
    if SKIP_PATTERNS.search(url.rsplit("/", 1)[-1]):
        return None
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        if len(resp.content) > 20_000_000:
            return None
        img = Image.open(io.BytesIO(resp.content))
        img.load()
    except Exception:
        return None

    if img.width < MIN_WIDTH or img.height < MIN_HEIGHT:
        return None
    if img.width / img.height > 3 or img.height / img.width > 3:
        return None  # вузькі банери/смужки

    if img.mode not in ("RGB", "L"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        rgba = img.convert("RGBA")
        background.paste(rgba, mask=rgba.split()[-1])
        img = background
    elif img.mode == "L":
        img = img.convert("RGB")

    img.thumbnail((2048, 2048))
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=88, optimize=True)
    data = out.getvalue()
    return data if len(data) <= MAX_BYTES else None


def get_source_image(entry, page_url: str) -> bytes | None:
    """Перше придатне фото з RSS-запису, а якщо там немає — з og:image сторінки новини."""
    try:
        return _find(entry, page_url)
    except Exception as e:  # фото — не критично, при будь-якій помилці просто згенеруємо своє
        print(f"   [image] Не вдалося взяти фото з джерела: {e}")
        return None


def _find(entry, page_url: str) -> bytes | None:
    seen = set()
    for url in _candidates_from_entry(entry, page_url):
        if url in seen:
            continue
        seen.add(url)
        data = _download_as_jpeg(url)
        if data:
            return data
    for url in _og_image(page_url):
        if url in seen:
            continue
        seen.add(url)
        data = _download_as_jpeg(url)
        if data:
            return data
    return None
