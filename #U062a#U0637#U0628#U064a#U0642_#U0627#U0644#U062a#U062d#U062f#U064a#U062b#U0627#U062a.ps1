# FBRAH AI - Safe security hardening installer (PowerShell 5.1)
# Run from the project root. Creates timestamped backups; never touches .env or data.
$ErrorActionPreference = 'Stop'
$root = (Get-Location).Path
$app = Join-Path $root 'app.py'
$index = Join-Path $root 'templates\index.html'
$module = Join-Path $root 'security_hardening.py'
$admin = Join-Path $root 'templates\admin_users.html'
if (!(Test-Path -LiteralPath $app) -or !(Test-Path -LiteralPath $index) -or !(Test-Path -LiteralPath $admin) -or !(Test-Path -LiteralPath $module)) {
    throw 'ضع ملفات الحقيبة في جذر المشروع ثم شغّل السكربت من جذر المشروع.'
}
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$backup = Join-Path $root ("backups\security_hardening_" + $stamp)
New-Item -ItemType Directory -Force -Path $backup | Out-Null
Copy-Item -LiteralPath $app -Destination (Join-Path $backup 'app.py.before')
Copy-Item -LiteralPath $index -Destination (Join-Path $backup 'index.html.before')
Copy-Item -LiteralPath $admin -Destination (Join-Path $backup 'admin_users.html.before')

$src = [System.IO.File]::ReadAllText($app, [System.Text.Encoding]::UTF8)
$idx = [System.IO.File]::ReadAllText($index, [System.Text.Encoding]::UTF8)
$adm = [System.IO.File]::ReadAllText($admin, [System.Text.Encoding]::UTF8)
if ($src.Contains('init_security_hardening(app, get_db, hash_password)')) {
    Write-Host 'طبقة الحماية مثبتة بالفعل؛ لن يكرر السكربت دمجها.' -ForegroundColor Yellow
} else {
    $anchor = '# 18. APPLICATION BOOTSTRAPPER & SERVER RUNNER'
    if (!$src.Contains($anchor)) { throw 'لم يتم العثور على موضع دمج معروف في app.py؛ لم يتم تعديل الملف.' }
    $integration = "`r`n# FBRAH SECURITY HARDENING EXTENSION`r`nfrom security_hardening import init_security_hardening`r`ninit_security_hardening(app, get_db, hash_password)`r`n`r`n"
    $src = $src.Replace($anchor, $integration + $anchor)
}

# Fail-closed model fallback defaults. Explicit .env values remain authoritative.
$src = $src.Replace('(os.environ.get("FBRAH_ALLOW_LOCAL_MODEL_FALLBACK") or "1")', '(os.environ.get("FBRAH_ALLOW_LOCAL_MODEL_FALLBACK") or "0")')
$src = $src.Replace('(os.environ.get("FBRAH_ALLOW_CLOUD_FALLBACK") or "1")', '(os.environ.get("FBRAH_ALLOW_CLOUD_FALLBACK") or "0")')
if (!$src.Contains('import html')) { $src = [regex]::Replace($src, '(?m)^import os$', "import os`r`nimport html", 1) }
$src = $src.Replace('if not username or len(username) < 3:', 'if not re.fullmatch(r"[\w.@+-]{3,64}", username, flags=re.UNICODE):')
$src = $src.Replace('username and len(username) >= 3', 're.fullmatch(r"[\w.@+-]{3,64}", username, flags=re.UNICODE)')
$src = $src.Replace('if not uid or len(new_name) < 3:', 'if not uid or not re.fullmatch(r"[\w.@+-]{3,64}", new_name, flags=re.UNICODE):')
$src = $src.Replace('if not new_name or len(new_name) < 3:', 'if not re.fullmatch(r"[\w.@+-]{3,64}", new_name, flags=re.UNICODE):')
$src = $src.Replace('{(row[''username''] if row else user)}', '{html.escape(str(row[''username''] if row else user), quote=True)}')
$src = $src.Replace('{(row[''email''] or '''') if row else ''''}', '{html.escape(str((row[''email''] or '''') if row else ''''), quote=True)}')
$src = $src.Replace('{(row[''phone''] or '''') if row else ''''}', '{html.escape(str((row[''phone''] or '''') if row else ''''), quote=True)}')

# Mutating endpoints must not mutate through GET.
$src = $src.Replace('@app.route("/api/clear_dialogue", methods=["POST", "GET"])', '@app.route("/api/clear_dialogue", methods=["POST"])')
$src = $src.Replace('@app.route("/api/recordings/export-all", methods=["GET", "POST"])', '@app.route("/api/recordings/export-all", methods=["POST"])')
$src = $src.Replace('@app.route("/recordings/api/export-all", methods=["GET", "POST"])', '@app.route("/recordings/api/export-all", methods=["POST"])')
$src = $src.Replace('@app.route("/api/recordings/<rid>/export", methods=["GET", "POST"])', '@app.route("/api/recordings/<rid>/export", methods=["POST"])')
$src = $src.Replace('@app.route("/recordings/api/<rid>/export", methods=["GET", "POST"])', '@app.route("/recordings/api/<rid>/export", methods=["POST"])')

