"""
╔══════════════════════════════════════════════════════════════╗
║     Fighter Pro Cloud Monitor v3.0 — GitHub Actions         ║
╚══════════════════════════════════════════════════════════════╝
"""

import csv, math, sys, time, logging, urllib.request, json, os
from datetime import datetime
from collections import deque
from pathlib import Path
from playwright.sync_api import sync_playwright

# ══════════════════════════════════════════════════════════════
#  ⚙️  إعدادات
# ══════════════════════════════════════════════════════════════
GAME_URL         = "https://fighter.onlyplaygames.net/?sid=5c6f09bf3cb52e1161d82e424fbaa27d067196d0607ee79a854f4fd854a8a38d096a9e688be09edb072177f9ad04e8577a933e14f8f40b51dde50d16e97f82ac&gid=104012504&api=api-eu.ig-onlyplay.net/pool_fviUB0kXDf/api&pid=1&launchedForPid=1&sn=jupiter&params=eyJzaWQiOiI1YzZmMDliZjNjYjUyZTExNjFkODJlNDI0ZmJhYTI3ZDA2NzE5NmQwNjA3ZWU3OWE4NTRmNGZkODU0YThhMzhkMDk2YTllNjg4YmUwOWVkYjA3MjE3N2Y5YWQwNGU4NTc3YTkzM2UxNGY4ZjQwYjUxZGRlNTBkMTZlOTdmODJhYyIsImdpZCI6IjEwNDAxMjUwNCIsImFwaSI6ImFwaS1ldS5pZy1vbmx5cGxheS5uZXRcL3Bvb2xfZnZpVUIwa1hEZlwvYXBpIiwicGlkIjoiMSIsImxhdW5jaGVkRm9yUGlkIjoiMSIsInNuIjoianVwaXRlciIsInVzZUxvd1F1YWxpdHlBc3NldHMiOiIwIn0="

TARGET_CASHOUT   = 2.50
LOW_MULTIPLIER   = 2.00
STREAK_THRESHOLD = 2
MIN_CONFIDENCE   = 30.0
HISTORY_WINDOW   = 50
EMA_PERIOD       = 10
PAGE_LOAD_WAIT   = 14
CRASH_WAIT       = 1.5
POLL_INTERVAL    = 0.4
CSV_FILE         = "history.csv"

# يقرأ من GitHub Secrets أو من القيمة المكتوبة مباشرة
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN",  "8545355234:AAEbz7wnMq8JWRKZFsJPs6Ai1EI1UQN9Dpo")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID",    "8114406682")

# ══════════════════════════════════════════════════════════════
#  📋  Logger — يظهر في GitHub Actions log
# ══════════════════════════════════════════════════════════════
logging.basicConfig(
    level    = logging.INFO,
    format   = "[%(asctime)s] %(message)s",
    datefmt  = "%H:%M:%S",
    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("monitor.log", encoding="utf-8"),
    ]
)
log = logging.getLogger()

# ══════════════════════════════════════════════════════════════
#  📊  محرك الإحصاء
# ══════════════════════════════════════════════════════════════
class Stats:
    def __init__(self):
        self.history  = deque(maxlen=HISTORY_WINDOW)
        self._ema     = None
        self.streak   = 0
        self.max_str  = 0
        self.total    = 0
        self.wins     = 0

    def add(self, v: float):
        self.history.append(v)
        self.total += 1
        k = 2 / (EMA_PERIOD + 1)
        self._ema = v if self._ema is None else v * k + self._ema * (1 - k)
        if v < LOW_MULTIPLIER:
            self.streak += 1
            self.max_str = max(self.max_str, self.streak)
        else:
            self.streak = 0
        if v >= TARGET_CASHOUT:
            self.wins += 1

    @property
    def ema(self):      return round(self._ema, 2) if self._ema else 0.0
    @property
    def sma(self):      return round(sum(self.history)/len(self.history), 2) if self.history else 0.0
    @property
    def win_rate(self): return round(self.wins / self.total * 100, 1) if self.total else 0.0
    @property
    def std_dev(self):
        if len(self.history) < 2: return 0.0
        avg = self.sma
        return round(math.sqrt(sum((x-avg)**2 for x in self.history)/len(self.history)), 2)

    def confidence(self) -> float:
        if not self.history: return 0.0
        s = min(self.streak / 4.0, 1.0) * 35
        r = sum(1 for x in self.history if x < LOW_MULTIPLIER) / len(self.history) * 30
        e = 0.0
        if self._ema and self._ema < TARGET_CASHOUT:
            e = min((TARGET_CASHOUT - self._ema) / TARGET_CASHOUT, 1.0) * 20
        h = (self.win_rate / 100) * 15
        return round(min(s + r + e + h, 99.9), 1)

