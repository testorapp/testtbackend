@echo off
echo ============================================
echo   Testora Backend - Local Server Launcher
echo ============================================
echo.

:: Navigate to the script directory
cd /d "%~dp0"

:: Activate the virtual environment
echo [*] Activating virtual environment...
call .venv\Scripts\activate.bat

:: Check if activation succeeded
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment.
    echo Make sure .venv exists in the project directory.
    pause
    exit /b 1
)

echo [*] Virtual environment activated.
echo.

:: Run the Flask development server
echo [*] Starting Flask server on http://0.0.0.0:5001
echo [*] Local access: http://127.0.0.1:5001
echo [*] Network access: http://YOUR_IP:5001
echo [*] Press Ctrl+C to stop the server
echo.

python app.py

:: If the script exits, keep the window open
echo.
echo [*] Server stopped.
pause

