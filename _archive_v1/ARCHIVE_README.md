# V1 Code Archive

This directory contains the original V1 (Windows-specific) implementation of DST Submittals Generator.

**Archived on:** August 3, 2025  
**Reason:** Migration to cross-platform V2 implementation using Gotenberg

## 📂 Archived Components

### **Core Processing Modules:**
- **`high_quality_pdf_converter.py`** - Windows Word COM automation and OfficeToPDF integration
- **`tag_extractor.py`** - Content-based tag extraction from document text
- **`enhanced_doc_extractor.py`** - Document enhancement and structure processing
- **`create_final_pdf.py`** - PDF assembly using PyPDF2/PyPDF libraries
- **`title_page_generator.py`** - ReportLab-based title page generation

### **Pipeline Framework:**
- **`pipeline/`** - Unused modular pipeline architecture
  - `base.py` - Pipeline stage base classes
  - `engine.py` - Pipeline execution engine
  - `checkpoint.py` - Stage checkpointing system

### **Stages:**
- **`stages/`** - Unused pipeline stage implementations
  - `tag_extraction.py` - Tag extraction stage
  - `tag_editing.py` - Interactive tag editing stage
  - `_TEMPLATE_stage.py` - Template for new stages

### **Utilities:**
- **`utils/`** - Utility modules
  - `debug_logger.py` - Debug logging utilities

### **Tests:**
- **`test_cli.py`** - V1 CLI interface tests
- **`test_conversion.py`** - V1 conversion functionality tests

### **Scripts:**
- **`start_web_interface.bat`** - Windows batch file for web interface
- **`start_web_interface_network.bat`** - Windows network-enabled startup
- **`shutdown_web_interface.bat`** - Windows shutdown script

### **Dependencies:**
- **`requirements_v1.txt`** - Original Windows-specific requirements including pywin32

## 🔄 Quick Restore Instructions

If you need to restore V1 functionality:

### 1. Restore Core Modules
```bash
cp -r _archive_v1/src/* src/
```

### 2. Restore Requirements
```bash
cp _archive_v1/requirements_v1.txt requirements.txt
```

### 3. Restore Scripts
```bash
cp _archive_v1/scripts/*.bat .
```

### 4. Restore Tests
```bash
cp _archive_v1/tests/* .
```

### 5. Re-enable V1 Imports
Edit these files and uncomment the lines marked with "V1 IMPORTS ARCHIVED":

**web_interface.py:**
- Line ~300: `from src.high_quality_pdf_converter import DocumentPDFConverter`
- Line ~371-376: Tag extractor, enhancer, converter, title generator, assembler imports
- Line ~1155-1156: Tag extractor and enhancer imports

**dst_submittals.py:**
- Line ~68-72: All V1 processing module imports

### 6. Remove V2-only Features
After restoring V1, you may need to:
- Remove V2-specific endpoints in web_interface.py
- Remove Gotenberg-related functionality
- Restore original CLI processing logic in dst_submittals.py

## ⚠️ Important Notes

### **Windows Dependencies:**
V1 functionality requires:
- Windows operating system
- Microsoft Word installed (for COM automation)
- pywin32 library for Windows API access
- OfficeToPDF.exe (optional but recommended)

### **Key Differences V1 vs V2:**

| Feature | V1 (Archived) | V2 (Current) |
|---------|---------------|--------------|
| Platform | Windows only | Cross-platform |
| PDF Conversion | Word COM/OfficeToPDF | Gotenberg |
| Tag Extraction | Content-based | Filename-based |
| Title Pages | ReportLab | HTML/CSS + Gotenberg |
| Pipeline | Complex stages | Simple processor |
| Dependencies | Heavy (Word, pywin32) | Lightweight |

### **Why V1 Was Archived:**

1. **Platform Limitation:** Required Windows and Microsoft Word
2. **Complexity:** Over-engineered pipeline architecture
3. **Reliability:** COM automation could hang or fail
4. **Maintenance:** Difficult to debug and maintain
5. **Performance:** Slower than filename-based extraction

## 🆕 V2 Advantages

The current V2 implementation provides:
- **Cross-platform compatibility** (Mac, Linux, Windows)
- **Docker-based PDF conversion** (Gotenberg)
- **Simplified architecture** following design philosophy
- **Better error handling** with detailed context
- **Real-time progress tracking** 
- **Interactive structure editing**
- **PDF bookmarks and navigation**
- **Improved debugging and logging**

## 📚 Migration Notes

If migrating from V1 to V2:

1. **File Naming:** Ensure files follow the format: `TAG-NUMBER - Document Type.extension`
2. **Structure:** Use the V2 web interface to preview and edit document structure
3. **Testing:** V2 includes comprehensive validation and error reporting
4. **Configuration:** V2 uses environment variables instead of complex config files

## 🔍 Code References

For implementation details, see:
- **V2 Processor:** `src/simple_processor.py`
- **V2 Tag Extraction:** `src/simple_tag_extractor.py` 
- **V2 Conversion:** `src/gotenberg_converter.py`
- **V2 Validation:** `src/validator.py`
- **Design Philosophy:** `DESIGN_PHILOSOPHY.md`

---

*This archive preserves the complete V1 implementation for historical reference and emergency rollback scenarios.*