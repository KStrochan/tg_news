"""Завантаження свіжих новин Стрия та Стрийського району з RSS-джерел."""
import html
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import feedparser
import requests

from config import config, load_feeds

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    )
}


@dataclass
class NewsItem:
    title: str
    link: str
    summary: str
    source: str
    published: datetime
    entry: object = field(default=None, repr=False)  # сирий RSS-запис (для пошуку фото)
    source_images: bool = True                        # чи можна брати фото з цього джерела


def _clean_html(raw: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw or "")
    text = html.unescape(text)
    # WordPress додає в кінець "The post ... appeared first on ..."
    text = re.sub(r"The post .*? appeared first on .*$", "", text, flags=re.DOTALL)
    return re.sub(r"\s+", " ", text).strip()


def _parse_date(entry) -> datetime:
    for attr in ("published_parsed", "updated_parsed"):
        val = getattr(entry, attr, None)
        if val:
            return datetime(*val[:6], tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def _load_settings() -> tuple[list[re.Pattern], int]:
    try:
        with open(config.sources_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return [], 48
    patterns = [
        # ключове слово має стояти на початку слова: "стрий" ≠ "австрия"
        re.compile(r"(?<![\w'’])" + re.escape(kw.lower()))
        for kw in data.get("local_keywords", [])
    ]
    return patterns, int(data.get("max_age_hours", 48))


def is_local(item: "NewsItem", patterns: list[re.Pattern]) -> bool:
    if not patterns:
        return True
    haystack = f"{item.title} {item.summary}".lower()
    return any(p.search(haystack) for p in patterns)


def _download(url: str):
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return feedparser.parse(resp.content)


def fetch_all_news(max_per_feed: int = 30) -> list[NewsItem]:
    """Повертає місцеві новини з усіх увімкнених джерел, нові першими."""
    patterns, max_age_hours = _load_settings()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

    items: list[NewsItem] = []
    for feed_cfg in load_feeds():
        try:
            parsed = _download(feed_cfg["url"])
        except Exception as e:
            print(f"[fetch_news] Помилка при читанні {feed_cfg['name']}: {e}")
            continue

        if not parsed.entries:
            print(f"[fetch_news] Джерело {feed_cfg['name']} не віддало новин")
            continue

        taken = 0
        for entry in parsed.entries[:max_per_feed]:
            title = _clean_html(getattr(entry, "title", ""))
            link = getattr(entry, "link", "")
            summary = _clean_html(getattr(entry, "summary", "") or getattr(entry, "description", ""))
            if not title or not link:
                continue
            item = NewsItem(
                title=title,
                link=link,
                summary=summary[:1500],
                source=feed_cfg["name"],
                published=_parse_date(entry),
                entry=entry,
                source_images=feed_cfg.get("source_images", True),
            )
            if item.published < cutoff:
                continue
            if feed_cfg.get("filter", True) and not is_local(item, patterns):
                continue
            items.append(item)
            taken += 1
        print(f"[fetch_news] {feed_cfg['name']}: свіжих місцевих новин {taken}")

    items.sort(key=lambda x: x.published, reverse=True)
    return items


def _norm_title(title: str) -> str:
    return re.sub(r"[^\w]+", " ", title.lower()).strip()


def get_unpublished_news(posted_links: set, limit: int) -> list[NewsItem]:
    fresh, seen_titles = [], set()
    for item in fetch_all_news():
        key = _norm_title(item.title)[:60]
        if item.link in posted_links or key in seen_titles:
            continue
        seen_titles.add(key)
        fresh.append(item)
    return fresh[:limit]
