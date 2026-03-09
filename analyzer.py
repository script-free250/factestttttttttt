import os
import json
import statistics
from collections import Counter

# --- ثوابت وإعدادات ---
DATA_FILE = 'crash_history.json'  # اسم ملف تخزين البيانات
STABLE_THRESHOLD = 1.9  # معامل الانهيار الذي نعتبره "منخفضًا" أو "آمنًا"
VOLATILE_THRESHOLD = 10.0 # معامل الانهيار الذي نعتبره "مرتفعًا" أو "متقلبًا"

# --- دوال الواجهة والطباعة ---

def print_header(title):
    """يطبع رأسًا منسقًا للقسم."""
    print("\n" + "="*40)
    print(f"    {title}")
    print("="*40)

def print_analysis_item(label, value):
    """يطبع عنصر تحليل بشكل منسق."""
    print(f"{label:<25}: {value}")

# --- دوال التعامل مع البيانات ---

def load_game_history():
    """
    يقوم بتحميل سجل نتائج اللعبة من ملف JSON.
    إذا لم يكن الملف موجودًا، يقوم بإنشائه وإرجاع قائمة فارغة.
    """
    if not os.path.exists(DATA_FILE):
        print(f"INFO: ملف البيانات '{DATA_FILE}' غير موجود. سيتم إنشاء ملف جديد.")
        return []
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            # التأكد من أن البيانات هي قائمة من الأرقام
            if isinstance(data, list) and all(isinstance(x, (int, float)) for x in data):
                return data
            else:
                print("WARNING: ملف البيانات تالف أو بتنسيق غير صحيح. سيتم البدء من جديد.")
                return []
    except (json.JSONDecodeError, IOError) as e:
        print(f"ERROR: خطأ في قراءة ملف البيانات: {e}. سيتم البدء بسجل فارغ.")
        return []

def save_game_history(history):
    """
    يقوم بحفظ سجل نتائج اللعبة المحدث في ملف JSON.
    """
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(history, f, indent=4)
        return True
    except IOError as e:
        print(f"ERROR: خطأ في حفظ ملف البيانات: {e}")
        return False

# --- دوال التحليل المتقدم ---

def analyze_streaks(history, threshold):
    """
    يحلل تكرار حدوث قيم متتالية تحت حد معين.
    """
    if not history:
        return 0, 0
    
    max_streak = 0
    current_streak = 0
    for value in history:
        if value < threshold:
            current_streak += 1
        else:
            if current_streak > max_streak:
                max_streak = current_streak
            current_streak = 0
    # التحقق مرة أخرى في النهاية
    if current_streak > max_streak:
        max_streak = current_streak

    # حساب السلسلة الحالية
    current_low_streak = 0
    for value in reversed(history):
        if value < threshold:
            current_low_streak += 1
        else:
            break
            
    return max_streak, current_low_streak

def analyze_moving_averages(history):
    """
    يحسب المتوسطات المتحركة القصيرة والطويلة الأجل.
    """
    if len(history) < 50:
        return None, None # لا توجد بيانات كافية للمتوسطات المتحركة
        
    short_term_ma = statistics.mean(history[-20:]) # متوسط آخر 20 جولة
    long_term_ma = statistics.mean(history[-50:]) # متوسط آخر 50 جولة
    return short_term_ma, long_term_ma

def advanced_analysis(history):
    """
    يقوم بإجراء تحليل إحصائي متقدم ويعرض النتائج.
    """
    print_header("التحليل الإحصائي المتقدم")
    if len(history) < 10:
        print("لا توجد بيانات كافية للتحليل (10 جولات على الأقل مطلوبة).")
        return

    numeric_history = [x for x in history if isinstance(x, (int, float))]

    print_analysis_item("إجمالي الجولات المسجلة", len(numeric_history))
    print_analysis_item("أعلى معامل مسجل", f"{max(numeric_history):.2f}x")
    print_analysis_item("أقل معامل مسجل", f"{min(numeric_history):.2f}x")
    print_analysis_item("المتوسط العام", f"{statistics.mean(numeric_history):.2f}x")
    print_analysis_item("الوسيط", f"{statistics.median(numeric_history):.2f}x")

    crashes_under_threshold = sum(1 for x in numeric_history if x < STABLE_THRESHOLD)
    print_analysis_item(f"الانهيارات تحت {STABLE_THRESHOLD}x", f"{crashes_under_threshold} ({crashes_under_threshold / len(numeric_history):.2%})")

    # تحليل السلاسل (Streaks)
    max_streak, current_streak = analyze_streaks(history, STABLE_THRESHOLD)
    print_analysis_item(f"أطول سلسلة انهيارات < {STABLE_THRESHOLD}x", f"{max_streak} جولات")
    print_analysis_item(f"السلسلة الحالية < {STABLE_THRESHOLD}x", f"{current_streak} جولات")

    # تحليل المتوسطات المتحركة
    short_ma, long_ma = analyze_moving_averages(history)
    if short_ma is not None:
        print("\n--- تحليل الاتجاه (يتطلب 50 جولة على الأقل) ---")
        print_analysis_item("متوسط قصير الأجل (20 جولة)", f"{short_ma:.2f}x")
        print_analysis_item("متوسط طويل الأجل (50 جولة)", f"{long_ma:.2f}x")
        if short_ma > long_ma:
            print("الاتجاه الحالي: يميل إلى الارتفاع (المتوسط القصير أعلى من الطويل).")
        else:
            print("الاتجاه الحالي: يميل إلى الانخفاض (المتوسط القصير أقل من الطويل).")


