"""Відбір новин: Claude оцінює, наскільки кожна новина цікава мешканцям Стрийщини (1–10)."""
import json
import re

from generate_content import client
from config import config

RANK_PROMPT = """Ти — головний редактор місцевого Telegram-каналу «Стрий | Новини Стрийщини».
Оціни кожну новину від 1 до 10: наскільки її захочуть прочитати й переслати мешканці Стрия та району.

Високо (7–10): те, що прямо зачіпає життя людей — відключення води/світла/газу, перекриття доріг,
зміни в транспорті й цінах, надзвичайні події, ДТП, злочини й суди з місцевими людьми, загибель
земляків на війні, великі ремонти й будівництва, нові заклади, гучні рішення влади з наслідками
для людей, гроші/виплати, події, на які можна піти, здобутки місцевих людей.
Середньо (4–6): цікаві, але не термінові місцеві історії, культура, спорт, співпраця громад.
Низько (1–3): канцелярія без наслідків для людей — засідання комісій, «відбулася нарада»,
оголошення про громадські обговорення документів, СЕО, звіти, привітання, протокольні зустрічі,
загальнообласні новини, де Стрийщина згадана мимохідь.

ДУЖЕ ВАЖЛИВО: якщо новина про ту саму подію, що вже є в списку «Вже опубліковано»
(та сама аварія, той самий злочин, те саме рішення — навіть з іншого джерела й іншими словами),
став їй оцінку 1. Якщо серед нових кілька новин про одну подію — високу оцінку лише одній, найповнішій.

Поверни ВИКЛЮЧНО JSON-масив без іншого тексту: [{"id": 0, "score": 7}, ...] для кожної новини."""


def rank_news(items: list, published_titles: list | None = None) -> list[tuple]:
    """Повертає [(item, score)], відсортовані від найцікавішої. При помилці — усі з оцінкою 5."""
    if not items:
        return []
    lines = []
    for i, it in enumerate(items):
        summary = (it.summary or "")[:300]
        lines.append(f"[{i}] ({it.source}) {it.title}\n{summary}")
    published = "\n".join(f"- {t}" for t in (published_titles or [])[-30:]) or "(поки нічого)"
    user_content = f"Вже опубліковано в каналі:\n{published}\n\nНові новини для оцінки:\n\n" + "\n\n".join(lines)
    try:
        response = client.messages.create(
            model=config.anthropic_model,
            max_tokens=600,
            system=RANK_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
        raw = "".join(b.text for b in response.content if b.type == "text")
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        scores = {int(x["id"]): int(x["score"]) for x in json.loads(match.group(0), strict=False)}
    except Exception as e:
        print(f"[ranker] Не вдалося оцінити новини ({e}), беру за свіжістю")
        scores = {}

    ranked = [(it, scores.get(i, 5)) for i, it in enumerate(items)]
    # стабільне сортування: при однаковій оцінці свіжіші лишаються першими
    ranked.sort(key=lambda x: x[1], reverse=True)
    for it, sc in ranked:
        print(f"[ranker] {sc:>2}  {it.title[:90]} ({it.source})")
    return ranked
