@echo off
setlocal
cd /d "%~dp0"
set "HASEEB_OLLAMA=ollama.exe"
where ollama.exe >nul 2>nul
if not errorlevel 1 goto pull
if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
 set "HASEEB_OLLAMA=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
 goto pull
)
echo Install Ollama from its official Windows download page.
echo After installation, run this file again.
start "" "https://ollama.com/download/windows"
pause
exit /b 1
:pull
echo Downloading qwen2.5:1.5b, approximately 986 MB. Internet required once.
echo Keep Ollama running. Its installation also needs several GB of disk space.
"%HASEEB_OLLAMA%" pull qwen2.5:1.5b
if errorlevel 1 (
 echo Download failed. Open Ollama from Start, check internet and try again.
 pause
 exit /b 1
)
echo Local AI ready. Open HASEEB AI and choose Local AI chat or AI action plan.
pause