def make_prediction(history):
    """
    يقوم بإنشاء توقع أكثر دقة بناءً على التحليلات المتقدمة.
    """
    print_header("محرك التوقع")
    if len(history) < 20:
        print("نحتاج إلى 20 جولة على الأقل لتقديم توقع ذي معنى.")
        return

    max_streak, current_streak = analyze_streaks(history, STABLE_THRESHOLD)
    short_ma, long_ma = analyze_moving_averages(history)

    confidence = 0
    reasons = []

    # منطق 1: الاقتراب من أطول سلسلة انهيارات منخفضة
    if current_streak > 0 and max_streak > 0:
        # إذا كانت السلسلة الحالية قريبة من أو تجاوزت أطول سلسلة مسجلة، تزداد احتمالية كسرها
        if current_streak >= max_streak * 0.8:
            confidence += 40
            reasons.append(f"السلسلة الحالية من الانهيارات المنخفضة ({current_streak}) تقترب من أطول سلسلة مسجلة ({max_streak}).")

    # منطق 2: تقاطع المتوسطات المتحركة
    if short_ma and long_ma:
        if short_ma > long_ma and history[-1] < STABLE_THRESHOLD:
            confidence += 25
            reasons.append("الاتجاه العام يميل للارتفاع، والجولة الأخيرة كانت منخفضة.")

    # منطق 3: جولات مرتفعة متتالية
    if all(game > VOLATILE_THRESHOLD for game in history[-2:]):
        confidence -= 50 # ثقة سلبية (توقع بالانخفاض)
        reasons.append("حدث انهياران مرتفعان جدًا بشكل متتالي، مما يزيد احتمالية التصحيح (انهيار منخفض).")
    
    # عرض النتيجة
    if confidence > 30:
        print(f"التوقع: احتمالية مرتفعة (بثقة {confidence}%) لمعامل انهيار **أعلى من {STABLE_THRESHOLD}x**.")
    elif confidence < -30:
         print(f"التوقع: احتمالية مرتفعة (بثقة {-confidence}%) لمعامل انهيار **أقل من {STABLE_THRESHOLD}x**.")
    else:
        print("لا توجد إشارة واضحة حاليًا. يفضل الانتظار أو اللعب بحذر.")

    if reasons:
        print("\nالأسباب:")
        for reason in reasons:
            print(f"- {reason}")


def main_menu():
    """
    يعرض القائمة الرئيسية ويتعامل مع مدخلات المستخدم.
    """
    history = load_game_history()

    while True:
        print_header("القائمة الرئيسية")
        print("1. إضافة نتيجة جولة جديدة")
        print("2. عرض التحليل المتقدم للبيانات")
        print("3. تشغيل محرك التوقع")
        print("4. مسح جميع البيانات")
        print("5. خروج")

        choice = input("اختر رقمًا: ")

        if choice == '1':
            while True:
                try:
                    new_result_str = input("أدخل معامل الانهيار (أو 'رجوع'): ")
                    if new_result_str.lower() == 'رجوع':
                        break
                    new_result = float(new_result_str)
                    if new_result < 1.0:
                        print("ERROR: معامل الانهيار يجب أن يكون 1.0 أو أعلى.")
                        continue
                    history.append(new_result)
                    if save_game_history(history):
                        print(f"SUCCESS: تمت إضافة {new_result:.2f}x. إجمالي الجولات: {len(history)}.")
                except ValueError:
                    print("ERROR: إدخال غير صالح. الرجاء إدخال رقم (مثل 1.54).")
        
        elif choice == '2':
            advanced_analysis(history)

        elif choice == '3':
            make_prediction(history)

        elif choice == '4':
            confirm = input("تحذير: هذا سيحذف كل البيانات المسجلة. هل أنت متأكد؟ (اكتب 'نعم' للتأكيد): ")
            if confirm.lower() == 'نعم':
                history = []
                save_game_history(history)
                print("SUCCESS: تم مسح جميع البيانات.")
        
        elif choice == '5':
            print("مع السلامة!")
            break

        else:
            print("ERROR: خيار غير صالح، الرجاء المحاولة مرة أخرى.")


if __name__ == "__main__":
    main_menu()
