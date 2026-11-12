[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$ProjectRoot
)

$ErrorActionPreference = 'Stop'
$trimChars = [char[]]@([char]92, [char]47)
$BundleRoot = [System.IO.Path]::GetFullPath((Split-Path -Parent $MyInvocation.MyCommand.Path)).TrimEnd($trimChars)
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd($trimChars)

function Assert-File([string]$Path, [string]$Label) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Missing $Label : $Path"
    }
}

function Get-SafeRelativePath([string]$RelativePath) {
    $candidate = $RelativePath.Replace('/', [System.IO.Path]::DirectorySeparatorChar)
    if ([System.IO.Path]::IsPathRooted($candidate) -or ($candidate -split '[\\/]') -contains '..') {
        throw "Unsafe path in release manifest: $RelativePath"
    }
    return $candidate
}

# Source and destination must be separate, non-overlapping folders.
$bundlePrefix = $BundleRoot + [System.IO.Path]::DirectorySeparatorChar
$projectPrefix = $ProjectRoot + [System.IO.Path]::DirectorySeparatorChar
if ([string]::Equals($BundleRoot, $ProjectRoot, [System.StringComparison]::OrdinalIgnoreCase) -or
    $BundleRoot.StartsWith($projectPrefix, [System.StringComparison]::OrdinalIgnoreCase) -or
    $ProjectRoot.StartsWith($bundlePrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'Unsafe installation: extract the ZIP outside the project folder. No project files were changed.'
}
if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
    throw "ProjectRoot does not exist: $ProjectRoot"
}
if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot '.git'))) {
    throw 'ProjectRoot is not a Git working tree. No project files were changed.'
}
Assert-File (Join-Path $ProjectRoot 'app.py') 'project app.py'
Assert-File (Join-Path $ProjectRoot 'templates\index.html') 'project templates/index.html'

$manifestPath = Join-Path $BundleRoot 'MANIFEST_SHA256.txt'
Assert-File $manifestPath 'SHA-256 manifest'
$manifestEntries = @()
foreach ($line in Get-Content -LiteralPath $manifestPath) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    if ($line -notmatch '^([0-9a-fA-F]{64})\s+(.+)$') {
        throw "Invalid manifest line: $line"
    }
    $expectedHash = $Matches[1].ToLowerInvariant()
    $relative = Get-SafeRelativePath $Matches[2].Trim()
    if ($relative -match '(^|[\\/])\.env($|[\\/])' -or
        $relative -match '\.(db|sqlite|sqlite3|pem|key)$' -or
        $relative -match '(^|[\\/])\.git([\\/]|$)') {
        throw "Sensitive/state file is forbidden in release manifest: $relative"
    }
    $source = [System.IO.Path]::GetFullPath((Join-Path $BundleRoot $relative))
    if (-not $source.StartsWith($bundlePrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Manifest path escapes the bundle folder: $relative"
    }
    Assert-File $source "manifest file $relative"
    $actualHash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualHash -ne $expectedHash) {
        throw "SHA-256 mismatch for $relative. No project files were changed."
    }
    $manifestEntries += [pscustomobject]@{ Relative = $relative; Hash = $expectedHash }
}
if ($manifestEntries.Count -lt 10) { throw 'Release manifest is unexpectedly small.' }

