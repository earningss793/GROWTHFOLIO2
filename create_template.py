
from pptx import Presentation
from pptx.util import Pt
import os

def create_template():
    # Create a new presentation
    prs = Presentation()

    # Add title slide
    title_slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(title_slide_layout)
    title = slide.shapes.title
    subtitle = slide.placeholders[1]

    # Set title slide defaults
    title.text = "Portfolio Template"
    subtitle.text = "Date Range"

    for shape in slide.shapes:
        if shape.has_text_frame:
            for paragraph in shape.text_frame.paragraphs:
                paragraph.font.name = 'Pretendard'
                if shape == title:
                    paragraph.font.size = Pt(44)
                else:
                    paragraph.font.size = Pt(24)

    # Add content slide layout with text placeholder
    content_slide_layout = prs.slide_layouts[1]  # Using layout 1 which typically has title and content
    slide = prs.slides.add_slide(content_slide_layout)
    
    # Set title
    if slide.shapes.title:
        title = slide.shapes.title
        title.text = "Project Template"
        for paragraph in title.text_frame.paragraphs:
            paragraph.font.name = 'Pretendard'
            paragraph.font.size = Pt(32)

    # Create directory if it doesn't exist
    os.makedirs('templates/pptx', exist_ok=True)
    
    # Save the template
    template_path = os.path.join('templates', 'pptx', 'test_template.pptx')
    prs.save(template_path)
    print(f"Template created at {template_path}")

if __name__ == "__main__":
    create_template()
