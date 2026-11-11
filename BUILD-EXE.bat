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
.venv\Scripts\python.exe tools\prepare_voice_model.py
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --windowed --onefile --name Jarvis --collect-all faster_whisper --collect-all ctranslate2 --collect-all tokenizers --collect-all onnxruntime --collect-all av --collect-all _sounddevice_data --collect-submodules pywinauto --collect-submodules comtypes --hidden-import win32com.client --add-data "build-assets/voice-model;voice-model" app.py
if errorlevel 1 goto failed
echo Build complete: dist\Jarvis.exe
echo This is a single EXE. Use its Setup local AI button for optional Ollama setup.
pause
exit /b
:failed
echo EXE build failed. Read the error above.
pause
