@echo off
setlocal enabledelayedexpansion

echo DST Submittals Generator - Web Interface Shutdown
echo ================================================

REM Check if the server is running before attempting to shut it down
curl -s http://127.0.0.1:5000/status >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo Server is not running.
    pause
    exit /b 0
)

echo.
echo Attempting to gracefully shutdown the web interface...

REM Try to shutdown via HTTP endpoint first
curl -X POST http://127.0.0.1:5000/shutdown 2>nul
if %errorlevel% == 0 (
    echo.
    echo Shutdown request sent successfully.
    echo The server should shutdown gracefully.
    pause
    exit /b 0
)

echo.
echo Could not reach server via HTTP. Trying alternative methods...

REM Try to find and kill Python processes running web_interface.py
echo Searching for Python processes...

REM Check for different Python executable names
set PYTHON_FOUND=0
for %%p in (python.exe python3.exe py.exe pythonw.exe) do (
    for /f "tokens=2 delims= " %%i in ('tasklist /fi "imagename eq %%p" /fo table /nh 2^>nul ^| findstr /i "%%p"') do (
        echo Found %%p process with PID: %%i
        set PYTHON_FOUND=1
        
        REM Try to terminate the process
        taskkill /pid %%i /f >nul 2>&1
        if !errorlevel! == 0 (
            echo Successfully terminated %%p process %%i
        ) else (
            echo Failed to terminate %%p process %%i
        )
    )
)

if !PYTHON_FOUND! == 0 (
    echo No Python processes found.
)

REM Also try killing processes on port 5000
for /f "tokens=5 delims= " %%i in ('netstat -ano ^| findstr ":5000"') do (
    echo Found process using port 5000: %%i
    taskkill /pid %%i /f >nul 2>&1
    if !errorlevel! == 0 (
        echo Successfully terminated process %%i
    )
)

echo.
echo Shutdown attempts completed.
echo.
pause