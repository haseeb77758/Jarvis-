@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title HASEEB AI - Windows 11 Installer
color 0B
echo.
echo ============================================================
echo    HASEEB AI - JARVIS    Windows 11 Installer
echo    Created by Haseeb Crafts
echo ============================================================
echo.
echo This installer keeps Windows Security and Smart App Control ON.
echo It uses the official Python runtime, not the blocked unsigned EXE.
echo Python and Jarvis dependencies are installed only with approval.
echo.
if not exist "tools\install_windows.py" (
    echo ERROR: Extract the complete ZIP first, then run this installer.
    goto :failed
)
:detect
set "PYTHON_EXE="
py -3.12 -c "import tkinter; import sys; assert sys.version_info[:2] == (3,12)" >nul 2>nul
if not errorlevel 1 goto :run_py
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -c "import tkinter; import sys; assert sys.version_info[:2] == (3,12)" >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
        goto :run_exe
    )
)
if exist "%ProgramFiles%\Python312\python.exe" (
    "%ProgramFiles%\Python312\python.exe" -c "import tkinter; import sys; assert sys.version_info[:2] == (3,12)" >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_EXE=%ProgramFiles%\Python312\python.exe"
        goto :run_exe
    )
)
echo Official Python 3.12 was not found.
where winget >nul 2>nul
if errorlevel 1 goto :python_manual
echo.
echo Windows Package Manager can install official Python 3.12.
choice /C YN /N /M "Install Python 3.12 from the winget source? [Y/N]: "
if errorlevel 2 goto :cancelled
winget install --id Python.Python.3.12 --exact --source winget --scope user --accept-source-agreements --accept-package-agreements
if errorlevel 1 goto :python_manual
echo.
echo Python installation finished. Checking available Python runtime...
goto :detect
:run_py
echo Official Python 3.12 detected.
py -3.12 tools\install_windows.py
if errorlevel 1 goto :failed
goto :success
:run_exe
echo Official Python 3.12 detected.
"%PYTHON_EXE%" "tools\install_windows.py"
if errorlevel 1 goto :failed
goto :success
:python_manual
echo.
echo Could not install Python automatically on this computer.
echo Please install Python 3.12 from https://www.python.org/downloads/windows/
echo and double-click INSTALL-JARVIS.cmd again.
start "" "https://www.python.org/downloads/windows/"
goto :failed
:cancelled
echo Installation cancelled. Nothing was installed by Jarvis.
exit /b 1
:success
echo.
echo Jarvis was installed successfully.
echo Look for "HASEEB AI - Jarvis" on your Desktop.
echo You can also launch it from the Start Menu.
timeout /t 5 >nul
exit /b 0
:failed
echo.
echo Installation did not complete. See the error above.
echo Windows security settings were not changed.
pause
exit /b 1
