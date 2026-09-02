"""Завантаження свіжих новин з RSS-джерел."""
import html
import re
from dataclasses import dataclass
from datetime import datetime, timezone

import json

import feedparser

from config import load_feeds, config


@dataclass
class NewsItem:
    title: str
    link: str
    summary: str
    source: str
    published: datetime


def _clean_html(raw: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_date(entry) -> datetime:
    for attr in ("published_parsed", "updated_parsed"):
        val = getattr(entry, attr, None)
        if val:
            return datetime(*val[:6], tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def _load_war_keywords() -> list[str]:
    try:
        with open(config.sources_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [kw.lower() for kw in data.get("war_keywords", [])]
    except (OSError, json.JSONDecodeError):
        return []


def is_war_related(item: "NewsItem", keywords: list[str]) -> bool:
    if not keywords:
        return True  # якщо список порожній - фільтр вимкнено, пропускаємо все
    haystack = f"{item.title} {item.summary}".lower()
    return any(kw in haystack for kw in keywords)


def fetch_all_news(max_per_feed: int = 15) -> list[NewsItem]:
    """Повертає список новин з усіх увімкнених джерел, відсортований за датою (нові першими)."""
    items: list[NewsItem] = []
    for feed_cfg in load_feeds():
        try:
            parsed = feedparser.parse(feed_cfg["url"])
        except Exception as e:
            print(f"[fetch_news] Помилка при читанні {feed_cfg['name']}: {e}")
            continue

        if getattr(parsed, "bozo", False) and not parsed.entries:
            print(f"[fetch_news] Джерело {feed_cfg['name']} не віддало новин (можливо, змінилась RSS-адреса)")
            continue

        for entry in parsed.entries[:max_per_feed]:
            title = _clean_html(getattr(entry, "title", ""))
            link = getattr(entry, "link", "")
            summary = _clean_html(getattr(entry, "summary", "") or getattr(entry, "description", ""))
            if not title or not link:
                continue
            items.append(
                NewsItem(
                    title=title,
                    link=link,
                    summary=summary[:1500],
                    source=feed_cfg["name"],
                    published=_parse_date(entry),
                )
            )

    items.sort(key=lambda x: x.published, reverse=True)
    return items


def get_unpublished_news(posted_links: set, limit: int) -> list[NewsItem]:
    all_news = fetch_all_news()
    keywords = _load_war_keywords()
    relevant = [item for item in all_news if is_war_related(item, keywords)]
    fresh = [item for item in relevant if item.link not in posted_links]
    return fresh[:limit]
