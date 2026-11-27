@echo off
title FBRAH AI - Update Installer
echo ================================================
echo FBRAH AI - Complete Update Installer
echo ================================================
echo This launcher opens PowerShell, NOT the Python console.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0APPLY_UPDATE.ps1" -ProjectRoot "C:\Users\hatho\Desktop\Amit\Fbrah AI\Fbrah Ai G"
if errorlevel 1 (
  echo.
  echo Update did not complete. Read the error above.
) else (
  echo.
  echo Installer finished. Review the backup path above.
)
pause
