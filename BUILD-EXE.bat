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
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --windowed --onefile --name Jarvis --collect-all edge_tts --copy-metadata edge-tts --collect-all certifi --collect-all faster_whisper --collect-all ctranslate2 --collect-all tokenizers --collect-all onnxruntime --collect-all av --collect-all _sounddevice_data --collect-submodules pywinauto --collect-submodules comtypes --hidden-import win32com.client --add-data "web/connect.html;web" --add-data "web/connect.js;web" --add-data "web/connect.css;web" --add-data "build-assets/voice-model;voice-model" --add-data "EDGE-TTS-LICENSE.txt;." --add-data "GPL-3.0.txt;." --add-data "THIRD-PARTY-NOTICES.txt;." app.py
if errorlevel 1 goto failed
echo Build complete: dist\Jarvis.exe
echo This is a single EXE. Use Connect AI for optional account sign-in chat; no API key required.
pause
exit /b
:failed
echo EXE build failed. Read the error above.
pause

