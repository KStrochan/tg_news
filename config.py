"""Завантаження налаштувань з .env та sources.json"""
import json
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


@dataclass
class Config:
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    telegram_channel_id: str = os.getenv("TELEGRAM_CHANNEL_ID", "").strip()

    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "").strip()
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL") or "claude-sonnet-5-5"

    image_provider: str = os.getenv("IMAGE_PROVIDER", "pollinations")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")

    posts_per_run: int = int(os.getenv("POSTS_PER_RUN", "1"))
    delay_between_posts: int = int(os.getenv("DELAY_BETWEEN_POSTS", "5"))

    storage_path: str = os.path.join(BASE_DIR, "posted_news.json")
    sources_path: str = os.path.join(BASE_DIR, "sources.json")

    def validate(self):
        missing = []
        if not self.telegram_bot_token:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not self.telegram_channel_id:
            missing.append("TELEGRAM_CHANNEL_ID")
        if not self.anthropic_api_key:
            missing.append("ANTHROPIC_API_KEY")
        if missing:
            raise RuntimeError(
                "Не задані секрети: " + ", ".join(missing)
                + ". Додайте їх у GitHub: Settings → Secrets and variables → Actions → New repository secret."
            )


def load_feeds():
    with open(Config().sources_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [f for f in data["feeds"] if f.get("enabled", True)]


config = Config()
