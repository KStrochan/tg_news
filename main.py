"""Головний скрипт: бере свіжі новини -> генерує текст та картинку -> постить у Telegram."""
import sys
import time

from config import config
from fetch_news import get_unpublished_news
from generate_content import generate_post_content
from generate_image import generate_image
from post_telegram import post_to_channel
from storage import load_posted, save_posted


def run():
    config.validate()

    posted = load_posted()
    news_items = get_unpublished_news(posted, limit=config.posts_per_run)

    if not news_items:
        print("Нових новин не знайдено (можливо, все вже опубліковано або джерела недоступні).")
        return

    published_count = 0
    for item in news_items:
        try:
            print(f"-> Обробляю: {item.title} ({item.source})")
            content = generate_post_content(item.title, item.summary, item.source)
            image_bytes = generate_image(content["image_prompt"])
            post_to_channel(
                image_bytes=image_bytes,
                title=content["title"],
                post_text=content["post_text"],
                source=item.source,
                link=item.link,
            )
            posted.add(item.link)
            published_count += 1
            print("   Опубліковано.")
        except Exception as e:
            print(f"   Помилка при обробці новини '{item.title}': {e}", file=sys.stderr)
            continue

        time.sleep(config.delay_between_posts)

    save_posted(posted)
    print(f"Готово. Опубліковано новин: {published_count}/{len(news_items)}")


if __name__ == "__main__":
    run()
