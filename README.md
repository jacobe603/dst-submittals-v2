# DST Submittals Generator

A comprehensive Python tool for generating professional HVAC submittal documents with an intuitive web interface, real-time progress tracking, and intelligent document processing.

## 🚀 Key Features

### 🌐 **Modern Web Interface**
- **Drag & Drop Upload**: Support for individual files (.doc, .docx, .pdf, .zip)
- **Real-Time Progress**: Live updates with Server-Sent Events (SSE)
- **Interactive PDF Structure**: Edit document order and titles before generation
- **Network Access**: Access from other computers on your network
- **Professional UI**: Responsive design with collapsible sections
- **Cleanup Management**: Real-time disk usage monitoring and manual cleanup controls

### 🤖 **Intelligent Processing**
- **Smart Tag Extraction**: Automatically identifies equipment tags (AHU-1, MAU-12, etc.)
- **Multi-Format Support**: Handles .doc, .docx, images, and PDF files
- **Automatic Organization**: Orders documents as Technical Data Sheet → Fan Curve → Drawing
- **Price Filtering**: Excludes pages with pricing information
- **Cut Sheets Integration**: Dedicated section for CS*.pdf files

### 🔧 **Production Ready**
- **Multiple Conversion Methods**: Word COM, OfficeToPDF, LibreOffice fallbacks
- **Comprehensive Logging**: Structured logging with correlation IDs
- **Error Recovery**: Robust error handling and user feedback
- **Graceful Shutdown**: Proper resource cleanup and shutdown procedures
- **Automatic Cleanup**: Intelligent disk space management with configurable retention policies

## 📋 Requirements

### System Requirements
- **Windows OS** (required for Microsoft Word COM automation)
- **Microsoft Word** installed (2010 or later recommended)
- **Python 3.7+**

### Quick Start
1. **Download** the latest release or clone this repository
2. **Install dependencies**: `pip install -r requirements.txt`
3. **Start the web interface**: Double-click `start_web_interface.bat`
4. **Open your browser** to `http://127.0.0.1:5000`

## 🎯 Usage

### Web Interface (Recommended)

**Local Access:**
```bash
# Start the web interface
start_web_interface.bat

# Access at: http://127.0.0.1:5000
```

**Network Access:**
```bash
# Start with network access
start_web_interface_network.bat

# Access from other computers: http://YOUR_IP_ADDRESS:5000
```

**Workflow:**
1. Drag and drop your HVAC documents (.doc, .docx, .pdf, .zip)
2. Click "Get Tags & Preview Structure" to analyze your files
3. Review and edit the PDF structure (optional)
4. Click "Generate Submittal PDF" and watch real-time progress
5. Download your professional submittal PDF
6. Monitor disk usage and cleanup status in the Cleanup Management section

### Command Line Interface

```bash
# Basic usage
python dst_submittals.py "path/to/documents"

# With custom output filename
python dst_submittals.py "path/to/documents" -o "Project_Submittal.pdf"

# Include pricing pages
python dst_submittals.py "path/to/documents" --no-pricing-filter

# Enable verbose output
python dst_submittals.py "path/to/documents" --verbose
```

## 📁 Document Organization

### Expected File Structure
```
your_documents/
├── AHU-10 - Technical Data Sheet.docx
├── AHU-10 - Fan Curve.jpg
├── AHU-10 - Drawing.doc
├── MAU-12 - Technical Data Sheet.docx
├── MAU-12 - Fan Curve.pdf
├── CS_Air_Handler_Light_Kit.pdf
└── CS_Variable_Speed_Drive.pdf
```

### Supported Naming Patterns
- **Tagged Files**: `AHU-10 - Technical Data Sheet.docx`
- **Numbered Files**: `10_Technical Data Sheet.docx`
- **Cut Sheets**: `CS_*.pdf`

See [DOCUMENT_EXAMPLES.md](DOCUMENT_EXAMPLES.md) for detailed guidance.

## 🔧 Configuration

### Environment Variables
```bash
# Set custom OfficeToPDF path
set DST_OFFICETOPDF_PATH=C:\Tools\OfficeToPDF.exe

# Custom output directories
set DST_CONVERTED_PDFS_DIR=output\pdfs
set DST_TITLE_PAGES_DIR=output\titles

# Processing timeouts
set DST_CONVERSION_TIMEOUT=180
set DST_LIBREOFFICE_TIMEOUT=90
```

### Advanced Options
The web interface provides access to all configuration options:
- Output filename customization
- Pricing filter control
- Timeout settings
- Directory configurations
- Logging levels

## 🏗️ Architecture

### Core Components
- **`web_interface.py`** - Flask web server with real-time progress
- **`src/tag_extractor.py`** - Intelligent equipment tag detection
- **`src/high_quality_pdf_converter.py`** - Multi-method document conversion
- **`src/enhanced_doc_extractor.py`** - PDF structure generation
- **`src/create_final_pdf.py`** - Professional document assembly
- **`src/title_page_generator.py`** - Title page creation

### Processing Pipeline
1. **File Upload & Validation** - Secure file handling and validation
2. **Tag Extraction** - Equipment identification from document content
3. **PDF Conversion** - High-quality document conversion with fallbacks
4. **Structure Generation** - Intelligent document organization
5. **Title Creation** - Professional title pages for each equipment group
6. **Final Assembly** - PDF compilation with bookmarks and navigation

