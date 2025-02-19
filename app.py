import os
import json
import anthropic
import logging
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
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

# Create necessary folders
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

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

        # Check text length (approximate length for 4 projects)
        if len(resume_text.split()) > 2000:
            return jsonify({
                'error': '프로젝트/캠페인은 한번에 최대 4개까지 생성 가능합니다. 경력기술 내용이 너무 길다면 프로젝트를 4개씩 끊어서 입력해주세요 :)'
            }), 400

        # Log successful API call
        logger.info("Claude API 호출 성공")

        # Analyze resume using Claude API
        analysis_result = analyze_resume(client, resume_text)

        return render_template('result.html', analysis=analysis_result)

    except ValueError as e:
        logger.error(f"Value error in analyze: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error in analyze: {str(e)}")
        return jsonify({'error': '이력서 분석 중 오류가 발생했습니다.'}), 500

## 프로젝트 추가 생성
@app.route('/api/projects', methods=['POST'])
def add_project():
    try:
        # 중복 요청 방지를 위한 요청 헤더 확인
        request_id = request.headers.get('X-Request-Id')
        if not request_id:
            return jsonify({'error': '요청 ID가 필요합니다.'}), 400

        data = request.get_json()
        if not data or 'project_name' not in data:
            return jsonify({'error': '프로젝트명이 필요합니다.'}), 400

        project_name = data['project_name']
        if not project_name.strip():
            return jsonify({'error': '유효한 프로젝트명을 입력해주세요.'}), 400

        # Claude API를 사용하여 프로젝트 세부사항 생성
        prompt = f"""다음 프로젝트에 대한 구체적인 업무 내용 5가지와 수치화된 성과 3가지를 생성해주세요:

프로젝트명: {project_name}

출력 형식:
{{
    "project_name": "프로젝트명",
    "details": [
        "구체적인 업무 내용 1",
        "구체적인 업무 내용 2",
        "구체적인 업무 내용 3",
        "구체적인 업무 내용 4",
        "구체적인 업무 내용 5"
    ],
    "results": [
        "수치화된 성과 1",
        "수치화된 성과 2",
        "수치화된 성과 3"
    ]
}}"""

        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        # API 응답에서 JSON 추출
        content = response.content[0].text
        json_start = content.find('{')
        json_end = content.rfind('}') + 1
        if json_start == -1 or json_end == 0:
            raise ValueError("API 응답을 처리할 수 없습니다")

        result = json.loads(content[json_start:json_end])
        return jsonify(result)

    except json.JSONDecodeError as e:
        logger.error(f"JSON 파싱 오류: {str(e)}")
        return jsonify({'error': 'API 응답을 처리할 수 없습니다.'}), 500
    except Exception as e:
        logger.error(f"프로젝트 추가 중 오류 발생: {str(e)}")
        return jsonify({'error': '프로젝트 추가 중 오류가 발생했습니다.'}), 500