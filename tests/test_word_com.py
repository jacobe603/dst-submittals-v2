#!/usr/bin/env python3
"""
Test Word COM automation with a single file
"""

import os
import win32com.client

def test_word_com_single_file():
    """Test converting a single .doc file"""
    
    # Test with one specific file
    test_file = r"C:\Users\jacob\Claude\python-docx\documents\CS_Air_Handler_Light_Kit\13_Drawing.doc"
    output_file = r"C:\Users\jacob\Claude\python-docx\test_13_Drawing.pdf"
    
    if not os.path.exists(test_file):
        print(f"Test file not found: {test_file}")
        return False
    
    try:
        print(f"Testing Word COM with: {os.path.basename(test_file)}")
        
        # Create Word application
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        print("Word application created")
        
        try:
            # Open document
            print("Opening document...")
            doc = word.Documents.Open(test_file, ReadOnly=True)
            print("Document opened successfully")
            
            # Export as PDF
            print("Exporting to PDF...")
            doc.ExportAsFixedFormat(
                OutputFileName=output_file,
                ExportFormat=17,  # PDF format
                OpenAfterExport=False,
                OptimizeFor=1,  # wdExportOptimizeForPrint = 1 (for quality)
                BitmapMissingFonts=True,
                DocStructureTags=False,
                CreateBookmarks=False
            )
            print("PDF export completed")
            
            # Close document
            doc.Close()
            print("Document closed")
            
        finally:
            # Always quit Word
            word.Quit()
            print("Word application closed")
        
        if os.path.exists(output_file):
            print(f"[SUCCESS] PDF created at {output_file}")
            print(f"File size: {os.path.getsize(output_file)} bytes")
            return True
        else:
            print("[FAILED] PDF file not created")
            return False
            
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        try:
            word.Quit()
        except:
            pass
        return False

if __name__ == "__main__":
    success = test_word_com_single_file()
    if success:
        print("\nWord COM automation is working!")
    else:
        print("\nWord COM automation failed!")