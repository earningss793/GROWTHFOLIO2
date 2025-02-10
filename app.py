import os
import json
import anthropic
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from pptx import Presentation
from pptx.util import Pt
from utils import analyze_resume
import logging
from PyPDF2 import PdfReader
from docx import Document

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

        os.remove(filepath)  # 임시 파일 삭제
        return text.strip()
    except Exception as e:
        logging.error(f"파일 처리 중 오류 발생: {str(e)}")
        if os.path.exists(filepath):
            os.remove(filepath)
        raise ValueError("파일 처리 중 오류가 발생했습니다.")

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

        # 텍스트 길이 체크 (대략적인 프로젝트 4개 분량)
        if len(resume_text.split()) > 2000:  # 단어 수로 체크
            return jsonify({
                'error': '프로젝트/캠페인은 한번에 최대 4개까지 생성 가능합니다. 경력기술 내용이 너무 길다면 프로젝트를 4개씩 끊어서 입력해주세요 :)'
            }), 400

        # Analyze resume using Claude API
        analysis_result = analyze_resume(client, resume_text)

        # Generate PowerPoint
        pptx_path = generate_portfolio(analysis_result)

        return render_template('result.html', 
                            analysis=analysis_result,
                            pptx_path=pptx_path)

    except ValueError as e:
        logging.error(f"Value error in analyze: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logging.error(f"Unexpected error in analyze: {str(e)}")
        return jsonify({'error': '이력서 분석 중 오류가 발생했습니다.'}), 500


#포트폴리오 생성(생성에집중)
def generate_portfolio(analysis_result):
    try:
        # 새로운 프레젠테이션 생성
        prs = Presentation()

        # 타이틀 슬라이드 추가
        title_slide_layout = prs.slide_layouts[0]
        slide = prs.slides.add_slide(title_slide_layout)
        title = slide.shapes.title
        subtitle = slide.placeholders[1]

        # 타이틀 슬라이드 폰트 설정
        title.text_frame.paragraphs[0].font.name = 'Pretendard'
        title.text_frame.paragraphs[0].font.size = Pt(44)
        title.text_frame.paragraphs[0].font.bold = True
        subtitle.text_frame.paragraphs[0].font.name = 'Pretendard'
        subtitle.text_frame.paragraphs[0].font.size = Pt(24)

        # 분석 결과를 슬라이드별 데이터 리스트로 변환
        data_list = []
        for exp in analysis_result['work_experience']:
            for resp in exp['responsibilities']:
                data = {
                    "company": exp['company'],
                    "team": exp['team'],
                    "project": resp['project'],
                    "details": "\n".join(f"• {detail}" for detail in resp['details']),
                    "results": "\n".join(f"• {result}" for result in resp['results'])
                }
                data_list.append(data)

        # 슬라이드별 데이터 삽입
        for idx, data in enumerate(data_list):
            if idx == 0:  # 첫 번째 데이터는 타이틀 슬라이드에 사용
                title.text = data["company"]
                subtitle.text = data["team"]
            else:  # 나머지 데이터는 새 슬라이드에 추가
                bullet_slide_layout = prs.slide_layouts[1]
                slide = prs.slides.add_slide(bullet_slide_layout)

                # 슬라이드 제목 설정
                title = slide.shapes.title
                title.text = data["project"]
                title.text_frame.paragraphs[0].font.name = 'Pretendard'
                title.text_frame.paragraphs[0].font.size = Pt(32)
                title.text_frame.paragraphs[0].font.bold = True

                # 본문 내용 설정
                body = slide.placeholders[1]
                tf = body.text_frame

                # 상세 내용 추가
                p = tf.add_paragraph()
                p.text = "프로젝트 상세"
                p.font.name = 'Pretendard'
                p.font.size = Pt(18)
                p.font.bold = True
                p.space_before = Pt(12)
                p.space_after = Pt(6)

                p = tf.add_paragraph()
                p.text = data["details"]
                p.font.name = 'Pretendard'
                p.font.size = Pt(14)
                p.space_after = Pt(12)

                # 성과 추가
                p = tf.add_paragraph()
                p.text = "주요 성과"
                p.font.name = 'Pretendard'
                p.font.size = Pt(18)
                p.font.bold = True
                p.space_before = Pt(12)
                p.space_after = Pt(6)

                p = tf.add_paragraph()
                p.text = data["results"]
                p.font.name = 'Pretendard'
                p.font.size = Pt(14)

        output_path = os.path.join(OUTPUT_FOLDER, 'portfolio.pptx')
        prs.save(output_path)
        logging.info("포트폴리오 생성 완료")
        return output_path

    except Exception as e:
        logging.error(f"포트폴리오 생성 중 오류 발생: {str(e)}")
        raise ValueError("포트폴리오 생성 중 오류가 발생했습니다.")

@app.route('/download/<filename>')
def download_file(filename):
    try:
        file_path = os.path.join(OUTPUT_FOLDER, filename)
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        logging.error(f"파일 다운로드 중 오류 발생: {str(e)}")
        return jsonify({'error': '파일 다운로드 중 오류가 발생했습니다.'}), 500



from flask import Flask, send_file, render_template, request
from utils import fill_template_with_api_response

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download_portfolio', methods=['POST'])
def download_portfolio():
    # 클라이언트로부터 API 응답 데이터를 받음
    api_response_json = request.json

    # 템플릿 파일 경로 지정 (상대경로 사용, raw string 권장)
    template_path = r"templates\pptx\test_template.pptx"
    output_path = "output_presentation.pptx"

    # 템플릿을 채우고 파일 생성
    fill_template_with_api_response(api_response_json, template_path, output_path)

    # 생성된 파일을 클라이언트에게 전송
    return send_file(output_path, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)