# ══════════════════════════════════════════════════════════════
#  📱  Telegram
# ══════════════════════════════════════════════════════════════
def tg(msg: str) -> bool:
    try:
        url  = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = json.dumps({
            "chat_id":    TELEGRAM_CHAT_ID,
            "text":       msg,
            "parse_mode": "HTML"
        }).encode()
        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=8)
        return True
    except Exception as e:
        log.warning(f"[Telegram] فشل الإرسال: {e}")
        return False

# ══════════════════════════════════════════════════════════════
#  🔍  قراءة تاريخ الجولات من الصفحة
# ══════════════════════════════════════════════════════════════
HISTORY_SELS = [
    "#coefs_history .factor",
    ".coefs_history .factor",
    "[class*='history'] [class*='factor']",
    "[class*='history'] [class*='coef']",
    "[class*='coefficient']",
    ".round-history span",
    "[class*='rounds'] span",
    "[class*='history'] span",
]

def get_history(page) -> list:
    for sel in HISTORY_SELS:
        try:
            items = page.locator(sel).all()
            vals  = []
            for it in items:
                try:
                    t = it.inner_text(timeout=1500).strip()
                    v = float(
                        t.replace("×","").replace("x","")
                         .replace("X","").replace(",",".").strip()
                    )
                    if 1.0 <= v <= 50000:
                        vals.append(v)
                except:
                    continue
            if vals:
                return vals
        except:
            continue
    return []

# ══════════════════════════════════════════════════════════════
#  📄  CSV
# ══════════════════════════════════════════════════════════════
def init_csv():
    if not Path(CSV_FILE).exists() or Path(CSV_FILE).stat().st_size == 0:
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                "time", "round", "multiplier", "streak",
                "confidence%", "ema", "sma", "std_dev", "win_rate%", "signal"
            ])

def save_csv(rid, mult, stats: Stats, conf: float, signal: bool):
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            datetime.now().strftime("%H:%M:%S"),
            rid,
            f"x{mult:.2f}",
            stats.streak,
            f"{conf:.1f}%",
            f"x{stats.ema:.2f}",
            f"x{stats.sma:.2f}",
            f"+-{stats.std_dev:.2f}",
            f"{stats.win_rate}%",
            "SIGNAL" if signal else ""
        ])