## 🚨 Error Handling

### Robust Error Recovery
- **Multiple Conversion Methods**: Automatic fallback between Word COM, OfficeToPDF, and LibreOffice
- **File Access Errors**: Graceful handling of locked or missing files
- **COM Automation**: Automatic Word application cleanup
- **Network Issues**: Proper timeout handling and retry logic
- **User Feedback**: Clear error messages with remediation suggestions

### Logging & Diagnostics
- **Structured Logging**: JSON format with correlation IDs
- **Real-Time Monitoring**: Live progress updates and error reporting
- **Debug Information**: Comprehensive logging for troubleshooting
- **Performance Metrics**: Processing time and success rate tracking

## 💡 Tips for Best Results

1. **Use Tagged Filenames**: `AHU-10 - Technical Data Sheet.docx` works better than generic names
2. **Include Equipment Tags**: Place tags prominently in document headers
3. **Organize Files**: Keep related documents in the same directory
4. **Check Dependencies**: Ensure Word or OfficeToPDF is properly installed
5. **Network Performance**: Use local access for fastest processing

## ⚙️ Configuration

### Environment Variables

The application supports various environment variables for customization:

**Cleanup Management:**
```bash
set DST_MAX_OUTPUT_FILES=10          # Max PDFs to keep in web_outputs (default: 10)
set DST_OUTPUT_RETENTION_DAYS=7      # Days to keep PDFs (default: 7)
set DST_CLEANUP_ON_STARTUP=true      # Run cleanup at startup (default: true)
set DST_PERIODIC_CLEANUP_HOURS=24    # Background cleanup interval, 0 to disable (default: 24)
```

**Processing Settings:**
```bash
set DST_CONVERSION_TIMEOUT=120       # Document conversion timeout in seconds
set DST_LIBREOFFICE_TIMEOUT=60       # LibreOffice timeout in seconds
set DST_PDF_RESOLUTION=300           # PDF image resolution in DPI
set DST_JPEG_QUALITY=100             # Word COM export JPEG quality (0-100)
```

**Output Directories:**
```bash
set DST_CONVERTED_PDFS_DIR=converted_pdfs    # Converted PDFs directory
set DST_TITLE_PAGES_DIR=title_pages          # Title pages directory
```

**Logging:**
```bash
set DST_LOG_LEVEL=INFO               # Logging level (DEBUG, INFO, WARNING, ERROR)
set DST_LOG_TO_FILE=false            # Enable file logging
set DST_LOG_FILE_PATH=dst_submittals.log     # Log file path
```

## 🛠️ Troubleshooting

### Common Issues

**Web Interface Won't Start:**
```bash
# Check if port 5000 is available
netstat -an | find "5000"

# Try alternative port
python web_interface.py --port 8080
```

**Document Conversion Fails:**
- Ensure Microsoft Word is installed and properly licensed
- Try installing OfficeToPDF for faster conversion
- Check file permissions and document accessibility

**Missing Dependencies:**
```bash
pip install --upgrade -r requirements.txt
```

**Disk Space Issues:**
- Check the Cleanup Status section in the web interface
- Run manual cleanup: click "Run Cleanup Now" button
- Adjust cleanup settings via environment variables
- Monitor `web_outputs/` directory size

**Cleanup Not Working:**
```bash
# Check cleanup configuration
echo $DST_MAX_OUTPUT_FILES
echo $DST_OUTPUT_RETENTION_DAYS

# Manual cleanup via API
curl -X POST http://127.0.0.1:5000/api/cleanup/run

# Check cleanup status
curl http://127.0.0.1:5000/api/cleanup/status
```

### Getting Help
- Check the [SHUTDOWN_GUIDE.md](SHUTDOWN_GUIDE.md) for shutdown procedures
- Review [DOCUMENT_EXAMPLES.md](DOCUMENT_EXAMPLES.md) for file organization
- See [CLAUDE.md](CLAUDE.md) for detailed technical documentation

## 🚀 Deployment

### Local Development
```bash
git clone https://github.com/jacobe603/dst-submittals-generator.git
cd dst-submittals-generator
pip install -r requirements.txt
python web_interface.py
```

### Network Deployment
```bash
# Allow network access
python web_interface.py --host 0.0.0.0 --port 5000

# Or use the batch file
start_web_interface_network.bat
```

## 📈 Performance

- **Processing Speed**: 2-5 seconds per document (varies by method)
- **Memory Efficiency**: Optimized for large document collections
- **Quality Preservation**: Maintains original formatting and resolution
- **Scalability**: Tested with 100+ document collections
- **Real-Time Updates**: Sub-second progress reporting

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/jacobe603/dst-submittals-generator/issues)
- **Documentation**: Check the included .md files
- **Examples**: See [DOCUMENT_EXAMPLES.md](DOCUMENT_EXAMPLES.md)

## 🎉 Acknowledgments

- **Microsoft Word COM** for professional-quality document conversion
- **Flask & Server-Sent Events** for real-time web interface
- **ReportLab** for beautiful title page generation
- **pypdf** for reliable PDF manipulation

---

**DST Submittals Generator** - Professional HVAC submittal creation with modern web interface and intelligent automation.

🌐 **Try it now**: Clone the repo, run `start_web_interface.bat`, and drag in your documents!