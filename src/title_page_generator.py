#!/usr/bin/env python3
"""
Title page generator for CS Air Handler PDF documents
Creates professional title pages for each TAG and CUT SHEETS section
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER

class TitlePageGenerator:
    def __init__(self, output_dir: str = "title_pages"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.setup_styles()
        
    def setup_styles(self):
        """Setup title page styles"""
        self.styles = getSampleStyleSheet()
        
        # Create custom title style - large, bold, centered
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
    
    def create_tag_title_page(self, tag: str) -> str:
        """Create a title page for a specific TAG"""
        filename = f"title_{tag.replace('-', '_')}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        
        # Create document
        doc = SimpleDocTemplate(
            filepath,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        story = []
        
        # Add vertical spacing to center the text vertically
        story.append(Spacer(1, 3.5*inch))
        
        # Add the main title
        story.append(Paragraph(tag, self.title_style))
        
        # Add some space after title
        story.append(Spacer(1, 1*inch))
        
        # Build the PDF
        doc.build(story)
        
        print(f"Created title page: {filename}")
        return filepath
    
    def create_cut_sheets_title_page(self) -> str:
        """Create a title page for the CUT SHEETS section"""
        filename = "title_CUT_SHEETS.pdf"
        filepath = os.path.join(self.output_dir, filename)
        
        # Create document
        doc = SimpleDocTemplate(
            filepath,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        story = []
        
        # Add vertical spacing to center the text vertically
        story.append(Spacer(1, 3.5*inch))
        
        # Add the main title
        story.append(Paragraph("CUT SHEETS", self.title_style))
        
        # Add some space after title
        story.append(Spacer(1, 1*inch))
        
        # Build the PDF
        doc.build(story)
        
        print(f"Created title page: {filename}")
        return filepath
    
    def create_all_title_pages(self, tags: list) -> dict:
        """Create title pages for all tags and cut sheets"""
        print("="*60)
        print("CREATING TITLE PAGES")
        print("="*60)
        
        title_pages = {}
        
        # Create title page for each tag
        for tag in tags:
            title_path = self.create_tag_title_page(tag)
            title_pages[tag] = title_path
        
        # Create cut sheets title page
        cut_sheets_path = self.create_cut_sheets_title_page()
        title_pages['CUT_SHEETS'] = cut_sheets_path
        
        print(f"\nCreated {len(title_pages)} title pages")
        return title_pages

def main():
    """Test the title page generator"""
    # Get tags from the mapping
    import json
    
    with open('tag_mapping_enhanced.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Get unique tags and sort them
    tags = list(data['tag_groups'].keys())
    sorted_tags = sorted(tags, key=lambda x: (
        x.startswith('MAU-'),  # MAU tags first
        x.replace('AHU-', '').replace('MAU-', '').zfill(10)  # Then AHU tags sorted
    ))
    
    # Create title pages
    generator = TitlePageGenerator()
    title_pages = generator.create_all_title_pages(sorted_tags)
    
    print(f"\nTitle pages saved to: {generator.output_dir}/")
    
    return generator, title_pages

if __name__ == "__main__":
    generator, title_pages = main()