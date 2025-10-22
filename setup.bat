@echo off
title Doctify Mirror Setup & Crawler
echo ==============================================
echo   SolVX Doctify.com Site Mirror Initialiser
echo ==============================================

REM Navigate to script directory
cd /d "%~dp0"

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ and rerun.
    pause
    exit /b
)

REM Create venv if missing
if not exist ".venv\" (
    echo [INFO] Creating virtual environment...
    python -m venv .venv
)

REM Activate environment
call .venv\Scripts\activate

REM Upgrade pip
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip >nul

REM Install dependencies
echo [INFO] Installing dependencies...
pip install requests beautifulsoup4 playwright >nul

REM Install browser if missing
if not exist "%USERPROFILE%\.cache\ms-playwright" (
    echo [INFO] Installing Playwright Chromium engine...
    playwright install chromium
)

REM Create mirror folder structure if missing
echo [INFO] Ensuring mirror folder structure...
mkdir mirror\raw 2>nul
mkdir mirror\rendered 2>nul
mkdir mirror\meta 2>nul
mkdir mirror\extracted 2>nul

REM Run the static crawler
echo [INFO] Starting static crawl (crawl_static.py)...
python crawl_static.py

REM Run dynamic renderer (optional)
echo.
choice /M "Run Playwright dynamic renderer now?"
if errorlevel 1 (
    python render_dynamic.py
)

echo.
echo [SUCCESS] Doctify mirror job complete.
pause
