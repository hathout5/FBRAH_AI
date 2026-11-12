# قائمة مراجعة رفع FBRAH AI إلى GitHub بأمان

## قبل أي أمر Git

1. فك الحزمة خارج مجلد المشروع، ثم شغّل `INSTALL_RELEASE.ps1` بعد مراجعة `FINAL_AUDIT_AR.md`.
2. لا ترفع `.env` أو قواعد البيانات أو `data/` أو Qdrant أو `backups/` أو مجلدات النسخ الاحتياطية.
3. تحقق من الحالة والفروق دون تغيير الفروع:

```powershell
git status --short
git diff --check
git diff --stat
git ls-files --others --exclude-standard
git check-ignore -v .env fbrah.db data backups
```

4. راجع الملفات المعدّلة والجديدة واحداً واحداً. لا تستخدم `git add -A` قبل فحص كل ملف غير متتبع.
5. لا تفتح `.env` في سجل الطرفية ولا تنسخ محتوياته إلى المحادثة أو GitHub.

## مسار النشر المقترح

- سجل الفحص الأخير أظهر أن `clean-main` و`origin/main` كانا عند الالتزام نفسه، وأن `main` المحلي له تاريخ منفصل. لا تدمج التاريخين ولا تحذف أياً منهما.
- بعد أن يصبح مجلد العمل آمناً وبعد التأكد من أنك على `clean-main`، أنشئ فرع مراجعة جديداً:

```powershell
git switch -c release/fbrah-ai-2026-11-12
```

- أضف الملفات المحددة بعد مراجعتها فقط، ثم افحص ما سيُرفع:

```powershell
git add app.py templates/index.html templates/admin_users.html backup_db.py restore_db.py reset_admin.py security_hardening.py fbrah_priority_enhancements.py requirements.txt requirements-rag.txt .env.example .gitignore .gitattributes test_release_integrity.py test_index_integrity.py test_priority_smoke.py
# أضف ملفات الوثائق والمثبت بأسمائها الصريحة بعد مراجعتها

git diff --cached --check
git diff --cached --stat
git status --short
```

- لا تنفذ commit أو push إلا بعد مراجعة `git diff --cached` والتأكد من عدم وجود أسرار أو قواعد بيانات أو بيانات مستخدمين.
- عند الموافقة النهائية، ادفع فرع المراجعة فقط وافتح Pull Request؛ لا تدفع مباشرة إلى `main` ولا تستخدم `--force`:

```powershell
git commit -m "Prepare FBRAH AI release candidate"
git push -u origin release/fbrah-ai-2026-11-12
```

## ملاحظة أمنية للتاريخ

جعل المستودع خاصاً أو إزالة سر من الملف الحالي لا يزيله من تاريخ Git. إذا سبق نشر كلمة مرور أو مفتاح API، غيّر/دوّر السر لدى مزوده أولاً، ثم خطط لتنظيف التاريخ بشكل منفصل ومدروس. لا تنفذ إعادة كتابة للتاريخ أو force-push كجزء من هذا التسليم.


## نتيجة مراجعة التاريخ — 12 نوفمبر 2026

- المرجع المحفوظ `origin/main` والفرع `clean-main` عند الالتزام `1cd9048` في بيانات الأرشيف.
- الفرع المحلي `main` تاريخ مستقل ويحتوي في الالتزام القديم `cc0f51a` على أداة إعادة تعيين مدير ذات كلمة مرور افتراضية داخل الكود. لا ترفع هذا الفرع ولا تدمجه ولا تستخدم `--force`.
- لا تخلط التاريخين. بعد تثبيت الحزمة ومراجعة الملفات، أنشئ فرع مراجعة من `clean-main` فقط، ثم أضف الملفات التي راجعتها بالاسم.
- استخدم `ENABLE_FALLBACK_LOCAL.ps1` عند الحاجة لتفعيل القيمتين في `.env` المحلي؛ هذا الملف لا يدخل في GitHub ولا يطبع مفاتيح API.
- ملف `.env` وقاعدة البيانات وبيانات المستخدمين ومجلد `data` وQdrant والنسخ الاحتياطية تبقى محلية.
- هذا التقرير مبني على مراجع Git المحفوظة في الأرشيف، وليس فحصاً لكل refs البعيدة أو طلبات السحب في GitHub.

## فحوص ما قبل النشر في هذه النسخة

```powershell
python -m py_compile app.py backup_db.py restore_db.py reset_admin.py security_hardening.py fbrah_priority_enhancements.py
python -m unittest -v test_release_integrity.py test_index_integrity.py
python test_priority_smoke.py
git diff --check
git status --short
```

لا ترفع `.env` أو أي قاعدة بيانات أو `data/` أو Qdrant أو ملفات `.bak` أو `.log` أو مجلد `.git`. لا تنفذ `git add -A`.
