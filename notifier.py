"""
================================================================
  notifier.py — نظام الإشعارات الفوري عبر Telegram
  Fighter Pro Cloud Monitor v2.0
================================================================
"""

import urllib.request
import urllib.parse
import json
import logging

logger = logging.getLogger("FighterMonitor")


class TelegramNotifier:
    """
    يرسل تنبيهات فورية عبر Telegram Bot API
    يستخدم urllib المدمج بدون dependencies إضافية
    """

    def __init__(self, token: str, chat_id: str, enabled: bool = True):
        self.token   = token
        self.chat_id = chat_id
        self.enabled = enabled and bool(token) and bool(chat_id)
        self.base_url = f"https://api.telegram.org/bot{token}/sendMessage"

    def send(self, message: str, parse_mode: str = "HTML") -> bool:
        """إرسال رسالة — يُرجع True عند النجاح"""
        if not self.enabled:
            return False
        try:
            payload = json.dumps({
                "chat_id"    : self.chat_id,
                "text"       : message,
                "parse_mode" : parse_mode,
            }).encode("utf-8")
            req = urllib.request.Request(
                self.base_url,
                data    = payload,
                headers = {"Content-Type": "application/json"},
                method  = "POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read())
                return result.get("ok", False)
        except Exception as e:
            logger.warning(f"[Telegram] فشل الإرسال: {e}")
            return False

    def send_alert(self, confidence: float, streak: int, last_mult: float,
                   target: float, win_rate: float, ema: str, sma: str) -> bool:
        """رسالة تنبيه منسقة"""
        msg = (
            f"🚨 <b>Fighter Pro — تنبيه دخول</b>\n"
            f"{'─' * 30}\n"
            f"🔥 <b>Streak:</b> {streak} جولات منخفضة متتالية\n"
            f"📊 <b>آخر مضاعف:</b> ×{last_mult:.2f}\n"
            f"🎯 <b>هدف السحب:</b> ×{target:.2f}\n"
            f"💡 <b>نسبة الثقة:</b> {confidence:.1f}%\n"
            f"📈 <b>EMA:</b> {ema} | <b>SMA:</b> {sma}\n"
            f"🏆 <b>معدل الفوز:</b> {win_rate}%\n"
            f"{'─' * 30}\n"
            f"⚡ <i>ادخل واسحب عند ×{target:.2f}</i>"
        )
        return self.send(msg)

    def send_stats(self, report: dict) -> bool:
        """إرسال تقرير إحصائي دوري"""
        msg = (
            f"📋 <b>Fighter Pro — تقرير إحصائي</b>\n"
            f"{'─' * 30}\n"
            f"🔢 إجمالي الجولات: {report['total_rounds']}\n"
            f"🏆 معدل الفوز: {report['win_rate']}\n"
            f"📈 EMA: {report['ema']} | SMA: {report['sma']}\n"
            f"📉 انحراف معياري: {report['std_dev']}\n"
            f"🔥 Streak الحالي: {report['current_streak']}\n"
            f"📌 أعلى Streak: {report['max_streak']}\n"
        )
        return self.send(msg)
