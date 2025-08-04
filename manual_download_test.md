# Manual Download API Test Guide

## Quick Download Test (Recommended)

### Step 1: Verify Files Exist
```bash
ls -la web_outputs/
```
Should show PDF files with reasonable sizes (> 1MB typically).

### Step 2: Start Web Server  
```bash
python3 web_interface.py
```
Server should start on http://localhost:5000

### Step 3: Test Download Directly
Open browser and visit a download URL directly:
```
http://localhost:5000/download/DST_Submittal_20250803_153309.pdf
```
(Replace with actual filename from Step 1)

**Expected Result**: PDF should download immediately or open in browser.

### Step 4: Test via Web Interface
1. Go to http://localhost:5000  
2. Upload some test files (use files from `test_files/` folder)
3. Click "Generate Submittal PDF"
4. When processing completes, click the download link
5. Verify PDF downloads and opens correctly

## Troubleshooting Download Issues

### Issue: 404 File Not Found

**Symptoms**: 
- Browser shows "File not found" error
- Network tab shows 404 status

**Causes & Solutions**:
1. **File doesn't exist in web_outputs/**
   ```bash
   ls -la web_outputs/
   ```
   If empty, generate a PDF first.

2. **Filename mismatch** 
   - Check server logs for exact filename being requested
   - Check if `secure_filename()` is changing the filename

3. **Permissions issue**
   ```bash
   chmod 644 web_outputs/*.pdf
   ```

### Issue: Download Starts But File Is Corrupt

**Symptoms**:
- File downloads but won't open
- PDF viewers show "corrupted file" error

**Solutions**:
1. **Check original file**:
   ```bash
   file web_outputs/filename.pdf
   head -c 10 web_outputs/filename.pdf
   ```
   Should show: `%PDF-1.4` or similar

2. **Check file size**:
   ```bash
   ls -lh web_outputs/filename.pdf
   ```
   Should be > 1MB for typical submittals

### Issue: Download Never Starts

**Symptoms**:
- Click download link but nothing happens
- Browser doesn't show download progress

**Solutions**:
1. **Check browser console** (F12 → Console tab)
2. **Check network tab** (F12 → Network tab)
3. **Try different browser**
4. **Check server logs** for error messages

### Issue: Server Not Responding

**Symptoms**:
- Cannot reach http://localhost:5000
- Connection refused errors

**Solutions**:
1. **Check if server is running**:
   ```bash
   ps aux | grep python
   lsof -i :5000
   ```

2. **Check server logs** for startup errors

3. **Try different port**:
   Edit web_interface.py line with `app.run()` to use different port

## API Testing with curl

Test download endpoint directly:
```bash
# List available files
ls web_outputs/

# Test download (replace filename)
curl -I http://localhost:5000/download/DST_Submittal_20250803_153309.pdf

# Download file
curl -O http://localhost:5000/download/DST_Submittal_20250803_153309.pdf
```

Expected headers:
```
HTTP/1.1 200 OK
Content-Type: application/pdf
Content-Disposition: attachment; filename=DST_Submittal_20250803_153309.pdf
```

## Automated Test

Run the comprehensive test script:
```bash
python3 test_download_comprehensive.py
```

This will:
- Check if files exist
- Start server if needed  
- Test download endpoints
- Simulate browser behavior
- Report any issues found

## Common File Patterns

Generated PDFs typically follow these patterns:
- `DST_Submittal_YYYYMMDD_HHMMSS.pdf` (timestamp format)
- `test_filename.pdf` (custom names)

All should be:
- Valid PDF files (start with `%PDF`)
- Reasonable size (1MB+ for real submittals)
- Readable permissions (644)

## Success Criteria

✅ **Download Working Correctly When**:
- PDF downloads immediately when clicking link
- Downloaded file opens in PDF viewer
- File size matches original
- No browser console errors
- Server logs show successful download requests

❌ **Download Broken When**:
- 404 errors for existing files
- Files download but are corrupted
- Download link does nothing
- Server errors in logs