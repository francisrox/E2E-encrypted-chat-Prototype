@echo off
title SecureMsg v3 — ngrok Edition
color 0A
echo.
echo   =====================================================
echo    SecureMsg v3.0 — Internet Messaging via ngrok
echo   =====================================================
echo.

cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    echo   ERROR: Python not found. Install from https://python.org
    pause & exit /b 1
)

if not exist venv (
    echo   Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo   Installing dependencies...
pip install -r requirements.txt -q

echo.
echo   =====================================================
echo    STEP 1: This window will start the server on :8000
echo    STEP 2: Open a NEW terminal and run:
echo            ngrok http 8000
echo    STEP 3: Copy the https://xxxx.ngrok-free.app URL
echo    STEP 4: Share that URL with anyone, anywhere
echo   =====================================================
echo.

python -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
pause
