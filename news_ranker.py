"""Відбір новин: Claude оцінює, наскільки кожна новина цікава мешканцям Стрийщини (1–10).

Оцінюються лише НОВІ новини — оцінки вже баченого беруться з кешу (posted_news.json → scores),
тож частіші запуски майже нічого не коштують. Для оцінки — дешевша модель (RANK_MODEL).
"""
import json
import os
import re

from config import config
from generate_content import client

RANK_MODEL = os.getenv("RANK_MODEL", "claude-haiku-5-5")

RANK_PROMPT = """Ти — головний редактор місцевого Telegram-каналу «Стрий | Новини Стрийщини».
Оціни кожну новину від 1 до 10: наскільки її захочуть прочитати й переслати мешканці Стрия та району.

[МІСЦЕВА] — новини про Стрий і громади району:
- 7–10: те, що прямо зачіпає життя людей — відключення води/світла/газу, перекриття доріг,
  зміни в транспорті й цінах, надзвичайні події, ДТП, злочини й суди з місцевими людьми, загибель
  земляків на війні, вшанування загиблих Захисників, великі ремонти й будівництва, нові заклади,
  рішення влади з наслідками для людей, гроші/виплати, події, на які можна піти, здобутки земляків.
- 4–6: цікаві, але не термінові місцеві історії, культура, спорт, співпраця громад.
- 1–3: канцелярія без наслідків для людей — засідання комісій, наради, обговорення документів,
  СЕО, звіти, привітання, протокольні зустрічі, новини, де Стрийщина згадана мимохідь.

[ЗАГАЛЬНА] — новини України та Львівщини. Місцевий канал публікує їх, ЛИШЕ якщо вони прямо
стосуються гаманця, безпеки чи побуту КОЖНОГО мешканця:
- 6–7 (максимум 7!): ціни на пальне, продукти, комуналку; тарифи; пенсії, виплати, субсидії;
  графіки відключень світла на Львівщині; зміни в правилах мобілізації, бронювання, перетину кордону;
  погодні попередження для Львівщини; масові атаки на Львівщину.
- 1–3: усе інше — політика, заяви політиків, фронтові зведення, новини інших міст і країн,
  спорт, шоу-бізнес, кримінал не зі Стрийщини.

ДУЖЕ ВАЖЛИВО: якщо новина про ту саму подію, що вже є в списку «Вже опубліковано»
(та сама аварія, той самий злочин, те саме рішення — навіть з іншого джерела й іншими словами),
став їй оцінку 1. Якщо серед нових кілька новин про одну подію — високу оцінку лише одній, найповнішій.

Поверни ВИКЛЮЧНО JSON-масив без іншого тексту: [{"id": 0, "score": 7}, ...] для кожної новини."""


def _ask(model: str, content: str) -> dict:
    response = client.messages.create(
        model=model,
        max_tokens=800,
        system=RANK_PROMPT,
        messages=[{"role": "user", "content": content}],
    )
    raw = "".join(b.text for b in response.content if b.type == "text")
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    return {int(x["id"]): int(x["score"]) for x in json.loads(match.group(0), strict=False)}


def rank_news(items: list, published_titles: list | None = None, cache: dict | None = None) -> list[tuple]:
    """Повертає [(item, score)] від найцікавішої. `cache` (link → score) доповнюється новими оцінками."""
    if not items:
        return []
    cache = cache if cache is not None else {}
    new_items = [it for it in items if it.link not in cache]

    if new_items:
        lines = []
        for i, it in enumerate(new_items):
            tag = "МІСЦЕВА" if it.local else "ЗАГАЛЬНА"
            lines.append(f"[{i}] [{tag}] ({it.source}) {it.title}\n{(it.summary or '')[:300]}")
        published = "\n".join(f"- {t}" for t in (published_titles or [])[-30:]) or "(поки нічого)"
        content = f"Вже опубліковано в каналі:\n{published}\n\nНові новини для оцінки:\n\n" + "\n\n".join(lines)
        scores = {}
        for model in dict.fromkeys([RANK_MODEL, config.anthropic_model]):
            try:
                scores = _ask(model, content)
                break
            except Exception as e:
                print(f"[ranker] Модель {model} не змогла оцінити ({e})")
        for i, it in enumerate(new_items):
            default = 5 if it.local else 2  # якщо оцінки немає — місцеве лишаємо, загальне ні
            cache[it.link] = max(1, min(10, scores.get(i, default)))

    ranked = [(it, cache[it.link]) for it in items]
    # стабільне сортування: при однаковій оцінці місцеві й свіжіші лишаються першими
    ranked.sort(key=lambda x: (x[1], x[0].local), reverse=True)
    for it, sc in ranked[:15]:
        print(f"[ranker] {sc:>2} {'М' if it.local else 'З'}  {it.title[:90]} ({it.source})")
    return ranked
