@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
 echo First run SETUP.bat. Extract the ZIP before running.
 pause
 exit /b 1
)
.venv\Scripts\python.exe app.py
if errorlevel 1 (
 echo App stopped with an error. Keep the message above for troubleshooting.
 pause
)
