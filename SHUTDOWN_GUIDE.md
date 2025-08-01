# DST Submittals Generator - Server Shutdown Guide

This guide explains how to properly shutdown the web interface server for the DST Submittals Generator.

## Quick Start

### ✅ Recommended Method: Batch File
```bash
# From command prompt or file explorer
shutdown_web_interface.bat
```

### ✅ Alternative: PowerShell Script  
```powershell
# From PowerShell (run as administrator if needed)
powershell -ExecutionPolicy Bypass -File shutdown_web_interface.ps1
```

### ✅ Keyboard Shortcut
```
Press Ctrl+C in the server window
```

## Shutdown Methods

### 1. **Graceful Shutdown via Batch File** (Recommended)
- **File**: `shutdown_web_interface.bat`
- **Method**: HTTP POST to `/shutdown` endpoint
- **Fallback**: Process termination if HTTP fails
- **Benefits**: 
  - Waits for active file processing to complete
  - Cleans up temporary files automatically
  - Works even if server is unresponsive

### 2. **PowerShell Script**
- **File**: `shutdown_web_interface.ps1`  
- **Method**: HTTP POST with process detection fallback
- **Features**:
  - Colored output for better visibility
  - Detailed process information
  - Comprehensive error handling

### 3. **Keyboard Interrupt (Ctrl+C)**
- **Method**: Signal handling in server process
- **Benefits**: 
  - Immediate response
  - Proper cleanup execution
  - Standard server shutdown method

### 4. **HTTP Endpoint**
- **URL**: `POST http://127.0.0.1:5000/shutdown`
- **Response**: JSON with shutdown status
- **Use Case**: Integration with other tools/scripts

### 5. **Manual Process Termination** (Last Resort)
```bash
# Find Python processes
tasklist | findstr python.exe

# Kill specific process ID  
taskkill /pid [PID] /f

# Kill all processes using port 5000
for /f "tokens=5" %i in ('netstat -ano ^| findstr ":5000"') do taskkill /pid %i /f
```

## Shutdown Behavior

### **Graceful Shutdown Process:**

1. **Signal Received**: Server receives shutdown request
2. **Stop New Requests**: New file processing requests are rejected  
3. **Wait for Active Processes**: Server waits up to 30 seconds for:
   - File uploads to complete
   - PDF conversions to finish
   - Document processing to wrap up
4. **Cleanup Resources**:
   - Close all client connections
   - Remove temporary directories
   - Clear progress tracking data
   - Release file handles
5. **Exit**: Server terminates cleanly

### **Force Shutdown (if graceful fails):**
- Automatically triggered after 30-second timeout
- Terminates all active processes immediately
- Attempts cleanup but may leave temporary files

## Server Status Monitoring

### Check Server Status
```bash
# HTTP request to status endpoint
curl http://127.0.0.1:5000/status
```

**Response includes:**
- Server readiness
- Number of active processes  
- Shutdown status
- Configuration details

### Example Status Response:
```json
{
  "status": "ready",
  "active_processes": 2,
  "shutdown_initiated": false,
  "officetopdf_path": "C:\\Tools\\OfficeToPDF.exe"
}
```

## Troubleshooting

### **Problem**: Shutdown script reports "Could not reach server"
**Solution**: 
- Server may already be stopped
- Check if port 5000 is in use: `netstat -ano | findstr :5000`
- Try manual process termination

### **Problem**: Server won't stop processing files
**Solution**:
- Wait for current processing to complete (up to 30 seconds)
- Use force shutdown: `taskkill /f /im python.exe`
- Check for locked files in temporary directories

### **Problem**: "Access Denied" when running shutdown script
**Solution**:
- Run Command Prompt as Administrator
- Or use PowerShell method: `shutdown_web_interface.ps1`

### **Problem**: Temporary files not cleaned up
**Solution**:
- Manual cleanup: Delete `dst_web_*` folders in temp directory
- Location: `%TEMP%\dst_web_*`
- Use: `rd /s /q %TEMP%\dst_web_*`

## Best Practices

### ✅ **Do:**
- Use the provided shutdown scripts
- Wait for file processing to complete when possible
- Check status before shutdown during heavy usage
- Run shutdown from Administrator command prompt if needed

### ❌ **Don't:**
- Force kill processes during active file processing
- Delete temporary files while server is running
- Shutdown during large file uploads (unless emergency)
- Use Task Manager unless other methods fail

## Integration Examples

### **Scheduled Shutdown** (Windows Task Scheduler)
```bash  
# Daily shutdown at 11 PM
schtasks /create /tn "DST Shutdown" /tr "C:\path\to\shutdown_web_interface.bat" /sc daily /st 23:00
```

### **Batch File with Confirmation**
```batch
@echo off
echo This will shutdown the DST web server.
set /p confirm="Continue? (y/n): "
if /i "%confirm%"=="y" (
    call shutdown_web_interface.bat
) else (
    echo Shutdown cancelled.
)
pause
```

### **PowerShell Remote Shutdown**
```powershell
# Shutdown server on remote machine
Invoke-Command -ComputerName "ServerName" -ScriptBlock {
    Invoke-RestMethod -Uri "http://localhost:5000/shutdown" -Method POST
}
```

## Automated Monitoring

### **Check if Server is Running**
```batch
@echo off
curl -s http://127.0.0.1:5000/status >nul 2>&1
if %errorlevel% == 0 (
    echo Server is running
) else (
    echo Server is not running
)
```

### **Wait for Shutdown Completion**
```powershell
do {
    try {
        $response = Invoke-RestMethod -Uri "http://127.0.0.1:5000/status" -TimeoutSec 5
        Write-Host "Server still running... waiting"
        Start-Sleep -Seconds 2
    } catch {
        Write-Host "Server shutdown complete"
        break
    }
} while ($true)
```

## Security Notes

- Shutdown endpoint (`/shutdown`) has no authentication by design for local use
- For production use, consider adding authentication to shutdown endpoint
- Scripts will attempt to terminate Python processes - use with caution in multi-Python environments
- PowerShell script requires execution policy bypass for unsigned scripts

## Support

If you encounter issues with server shutdown:

1. Check the server logs for error messages
2. Verify no critical file operations are in progress
3. Ensure you have sufficient permissions
4. Try the alternative shutdown methods in order
5. As last resort, restart your computer to clear all processes

The shutdown system is designed to be robust and handle various failure scenarios gracefully while protecting your data and system resources.