$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$ConfigPath = Join-Path $Root 'fbrah_reminder_sound.json'

Write-Host ''
Write-Host 'إعداد صوت تنبيهات FBRAH على Windows' -ForegroundColor Cyan
Write-Host '------------------------------------'
Write-Host 'اختر نغمة التنبيه:'
Write-Host '1) كلاسيكية'
Write-Host '2) هادئة'
Write-Host '3) عاجلة'
Write-Host '4) متقطعة'
Write-Host '5) جرس رنان'
Write-Host '6) تصاعدية'
Write-Host '7) رقمية'
Write-Host '8) جرس مزدوج'
$choice = Read-Host 'رقم النغمة (1-8)'
$tones = @('classic','soft','urgent','double','chime','ascending','digital','bell')
$labels = @('كلاسيكية','هادئة','عاجلة','متقطعة','جرس رنان','تصاعدية','رقمية','جرس مزدوج')
if ($choice -notmatch '^[1-8]$') { throw 'اختيار النغمة يجب أن يكون من 1 إلى 8.' }
$index = [int]$choice - 1

$volumeText = Read-Host 'مستوى الصوت من 0 إلى 100 (الافتراضي 65)'
if ([string]::IsNullOrWhiteSpace($volumeText)) { $volume = 65 }
elseif ($volumeText -match '^\d{1,3}$' -and [int]$volumeText -ge 0 -and [int]$volumeText -le 100) { $volume = [int]$volumeText }
else { throw 'مستوى الصوت يجب أن يكون رقماً من 0 إلى 100.' }

Write-Host 'عدد مرات تكرار الرنة:'
Write-Host '1) مرة واحدة   2) مرتان   3) ثلاث مرات   4) خمس مرات   5) عشر مرات'
$repeatChoice = Read-Host 'اختر 1-5 (الافتراضي 3)'
if ([string]::IsNullOrWhiteSpace($repeatChoice)) { $repeats = 3 }
else {
    $repeatMap = @{ '1'=1; '2'=2; '3'=3; '4'=5; '5'=10 }
    if (-not $repeatMap.ContainsKey($repeatChoice)) { throw 'اختيار عدد التكرار غير صحيح.' }
    $repeats = $repeatMap[$repeatChoice]
}

$config = @{ tone = $tones[$index]; volume = $volume; repeats = $repeats }
$json = $config | ConvertTo-Json -Compress
$utf8 = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($ConfigPath, $json, $utf8)
Write-Host ''
Write-Host ('تم حفظ الإعدادات: ' + $labels[$index] + '، مستوى ' + $volume + '%، ' + $repeats + ' مرات.') -ForegroundColor Green
Write-Host 'ستُستخدم الإعدادات في إشعارات Windows التالية دون إعادة تثبيت المهمة.' -ForegroundColor Green
Write-Host 'لتجربة الصوت، أنشئ تذكيراً اختبارياً بعد دقيقة.' -ForegroundColor Yellow
