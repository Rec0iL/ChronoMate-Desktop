@echo off
setlocal enabledelayedexpansion

title ChronoMate Desktop Launcher
cd /d "%~dp0"

echo ====================================================
echo    ChronoMate Desktop - Windows Launcher
echo ====================================================

:: 1. Locate Python
set "PY_CMD="
where py >nul 2>nul
if %errorlevel% equ 0 (
    py -3 --version >nul 2>nul
    if %errorlevel% equ 0 set "PY_CMD=py -3"
)

if not defined PY_CMD (
    where python >nul 2>nul
    if %errorlevel% equ 0 (
        python --version >nul 2>nul
        if %errorlevel% equ 0 set "PY_CMD=python"
    )
)

if not defined PY_CMD (
    where python3 >nul 2>nul
    if %errorlevel% equ 0 set "PY_CMD=python3"
)

if not defined PY_CMD (
    echo [ERROR] Python 3 was not found on your system.
    echo Please install Python from https://www.python.org/downloads/
    echo (Make sure to check "Add python.exe to PATH" during installation)
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('%PY_CMD% -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"') do set "PY_VER=%%i"
echo [INFO] Found Python %PY_VER% (%PY_CMD%)

:: 2. Check / Setup Virtual Environment (.venv)
if defined VIRTUAL_ENV (
    echo [INFO] Active virtual environment detected: %VIRTUAL_ENV%
    set "RUN_PY=python"
    set "RUN_PIP=pip"
) else if exist ".venv\Scripts\activate.bat" (
    echo [INFO] Activating local virtual environment (.venv)...
    call .venv\Scripts\activate.bat
    set "RUN_PY=python"
    set "RUN_PIP=pip"
) else (
    set "RUN_PY=%PY_CMD%"
    set "RUN_PIP=%PY_CMD% -m pip"
    
    :: Test if dependencies are already in system environment
    %PY_CMD% -c "import PySide6, requests, reportlab, numpy, openpyxl, pygame" >nul 2>nul
    if %errorlevel% neq 0 (
        echo [SETUP] Creating local virtual environment in .venv...
        %PY_CMD% -m venv .venv
        if exist ".venv\Scripts\activate.bat" (
            call .venv\Scripts\activate.bat
            set "RUN_PY=python"
            set "RUN_PIP=pip"
            echo [INFO] Virtual environment created and activated.
        ) else (
            echo [WARN] Could not create virtual environment. Using default Python...
        )
    )
)

:: 3. Verify Dependencies
echo [CHECK] Verifying application dependencies...
set "PYGAME_HIDE_SUPPORT_PROMPT=1"

%RUN_PY% -c "import PySide6, requests, reportlab, numpy, openpyxl, pygame" >nul 2>nul
if %errorlevel% neq 0 (
    echo [INSTALL] Installing missing dependencies from requirements.txt...
    %RUN_PIP% install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b %errorlevel%
    )
    echo [OK] All dependencies installed successfully!
) else (
    echo [OK] All dependencies are already installed and up to date.
)

:: 4. Launch Application
echo ====================================================
echo    Launching ChronoMate Desktop...
echo ====================================================

%RUN_PY% main.py %*
if %errorlevel% neq 0 (
    echo.
    echo Application exited with code %errorlevel%.
    pause
)
