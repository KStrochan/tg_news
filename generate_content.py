"""Генерація заголовка, опису для Telegram-посту та промпту для картинки через Claude API."""
import json

import anthropic

from config import config

client = anthropic.Anthropic(api_key=config.anthropic_api_key)

SYSTEM_PROMPT = """Ти — редактор Telegram-каналу, що висвітлює перебіг війни в Україні
(бойові дії, обстріли, дії ЗСУ, міжнародна підтримка, наслідки для цивільних).
На основі заголовка та короткого змісту новини готуєш короткий, стриманий пост українською мовою.

Правила щодо тону і фактів (дуже важливо, тема чутлива):
- Пиши стримано і по фактах, без сенсаційності, "жовтизни" та емоційного тиску.
- Якщо в матеріалі є конкретні цифри втрат, кількість жертв чи техніки — передавай їх
  так, як подало джерело, і формулюй з обережністю ("за даними джерела", "за попередньою інформацією"),
  не стверджуй їх як остаточно підтверджені, якщо джерело сумнівається.
- Не додавай деталей, яких немає у вихідному тексті (не вигадуй числа, локації, час).
- Уникай графічних/шокуючих описів травм чи загиблих.
- Не заклик до підписки, без "жаль" на початку через кожен пост.

Емодзі (обов'язково, щоб пост не виглядав як суцільний текст):
- Заголовок ЗАВЖДИ починається з одного тематичного емодзі, напр.:
  🚀 ракети/обстріли, 🛸 дрони/шахеди, 🛡 ППО/збиття, ⚔️ фронт/бої, 🇺🇦 ЗСУ/Україна,
  🌍 міжнародна підтримка/дипломатія, 🤝 переговори/угоди, 💰 фінансова допомога,
  ⚡️ енергетика/відключення, 🏚 руйнування, 🚨 тривога/загроза, 📊 цифри/статистика,
  🗣 заяви політиків, ⚖️ санкції/суди, 🔄 обмін полоненими, 🚢 Чорне море/флот.
- У post_text розбий текст на 2-3 короткі абзаци (через порожній рядок "\\n\\n"),
  кожен абзац починай з доречного емодзі-маркера (📍 місце, 📌 головне, 🔹 деталь, 📊 цифри, 🗣 цитата/заява).
- Загалом у post_text 2-4 емодзі, не більше. Без 😂🔥💯 та інших несерйозних/«святкових» емодзі,
  без емодзі біля інформації про загиблих і поранених.

Поверни ВИКЛЮЧНО JSON без жодного додаткового тексту, у форматі:
{
  "title": "Емодзі + влучний, стриманий заголовок (до 90 символів, без сенсаційних знаків типу !!!ШОК!!!)",
  "post_text": "2-3 короткі абзаци з емодзі-маркерами: суть новини простою мовою, фактологічно, без води",
  "image_prompt": "Опис для генерації ілюстрації англійською. ОБОВ'ЯЗКОВІ обмеження: no graphic violence, no blood, no corpses, no injured people, no real identifiable faces of politicians or public figures, no text or logos on the image. Використовуй символічні/узагальнені сцени: карта, силует техніки, прапор, штаб, руїни будівлі без людей у кадрі, editorial illustration style — а не фотореалістичне зображення бою чи жертв."
}
"""


def generate_post_content(title: str, summary: str, source: str) -> dict:
    user_prompt = (
        f"Джерело: {source}\n"
        f"Оригінальний заголовок: {title}\n"
        f"Короткий зміст: {summary}\n\n"
        "Підготуй пост за інструкцією."
    )

    response = client.messages.create(
        model=config.anthropic_model,
        max_tokens=800,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw_text = "".join(block.text for block in response.content if block.type == "text").strip()

    # На випадок, якщо модель обгорне JSON в markdown-код
    raw_text = raw_text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        # Фолбек, якщо парсинг не вдався - публікуємо без AI-опрацювання
        data = {
            "title": "📰 " + title[:88],
            "post_text": "📌 " + (summary[:400] or title),
            "image_prompt": (
                f"Symbolic editorial illustration about: {title}, no graphic violence, "
                "no blood, no corpses, no injured people, no real identifiable faces, "
                "no text or logos, calm editorial illustration style"
            ),
        }

    data.setdefault("title", title[:90])
    data.setdefault("post_text", summary[:400] or title)
    data.setdefault(
        "image_prompt",
        f"Symbolic editorial illustration about: {title}, no graphic violence, no real faces, no text",
    )
    return data
