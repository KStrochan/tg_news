"""Ставить assets/avatar.jpg аватаркою каналу через бота (боту потрібне право «Змінювати профіль каналу»)."""
import os
import sys

import requests

from config import config

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "avatar.jpg")
url = f"https://api.telegram.org/bot{config.telegram_bot_token}/setChatPhoto"

with open(path, "rb") as f:
    resp = requests.post(url, data={"chat_id": config.telegram_channel_id}, files={"photo": f}, timeout=60)

print(resp.status_code, resp.text)
sys.exit(0 if resp.ok else 1)
