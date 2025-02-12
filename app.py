import os
import json
import anthropic
import logging
from flask import Flask, render_template, request, jsonify, send_file, session
from werkzeug.utils import secure_filename
from pptx import Presentation 
from utils import analyze_resume
from PyPDF2 import PdfReader
from docx import Document
import shutil

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

        # Copy template to output folder
        template_path = os.path.join('templates', 'pptx', 'test_template.pptx')
        output_path = os.path.join(OUTPUT_FOLDER, 'portfolio.pptx')

        if not os.path.exists(template_path):
            return jsonify({'error': '템플릿 파일을 찾을 수 없습니다.'}), 500

        shutil.copy2(template_path, output_path)

        return render_template('result.html', 
                            analysis=analysis_result,
                            pptx_path=output_path)

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

@app.route('/save_portfolio', methods=['POST'])
def save_portfolio():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '데이터가 없습니다.'}), 400

        # 수정된 데이터를 세션에 저장
        session['portfolio_data'] = data

        return jsonify({'message': '포트폴리오가 성공적으로 저장되었습니다.'}), 200
    except Exception as e:
        logger.error(f"Error saving portfolio: {str(e)}")
        return jsonify({'error': '저장 중 오류가 발생했습니다.'}), 500