# The manifest itself is copied too, but is intentionally not self-hashed.
$manifestEntries += [pscustomobject]@{ Relative = 'MANIFEST_SHA256.txt'; Hash = $null }
$required = @(
    'app.py', 'templates/index.html', 'templates/admin_users.html',
    'backup_db.py', 'restore_db.py', 'reset_admin.py', 'security_hardening.py',
    'requirements.txt', 'requirements-rag.txt', '.env.example', '.gitignore', '.gitattributes',
    'test_release_integrity.py', 'INSTALL_RELEASE.ps1'
)
$present = @($manifestEntries | ForEach-Object { $_.Relative.Replace('\', '/') })
foreach ($name in $required) {
    if ($present -notcontains $name) { throw "Required release file missing from manifest: $name" }
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { throw 'Python was not found on PATH. No project files were changed.' }

# Show the exact target branch, working-tree state, and high-impact file differences.
$branch = & git -C $ProjectRoot branch --show-current 2>$null
if ($LASTEXITCODE -eq 0) { Write-Host "Target Git branch: $branch" }
$gitState = & git -C $ProjectRoot status --short 2>$null
if ($LASTEXITCODE -eq 0 -and $gitState) {
    Write-Host 'Existing Git changes (these are not discarded):' -ForegroundColor Yellow
    $gitState | ForEach-Object { Write-Host "  $_" }
}
foreach ($relative in @('app.py', 'templates/index.html')) {
    $source = Join-Path $BundleRoot $relative
    $target = Join-Path $ProjectRoot $relative
    if (Test-Path -LiteralPath $target -PathType Leaf) {
        $sourceInfo = Get-Item -LiteralPath $source
        $targetInfo = Get-Item -LiteralPath $target
        Write-Host ("{0}: bundle={1} bytes; project={2} bytes" -f $relative, $sourceInfo.Length, $targetInfo.Length)
        $sourceHash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
        $targetHash = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
        if ($sourceHash -ne $targetHash) { Write-Host "  DIFFERENT: $relative will be backed up before replacement." -ForegroundColor Yellow }
    }
}
Write-Host 'The installer will not modify .env, databases, data, Qdrant, backups, or Git history.'
$approval = Read-Host 'Review the differences. Type APPLY to install, or anything else to cancel'
if ($approval -cne 'APPLY') { throw 'Installation cancelled by user. No project files were changed.' }

# Stage all release files away from live targets and verify the staged copies.
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
$stageRoot = Join-Path $ProjectRoot ('.fbrah_release_staging_' + $stamp)
$backupRoot = Join-Path $ProjectRoot ('.fbrah_release_backup_' + $stamp)
New-Item -ItemType Directory -Path $stageRoot -ErrorAction Stop | Out-Null
$targetRecords = @()
$backupCreated = $false
$installStarted = $false

try {
    foreach ($entry in $manifestEntries) {
        $relative = Get-SafeRelativePath $entry.Relative
        $source = Join-Path $BundleRoot $relative
        $staged = Join-Path $stageRoot $relative
        $target = [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot $relative))
        if (-not $target.StartsWith($projectPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Target path escapes ProjectRoot: $relative"
        }
        $parent = Split-Path -Parent $staged
        if (-not (Test-Path -LiteralPath $parent)) {
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
        }
        Copy-Item -LiteralPath $source -Destination $staged -Force -ErrorAction Stop
        if ($null -ne $entry.Hash) {
            $stagedHash = (Get-FileHash -LiteralPath $staged -Algorithm SHA256).Hash.ToLowerInvariant()
            if ($stagedHash -ne $entry.Hash) { throw "Staging verification failed for $relative" }
        }
        if (Test-Path -LiteralPath $target -PathType Container) {
            throw "A directory exists where a release file should be: $target"
        }
        $targetRecords += [pscustomobject]@{ Relative = $relative; Target = $target; Staged = $staged; Existed = (Test-Path -LiteralPath $target -PathType Leaf) }
    }

    # Run the static suite from the staged package before touching the project.
    Push-Location $stageRoot
    try {
        & $python.Source -m unittest -v test_release_integrity.py
        if ($LASTEXITCODE -ne 0) { throw "Staged release tests failed (exit $LASTEXITCODE). No project files were changed." }
    }
    finally { Pop-Location }

    # Back up every file that will be replaced, preserving its relative path.
    New-Item -ItemType Directory -Path $backupRoot -ErrorAction Stop | Out-Null
    foreach ($record in $targetRecords) {
        if ($record.Existed) {
            $backup = Join-Path $backupRoot $record.Relative
            $backupParent = Split-Path -Parent $backup
            if (-not (Test-Path -LiteralPath $backupParent)) {
                New-Item -ItemType Directory -Path $backupParent -Force | Out-Null
            }
            Copy-Item -LiteralPath $record.Target -Destination $backup -Force -ErrorAction Stop
        }
    }
    $backupCreated = $true

    # Install only after every source has been verified and every existing target backed up.
    $installStarted = $true
    foreach ($record in $targetRecords) {
        $targetParent = Split-Path -Parent $record.Target
        if (-not (Test-Path -LiteralPath $targetParent)) {
            New-Item -ItemType Directory -Path $targetParent -Force | Out-Null
        }
        Copy-Item -LiteralPath $record.Staged -Destination $record.Target -Force -ErrorAction Stop
    }

    Push-Location $ProjectRoot
    try {
        & $python.Source -m unittest -v test_release_integrity.py
        if ($LASTEXITCODE -ne 0) { throw "Installed release tests failed (exit $LASTEXITCODE). Rolling back source files." }
    }
    finally { Pop-Location }

    Write-Host ''
    Write-Host 'FBRAH AI release files installed and verified.' -ForegroundColor Green
    Write-Host "Pre-install backup: $backupRoot"
    Write-Host 'No .env, database, data, Qdrant, backup database, or Git history was modified.'
    Write-Host 'Review git diff --check and git status --short. Do not commit or push automatically.'
}
catch {
    $failure = $_
    if ($installStarted -and $backupCreated) {
        foreach ($record in $targetRecords) {
            $backup = Join-Path $backupRoot $record.Relative
            if (Test-Path -LiteralPath $backup -PathType Leaf) {
                Copy-Item -LiteralPath $backup -Destination $record.Target -Force -ErrorAction Continue
            }
            elseif (-not $record.Existed -and (Test-Path -LiteralPath $record.Target -PathType Leaf)) {
                Remove-Item -LiteralPath $record.Target -Force -ErrorAction Continue
            }
        }
        Write-Host 'Installation failed; previous source files were restored from the pre-install backup.' -ForegroundColor Yellow
        Write-Host "Backup retained: $backupRoot"
    }
    throw $failure
}
finally {
    if (Test-Path -LiteralPath $stageRoot) {
        Remove-Item -LiteralPath $stageRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
