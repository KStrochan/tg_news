"""Фірмова картка-обкладинка для новини без фото: назва каналу, заголовок, дата, посилання.

Малюється локально через Pillow — безкоштовно і завжди в одному стилі.
"""
import io
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
FONT_TITLE = os.path.join(ASSETS, "InterDisplay-ExtraBold.otf")
FONT_LABEL = os.path.join(ASSETS, "Inter-SemiBold.otf")
FONT_SMALL = os.path.join(ASSETS, "Inter-Medium.otf")

W, H = 1280, 720
PAD = 80
BG_TOP = (14, 27, 48)
BG_BOTTOM = (24, 44, 74)
ACCENT = (247, 200, 70)      # жовтий
TEXT = (255, 255, 255)
MUTED = (160, 176, 200)

MONTHS = ["січня", "лютого", "березня", "квітня", "травня", "червня",
          "липня", "серпня", "вересня", "жовтня", "листопада", "грудня"]

EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF️‍⃣]+"
)


def _clean(text: str) -> str:
    text = EMOJI_RE.sub("", text or "")
    return re.sub(r"\s+", " ", text).strip()


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    lines, line = [], ""
    for word in text.split(" "):
        candidate = f"{line} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_width:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def _fit_title(draw, text: str, max_width: int, max_height: int):
    for size in range(76, 39, -4):
        font = ImageFont.truetype(FONT_TITLE, size)
        lines = _wrap(draw, text, font, max_width)
        line_h = int(size * 1.18)
        if len(lines) * line_h <= max_height:
            return font, lines, line_h
    font = ImageFont.truetype(FONT_TITLE, 40)
    lines = _wrap(draw, text, font, max_width)
    max_lines = max_height // 47
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(" ,.:;—-") + "…"
    return font, lines, 47


def make_card(title: str, source: str, channel_title: str, channel_link: str) -> bytes:
    img = Image.new("RGB", (W, H), BG_TOP)
    draw = ImageDraw.Draw(img)

    # вертикальний градієнт
    for y in range(H):
        t = y / (H - 1)
        color = tuple(int(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * t) for i in range(3))
        draw.line([(0, y), (W, y)], fill=color)

    # декоративна смуга справа зверху
    draw.polygon([(W - 260, 0), (W, 0), (W, 260)], fill=(30, 55, 92))

    # шапка: жовта плашка + назва каналу
    label_font = ImageFont.truetype(FONT_LABEL, 30)
    draw.rectangle([PAD, PAD, PAD + 14, PAD + 36], fill=ACCENT)
    draw.text((PAD + 30, PAD - 1), _clean(channel_title).upper(), font=label_font, fill=ACCENT)

    # заголовок
    top, bottom = PAD + 90, H - PAD - 70
    font, lines, line_h = _fit_title(draw, _clean(title), W - 2 * PAD - 30, bottom - top)
    block_h = len(lines) * line_h
    y = top + (bottom - top - block_h) // 2
    draw.rectangle([PAD, y + 8, PAD + 8, y + block_h - 14], fill=ACCENT)
    for line in lines:
        draw.text((PAD + 30, y), line, font=font, fill=TEXT)
        y += line_h

    # підвал: дата + джерело зліва, посилання справа
    small = ImageFont.truetype(FONT_SMALL, 26)
    now = datetime.now(ZoneInfo("Europe/Kyiv"))
    left = f"{now.day} {MONTHS[now.month - 1]} {now.year}"
    if source:
        left += f"  ·  {_clean(source)}"
    draw.text((PAD, H - PAD - 10), left, font=small, fill=MUTED)
    if channel_link:
        w = draw.textlength(channel_link, font=small)
        draw.text((W - PAD - w, H - PAD - 10), channel_link, font=small, fill=MUTED)

    out = io.BytesIO()
    img.save(out, format="JPEG", quality=92)
    return out.getvalue()
