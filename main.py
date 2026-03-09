"""
================================================================
  main.py — Fighter Pro Cloud Monitor v2.0
  المراقب الاحترافي للألعاب السحابية

  المميزات:
  ✅ State Machine كاملة (Betting → Flying → Crashed)
  ✅ تحليل إحصائي متقدم (EMA, SMA, StdDev, Confidence)
  ✅ تنبيهات Telegram فورية
  ✅ تسجيل احترافي بـ Logger
  ✅ CSV منظم مع headers
  ✅ نظام إعادة المحاولة عند الفشل
  ✅ Selectors متعددة مع Fallback
================================================================
"""

import csv
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from playwright.sync_api import sync_playwright, Page, Browser

# ── استيراد الوحدات المحلية ──────────────────────────────────────
from config import (
    GAME_URL, TARGET_CASHOUT, LOW_MULTIPLIER, STREAK_THRESHOLD,
    HISTORY_WINDOW, EMA_PERIOD, MIN_CONFIDENCE,
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_ENABLED,
    POLL_INTERVAL, CRASH_WAIT, PAGE_LOAD_WAIT,
    CSV_FILE, LOG_FILE, MAX_RETRIES
)
from stats_engine import StatsEngine
from notifier import TelegramNotifier

# ================================================================
#  إعداد Logger احترافي
# ================================================================
def setup_logger() -> logging.Logger:
    log = logging.getLogger("FighterMonitor")
    log.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )
    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    log.addHandler(ch)
    # File handler
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    log.addHandler(fh)
    return log

logger = setup_logger()

# ================================================================
#  إعداد CSV مع Headers
# ================================================================
def init_csv() -> None:
    """يُنشئ CSV مع headers إذا لم يكن موجوداً"""
    if not Path(CSV_FILE).exists() or Path(CSV_FILE).stat().st_size == 0:
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp", "round_id", "last_multiplier",
                "streak", "confidence_pct", "ema", "sma",
                "std_dev", "win_rate_pct", "alert", "note"
            ])
        logger.info(f"[CSV] تم إنشاء {CSV_FILE} بـ headers")

def append_csv(row: dict) -> None:
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        writer.writerow(row)

# ================================================================
#  State Machine للعبة
# ================================================================
class GameState:
    UNKNOWN  = "UNKNOWN"
    BETTING  = "BETTING"   # فترة الرهان
    FLYING   = "FLYING"    # اللعبة تطير — المضاعف يرتفع
    CRASHED  = "CRASHED"   # انتهت الجولة

# ================================================================
#  Selector Engine — يجرب أكثر من محدد CSS مع Fallback
# ================================================================
COUNTER_SELECTORS = [
    "#counter",
    ".counter",
    "[class*='multiplier']",
    "[class*='counter']",
    "[data-testid='multiplier']",
    ".game-multiplier",
    "canvas",   # بعض الألعاب تعرض المضاعف على Canvas
]

HISTORY_SELECTORS = [
    "#coefs_history .factor",
    ".coefs_history .factor",
    "[class*='history'] [class*='factor']",
    "[class*='history'] [class*='coef']",
    "[class*='rounds'] [class*='mult']",
    ".round-history span",
    "[class*='coefficient']",
]

def try_get_text(page: Page, selectors: list, timeout: int = 2000) -> Optional[str]:
    """يجرب كل Selector ويُرجع أول نتيجة صالحة"""
    for sel in selectors:
        try:
            el = page.locator(sel).first
            text = el.inner_text(timeout=timeout).strip()
            if text:
                return text
        except Exception:
            continue
    return None

def try_get_all_texts(page: Page, selectors: list, timeout: int = 2000) -> list[str]:
    """يُرجع قائمة نصوص من أول Selector يعمل"""
    for sel in selectors:
        try:
            items = page.locator(sel).all()
            texts = []
            for item in items:
                try:
                    t = item.inner_text(timeout=timeout).strip()
                    if t:
                        texts.append(t)
                except Exception:
                    continue
            if texts:
                return texts
        except Exception:
            continue
    return []

