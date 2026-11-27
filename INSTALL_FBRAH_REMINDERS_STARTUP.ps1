$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = (Get-Command python -ErrorAction Stop).Source
$VenvPython = Join-Path $Root '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $VenvPython) { $Python = $VenvPython }
$InstallResult = & $Python -m pip show winotify 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host 'جارٍ تثبيت winotify على بيئة Python المختارة...' -ForegroundColor Cyan
    & $Python -m pip install winotify
    if ($LASTEXITCODE -ne 0) { throw 'تعذر تثبيت winotify. تحقق من اتصال الإنترنت ثم أعد تشغيل هذا الملف.' }
}
$Worker = Join-Path $Root 'fbrah_reminder_worker.py' 
$AppUsername = Read-Host 'اكتب اسم مستخدم FBRAH الذي ستظهر تنبيهاته على حساب Windows الحالي'
if ([string]::IsNullOrWhiteSpace($AppUsername)) { throw 'يجب إدخال اسم مستخدم FBRAH لحماية خصوصية الحسابات الأخرى.' }
$Argument = '"' + $Worker + '" --username "' + $AppUsername.Replace('"','') + '"'
$Action = New-ScheduledTaskAction -Execute $Python -Argument $Argument -WorkingDirectory $Root
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Days 3650)
Register-ScheduledTask -TaskName 'FBRAH AI Reminders' -Action $Action -Trigger $Trigger -Settings $Settings -Description 'FBRAH reminders and appointment Windows notifications' -Force | Out-Null
Write-Host 'تم إعداد تشغيل تنبيهات FBRAH عند تسجيل الدخول إلى Windows.' -ForegroundColor Green
Write-Host 'تم التحقق من winotify على بيئة Python التي ستشغل العامل.'
Write-Host 'يمكنك إيقاف المهمة من Task Scheduler باسم FBRAH AI Reminders.'
