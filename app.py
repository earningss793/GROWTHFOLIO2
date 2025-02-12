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

        template_path = os.path.join('templates', 'pptx', 'test_template.pptx')
        if not os.path.exists(template_path):
            raise ValueError(f"Template file not found: {template_path}")

        prs = Presentation(template_path)

        # Process each slide in the presentation
        for slide in prs.slides:
            for shape in slide.shapes:
                if not shape.has_text_frame:
                    continue

                text_frame = shape.text_frame
                for paragraph in text_frame.paragraphs:
                    for run in paragraph.runs:
                        text = run.text
                        # Replace company variable
                        if '{{company}}' in text:
                            text = text.replace('{{company}}', analysis_result['work_experience'][0]['company'])
                        
                        # Replace project variable
                        if '{{project}}' in text:
                            text = text.replace('{{project}}', analysis_result['work_experience'][0]['responsibilities'][0]['project'])
                        
                        # Replace details variable
                        if '{{details}}' in text:
                            details = analysis_result['work_experience'][0]['responsibilities'][0]['details']
                            details_text = "\n".join([f"• {detail}" for detail in details])
                            text = text.replace('{{details}}', details_text)
                        
                        # Replace results variable
                        if '{{results}}' in text:
                            results = analysis_result['work_experience'][0]['responsibilities'][0]['results']
                            results_text = "\n".join([f"• {result}" for result in results])
                            text = text.replace('{{results}}', results_text)
                        
                        run.text = text

        output_path = os.path.join(OUTPUT_FOLDER, 'portfolio.pptx')
        prs.save(output_path)
        logger.info(f"Portfolio saved successfully at {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"Error generating portfolio: {str(e)}")
        raise ValueError(f"Failed to generate portfolio: {str(e)}")

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

        if len(resume_text.split()) > 2000:
            return jsonify({
                'error': '프로젝트/캠페인은 한번에 최대 4개까지 생성 가능합니다. 경력기술 내용이 너무 길다면 프로젝트를 4개씩 끊어서 입력해주세요 :)'
            }), 400

        logger.info("Claude API 호출 성공")
        analysis_result = analyze_resume(client, resume_text)
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
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return jsonify({'error': '파일을 찾을 수 없습니다.'}), 404

        if not os.path.getsize(file_path):
            logger.error(f"Empty file: {file_path}")
            return jsonify({'error': '파일이 비어있습니다.'}), 400

        try:
            response = send_file(
                file_path,
                as_attachment=True,
                download_name='portfolio.pptx',
                mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation'
            )
            response.headers.update({
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0',
                'X-Content-Type-Options': 'nosniff'
            })
            return response
        except Exception as e:
            logger.error(f"Error sending file: {str(e)}")
            return jsonify({'error': '파일 전송 중 오류가 발생했습니다.'}), 500

    except Exception as e:
        logger.error(f"Error in download route: {str(e)}")
        return jsonify({'error': '파일 다운로드 중 오류가 발생했습니다.'}), 500