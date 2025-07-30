@echo off
echo DST Submittals Generator - Web Interface (Network Access)
echo ========================================================
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

REM Get the computer's IP address
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4 Address"') do (
    set "ip=%%a"
    goto :found_ip
)
:found_ip
set ip=%ip: =%

echo Starting web interface with network access...
echo.
echo Local access:   http://127.0.0.1:5000
echo Network access: http://%ip%:5000
echo.
echo Other computers on your network can access this at:
echo   http://%ip%:5000
echo.
echo SECURITY WARNING: This exposes the interface to your entire network!
echo Only run this on trusted networks.
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start the web interface with network access
python web_interface.py --host 0.0.0.0 --port 5000

pause