FBRAH AI — حقيبة تحديث موثوقية الأخبار والتسجيل
20 نوفمبر 2026

1) فك ضغط الحقيبة في مجلد مستقل.
2) اقرأ PATCH_REPORT_AR_2026-11-20.md.
3) أغلق خادم FBRAH AI.
4) افتح PowerShell داخل مجلد الحقيبة ونفّذ:

Set-ExecutionPolicy -Scope Process Bypass
.\APPLY_PATCH_SAFE.ps1 -ProjectRoot "C:\Users\hatho\Desktop\Amit\Fbrah AI\Fbrah Ai G"

البرنامج ينشئ نسخة احتياطية من app.py وtemplates\index.html قبل استبدالهما.
إذا فشل فحص Python يعيد الملفين الأصليين تلقائيًا.
لا يغيّر .env أو قواعد البيانات أو data أو التسجيلات أو GitHub.

التعديلات: app.py وtemplates/index.html.
الاختبارات الجديدة: test_news_recording_patch.py.
التفاصيل والاختبارات القديمة غير المطابقة: راجع التقرير العربي.
