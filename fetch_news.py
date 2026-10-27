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
    local: bool = True                                # про Стрийщину (True) чи загальна новина (False)


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


GENERAL_MAX_AGE_HOURS = 12  # загальні новини швидко старіють


def fetch_all_news(max_per_feed: int = 30) -> list[NewsItem]:
    """Новини з усіх джерел, нові першими.

    Місцеві: з джерел без фільтра або ті, де згадано Стрийщину.
    Загальні (local=False): з джерел з "general": true — решта їхніх новин, лише свіжі (12 год).
    """
    patterns, max_age_hours = _load_settings()
    now = datetime.now(timezone.utc)
    cutoff_local = now - timedelta(hours=max_age_hours)
    cutoff_general = now - timedelta(hours=GENERAL_MAX_AGE_HOURS)

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

        n_local = n_general = 0
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
            item.local = (not feed_cfg.get("filter", True)) or is_local(item, patterns)
            if item.local:
                if item.published < cutoff_local:
                    continue
                n_local += 1
            else:
                if not feed_cfg.get("general", False) or item.published < cutoff_general:
                    continue
                n_general += 1
            items.append(item)
        print(f"[fetch_news] {feed_cfg['name']}: місцевих {n_local}, загальних {n_general}")

    items.sort(key=lambda x: x.published, reverse=True)
    return items


def _norm_title(title: str) -> str:
    return re.sub(r"[^\w]+", " ", title.lower()).strip()


def get_unpublished_news(posted_links: set, limit: int = 20, general_limit: int = 15) -> list[NewsItem]:
    """Неопубліковані кандидати: до `limit` місцевих і до `general_limit` загальних (найсвіжіших)."""
    local, general, seen_titles = [], [], set()
    for item in fetch_all_news():
        key = _norm_title(item.title)[:60]
        if item.link in posted_links or key in seen_titles:
            continue
        seen_titles.add(key)
        (local if item.local else general).append(item)
    return local[:limit] + general[:general_limit]
