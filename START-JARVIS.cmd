@echo off
setlocal
cd /d "%~dp0"
echo HASEEB AI - reviewable source launcher
echo No Windows security settings will be changed.
where py >nul 2>nul
if errorlevel 1 (
  echo Official Python launcher not found.
  echo Install Python from https://www.python.org/downloads/windows/
  pause
  exit /b 1
)
py -3 RUN-JARVIS.py
if errorlevel 1 (
  echo.
  echo Jarvis could not start. Read the error above and SMART-APP-CONTROL.md.
  pause
  exit /b 1
)
exit /b 0
