import os
import json
import statistics

# --- ثوابت وإعدادات ---
DATA_FILE = 'crash_history.json'  # اسم ملف تخزين البيانات

# --- دوال التعامل مع البيانات ---

def load_game_history():
    """
    يقوم بتحميل سجل نتائج اللعبة من ملف JSON.
    إذا لم يكن الملف موجودًا، يقوم بإنشائه وإرجاع قائمة فارغة.
    """
    if not os.path.exists(DATA_FILE):
        print(f"ملف البيانات '{DATA_FILE}' غير موجود. سيتم إنشاء ملف جديد.")
        return []
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"خطأ في قراءة ملف البيانات: {e}. سيتم البدء بسجل فارغ.")
        return []

def save_game_history(history):
    """
    يقوم بحفظ سجل نتائج اللعبة المحدث في ملف JSON.
    """
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(history, f, indent=4)
    except IOError as e:
        print(f"خطأ في حفظ ملف البيانات: {e}")

# --- دوال التحليل والتوقع ---

def analyze_history(history):
    """
    يقوم بإجراء تحليل إحصائي أساسي لسجل النتائج.
    """
    if not history:
        print("\n--- تحليل البيانات ---")
        print("لا توجد بيانات كافية للتحليل.")
        return

    # استبعاد أي قيم غير رقمية قد تكون أُدخلت عن طريق الخطأ
    numeric_history = [x for x in history if isinstance(x, (int, float))]
    
    if not numeric_history:
        print("\n--- تحليل البيانات ---")
        print("لا توجد بيانات رقمية صالحة للتحليل.")
        return

    print("\n--- تحليل البيانات ---")
    print(f"عدد الجولات المسجلة: {len(numeric_history)}")
    print(f"أعلى معامل انهيار مسجل: {max(numeric_history):.2f}x")
    print(f"أقل معامل انهيار مسجل: {min(numeric_history):.2f}x")
    print(f"متوسط معامل الانهيار: {statistics.mean(numeric_history):.2f}x")
    
    try:
        print(f"وسيط معامل الانهيار: {statistics.median(numeric_history):.2f}x")
    except statistics.StatisticsError:
        print("لا يمكن حساب الوسيط (تحتاج إلى جولتين على الأقل).")

    crashes_under_2x = sum(1 for x in numeric_history if x < 2.0)
    print(f"عدد مرات الانهيار تحت 2.0x: {crashes_under_2x} (بنسبة {crashes_under_2x / len(numeric_history):.2%})")

def make_prediction(history):
    """
    يقوم بإنشاء توقع بسيط بناءً على البيانات التاريخية.
    **هذه مجرد استراتيجية مثال بسيطة جدًا وغير مضمونة.**
    """
    print("\n--- التوقع للجولة القادمة ---")
    if len(history) < 5:
        print("نحتاج إلى 5 جولات على الأقل لتقديم توقع.")
        return

    # استراتيجية مثال: إذا كانت آخر 3 جولات أقل من 2.0x، توقع أن الجولة التالية ستكون أعلى.
    last_three_games = history[-3:]
    if all(game < 2.0 for game in last_three_games):
        print("التوقع: احتمالية عالية أن يكون معامل الانهيار القادم **أعلى من 2.0x**.")
        print("السبب: آخر 3 جولات كانت منخفضة بشكل متتالي.")
    # استراتيجية مثال: إذا كانت آخر جولتين أعلى من 10.0x، توقع أن الجولة التالية ستكون منخفضة.
    elif all(game > 10.0 for game in history[-2:]):
        print("التوقع: احتمالية عالية أن يكون معامل الانهيار القادم **أقل من 2.0x**.")
        print("السبب: آخر جولتين كانتا مرتفعتين جدًا.")
    else:
        print("لا يوجد نمط واضح حاليًا بناءً على الاستراتيجية البسيطة المبرمجة.")
        avg = statistics.mean(history)
        print(f"نصيحة عامة: كن حذرًا. المتوسط العام هو {avg:.2f}x.")

# --- الواجهة الرئيسية للبرنامج ---

def main_menu():
    """
    يعرض القائمة الرئيسية ويتعامل مع مدخلات المستخدم.
    """
    history = load_game_history()

    while True:
        print("\n===============================")
        print("  برنامج تحليل لعبة Crash")
        print("===============================")
        print("1. إضافة نتيجة جولة جديدة")
        print("2. عرض وتحليل البيانات الحالية")
        print("3. الحصول على توقع للجولة القادمة")
        print("4. مسح جميع البيانات والبدء من جديد")
        print("5. خروج")

        choice = input("اختر رقمًا: ")

        if choice == '1':
            while True:
                try:
                    new_result_str = input("أدخل معامل الانهيار للجولة الجديدة (أو اكتب 'رجوع' للعودة): ")
                    if new_result_str.lower() == 'رجوع':
                        break
                    new_result = float(new_result_str)
                    if new_result < 1.0:
                        print("معامل الانهيار يجب أن يكون 1.0 أو أعلى.")
                        continue
                    history.append(new_result)
                    save_game_history(history)
                    print(f"تمت إضافة النتيجة {new_result:.2f}x بنجاح.")
                except ValueError:
                    print("إدخال غير صالح. الرجاء إدخال رقم عشري (مثل 1.54).")
        
        elif choice == '2':
            analyze_history(history)

        elif choice == '3':
            make_prediction(history)

        elif choice == '4':
            confirm = input("هل أنت متأكد أنك تريد مسح كل البيانات؟ (اكتب 'نعم' للتأكيد): ")
            if confirm.lower() == 'نعم':
                history = []
                save_game_history(history)
                print("تم مسح جميع البيانات.")
        
        elif choice == '5':
            print("مع السلامة!")
            break

        else:
            print("خيار غير صالح، الرجاء المحاولة مرة أخرى.")


if __name__ == "__main__":
    main_menu()

