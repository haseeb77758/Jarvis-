@echo off
setlocal
cd /d "%~dp0"
echo HASEEB AI - Windows 11 setup
if exist .venv\Scripts\python.exe goto dependencies
py -3 -c "import sys, tkinter; assert sys.version_info >= (3,10)" >nul 2>nul
if not errorlevel 1 (
 py -3 -m venv .venv
 goto checkvenv
)
python -c "import sys, tkinter; assert sys.version_info >= (3,10)" >nul 2>nul
if not errorlevel 1 (
 python -m venv .venv
 goto checkvenv
)
echo Python 3.10 or newer with tkinter is required.
echo Install Python from the official page. Enable Add python.exe to PATH.
start "" "https://www.python.org/downloads/windows/"
echo After installation, run SETUP.bat again.
pause
exit /b 1
:checkvenv
if not exist .venv\Scripts\python.exe (
 echo Virtual environment creation failed. Extract the ZIP into a writable folder.
 pause
 exit /b 1
)
:dependencies
.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m unittest discover -s tests -v
if errorlevel 1 goto failed
echo Setup complete. Starting HASEEB AI.
call START.bat
exit /b
:failed
echo Setup failed. Check the error above and your internet connection, then retry.
pause
exit /b 1
