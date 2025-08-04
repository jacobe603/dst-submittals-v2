@echo off
echo DST Submittals Generator - Web Interface
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7+ and try again
    pause
    exit /b 1
)

REM Check if Flask is installed
python -c "import flask" >nul 2>&1
if %errorlevel% neq 0 (
    echo Flask not found. Installing dependencies...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
)

REM Create necessary directories
if not exist "uploads" mkdir uploads
if not exist "web_outputs" mkdir web_outputs
if not exist "templates" mkdir templates

echo Starting web interface...
echo.
echo Access the interface at: http://127.0.0.1:5000 (local)
echo Network access: http://YOUR_IP_ADDRESS:5000 (replace with your computer's IP)
echo.
echo SHUTDOWN OPTIONS:
echo   - Press Ctrl+C in this window for graceful shutdown, OR
echo   - Run shutdown_web_interface.bat from another window, OR  
echo   - POST to http://127.0.0.1:5000/shutdown endpoint
echo.

REM Start the web interface
python web_interface.py --host 0.0.0.0 --port 5000

pause