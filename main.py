import time
import csv
import os
from datetime import datetime
from playwright.sync_api import sync_playwright
import requests

# ================== إعدادات ==================
GAME_URL = "https://1xbet.com/ar/allgamesentrance/crash"
TARGET_CASHOUT = 2.50
STREAK_THRESHOLD = 3
LOW_MULTIPLIER = 2.00
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
# ===========================================

def send_telegram(message):
    if TELEGRAM_TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"})

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(GAME_URL)
    time.sleep(8)  # انتظار تحميل اللعبة

    streak = 0
    total = 0
    success = 0

    while True:
        try:
            counter = page.locator("#counter").inner_text(timeout=3000)
            mult = float(counter.replace("×", "").strip())

            factors = page.locator("#coefs_history .factor").all()
            last_mult = float(factors[-1].inner_text().replace("×", "").strip())

            timestamp = datetime.now().strftime("%H:%M:%S")

            if last_mult < LOW_MULTIPLIER:
                streak += 1
            else:
                streak = 0

            action = ""
            if streak >= STREAK_THRESHOLD:
                action = f"🔥 جيم مناسب! ادخل واسحب عند ×{TARGET_CASHOUT}"
                send_telegram(f"<b>🚨 Fighter Alert!</b>\n{action}\nMultiplier: ×{last_mult:.2f}\nTime: {timestamp}")

            total += 1
            if last_mult >= TARGET_CASHOUT:
                success += 1
            win_rate = round((success / total) * 100, 2)

            # حفظ في CSV
            with open("history.csv", "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, f"×{last_mult:.2f}", streak, action, f"{win_rate}%"])

            time.sleep(0.45)  # دقة عالية جداً

        except:
            time.sleep(1)
