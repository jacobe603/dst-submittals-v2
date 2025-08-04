# DST Submittals Generator V2 API Documentation

## 🔗 Available API Endpoints

### **GET /status-v2**
Get V2 service status and health check
- **Response:** JSON with gotenberg, tag_extractor, and processor status
- **Example:** `curl http://localhost:5000/status-v2`

### **GET /api/v2/structure**
Get current document structure from JSON file
- **Response:** JSON structure with equipment_structure and processing_order
- **Example:** `curl http://localhost:5000/api/v2/structure`

### **POST /api/v2/save-structure**
Save document structure to JSON file
- **Body:** JSON structure data
- **Response:** Success/error status

### **POST /api/v2/reload-structure**
Reload structure from JSON file
- **Response:** Updated structure data

### **POST /extract-tags-v2**
Extract tags from uploaded files (V2 filename-based)
- **Body:** Multipart form with files
- **Response:** Extracted structure with equipment groups
- **Example:**
```bash
curl -X POST -F "files=@AHU-1_Technical_Data.docx" \
     -F "files=@AHU-1_Fan_Curve.pdf" \
     http://localhost:5000/extract-tags-v2
```

### **POST /upload-v2**
Upload files and generate PDF with real-time progress
- **Body:** Multipart form with files and options
- **Response:** Processing results and download link
- **Example:**
```bash
curl -X POST -F "files=@file1.docx" -F "files=@file2.pdf" \
     -F "output_filename=my_submittal.pdf" \
     -F "quality_mode=high" \
     http://localhost:5000/upload-v2
```

### **GET /progress/<correlation_id>**
Real-time progress updates via Server-Sent Events
- **Response:** SSE stream with progress updates
- **JavaScript Example:**
```javascript
const eventSource = new EventSource("/progress/your-correlation-id");
eventSource.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log(`Progress: ${data.progress}% - ${data.message}`);
};
```

## 🎯 Tag Extraction API Results

The tag extraction API returns structured JSON like this:

```json
{
  "success": true,
  "total_equipment": 3,
  "total_files": 7,
  "processing_order": ["MAU-12", "AHU-0", "AHU-09"],
  "structure": {
    "MAU-12": {
      "order": 1,
      "documents": [
        {
          "filename": "MAU-12 - Technical Data Sheet.doc",
          "type": "technical_data",
          "position": 1
        },
        {
          "filename": "MAU-12 - Fan Curve.doc", 
          "type": "fan_curve",
          "position": 2
        }
      ]
    },
    "AHU-0": {
      "order": 2,
      "documents": [
        {
          "filename": "AHU-0 - Technical Data Sheet.docx",
          "type": "technical_data", 
          "position": 1
        },
        {
          "filename": "AHU-0 - Fan Curve - Supply.jpg",
          "type": "fan_curve",
          "position": 2
        },
        {
          "filename": "AHU-0 - PreciseLine Drawings.docx",
          "type": "drawing",
          "position": 3
        }
      ]
    }
  }
}
```

## 📋 Supported File Naming Patterns

The tag extraction works with these filename patterns:

- **Equipment Tags:** `AHU-1`, `MAU-12`, `EF-3`, `RTU-5`, `FCU-10`, `VAV-15`, `CAV-20`
- **Document Types:**
  - `Technical Data Sheet` → `technical_data`
  - `Fan Curve` → `fan_curve`
  - `Drawing` / `Drawings` → `drawing`
  - `Item Summary` → `item_summary`
  - `Specification` → `specification`
  - `CS_*` → `cutsheet`

**Example Filenames:**
- ✅ `AHU-1 - Technical Data Sheet.docx`
- ✅ `MAU-12 - Fan Curve.pdf`
- ✅ `EF-3 - SmartSource Drawing.png`
- ✅ `CS - Light Kit.pdf`

## ✨ Key Features

- ✅ **Cross-platform** (Mac/Linux/Windows)
- ✅ **Filename-based** tag extraction (fast, reliable)
- ✅ **Real-time progress** tracking via SSE
- ✅ **PDF bookmarks** and navigation
- ✅ **Interactive structure** editing
- ✅ **JSON persistence** as single source of truth
- ✅ **Comprehensive validation** and error handling
- ✅ **Gotenberg integration** for high-quality PDF conversion

## 🚀 Quick Start

1. **Start the server:**
   ```bash
   python web_interface.py
   ```

2. **Open browser:** http://localhost:5000

3. **Or use API directly:**
   ```bash
   # Check status
   curl http://localhost:5000/status-v2
   
   # Extract tags from files
   curl -X POST -F "files=@your_files.docx" \
        http://localhost:5000/extract-tags-v2
   ```

## 🔍 Direct Module Testing

You can also test the tag extraction directly without the web server:

```python
import sys
sys.path.append('src')
from simple_processor import SimpleProcessor

processor = SimpleProcessor()
result = processor.extract_tags_only(['AHU-1 - Technical Data.docx'], 'test-id')
print(result)
```

This approach is perfect for testing and integration into other systems!