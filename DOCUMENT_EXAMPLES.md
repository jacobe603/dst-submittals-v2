# Document Structure Examples

This file shows how to organize your HVAC documents for processing with the DST Submittals Generator.

## Expected File Naming Patterns

The tool recognizes these document types based on filename patterns:

### Tagged Files (Recommended)
```
AHU-10 - Technical Data Sheet.docx
AHU-10 - Fan Curve.jpg
AHU-10 - Drawing.doc
MAU-12 - Technical Data Sheet.docx
MAU-12 - Fan Curve.pdf
```

### Numbered Files (Legacy Support)
```
10_Technical Data Sheet.docx
10_Fan Curve - Supply.jpg
10_PreciseLine Drawings.docx
12_Technical Data Sheet.docx
12_Fan Curve.doc
```

### Cut Sheets
```
CS_Air_Handler_Light_Kit.pdf
CS_Variable_Speed_Drive.pdf
CS_Filter_Media.pdf
```

## Directory Structure

Create your documents directory like this:

```
my_project_documents/
├── AHU-10 - Technical Data Sheet.docx
├── AHU-10 - Fan Curve.jpg
├── AHU-10 - Drawing.doc
├── MAU-12 - Technical Data Sheet.docx
├── MAU-12 - Fan Curve.pdf
├── CS_Air_Handler_Light_Kit.pdf
└── CS_Variable_Speed_Drive.pdf
```

## Supported File Types

- **Documents**: .doc, .docx (converted to PDF)
- **Images**: .jpg, .jpeg, .png (embedded in PDF)
- **PDFs**: .pdf (used directly)
- **Archives**: .zip (extracted automatically)

## Equipment Tag Patterns

The tool automatically detects these equipment patterns:

- `AHU-##` (Air Handling Units)
- `MAU-##` (Makeup Air Units)
- `Unit Tag: AHU-##` (in document content)
- Various other HVAC equipment identifiers

## Processing Order

Documents are organized in this order:
1. **MAU units** (numerical order: MAU-1, MAU-2, etc.)
2. **AHU units** (numerical order: AHU-1, AHU-2, etc.)
3. **Cut Sheets** section

Within each unit:
1. Technical Data Sheet
2. Fan Curve
3. Drawing
4. Other documents

## Getting Started

1. Create a folder with your HVAC documents
2. Use the naming patterns shown above
3. Run the DST Submittals Generator:
   ```bash
   python dst_submittals.py "path/to/your/documents"
   ```
   Or use the web interface:
   ```bash
   start_web_interface.bat
   ```

The tool will automatically organize everything into a professional submittal PDF!