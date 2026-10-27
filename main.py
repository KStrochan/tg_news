"""Головний скрипт: бере свіжі новини -> генерує текст та картинку -> постить у Telegram."""
import os
import sys
import time

from config import config
from fetch_news import get_unpublished_news
from article_text import get_article_text
from generate_content import generate_post_content
from news_ranker import rank_news
from generate_image import generate_image
from source_image import get_source_image
from post_telegram import post_to_channel
from storage import load_posted, save_posted

IN_GITHUB = os.getenv("GITHUB_ACTIONS") == "true"

MIN_SCORE = int(os.getenv("MIN_SCORE", "5"))   # нижче — не публікуємо
SKIP_SCORE = 3                                  # таке більше не розглядаємо


def gh_error(message: str):
    """Виводить помилку так, щоб GitHub показав її текстом прямо на сторінці запуску."""
    print(message, file=sys.stderr)
    if IN_GITHUB:
        print(f"::error title=tg_news::{message}".replace("\n", " "))


def run() -> int:
    try:
        config.validate()
    except RuntimeError as e:
        gh_error(str(e))
        return 1

    posted = load_posted()
    candidates = get_unpublished_news(set(posted), limit=25)
    if not candidates:
        print("Нових новин не знайдено (можливо, все вже опубліковано або джерела недоступні).")
        save_posted(posted)
        return 0

    # Claude оцінює цікавість; нудне (≤ SKIP_SCORE) запам'ятовуємо, щоб не оцінювати повторно
    ranked = rank_news(candidates)
    for it, score in ranked:
        if score <= SKIP_SCORE:
            posted.append(it.link)
    news_items = [it for it, score in ranked if score >= MIN_SCORE]
    if not news_items:
        print(f"Цікавих новин (оцінка ≥ {MIN_SCORE}) зараз немає — пропускаю публікацію.")
        save_posted(posted)
        return 0

    published_count = 0
    errors = []
    for item in news_items:
        if published_count >= config.posts_per_run:
            break
        try:
            print(f"-> Обробляю: {item.title} ({item.source})")
            full_text = get_article_text(item.link)
            content = generate_post_content(item.title, item.summary, item.source, full_text)
            image_bytes = None
            if item.source_images:
                image_bytes = get_source_image(item.entry, item.link)
                print("   [image] Фото з джерела" if image_bytes else "   [image] У джерелі фото немає — роблю картку")
            if image_bytes is None:
                image_bytes = generate_image(content["image_prompt"], content["title"], item.source)
            post_to_channel(
                image_bytes=image_bytes,
                title=content["title"],
                post_text=content["post_text"],
                source=item.source,
                link=item.link,
            )
            posted.append(item.link)
            published_count += 1
            print("   Опубліковано.")
        except Exception as e:
            errors.append(f"'{item.title[:60]}': {e}")
            print(f"   Помилка при обробці новини '{item.title}': {e}", file=sys.stderr)
            continue

        time.sleep(config.delay_between_posts)

    save_posted(posted)
    print(f"Готово. Опубліковано новин: {published_count}/{config.posts_per_run}")

    if published_count == 0:
        gh_error("Жодну новину не опубліковано. " + " | ".join(errors)[:900])
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(run())
