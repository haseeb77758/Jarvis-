@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
 echo Run SETUP.bat first.
 pause
 exit /b 1
)
.venv\Scripts\python.exe -m pip install pyinstaller
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --windowed --onedir --name Jarvis app.py
if errorlevel 1 goto failed
echo Build complete: dist\Jarvis\Jarvis.exe
echo Keep the entire dist\Jarvis folder together. Ollama remains a separate installation.
pause
exit /b
:failed
echo EXE build failed. Read the error above.
pause
