@echo off
cd /d "%~dp0"
set /p FBRAH_USER=Enter the FBRAH username for Windows notifications: 
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" fbrah_reminder_worker.py --username "%FBRAH_USER%"
) else (
  python fbrah_reminder_worker.py --username "%FBRAH_USER%"
)
