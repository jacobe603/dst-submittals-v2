# DST Submittals Generator - Web Interface Shutdown (PowerShell)
# Usage: powershell -ExecutionPolicy Bypass -File shutdown_web_interface.ps1

Write-Host "DST Submittals Generator - Web Interface Shutdown" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# Try to shutdown via HTTP endpoint first
Write-Host "Attempting graceful shutdown via HTTP endpoint..." -ForegroundColor Yellow

try {
    $response = Invoke-RestMethod -Uri "http://127.0.0.1:5000/shutdown" -Method POST -TimeoutSec 10
    Write-Host "SUCCESS: $($response.message)" -ForegroundColor Green
    Write-Host "Active processes: $($response.active_processes)" -ForegroundColor Green
    
    if ($response.active_processes -gt 0) {
        Write-Host "Waiting for processes to complete..." -ForegroundColor Yellow
        Start-Sleep -Seconds 5
    }
    
    Write-Host "Shutdown completed successfully." -ForegroundColor Green
    
} catch {
    Write-Host "Could not reach server via HTTP: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Trying alternative shutdown methods..." -ForegroundColor Yellow
    
    # Try to find and kill Python processes
    $pythonNames = @("python", "python3", "py", "pythonw")
    $foundPython = $false
    
    foreach ($name in $pythonNames) {
        $pythonProcesses = Get-Process -Name $name -ErrorAction SilentlyContinue
        
        if ($pythonProcesses) {
            $foundPython = $true
            Write-Host "Found $name processes. Checking for web interface..." -ForegroundColor Yellow
            
            foreach ($process in $pythonProcesses) {
                try {
                    $commandLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($process.Id)").CommandLine
                    if ($commandLine -and $commandLine.Contains("web_interface.py")) {
                        Write-Host "Terminating web interface process $name (PID: $($process.Id))" -ForegroundColor Yellow
                        Stop-Process -Id $process.Id -Force
                        Write-Host "Process terminated successfully." -ForegroundColor Green
                    }
                } catch {
                    # Try to terminate anyway if we can't check the command line
                    try {
                        Write-Host "Terminating $name process (PID: $($process.Id)) - could not verify command line" -ForegroundColor Yellow
                        Stop-Process -Id $process.Id -Force
                        Write-Host "Process terminated successfully." -ForegroundColor Green
                    } catch {
                        Write-Host "Could not check or terminate process $($process.Id): $($_.Exception.Message)" -ForegroundColor Red
                    }
                }
            }
        }
    }
    
    if (-not $foundPython) {
        Write-Host "No Python processes found." -ForegroundColor Yellow
    }
    
    # Check for processes using port 5000
    try {
        $netstat = netstat -ano | Select-String ":5000"
        if ($netstat) {
            Write-Host "Found processes using port 5000:" -ForegroundColor Yellow
            foreach ($line in $netstat) {
                $pid = ($line -split '\s+')[-1]
                if ($pid -match '^\d+$') {
                    Write-Host "Terminating process using port 5000 (PID: $pid)" -ForegroundColor Yellow
                    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                }
            }
        }
    } catch {
        Write-Host "Could not check port usage: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Final check to confirm shutdown
Start-Sleep -Seconds 2
$stillRunning = $false

# Check all Python process types
foreach ($name in @("python", "python3", "py", "pythonw")) {
    $pythonProcesses = Get-Process -Name $name -ErrorAction SilentlyContinue
    if ($pythonProcesses) {
        foreach ($process in $pythonProcesses) {
            try {
                $commandLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($process.Id)").CommandLine
                if ($commandLine -and $commandLine.Contains("web_interface.py")) {
                    $stillRunning = $true
                    Write-Host "Warning: Found still running $name process (PID: $($process.Id))" -ForegroundColor Red
                    break
                }
            } catch {
                # Ignore errors from processes that disappear during the check
            }
        }
        if ($stillRunning) { break }
    }
}

# Also check if port 5000 is still in use
try {
    $portCheck = netstat -ano | Select-String ":5000" | Select-String "LISTENING"
    if ($portCheck) {
        $stillRunning = $true
        Write-Host "Warning: Port 5000 is still in use" -ForegroundColor Red
    }
} catch {
    # Ignore netstat errors
}

if (-not $stillRunning) {
    Write-Host "Server has been successfully shut down." -ForegroundColor Green
} else {
    Write-Host "Server may still be running. Please check Task Manager." -ForegroundColor Red
}

Write-Host ""
Write-Host "Shutdown process completed." -ForegroundColor Cyan
Write-Host "Press any key to continue..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")