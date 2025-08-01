# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DST Submittals Generator is a Python tool for creating professional HVAC submittal documents. It processes .doc/.docx files and organizes them into structured PDFs with intelligent tag extraction, document ordering, and professional formatting.

**Key Requirements:**
- Windows OS with Microsoft Word installed (uses COM automation)
- Python 3.7+ with specific dependencies for document processing

## Common Commands

### Installation and Setup
```bash
pip install -r requirements.txt
```

### Environment Configuration
The tool supports environment variables for flexible configuration:

```bash
# Set OfficeToPDF path (if different from default)
set DST_OFFICETOPDF_PATH=C:\Tools\OfficeToPDF.exe

# Set custom output directories
set DST_CONVERTED_PDFS_DIR=output\pdfs
set DST_TITLE_PAGES_DIR=output\titles

# Set custom mapping file names
set DST_TAG_MAPPING_FILE=custom_tag_mapping.json
set DST_PDF_CONVERSION_MAPPING_FILE=custom_pdf_mapping.json

# Configure processing settings
set DST_CONVERSION_TIMEOUT=180
set DST_LIBREOFFICE_TIMEOUT=90

# Set default documents path for development/testing
set DST_DEFAULT_DOCS_PATH=C:\MyDocuments\HVAC_Submittals
```

**Environment Variables Reference:**
- `DST_OFFICETOPDF_PATH`: Path to OfficeToPDF.exe executable
- `DST_CONVERTED_PDFS_DIR`: Output directory for converted PDFs (default: converted_pdfs)
- `DST_TITLE_PAGES_DIR`: Output directory for title pages (default: title_pages)
- `DST_TAG_MAPPING_FILE`: JSON file for tag mappings (default: tag_mapping_enhanced.json)
- `DST_PDF_CONVERSION_MAPPING_FILE`: JSON file for conversion tracking (default: pdf_conversion_mapping.json)
- `DST_CONVERSION_TIMEOUT`: Conversion timeout in seconds (default: 120)
- `DST_LIBREOFFICE_TIMEOUT`: LibreOffice timeout in seconds (default: 60)
- `DST_DEFAULT_DOCS_PATH`: Default documents path for testing

### Running the Application
```bash
# Basic usage
python dst_submittals.py "path/to/documents"

# With verbose output
python dst_submittals.py "path/to/documents" --verbose

# Custom output filename
python dst_submittals.py "path/to/documents" -o "custom_submittal.pdf"

# Disable pricing filter
python dst_submittals.py "path/to/documents" --no-pricing-filter
```

### Development Commands
```bash
# Install with development dependencies
pip install -e .[dev]

# Run tests (if pytest is available)
pytest

# Code formatting (if black is available)
black src/

# Type checking (if mypy is available)
mypy src/
```

## Architecture Overview

### Core Components

**Processing Pipeline:**
1. **Tag Extraction** (`tag_extractor.py`) - Extracts equipment tags (AHU-1, MAU-12, etc.) from document content
2. **Document Enhancement** (`enhanced_doc_extractor.py`) - Processes .doc files with fallback methods
3. **PDF Conversion** (`high_quality_pdf_converter.py`) - Converts documents to PDF using Word COM automation
4. **Title Generation** (`title_page_generator.py`) - Creates professional title pages using ReportLab
5. **Final Assembly** (`create_final_pdf.py`) - Assembles documents in proper order with cut sheets

**Document Flow:**
- MAU tags processed first, then AHU tags (numerical order)
- Per tag order: Technical Data Sheet → Fan Curve → Drawing
- Automatic price filtering (pages with "$" symbols removed)
- CS*.pdf files added as cut sheets section

### Key Technical Details

**OfficeToPDF:** Primary conversion method for fastest, most reliable output. Uses command-line tool (configurable via `DST_OFFICETOPDF_PATH`, default: `C:\Users\jacob\Downloads\OfficeToPDF.exe`).

**Word COM Automation:** Fallback conversion method for highest quality output. Requires Word installation and proper COM object cleanup.

**Tag Detection Patterns:**
- `Unit Tag: AHU-10`
- `AHU-1`, `MAU-12` (direct matches)
- Various regex patterns for different document formats

**File Mappings:** The system creates JSON mappings (configurable via environment variables):
- Tag mapping file (default: `tag_mapping_enhanced.json`) - Tag to document relationships
- PDF conversion mapping file (default: `pdf_conversion_mapping.json`) - Conversion results tracking

## Important Considerations

### Windows-Specific Dependencies
- Uses `pywin32` for Word COM automation
- Fallback methods: docx2pdf, LibreOffice (if available)
- File path handling uses Windows conventions

