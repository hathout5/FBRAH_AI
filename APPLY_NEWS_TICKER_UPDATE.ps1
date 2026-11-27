param(
    [string]$ProjectRoot = "C:\Users\hatho\Desktop\Amit\Fbrah AI\Fbrah Ai G"
)
$ErrorActionPreference = "Stop"
$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$Files = @("app.py", "templates\index.html")
foreach ($f in $Files) {
    if (!(Test-Path -LiteralPath (Join-Path $PackageRoot $f))) { throw "ملف التحديث مفقود: $f" }
    if (!(Test-Path -LiteralPath (Join-Path $ProjectRoot $f))) { throw "ملف المشروع غير موجود: $f" }
}
Write-Host "سيتم تحديث محرك الأخبار وواجهة الشريط فقط." -ForegroundColor Cyan
Write-Host "لن تتغير قاعدة البيانات أو الملفات المرفوعة أو الإعدادات." -ForegroundColor Yellow
$confirm = Read-Host "للمتابعة اكتب APPLY"
if ($confirm -cne "APPLY") { Write-Host "تم الإلغاء."; exit 0 }
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backup = Join-Path $ProjectRoot ("backups\FBRAH_news_ticker_" + $stamp)
New-Item -ItemType Directory -Force -Path (Join-Path $backup "templates") | Out-Null
Copy-Item -LiteralPath (Join-Path $ProjectRoot "app.py") -Destination (Join-Path $backup "app.py") -Force
Copy-Item -LiteralPath (Join-Path $ProjectRoot "templates\index.html") -Destination (Join-Path $backup "templates\index.html") -Force
try {
    Copy-Item -LiteralPath (Join-Path $PackageRoot "app.py") -Destination (Join-Path $ProjectRoot "app.py") -Force
    Copy-Item -LiteralPath (Join-Path $PackageRoot "templates\index.html") -Destination (Join-Path $ProjectRoot "templates\index.html") -Force
    $Python = (Get-Command python -ErrorAction Stop).Source
    & $Python -m py_compile (Join-Path $ProjectRoot "app.py")
    if ($LASTEXITCODE -ne 0) { throw "فشل فحص Python." }
    Write-Host "تم تحديث شريط الأخبار واجتاز app.py فحص Python." -ForegroundColor Green
    Write-Host "النسخة الاحتياطية: $backup" -ForegroundColor Green
    Write-Host "أعد تشغيل FBRAH ثم جرّب زر تحديث الأخبار." -ForegroundColor Cyan
} catch {
    Copy-Item -LiteralPath (Join-Path $backup "app.py") -Destination (Join-Path $ProjectRoot "app.py") -Force
    Copy-Item -LiteralPath (Join-Path $backup "templates\index.html") -Destination (Join-Path $ProjectRoot "templates\index.html") -Force
    throw
}
