# 🛩️ Fighter Pro Cloud Monitor v2.0

مراقب سحابي احترافي يعمل على GitHub Actions

## 📁 هيكل الملفات

```
├── main.py            ← نقطة الدخول الرئيسية
├── config.py          ← جميع الإعدادات في مكان واحد
├── stats_engine.py    ← محرك التحليل الإحصائي
├── notifier.py        ← إشعارات Telegram
├── requirements.txt   ← المكتبات المطلوبة
├── history.csv        ← سجل الجولات (يُنشأ تلقائياً)
├── monitor.log        ← سجل التشغيل (يُنشأ تلقائياً)
└── .github/
    └── workflows/
        └── main.yml   ← GitHub Actions Workflow
```

## ⚙️ إعداد Telegram (اختياري لكن موصى به)

1. ابحث عن `@BotFather` في Telegram → أنشئ bot جديد → احتفظ بـ **TOKEN**
2. ابحث عن `@userinfobot` → أرسل له أي رسالة → احتفظ بـ **CHAT_ID**
3. في GitHub Repo → **Settings → Secrets → Actions**:
   - أضف `TELEGRAM_BOT_TOKEN` = التوكن
   - أضف `TELEGRAM_CHAT_ID` = الـ Chat ID
4. في `config.py`: اجعل `TELEGRAM_ENABLED = True`

## 📊 خوارزمية نسبة الثقة

| العامل | الوزن | الوصف |
|--------|-------|-------|
| Streak الحالي | 30% | جولات منخفضة متتالية |
| نسبة الجولات المنخفضة | 25% | في آخر N جولة |
| مسافة EMA عن الهدف | 25% | momentum gap |
| نسبة الفوز التاريخية | 20% | win rate |

## 🔧 تخصيص الإعدادات

افتح `config.py` وعدّل:
- `TARGET_CASHOUT` — مضاعف السحب المستهدف
- `STREAK_THRESHOLD` — الـ Streak المطلوب للتنبيه
- `MIN_CONFIDENCE` — الحد الأدنى لنسبة الثقة
- `HISTORY_WINDOW` — عمق التحليل الإحصائي
