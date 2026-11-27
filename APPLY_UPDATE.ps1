param(
    [Parameter(Mandatory=$false)]
    [string]$ProjectRoot = ""
)
$ErrorActionPreference = "Stop"
$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($ProjectRoot)) { $ProjectRoot = Read-Host "اكتب المسار الكامل لمجلد مشروع FBRAH الحالي" }
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$Required = @(
  "app.py", "templates\index.html", "fbrah_advanced_calculator.py", "fbrah_calculation_router.py", "fbrah_jokes.py",
  "fbrah_reminder_core.py", "fbrah_reminder_worker.py", "requirements.txt"
)
foreach ($File in $Required) {
  if (!(Test-Path -LiteralPath (Join-Path $PackageRoot $File))) { throw "ملف الحزمة مفقود: $File" }
}
if (!(Test-Path -LiteralPath (Join-Path $ProjectRoot "app.py"))) { throw "لم أجد app.py في المسار المحدد." }
if (!(Test-Path -LiteralPath (Join-Path $ProjectRoot "templates\index.html"))) { throw "لم أجد templates\index.html في المسار المحدد." }
Write-Host "سيتم تحديث ملفات التطبيق والواجهة والحاسبة والتذكيرات فقط." -ForegroundColor Cyan
Write-Host "لن يتم استبدال .env أو fbrah.db أو مجلد data أو الملفات المرفوعة أو التسجيلات." -ForegroundColor Yellow
$Confirm = Read-Host "للمتابعة اكتب APPLY"
if ($Confirm -cne "APPLY") { Write-Host "تم الإلغاء دون تغيير." -ForegroundColor Yellow; exit 0 }
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Backup = Join-Path $ProjectRoot ("backups\FBRAH_complete_update_" + $Stamp)
New-Item -ItemType Directory -Force -Path $Backup | Out-Null
$Files = @(
  "app.py", "templates\index.html", "fbrah_advanced_calculator.py", "fbrah_calculation_router.py", "fbrah_jokes.py",
  "fbrah_reminder_core.py", "fbrah_reminder_worker.py", "requirements.txt", ".env.example",
  "START_FBRAH_REMINDERS.bat", "INSTALL_FBRAH_REMINDERS_STARTUP.ps1",
  "test_advanced_calculator.py", "test_calculation_router.py", "test_joke_rotation.py", "test_reminder_worker.py",
  "test_new_reliability_updates.py", "test_fbrah_update_package.py", "test_priority_smoke.py"
)
$Existing = @{}
foreach ($File in $Files) {
  $Target = Join-Path $ProjectRoot $File
  if (Test-Path -LiteralPath $Target) {
    $Existing[$File] = $true
    $BackupTarget = Join-Path $Backup $File
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $BackupTarget) | Out-Null
    Copy-Item -LiteralPath $Target -Destination $BackupTarget -Force
  } else { $Existing[$File] = $false }
}
try {
  foreach ($File in $Files) {
    $Source = Join-Path $PackageRoot $File
    if (!(Test-Path -LiteralPath $Source)) { continue }
    $Target = Join-Path $ProjectRoot $File
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Target) | Out-Null
    Copy-Item -LiteralPath $Source -Destination $Target -Force
  }
  $Python = (Get-Command python -ErrorAction Stop).Source
  & $Python -m py_compile (Join-Path $ProjectRoot "app.py") (Join-Path $ProjectRoot "fbrah_advanced_calculator.py") (Join-Path $ProjectRoot "fbrah_calculation_router.py") (Join-Path $ProjectRoot "fbrah_reminder_core.py") (Join-Path $ProjectRoot "fbrah_reminder_worker.py")
  if ($LASTEXITCODE -ne 0) { throw "فشل فحص Python. سيُستعاد الإصدار السابق." }
  Write-Host "نجح فحص صياغة Python." -ForegroundColor Green
  Write-Host ("النسخة الاحتياطية: " + $Backup) -ForegroundColor Green
  Write-Host "أعد تشغيل FBRAH. لتنبيهات Windows عند إغلاق المتصفح ثبّت winotify ثم شغّل INSTALL_FBRAH_REMINDERS_STARTUP.ps1." -ForegroundColor Cyan
} catch {
  Write-Host "فشل التحديث: $_ — جارٍ استعادة الملفات السابقة." -ForegroundColor Red
  foreach ($File in $Files) {
    $Target = Join-Path $ProjectRoot $File
    if ($Existing[$File] -and (Test-Path -LiteralPath (Join-Path $Backup $File))) {
      Copy-Item -LiteralPath (Join-Path $Backup $File) -Destination $Target -Force
    } elseif (!$Existing[$File] -and (Test-Path -LiteralPath $Target)) {
      Remove-Item -LiteralPath $Target -Force
    }
  }
  throw
}