### Error Handling and Logging
- **Structured Logging**: JSON and human-readable formats with correlation IDs for operation tracking
- **Custom Exceptions**: Domain-specific error types with remediation guidance and context
- **Robust Error Recovery**: COM automation cleanup prevents Word process hanging
- **Multiple Conversion Fallbacks**: Intelligent fallback methods for document conversion
- **Operation Tracking**: Each pipeline stage tracked with start/success/failure logging
- **User-Friendly Messages**: Clear error descriptions with actionable remediation steps

### Document Processing
- Handles both .doc and .docx formats
- Price filtering automatically excludes cost pages
- Professional formatting with 48pt Helvetica-Bold titles
- Maintains original document quality during conversion

## Development Notes

**Testing COM Automation:**
Check Word automation functionality by examining conversion logs and testing individual file processing.

**Debugging and Logging:**
- Use `--verbose` flag for detailed processing information
- Set `DST_LOG_LEVEL=DEBUG` for comprehensive logging
- Enable file logging with `DST_LOG_TO_FILE=true` for persistent logs
- JSON mapping files provide insight into tag extraction and conversion results
- Correlation IDs track operations across the entire pipeline
- Structured JSON logs available for automated monitoring and analysis

**File Organization:**
- Source code in `src/` directory
- Generated files: `converted_pdfs/`, `title_pages/` (configurable via environment variables)
- Output PDFs created in project root
- Configuration module: `src/config.py` handles environment variables and defaults

## Web Interface

### 🌐 **Core Functionality**
- **Drag & Drop Upload**: Support for individual files (.doc, .docx, .pdf) and ZIP archives
- **All CLI Options**: Complete web form interface for all command-line switches and environment variables
- **Network Access**: Can be accessed from other computers on the network using `start_web_interface_network.bat`
- **File Download**: Direct download of generated PDFs with proper filename handling
- **PDF Structure Editing**: Interactive preview and editing of document structure before generation
- **Collapsible Sections**: Clean, organized interface with collapsible sections for optimal workflow

### ⚡ **Real-Time Progress Reporting**
- **Live Updates**: Server-Sent Events (SSE) for real-time progress streaming without page refresh
- **Multi-Phase Tracking**: Detailed progress through 5 processing phases:
  1. **Setup** (0-5%): Environment configuration and validation
  2. **Tag Extraction** (10-20%): Document scanning and equipment identification  
  3. **PDF Conversion** (25-60%): File-by-file conversion with individual success/error tracking
  4. **Title Generation** (65-75%): Creating title pages for each equipment group
  5. **PDF Assembly** (80-90%): Combining documents with bookmarks and navigation
- **Detailed Logging**: Real-time activity log with timestamps and file-specific details
- **Error Reporting**: Individual file errors with context and remediation suggestions
- **Completion Summary**: Processing time, tags found, equipment groups created

### 📊 **Enhanced User Experience**
- **Professional Interface**: Modern responsive design with intuitive workflow
- **Background Processing**: Non-blocking operations with immediate response
- **Connection Management**: Automatic SSE connection handling with keepalive
- **File Progress Tracking**: Shows X/Y files processed during conversion phases
- **Correlation ID Tracking**: Each operation tracked with unique identifier for debugging

### 🚀 **Usage**

**Local Access:**
```bash
# Basic startup
start_web_interface.bat
# Or manually
python web_interface.py

# Access at: http://127.0.0.1:5000
```

**Network Access:**
```bash
# Network-enabled startup  
start_web_interface_network.bat
# Or manually
python web_interface.py --host 0.0.0.0 --port 5000

# Access from other computers: http://YOUR_IP_ADDRESS:5000
```

**Graceful Shutdown:**
```bash
# Recommended methods (in order of preference):
shutdown_web_interface.bat              # Batch file with HTTP + fallback
shutdown_web_interface.ps1              # PowerShell script with detailed feedback
# Press Ctrl+C in server window         # Direct keyboard interrupt
# POST http://127.0.0.1:5000/shutdown   # HTTP endpoint for automation
```

**Workflow:**
1. Drag and drop files or browse to select documents/ZIP files
2. Configure processing options through web form (all CLI options available)
3. Click "Generate Submittal PDF" to start processing
4. Watch real-time progress updates with detailed logging
5. Download generated PDF when complete

### 🔧 **Technical Architecture**
- **Flask Backend**: Handles file upload, processing coordination, and SSE streaming
- **Background Threading**: Processing runs in separate thread for responsiveness
- **ProgressManager**: Centralized progress tracking and event broadcasting
- **EventSource Frontend**: JavaScript EventSource for real-time SSE consumption
- **Memory Management**: Proper cleanup of resources, temporary files, and connections

## Entry Points

**Main CLI:** `dst_submittals.py` - Primary command-line interface
**Web Interface:** `web_interface.py` - Flask-based web server with real-time progress
**Setup Script:** `setup.py` provides console script entry point
**Module Import:** Components can be imported individually from `src/` directory