# Stronger password policy for new registrations, self-service changes and admin resets.
$src = $src.Replace('len(password) < 6', 'len(password) < 12')
$src = $src.Replace('len(password) >= 6', 'len(password) >= 12')
$src = $src.Replace('len(new_pw) < 6', 'len(new_pw) < 12')
$src = $src.Replace('minlength="6"', 'minlength="12"')
$adm = $adm.Replace('minlength="6"', 'minlength="12"')
$src = $src.Replace('6 أحرف على الأقل', '12 حرفاً على الأقل')
$src = $src.Replace('6 أحرف', '12 حرفاً')

# Login page reset link.
$loginAnchor = '<div class="foot"><span data-i="noAcc">ليس لديك حساب؟</span> <a href="/register" data-i="reg">إنشاء حساب جديد</a></div>'
if (!$src.Contains('/forgot-password')) {
    if (!$src.Contains($loginAnchor)) { throw 'تعذر تحديد موضع رابط استعادة كلمة المرور في LOGIN_HTML؛ لم يتم حفظ app.py.' }
    $loginReplacement = $loginAnchor + @'
      <div class="foot"><a href="/forgot-password">نسيت كلمة المرور؟ استعادة آمنة</a></div>
'@
    $src = $src.Replace($loginAnchor, $loginReplacement)
}

# Logout becomes POST-only, and the existing UI link becomes a POST form.
$src = $src.Replace('@app.route("/logout")', '@app.route("/logout", methods=["POST"])')
# Never write password-reset bearer tokens into HTTP terminal logs.
$src = $src.Replace('path = request.path', 'path = re.sub(r"(?i)(/reset-password/)[^/]+", r"\1[REDACTED]", request.path)')
$logoutOld = '<a href="{{ url_for(''logout'') }}" id="logoutLink" data-i18n="logout">خروج</a>'
$logoutNew = '<form method="post" action="{{ url_for(''logout'') }}" style="display:inline"><button type="submit" id="logoutLink" data-i18n="logout">خروج</button></form>'
if ($idx.Contains($logoutOld)) { $idx = $idx.Replace($logoutOld, $logoutNew) }

# Verify integration uniqueness and expected anchors before writing.
if (([regex]::Matches($src, 'init_security_hardening\(app, get_db, hash_password\)')).Count -ne 1) { throw 'فشل تحقق دمج وحدة الحماية؛ لم يتم حفظ الملفات.' }
if (!$src.Contains('@app.route("/logout", methods=["POST"])')) { throw 'فشل تحقق حماية تسجيل الخروج.' }
if (!$src.Contains('@app.route("/api/clear_dialogue", methods=["POST"])')) { throw 'فشل تحقق مسار مسح المحادثة.' }
if (!$src.Contains('import html') -or !$src.Contains('html.escape(str(row[''username''] if row else user), quote=True)')) { throw 'فشل تحقق ترميز مخرجات صفحة الحساب.' }
if (!$src.Contains('html.escape(str((row[''email''] or '''') if row else ''''), quote=True)') -or !$src.Contains('html.escape(str((row[''phone''] or '''') if row else ''''), quote=True)')) { throw 'فشل تحقق ترميز البريد والهاتف في صفحة الحساب.' }
if (!$src.Contains('[REDACTED]')) { throw 'فشل تحقق إخفاء رموز إعادة التعيين من السجلات.' }
if ($src.Contains('@app.route("/api/recordings/export-all", methods=["GET", "POST"])')) { throw 'مسار export-all ما زال يقبل GET.' }
if ($src.Contains('@app.route("/api/recordings/<rid>/export", methods=["GET", "POST"])')) { throw 'مسار تصدير التسجيل ما زال يقبل GET.' }
if (!$adm.Contains('minlength="12"')) { throw 'لم يتم تحديث حد كلمة المرور في لوحة الإدارة.' }

[System.IO.File]::WriteAllText($app, $src, (New-Object System.Text.UTF8Encoding($false)))
[System.IO.File]::WriteAllText($index, $idx, (New-Object System.Text.UTF8Encoding($false)))
[System.IO.File]::WriteAllText($admin, $adm, (New-Object System.Text.UTF8Encoding($false)))
Write-Host "تم تطبيق التعديلات. النسخ السابقة محفوظة في: $backup" -ForegroundColor Green
Write-Host 'لم يتم تنفيذ أي أمر Git أو تعديل .env أو قواعد البيانات أو مجلد data.' -ForegroundColor Cyan