def parse_multiplier(text: str) -> Optional[float]:
    """يحول نص المضاعف إلى float بأمان"""
    if not text:
        return None
    cleaned = (
        text.replace("×", "").replace("x", "").replace("X", "")
            .replace(",", ".").strip()
    )
    try:
        val = float(cleaned)
        return val if 1.0 <= val <= 10000.0 else None
    except ValueError:
        return None

# ================================================================
#  دالة الجلسة الرئيسية
# ================================================================
def run_session(page: Page, stats: StatsEngine, notifier: TelegramNotifier) -> None:
    """
    الحلقة الرئيسية للمراقبة
    تنتظر انتهاء كل جولة، تسجل النتيجة، وتحلل الأنماط
    """
    round_id    = 0
    last_crash  = None  # آخر مضاعف سقوط مسجل
    state       = GameState.UNKNOWN
    stats_every = 20    # إرسال تقرير إحصائي كل N جولة

    logger.info("▶  بدأت حلقة المراقبة الرئيسية")

    while True:
        try:
            # ── 1. قراءة المضاعف الحالي ─────────────────────────
            counter_text = try_get_text(page, COUNTER_SELECTORS)
            current_mult = parse_multiplier(counter_text) if counter_text else None

            # ── 2. قراءة تاريخ الجولات ───────────────────────────
            history_texts = try_get_all_texts(page, HISTORY_SELECTORS)
            history_vals  = []
            for t in history_texts:
                v = parse_multiplier(t)
                if v:
                    history_vals.append(v)

            # ── 3. تحديد آخر نتيجة جولة منتهية ──────────────────
            latest_crash = history_vals[-1] if history_vals else None

            # ── 4. State Detection ───────────────────────────────
            if current_mult and current_mult > 1.0:
                state = GameState.FLYING
            elif latest_crash and latest_crash != last_crash:
                state = GameState.CRASHED
            else:
                state = GameState.BETTING

            # ── 5. معالجة الجولة المنتهية ────────────────────────
            if state == GameState.CRASHED and latest_crash != last_crash:
                last_crash = latest_crash
                round_id  += 1

                stats.add(latest_crash, LOW_MULTIPLIER, TARGET_CASHOUT)
                confidence = stats.confidence_score(LOW_MULTIPLIER, TARGET_CASHOUT)
                report     = stats.report()
                timestamp  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # ── تحديد التنبيه ─────────────────────────────────
                alert = ""
                is_signal = (
                    stats.streak   >= STREAK_THRESHOLD and
                    confidence     >= MIN_CONFIDENCE
                )

                if is_signal:
                    alert = f"🔥 SIGNAL | Confidence: {confidence:.1f}% | Streak: {stats.streak}"
                    logger.warning(
                        f"\n{'='*65}\n"
                        f"  🔥 تنبيه دخول! الثقة: {confidence:.1f}% | Streak: {stats.streak}\n"
                        f"  آخر مضاعف: ×{latest_crash:.2f} | هدف: ×{TARGET_CASHOUT}\n"
                        f"  EMA: {report['ema']} | SMA: {report['sma']}\n"
                        f"{'='*65}\n"
                    )
                    notifier.send_alert(
                        confidence = confidence,
                        streak     = stats.streak,
                        last_mult  = latest_crash,
                        target     = TARGET_CASHOUT,
                        win_rate   = float(report['win_rate'].replace('%','')),
                        ema        = report['ema'],
                        sma        = report['sma'],
                    )
                else:
                    logger.info(
                        f"[#{round_id:04d}] ×{latest_crash:.2f} | "
                        f"Streak:{stats.streak} | "
                        f"Conf:{confidence:.1f}% | "
                        f"WinRate:{report['win_rate']} | "
                        f"EMA:{report['ema']}"
                    )

                # ── حفظ في CSV ────────────────────────────────────
                append_csv({
                    "timestamp"     : timestamp,
                    "round_id"      : round_id,
                    "last_multiplier": f"×{latest_crash:.2f}",
                    "streak"        : stats.streak,
                    "confidence_pct": f"{confidence:.2f}%",
                    "ema"           : report['ema'],
                    "sma"           : report['sma'],
                    "std_dev"       : report['std_dev'],
                    "win_rate_pct"  : report['win_rate'],
                    "alert"         : alert,
                    "note"          : GameState.CRASHED,
                })

                # ── تقرير إحصائي دوري ─────────────────────────────
                if round_id % stats_every == 0:
                    notifier.send_stats(report)
                    logger.info(f"[STATS] {report}")

                time.sleep(CRASH_WAIT)

            else:
                # اللعبة قيد الطيران أو الانتظار
                time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            logger.info("⛔ تم إيقاف المراقب يدوياً")
            break
        except Exception as e:
            logger.error(f"[خطأ] {type(e).__name__}: {e}")
            time.sleep(CRASH_WAIT)

