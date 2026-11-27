@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0CONFIGURE_FBRAH_WINDOWS_SOUND.ps1"
pause
