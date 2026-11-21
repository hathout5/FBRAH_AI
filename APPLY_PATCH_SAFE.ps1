[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectRoot
)

$ErrorActionPreference = 'Stop'
$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path

$SourceApp = Join-Path $PackageRoot 'app.py'
$SourceIndex = Join-Path $PackageRoot 'templates\index.html'
$TargetApp = Join-Path $ProjectRoot 'app.py'
$TargetTemplates = Join-Path $ProjectRoot 'templates'
$TargetIndex = Join-Path $TargetTemplates 'index.html'

foreach ($p in @($SourceApp, $SourceIndex, $TargetApp, $TargetIndex)) {
    if (-not (Test-Path -LiteralPath $p -PathType Leaf)) {
        throw "Required file not found: $p"
    }
}

$Stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$BackupDir = Join-Path $ProjectRoot ("backups\FBRAH_PATCH_" + $Stamp)
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null

Copy-Item -LiteralPath $TargetApp -Destination (Join-Path $BackupDir 'app.py') -Force
Copy-Item -LiteralPath $TargetIndex -Destination (Join-Path $BackupDir 'index.html') -Force

try {
    Copy-Item -LiteralPath $SourceApp -Destination $TargetApp -Force
    Copy-Item -LiteralPath $SourceIndex -Destination $TargetIndex -Force

    Push-Location $ProjectRoot
    try {
        $Python = Get-Command python -ErrorAction Stop
        & $Python.Source -m py_compile app.py
        if ($LASTEXITCODE -ne 0) {
            throw "Python syntax validation failed."
        }
    }
    finally {
        Pop-Location
    }

    Write-Host "Patch applied and Python syntax check passed." -ForegroundColor Green
    Write-Host "Backup: $BackupDir"
    Write-Host "No .env, database, data, recordings, Git branch, or remote was changed."
}
catch {
    Copy-Item -LiteralPath (Join-Path $BackupDir 'app.py') -Destination $TargetApp -Force
    Copy-Item -LiteralPath (Join-Path $BackupDir 'index.html') -Destination $TargetIndex -Force
    throw "Patch failed and original files were restored. Backup: $BackupDir. Details: $($_.Exception.Message)"
}
