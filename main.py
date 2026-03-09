import time
import csv
from datetime import datetime
from playwright.sync_api import sync_playwright

# ================== إعدادات احترافية ==================
GAME_URL = "https://fighter.onlyplaygames.net/?sid=5c6f09bf3cb52e1161d82e424fbaa27d067196d0607ee79a854f4fd854a8a38d096a9e688be09edb072177f9ad04e8577a933e14f8f40b51dde50d16e97f82ac&gid=104012504&api=api-eu.ig-onlyplay.net/pool_fviUB0kXDf/api&pid=1&launchedForPid=1&sn=jupiter&params=eyJzaWQiOiI1YzZmMDliZjNjYjUyZTExNjFkODJlNDI0ZmJhYTI3ZDA2NzE5NmQwNjA3ZWU3OWE4NTRmNGZkODU0YThhMzhkMDk2YTllNjg4YmUwOWVkYjA3MjE3N2Y5YWQwNGU4NTc3YTkzM2UxNGY4ZjQwYjUxZGRlNTBkMTZlOTdmODJhYyIsImdpZCI6IjEwNDAxMjUwNCIsImFwaSI6ImFwaS1ldS5pZy1vbmx5cGxheS5uZXRcL3Bvb2xfZnZpVUIwa1hEZlwvYXBpIiwicGlkIjoiMSIsImxhdW5jaGVkRm9yUGlkIjoiMSIsInNuIjoianVwaXRlciIsInVzZUxvd1F1YWxpdHlBc3NldHMiOiIwIn0="
TARGET_CASHOUT = 2.50
STREAK_THRESHOLD = 3
LOW_MULTIPLIER = 2.00
# ====================================================

print("🚀 Fighter Pro Cloud Monitor بدأ العمل")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(GAME_URL)
    time.sleep(10)

    streak = 0
    total = 0
    success = 0

    while True:
        try:
            counter = page.locator("#counter").inner_text(timeout=3000)
            current_mult = float(counter.replace("×", "").strip())

            factors = page.locator("#coefs_history .factor").all()
            last_mult = float(factors[-1].inner_text().replace("×", "").strip())

            timestamp = datetime.now().strftime("%H:%M:%S")

            # حساب Streak
            if last_mult < LOW_MULTIPLIER:
                streak += 1
            else:
                streak = 0

            # كشف الجيم المناسب
            alert = ""
            if streak >= STREAK_THRESHOLD:
                alert = f"🔥 جيم مناسب! ادخل واسحب عند ×{TARGET_CASHOUT}"
                print(f"\n{'='*60}\n{alert}\nMultiplier: ×{last_mult:.2f} | Time: {timestamp}\n{'='*60}\n")

            # حساب نسبة النجاح
            total += 1
            if last_mult >= TARGET_CASHOUT:
                success += 1
            win_rate = round((success / total) * 100, 2)

            # حفظ في CSV
            with open("history.csv", "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, f"×{last_mult:.2f}", streak, alert, f"{win_rate}%"])

            time.sleep(0.40)   # دقة فائقة

        except Exception as e:
            time.sleep(1)
