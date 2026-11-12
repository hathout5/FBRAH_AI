FBRAH — حزمة الأولويات الشاملة
==============================

المجلد المعدَّل بالكامل:
  /home/workdir/artifacts/fbrah_src/

لإنشاء ZIP واحد على جهازك أو السندبوكس:
  python /home/workdir/artifacts/CREATE_FBRAH_ZIP.py
الناتج:
  /home/workdir/artifacts/FBRAH_COMPLETE_PRIORITY.zip

الملفات الحرجة داخل fbrah_src:
  app.py
  fbrah_priority_enhancements.py   (جديد — صور + RAG + OCR بوابة)
  package/templates/index.html
  Fbrah Ai G/templates/index.html
  .gitignore
  tests/test_priority_smoke.py

اختبار سريع:
  cd fbrah_src
  python tests/test_priority_smoke.py

تغطية الأولويات:
  P0  HTML آمن، كلمة المرور، فصل بيئات          [منفَّذ]
  P1  توجيه/نماذج، ترجمة كاملة، OCR/PDF، عرض     [منفَّذ]
  P2  صور محسّنة، أدلة RAG، بوابة OCR سحابي    [منفَّذ أساس]
  P2  نداء فبرا/ميكروفون متقدم                   [جزئي — البنية موجودة]
  P3  Word/Excel/PDF/PPT موجودة مسبقاً + جداول   [محسَّن جزئياً]
  P3  اختبارات دخان AR/EN                        [منفَّذ]