# ══════════════════════════════════════════════════════════════
#  🚀  الحلقة الرئيسية
# ══════════════════════════════════════════════════════════════
def run():
    init_csv()
    stats = Stats()

    log.info("=" * 62)
    log.info("  Fighter Pro Cloud Monitor v3.0 - GitHub Actions")
    log.info(f"  Target: x{TARGET_CASHOUT}  Streak: {STREAK_THRESHOLD}  Conf: {MIN_CONFIDENCE}%")
    log.info("=" * 62)

    # رسالة بداية Telegram
    ok = tg(
        "✅ <b>Fighter Pro Monitor v3.0</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🟢 البوت شغال ومراقب!\n"
        f"🎯 هدف السحب: <b>×{TARGET_CASHOUT}</b>\n"
        f"🔁 Streak المطلوب: {STREAK_THRESHOLD} جولات منخفضة\n"
        f"📊 نسبة الثقة الدنيا: {MIN_CONFIDENCE}%"
    )
    log.info(f"[Telegram] {'OK - رسالة البداية اتبعتت' if ok else 'FAILED - تحقق من التوكن'}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless = True,
            args     = [
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--window-size=1280,720",
            ]
        )
        ctx = browser.new_context(
            viewport   = {"width": 1280, "height": 720},
            user_agent = (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = ctx.new_page()

        log.info("[Browser] جاري فتح اللعبة...")
        page.goto(GAME_URL, wait_until="domcontentloaded", timeout=30000)
        log.info(f"[Browser] انتظار {PAGE_LOAD_WAIT}s لتحميل اللعبة...")
        time.sleep(PAGE_LOAD_WAIT)
        log.info("[Browser] اللعبة محملة — بدأت المراقبة\n")

        last_crash = None
        round_id   = 0
        no_data    = 0

        while True:
            try:
                history = get_history(page)

                # ── لو مفيش بيانات ──────────────────────────────
                if not history:
                    no_data += 1
                    if no_data == 1:
                        log.warning("[!] لا توجد بيانات — اللعبة ربما لسه بتحمّل")
                    if no_data % 30 == 0:
                        log.warning(f"[!] {no_data} محاولة بدون بيانات — جاري الانتظار...")
                    time.sleep(POLL_INTERVAL)
                    continue

                no_data = 0
                latest  = history[-1]

                # ── جولة جديدة انتهت ────────────────────────────
                if latest != last_crash:
                    last_crash = latest
                    round_id  += 1

                    stats.add(latest)
                    conf   = stats.confidence()
                    is_sig = (stats.streak >= STREAK_THRESHOLD and conf >= MIN_CONFIDENCE)

                    # ─ سطر اللوق
                    flag = ">>> SIGNAL <<<" if is_sig else "           "
                    log.info(
                        f"{flag}  "
                        f"#{round_id:04d}  "
                        f"x{latest:.2f}  |  "
                        f"Streak:{stats.streak}  "
                        f"Conf:{conf:.1f}%  "
                        f"WR:{stats.win_rate}%  "
                        f"EMA:x{stats.ema:.2f}  "
                        f"SMA:x{stats.sma:.2f}"
                    )

                    # ─ تنبيه Telegram عند الإشارة
                    if is_sig:
                        log.info(
                            f"\n{'='*62}\n"
                            f"  >>> تنبيه دخول! <<<\n"
                            f"  خش الجيم الجاي واسحب عند x{TARGET_CASHOUT}\n"
                            f"  Streak: {stats.streak}  |  الثقة: {conf:.1f}%\n"
                            f"{'='*62}\n"
                        )
                        tg(
                            f"🔥 <b>تنبيه دخول!</b>\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"✅ خش <b>الجيم الجاي</b> واسحب عند <b>×{TARGET_CASHOUT}</b>\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"🔁 Streak: <b>{stats.streak}</b> جولات منخفضة متتالية\n"
                            f"📊 نسبة الثقة: <b>{conf:.1f}%</b>\n"
                            f"📉 آخر مضاعف: ×{latest:.2f}\n"
                            f"📈 EMA: ×{stats.ema:.2f}  |  SMA: ×{stats.sma:.2f}\n"
                            f"🏆 Win Rate: {stats.win_rate}%  |  جولة #{round_id}"
                        )

                    # ─ تقرير إحصائي كل 25 جولة
                    if round_id % 25 == 0:
                        tg(
                            f"📋 <b>تقرير إحصائي — جولة #{round_id}</b>\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"🔢 إجمالي الجولات: {stats.total}\n"
                            f"🏆 Win Rate: {stats.win_rate}%\n"
                            f"📈 EMA: ×{stats.ema:.2f}  |  SMA: ×{stats.sma:.2f}\n"
                            f"📉 انحراف معياري: ±{stats.std_dev:.2f}\n"
                            f"🔥 Streak الحالي: {stats.streak}\n"
                            f"📌 أعلى Streak: {stats.max_str}"
                        )

                    save_csv(round_id, latest, stats, conf, is_sig)
                    time.sleep(CRASH_WAIT)

                else:
                    time.sleep(POLL_INTERVAL)

            except KeyboardInterrupt:
                log.info("Stopped manually")
                break
            except Exception as e:
                log.error(f"[Error] {type(e).__name__}: {e}")
                time.sleep(2)

        browser.close()
        log.info("Browser closed.")


if __name__ == "__main__":
    run()
