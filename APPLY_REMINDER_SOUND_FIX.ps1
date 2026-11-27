param([string]$ProjectRoot = "")
$ErrorActionPreference = 'Stop'
$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($ProjectRoot)) { $ProjectRoot = Read-Host 'اكتب مسار مجلد FBRAH الحالي' }
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)

function Get-FullPath([string]$Path) {
    return [System.IO.Path]::GetFullPath($Path).TrimEnd('\')
}
function Copy-IfDifferent([string]$Source, [string]$Destination) {
    $src = Get-FullPath $Source
    $dst = Get-FullPath $Destination
    if ($src -ieq $dst) {
        Write-Host "تخطي النسخ: الملف موجود بالفعل في مجلد المشروع ($([System.IO.Path]::GetFileName($src)))." -ForegroundColor DarkYellow
        return
    }
    Copy-Item -LiteralPath $Source -Destination $Destination -Force
}

$WorkerSource = Join-Path $PackageRoot 'fbrah_reminder_worker.py'
$ConfigSource = Join-Path $PackageRoot 'CONFIGURE_FBRAH_WINDOWS_SOUND.ps1'
$ConfigBatSource = Join-Path $PackageRoot 'CONFIGURE_FBRAH_WINDOWS_SOUND.bat'
foreach ($f in @($WorkerSource,$ConfigSource,$ConfigBatSource)) {
    if (!(Test-Path -LiteralPath $f)) { throw "ملف ناقص في الحقيبة: $f" }
}
$ProjectWorker = Join-Path $ProjectRoot 'fbrah_reminder_worker.py'
if (!(Test-Path -LiteralPath $ProjectWorker)) { throw 'لم أجد عامل التذكيرات في مجلد المشروع.' }

$Task = Get-ScheduledTask -TaskName 'FBRAH AI Reminders' -ErrorAction SilentlyContinue
$WasRunning = $false
if ($Task) {
    $WasRunning = ($Task.State -eq 'Running')
    if ($WasRunning) { Stop-ScheduledTask -TaskName 'FBRAH AI Reminders'; Start-Sleep -Seconds 2 }
}

$Stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$Backup = Join-Path $ProjectRoot "backups\FBRAH_reminder_sound_$Stamp"
New-Item -ItemType Directory -Force -Path $Backup | Out-Null
Copy-Item -LiteralPath $ProjectWorker -Destination $Backup -Force
foreach ($name in @('CONFIGURE_FBRAH_WINDOWS_SOUND.ps1','CONFIGURE_FBRAH_WINDOWS_SOUND.bat')) {
    $target = Join-Path $ProjectRoot $name
    if (Test-Path -LiteralPath $target) { Copy-Item -LiteralPath $target -Destination $Backup -Force }
}

try {
    Copy-IfDifferent $WorkerSource $ProjectWorker
    Copy-IfDifferent $ConfigSource (Join-Path $ProjectRoot 'CONFIGURE_FBRAH_WINDOWS_SOUND.ps1')
    Copy-IfDifferent $ConfigBatSource (Join-Path $ProjectRoot 'CONFIGURE_FBRAH_WINDOWS_SOUND.bat')

    $Python = (Get-Command python -ErrorAction Stop).Source
    $VenvPython = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
    if (Test-Path -LiteralPath $VenvPython) { $Python = $VenvPython }
    & $Python -m py_compile $ProjectWorker
    if ($LASTEXITCODE -ne 0) { throw 'فشل فحص صياغة عامل التذكيرات.' }

    if ($Task) { Start-ScheduledTask -TaskName 'FBRAH AI Reminders' }
    Write-Host 'تم تحديث/التحقق من عامل تنبيهات Windows بنجاح.' -ForegroundColor Green
    Write-Host "النسخة الاحتياطية: $Backup" -ForegroundColor Green
    Write-Host 'لتغيير النغمة ومستوى الصوت وعدد مرات الرنين شغّل CONFIGURE_FBRAH_WINDOWS_SOUND.bat.' -ForegroundColor Cyan
} catch {
    $backupWorker = Join-Path $Backup 'fbrah_reminder_worker.py'
    if (Test-Path -LiteralPath $backupWorker) {
        Copy-Item -LiteralPath $backupWorker -Destination $ProjectWorker -Force
    }
    if ($Task -and $WasRunning) { Start-ScheduledTask -TaskName 'FBRAH AI Reminders' }
    throw
}
