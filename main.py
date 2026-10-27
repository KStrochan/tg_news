"""Головний скрипт: бере свіжі новини -> генерує текст та картинку -> постить у Telegram."""
import os
import sys
import time

from config import config
from fetch_news import get_unpublished_news
from generate_content import generate_post_content
from generate_image import generate_image
from source_image import get_source_image
from post_telegram import post_to_channel
from storage import load_posted, save_posted

IN_GITHUB = os.getenv("GITHUB_ACTIONS") == "true"


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
    # беремо кандидатів із запасом: якщо одна новина не вдалась, публікуємо наступну
    news_items = get_unpublished_news(set(posted), limit=config.posts_per_run * 3)

    if not news_items:
        print("Нових новин не знайдено (можливо, все вже опубліковано або джерела недоступні).")
        save_posted(posted)
        return 0

    published_count = 0
    errors = []
    for item in news_items:
        if published_count >= config.posts_per_run:
            break
        try:
            print(f"-> Обробляю: {item.title} ({item.source})")
            content = generate_post_content(item.title, item.summary, item.source)
            image_bytes = None
            if item.source_images:
                image_bytes = get_source_image(item.entry, item.link)
                print("   [image] Фото з джерела" if image_bytes else "   [image] У джерелі фото немає — генерую")
            if image_bytes is None:
                image_bytes = generate_image(content["image_prompt"])
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
