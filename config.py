# ================================================================
#         Fighter Pro Cloud Monitor — Configuration
#         الإصدار 2.0 | احترافي ودقيق
# ================================================================

# ── إعدادات اللعبة ─────────────────────────────────────────────
GAME_URL = "https://fighter.onlyplaygames.net/?sid=5c6f09bf3cb52e1161d82e424fbaa27d067196d0607ee79a854f4fd854a8a38d096a9e688be09edb072177f9ad04e8577a933e14f8f40b51dde50d16e97f82ac&gid=104012504&api=api-eu.ig-onlyplay.net/pool_fviUB0kXDf/api&pid=1&launchedForPid=1&sn=jupiter&params=eyJzaWQiOiI1YzZmMDliZjNjYjUyZTExNjFkODJlNDI0ZmJhYTI3ZDA2NzE5NmQwNjA3ZWU3OWE4NTRmNGZkODU0YThhMzhkMDk2YTllNjg4YmUwOWVkYjA3MjE3N2Y5YWQwNGU4NTc3YTkzM2UxNGY4ZjQwYjUxZGRlNTBkMTZlOTdmODJhYyIsImdpZCI6IjEwNDAxMjUwNCIsImFwaSI6ImFwaS1ldS5pZy1vbmx5cGxheS5uZXRcL3Bvb2xfZnZpVUIwa1hEZlwvYXBpIiwicGlkIjoiMSIsImxhdW5jaGVkRm9yUGlkIjoiMSIsInNuIjoianVwaXRlciIsInVzZUxvd1F1YWxpdHlBc3NldHMiOiIwIn0="

# ── إعدادات الاستراتيجية ────────────────────────────────────────
TARGET_CASHOUT       = 2.50   # المضاعف المستهدف للسحب
LOW_MULTIPLIER       = 2.00   # حد المضاعف المنخفض لتفعيل الـ Streak
STREAK_THRESHOLD     = 2      # عدد الجولات المنخفضة المتتالية لإصدار تنبيه
HISTORY_WINDOW       = 50     # عدد الجولات المستخدمة في التحليل الإحصائي
EMA_PERIOD           = 10     # فترة المتوسط المتحرك الأسي
MIN_CONFIDENCE       = 35.0   # الحد الأدنى لنسبة الثقة لإصدار تنبيه (%)
CONSECUTIVE_LOWS_WIN = 3      # جولات منخفضة متتالية مطلوبة لتأهيل التنبيه

# ── إعدادات Telegram ────────────────────────────────────────────
# احصل على BOT_TOKEN من @BotFather و CHAT_ID من @userinfobot
TELEGRAM_BOT_TOKEN   = "8545355234:AAEbz7wnMq8JWRKZFsJPs6Ai1EI1UQN9Dpo"
TELEGRAM_CHAT_ID     = "8114406682"
TELEGRAM_ENABLED     = True

# ── إعدادات النظام ──────────────────────────────────────────────
POLL_INTERVAL        = 0.5    # ثانية بين كل قراءة أثناء الطيران
CRASH_WAIT           = 2.0    # انتظار بعد كل جولة
PAGE_LOAD_WAIT       = 12     # انتظار تحميل الصفحة
CSV_FILE             = "history.csv"
LOG_FILE             = "monitor.log"
MAX_RETRIES          = 5      # محاولات إعادة الاتصال عند الخطأ