# ================================================================
#  نقطة الدخول الرئيسية
# ================================================================
def main() -> None:
    logger.info("=" * 65)
    logger.info("  🚀 Fighter Pro Cloud Monitor v2.0 — بدأ العمل")
    logger.info(f"  هدف: ×{TARGET_CASHOUT} | Streak: {STREAK_THRESHOLD} | ثقة: {MIN_CONFIDENCE}%")
    logger.info("=" * 65)

    init_csv()

    stats    = StatsEngine(window=HISTORY_WINDOW, ema_period=EMA_PERIOD)
    notifier = TelegramNotifier(
        token   = TELEGRAM_BOT_TOKEN,
        chat_id = TELEGRAM_CHAT_ID,
        enabled = TELEGRAM_ENABLED,
    )

    # ── اختبار Telegram فوراً عند البدء ─────────────────────────
    if TELEGRAM_ENABLED:
        ok = notifier.send(
            "✅ <b>Fighter Pro Monitor v2.0</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🟢 البوت شغال وبيراقب!\n"
            f"🎯 هدف: ×{TARGET_CASHOUT} | Streak: {STREAK_THRESHOLD} | ثقة: {MIN_CONFIDENCE}%"
        )
        if ok:
            logger.info("[Telegram] ✅ رسالة الاختبار اتبعتت بنجاح")
        else:
            logger.warning("[Telegram] ❌ فشل إرسال رسالة الاختبار — تحقق من التوكن والـ Chat ID")

    retries = 0
    while retries < MAX_RETRIES:
        try:
            with sync_playwright() as p:
                browser: Browser = p.chromium.launch(
                    headless = True,
                    args     = [
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--window-size=1280,720",
                    ]
                )
                context = browser.new_context(
                    viewport         = {"width": 1280, "height": 720},
                    user_agent       = (
                        "Mozilla/5.0 (X11; Linux x86_64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    locale           = "en-US",
                    timezone_id      = "Africa/Cairo",
                )
                page = context.new_page()

                logger.info(f"[Browser] جاري تحميل الصفحة...")
                page.goto(GAME_URL, wait_until="domcontentloaded", timeout=30000)
                time.sleep(PAGE_LOAD_WAIT)
                logger.info("[Browser] ✅ الصفحة محملة — بدأ المراقبة")

                retries = 0   # إعادة تعيين العداد عند النجاح
                run_session(page, stats, notifier)
                browser.close()

        except KeyboardInterrupt:
            logger.info("⛔ إيقاف يدوي")
            sys.exit(0)

        except Exception as e:
            retries += 1
            logger.error(f"[خطأ حرج] المحاولة {retries}/{MAX_RETRIES}: {e}")
            if retries < MAX_RETRIES:
                wait_time = retries * 10
                logger.info(f"⏳ إعادة الاتصال خلال {wait_time}s ...")
                time.sleep(wait_time)
            else:
                logger.critical("❌ استُنفدت جميع محاولات إعادة الاتصال. إيقاف.")
                sys.exit(1)


if __name__ == "__main__":
    main()
