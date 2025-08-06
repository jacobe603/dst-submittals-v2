#!/usr/bin/env python3
"""
Title page generator for DST Submittals using ReportLab
Creates professional title pages with perfect vertical centering
"""

import os
import tempfile
from typing import Optional

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    from .logger import get_logger
except ImportError:
    from logger import get_logger

logger = get_logger('title_page_generator')


class TitlePageGenerator:
    """
    ReportLab-based title page generator for DST Submittals
    
    Provides reliable PDF title page generation with perfect vertical centering,
    avoiding the CSS compatibility issues of HTML-to-PDF conversion.
    """
    
    def __init__(self):
        if not REPORTLAB_AVAILABLE:
            raise ImportError(
                "ReportLab is not available. Install with: pip install reportlab"
            )
        self.setup_styles()
        
    def setup_styles(self):
        """Setup title page styles using ReportLab"""
        self.styles = getSampleStyleSheet()
        
        # Create custom title style - large, bold, centered
        # Matches the original 48pt Helvetica-Bold requirement
        self.title_style = ParagraphStyle(
            'TitleStyle',
            parent=self.styles['Heading1'],
            fontSize=48,
            leading=60,
            alignment=TA_CENTER,
            textColor=colors.black,
            fontName='Helvetica-Bold',
            spaceAfter=0,
            spaceBefore=0
        )
        
        # Create subtitle style for additional info if needed
        self.subtitle_style = ParagraphStyle(
            'SubtitleStyle',
            parent=self.styles['Normal'],
            fontSize=18,
            leading=24,
            alignment=TA_CENTER,
            textColor=colors.darkblue,
            fontName='Helvetica',
            spaceAfter=0,
            spaceBefore=20
        )
    
    def create_title_page_pdf(self, equipment_tag: str, output_path: Optional[str] = None) -> str:
        """
        Create a title page PDF for the given equipment tag
        
        Args:
            equipment_tag: Equipment identifier (e.g., "BCU-1,2", "CUTSHEETS")
            output_path: Optional output path, creates temp file if None
        
        Returns:
            Path to the created PDF file
        
        Raises:
            RuntimeError: If PDF creation fails
        """
        try:
            # Handle output path
            if output_path is None:
                output_path = tempfile.mktemp(suffix=f'_title_{equipment_tag.replace("-", "_").replace(",", "_")}.pdf')
            
            # Transform equipment tag for display (same logic as HTML version)
            display_tag = equipment_tag.replace('CUTSHEETS', 'CUT SHEETS')
            
            # Create document with letter size (8.5" x 11")
            doc = SimpleDocTemplate(
                output_path,
                pagesize=letter,
                rightMargin=72,  # 1 inch margins
                leftMargin=72,
                topMargin=72,
                bottomMargin=72
            )
            
            story = []
            
            # Add vertical spacing to center the text vertically
            # 3.5 inches from top on 11" page = perfectly centered
            story.append(Spacer(1, 3.5*inch))
            
            # Add the main title
            story.append(Paragraph(display_tag, self.title_style))
            
            # Add some space after title
            story.append(Spacer(1, 1*inch))
            
            # Build the PDF
            doc.build(story)
            
            logger.info(f"Created ReportLab title page: {os.path.basename(output_path)} for tag '{display_tag}'")
            return output_path
            
        except Exception as e:
            error_msg = f"Failed to create title page PDF for {equipment_tag}: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
    
    def create_title_page_for_tag(self, equipment_tag: str) -> str:
        """
        Convenience method to create a title page with automatic file naming
        
        Args:
            equipment_tag: Equipment identifier
        
        Returns:
            Path to the created PDF file
        """
        filename = f"title_{equipment_tag.replace('-', '_').replace(',', '_').replace(' ', '_')}.pdf"
        output_path = tempfile.mktemp(suffix=f'_{filename}')
        return self.create_title_page_pdf(equipment_tag, output_path)
    
    def is_available(self) -> bool:
        """Check if ReportLab is available for title page generation"""
        return REPORTLAB_AVAILABLE
    
    @staticmethod
    def check_dependencies() -> dict:
        """
        Check if all dependencies are available
        
        Returns:
            Dictionary with dependency status
        """
        return {
            'reportlab': REPORTLAB_AVAILABLE,
            'status': 'ready' if REPORTLAB_AVAILABLE else 'missing_dependencies'
        }


def test_title_page_generator():
    """Test the title page generator"""
    if not REPORTLAB_AVAILABLE:
        print("ERROR: ReportLab not available. Install with: pip install reportlab")
        return False
    
    try:
        generator = TitlePageGenerator()
        
        # Test various equipment tags
        test_tags = ["BCU-1,2", "CUTSHEETS", "AHU-1", "MAU-5"]
        
        print("Testing ReportLab title page generation:")
        for tag in test_tags:
            pdf_path = generator.create_title_page_for_tag(tag)
            print(f"  ✓ Created: {pdf_path}")
            
            # Verify file exists and has content
            if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
                print(f"    File size: {os.path.getsize(pdf_path):,} bytes")
            else:
                print(f"    ERROR: File creation failed")
                return False
        
        print("\nAll title page tests passed!")
        return True
        
    except Exception as e:
        print(f"Test failed: {e}")
        return False


if __name__ == "__main__":
    # Run tests when executed directly
    success = test_title_page_generator()
    if success:
        print("\nTitle page generator is working correctly!")
    else:
        print("\nTitle page generator tests failed!")