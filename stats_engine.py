"""
================================================================
  stats_engine.py — محرك التحليل الإحصائي الاحترافي
  Fighter Pro Cloud Monitor v2.0
================================================================
"""

import math
from collections import deque
from typing import Optional


class StatsEngine:
    """
    محرك إحصائي متكامل يحسب:
    - المتوسط المتحرك البسيط (SMA) والأسي (EMA)
    - الانحراف المعياري والتباين
    - نسبة الثقة للتنبؤ بجولة مرتفعة
    - تحليل Streak متقدم
    - نسبة الفوز التراكمية
    """

    def __init__(self, window: int = 50, ema_period: int = 10):
        self.window      = window
        self.ema_period  = ema_period
        self.history     = deque(maxlen=window)   # آخر N نتيجة
        self.all_history = []                      # كل النتائج للإحصاء الكامل
        self._ema        = None
        self.streak      = 0          # جولات منخفضة متتالية حالية
        self.max_streak  = 0          # أعلى Streak مسجل
        self.total       = 0
        self.wins        = 0          # جولات تجاوزت TARGET_CASHOUT
        self.low_count   = 0          # إجمالي الجولات المنخفضة

    # ── إضافة نتيجة جديدة ────────────────────────────────────────
    def add(self, multiplier: float, low_threshold: float, target: float) -> None:
        self.history.append(multiplier)
        self.all_history.append(multiplier)
        self.total += 1

        # تحديث EMA
        k = 2 / (self.ema_period + 1)
        if self._ema is None:
            self._ema = multiplier
        else:
            self._ema = multiplier * k + self._ema * (1 - k)

        # تحديث Streak
        if multiplier < low_threshold:
            self.streak += 1
            self.low_count += 1
            self.max_streak = max(self.max_streak, self.streak)
        else:
            self.streak = 0

        # تحديث نسبة الفوز
        if multiplier >= target:
            self.wins += 1

    # ── المتوسط المتحرك البسيط ───────────────────────────────────
    @property
    def sma(self) -> Optional[float]:
        if not self.history:
            return None
        return sum(self.history) / len(self.history)

    # ── المتوسط المتحرك الأسي ────────────────────────────────────
    @property
    def ema(self) -> Optional[float]:
        return round(self._ema, 4) if self._ema else None

    # ── الانحراف المعياري ────────────────────────────────────────
    @property
    def std_dev(self) -> Optional[float]:
        if len(self.history) < 2:
            return None
        avg = self.sma
        variance = sum((x - avg) ** 2 for x in self.history) / len(self.history)
        return round(math.sqrt(variance), 4)

    # ── نسبة الفوز ───────────────────────────────────────────────
    @property
    def win_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return round((self.wins / self.total) * 100, 2)

    # ── حساب نسبة الثقة للتنبؤ ───────────────────────────────────
    def confidence_score(self, low_threshold: float, target: float) -> float:
        """
        خوارزمية نسبة الثقة المركبة:
        تجمع بين:
        1. نسبة الجولات المنخفضة في التاريخ الحديث (Streak probability)
        2. المسافة بين EMA و TARGET (momentum gap)
        3. الانحراف المعياري (volatility factor)
        4. نسبة الفوز التاريخية
        """
        if len(self.history) < 2:
            return 0.0

        # ─ عامل 1: الـ Streak الحالي
        streak_factor = min(self.streak / 5.0, 1.0) * 30  # max 30 points

        # ─ عامل 2: نسبة الجولات المنخفضة في آخر N جولة
        recent_lows = sum(1 for x in self.history if x < low_threshold)
        low_ratio = recent_lows / len(self.history)
        low_factor = low_ratio * 25  # max 25 points

        # ─ عامل 3: EMA مقابل TARGET
        if self._ema and self._ema < target:
            gap = target - self._ema
            ema_factor = min(gap / target, 1.0) * 25  # max 25 points
        else:
            ema_factor = 0.0

        # ─ عامل 4: نسبة الفوز التاريخية
        historical_factor = (self.win_rate / 100) * 20  # max 20 points

        total_score = streak_factor + low_factor + ema_factor + historical_factor
        return round(min(total_score, 99.9), 2)

    # ── تقرير إحصائي كامل ────────────────────────────────────────
    def report(self) -> dict:
        return {
            "total_rounds"  : self.total,
            "win_rate"      : f"{self.win_rate}%",
            "sma"           : f"×{self.sma:.2f}" if self.sma else "N/A",
            "ema"           : f"×{self.ema:.2f}" if self.ema else "N/A",
            "std_dev"       : f"±{self.std_dev:.2f}" if self.std_dev else "N/A",
            "current_streak": self.streak,
            "max_streak"    : self.max_streak,
            "low_count"     : self.low_count,
        }
