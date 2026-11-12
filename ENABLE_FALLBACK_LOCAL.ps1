[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$ProjectRoot
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$EnvPath = Join-Path $ProjectRoot '.env'
if (-not (Test-Path -LiteralPath $EnvPath -PathType Leaf)) {
    throw 'The project .env file was not found. No file was changed.'
}

$raw = [System.IO.File]::ReadAllText($EnvPath)
$bytes = [System.IO.File]::ReadAllBytes($EnvPath)
$hasBom = ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF)
$encoding = New-Object System.Text.UTF8Encoding($hasBom)
$updated = $raw

foreach ($key in @('FBRAH_ALLOW_CLOUD_FALLBACK', 'FBRAH_ALLOW_LOCAL_MODEL_FALLBACK')) {
    $pattern = '(?m)^[ \t]*' + [regex]::Escape($key) + '[ \t]*=.*$'
    if ([regex]::IsMatch($updated, $pattern)) {
        $updated = [regex]::Replace($updated, $pattern, ($key + '=1'))
    }
    else {
        if ($updated.Length -gt 0 -and -not $updated.EndsWith("`n")) { $updated += "`r`n" }
        $updated += ($key + '=1' + "`r`n")
    }
}

if ($updated -eq $raw) {
    Write-Host 'Both fallback settings are already enabled. No changes needed.'
    exit 0
}

Write-Host 'This operation changes only these two .env settings:'
Write-Host '  FBRAH_ALLOW_CLOUD_FALLBACK=1'
Write-Host '  FBRAH_ALLOW_LOCAL_MODEL_FALLBACK=1'
Write-Host 'All API keys and other .env values remain untouched and will not be displayed.'
$approval = Read-Host 'Type APPLY to back up .env and enable the two isolated fallback paths'
if ($approval -cne 'APPLY') { throw 'Cancelled. No file was changed.' }

$backup = $EnvPath + '.before_fallback_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff') + '.bak'
Copy-Item -LiteralPath $EnvPath -Destination $backup -ErrorAction Stop
[System.IO.File]::WriteAllText($EnvPath, $updated, $encoding)

$verify = [System.IO.File]::ReadAllText($EnvPath)
foreach ($key in @('FBRAH_ALLOW_CLOUD_FALLBACK', 'FBRAH_ALLOW_LOCAL_MODEL_FALLBACK')) {
    $matches = [regex]::Matches($verify, '(?m)^[ \t]*' + [regex]::Escape($key) + '[ \t]*=([^\r\n]*)')
    if ($matches.Count -lt 1) { throw "Verification failed for $key. Restore the backup: $backup" }
    foreach ($match in $matches) {
        if ($match.Groups[1].Value.Trim() -ne '1') { throw "Verification failed for $key. Restore the backup: $backup" }
    }
}

Write-Host 'SUCCESS: Cloud-to-cloud and local-to-local fallback are enabled.' -ForegroundColor Green
Write-Host 'Cloud/local cross-mode fallback remains prohibited by the application router.'
Write-Host "Original .env backup: $backup"
Write-Host 'Restart FBRAH AI for the new settings to take effect.'
