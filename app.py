import os
import json
import anthropic
import logging
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from pptx import Presentation
from pptx.util import Pt
from utils import analyze_resume
from PyPDF2 import PdfReader
from docx import Document

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configure folders
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'

# Create necessary folders
for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# Initialize Anthropic client
client = anthropic.Anthropic(
    api_key=os.environ.get('ANTHROPIC_API_KEY')
)

def extract_text_from_file(file):
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    try:
        text = ""
        if filename.endswith('.pdf'):
            with open(filepath, 'rb') as f:
                pdf = PdfReader(f)
                for page in pdf.pages:
                    text += page.extract_text()
        elif filename.endswith(('.doc', '.docx')):
            doc = Document(filepath)
            for para in doc.paragraphs:
                text += para.text + '\n'

        os.remove(filepath)  # Clean up temporary file
        return text.strip()
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        if os.path.exists(filepath):
            os.remove(filepath)
        raise ValueError("Error occurred while processing the file.")

def generate_portfolio(analysis_result):
    try:
        logger.debug("Starting portfolio generation...")

        # Create new presentation
        prs = Presentation()

        # Add title slide
        title_slide_layout = prs.slide_layouts[0]
        slide = prs.slides.add_slide(title_slide_layout)
        title = slide.shapes.title
        subtitle = slide.placeholders[1]

        # Set Pretendard font for title slide
        title.text = "{{company}}"
        title.text_frame.paragraphs[0].font.name = 'Pretendard'
        title.text_frame.paragraphs[0].font.size = Pt(44)
        title.text_frame.paragraphs[0].font.bold = True

        subtitle.text = "{{start_date}} - {{end_date}}"
        subtitle.text_frame.paragraphs[0].font.name = 'Pretendard'
        subtitle.text_frame.paragraphs[0].font.size = Pt(24)

        # Add content slides
        for project in analysis_result['work_experience']:
            bullet_slide_layout = prs.slide_layouts[1]
            slide = prs.slides.add_slide(bullet_slide_layout)

            # Set slide title
            title = slide.shapes.title
            title.text = "{{project}}"
            title.text_frame.paragraphs[0].font.name = 'Pretendard'
            title.text_frame.paragraphs[0].font.size = Pt(32)
            title.text_frame.paragraphs[0].font.bold = True

            # Add content
            body = slide.placeholders[1]
            tf = body.text_frame

            # Project details
            p = tf.add_paragraph()
            p.text = "프로젝트 상세"
            p.font.name = 'Pretendard'
            p.font.size = Pt(18)
            p.font.bold = True
            p.space_before = Pt(12)
            p.space_after = Pt(6)

            p = tf.add_paragraph()
            p.text = "{{details}}"
            p.font.name = 'Pretendard'
            p.font.size = Pt(14)
            p.space_after = Pt(12)

            # Results
            p = tf.add_paragraph()
            p.text = "주요 성과"
            p.font.name = 'Pretendard'
            p.font.size = Pt(18)
            p.font.bold = True
            p.space_before = Pt(12)
            p.space_after = Pt(6)

            p = tf.add_paragraph()
            p.text = "{{results}}"
            p.font.name = 'Pretendard'
            p.font.size = Pt(14)

        output_path = os.path.join(OUTPUT_FOLDER, 'portfolio.pptx')
        prs.save(output_path)
        logger.info("Portfolio generation completed successfully")
        return output_path

    except Exception as e:
        logger.error(f"Error generating portfolio: {str(e)}")
        raise ValueError("Error occurred while generating the portfolio.")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        resume_text = request.form.get('resume_text', '')
        if 'resume_file' in request.files:
            file = request.files['resume_file']
            if file.filename:
                file_text = extract_text_from_file(file)
                resume_text = file_text if not resume_text else resume_text + '\n' + file_text

        if not resume_text:
            return jsonify({'error': '이력서 내용이 비어있습니다.'}), 400

        # Check text length (approximate length for 4 projects)
        if len(resume_text.split()) > 2000:
            return jsonify({
                'error': '프로젝트/캠페인은 한번에 최대 4개까지 생성 가능합니다. 경력기술 내용이 너무 길다면 프로젝트를 4개씩 끊어서 입력해주세요 :)'
            }), 400

        # Log successful API call
        logger.info("Claude API 호출 성공")
        logger.debug("API 응답 내용을 참고해서 python-pptx 패키지를 활용하여 포트폴리오를 생성할거야.")

        # Analyze resume using Claude API
        analysis_result = analyze_resume(client, resume_text)

        # Generate PowerPoint
        pptx_path = generate_portfolio(analysis_result)

        return render_template('result.html', 
                            analysis=analysis_result,
                            pptx_path=pptx_path)

    except ValueError as e:
        logger.error(f"Value error in analyze: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error in analyze: {str(e)}")
        return jsonify({'error': '이력서 분석 중 오류가 발생했습니다.'}), 500

@app.route('/download/<filename>')
def download_file(filename):
    try:
        file_path = os.path.join(OUTPUT_FOLDER, filename)
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        return jsonify({'error': '파일 다운로드 중 오류가 발생했습니다.'}), 500