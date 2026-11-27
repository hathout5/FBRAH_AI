param([string]$ProjectRoot = "")
& (Join-Path $PSScriptRoot "APPLY_UPDATE.ps1") -ProjectRoot $ProjectRoot
