import os
import json
import anthropic
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from pptx import Presentation
from pptx.util import Pt
from utils import analyze_resume
import logging
import shutil

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configure folders
OUTPUT_FOLDER = 'output'
TEMPLATE_FOLDER = 'templates/pptx'

# Create necessary folders
for folder in [OUTPUT_FOLDER, TEMPLATE_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# 기본 템플릿 복사 (처음 한 번만)
default_template_path = os.path.join(TEMPLATE_FOLDER, 'default_template.pptx')
if not os.path.exists(default_template_path):
    # 새로운 빈 프레젠테이션 생성
    prs = Presentation()

    # 타이틀 슬라이드 추가
    title_slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(title_slide_layout)
    title = slide.shapes.title
    subtitle = slide.placeholders[1]
    title.text = "{{company}}"
    subtitle.text = "{{team}}"

    # 컨텐츠 슬라이드 추가 (3개)
    for _ in range(3):
        bullet_slide_layout = prs.slide_layouts[1]
        slide = prs.slides.add_slide(bullet_slide_layout)
        title = slide.shapes.title
        body = slide.placeholders[1]

        title.text = "{{project}}"
        body_frame = body.text_frame
        p = body_frame.add_paragraph()
        p.text = "{{details}}"
        p = body_frame.add_paragraph()
        p.text = "{{results}}"

    # 기본 템플릿 저장
    prs.save(default_template_path)

# Initialize Anthropic client
client = anthropic.Anthropic(
    api_key=os.getenv('ANTHROPIC_API_KEY')
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload_template', methods=['POST'])
def upload_template():
    if 'template' not in request.files:
        return jsonify({'error': '템플릿 파일이 선택되지 않았습니다.'}), 400

    file = request.files['template']
    if file.filename == '':
        return jsonify({'error': '템플릿 파일이 선택되지 않았습니다.'}), 400

    if not file.filename.endswith('.pptx'):
        return jsonify({'error': 'PPTX 파일만 업로드 가능합니다.'}), 400

    try:
        filename = secure_filename('template.pptx')
        filepath = os.path.join(TEMPLATE_FOLDER, filename)
        file.save(filepath)
        return jsonify({'message': '템플릿이 성공적으로 업로드되었습니다.'}), 200
    except Exception as e:
        logging.error(f"템플릿 업로드 중 오류 발생: {str(e)}")
        return jsonify({'error': '템플릿 업로드 중 오류가 발생했습니다.'}), 500

@app.route('/analyze', methods=['POST'])
def analyze():
    if not request.is_json:
        return jsonify({'error': '잘못된 요청 형식입니다.'}), 400

    data = request.get_json()
    resume_text = data.get('resume_text')

    if not resume_text:
        return jsonify({'error': '이력서 내용이 비어있습니다.'}), 400

    try:
        # Analyze resume using Claude API
        analysis_result = analyze_resume(client, resume_text)

        # 사용자가 업로드한 템플릿이 있는지 확인
        custom_template_path = os.path.join(TEMPLATE_FOLDER, 'template.pptx')

        # 커스텀 템플릿이 있으면 그것을 사용, 없으면 기본 템플릿 사용
        template_path = custom_template_path if os.path.exists(custom_template_path) else default_template_path

        # Generate PowerPoint
        pptx_path = generate_portfolio(analysis_result, template_path)

        return render_template('result.html', 
                            analysis=analysis_result,
                            pptx_path=pptx_path)

    except ValueError as e:
        logging.error(f"Value error in analyze: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logging.error(f"Unexpected error in analyze: {str(e)}")
        return jsonify({'error': '이력서 분석 중 오류가 발생했습니다.'}), 500

def generate_portfolio(analysis_result, template_path):
    try:
        # 템플릿 파일 로드
        prs = Presentation(template_path)
        logging.info("템플릿 파일을 사용하여 포트폴리오 생성")

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
        for idx, slide in enumerate(prs.slides):
            if idx < len(data_list):  # 데이터가 있는 경우에만 처리
                data = data_list[idx]  # 현재 슬라이드에 삽입할 데이터
                processed_placeholders = set()  # 이미 처리된 플레이스홀더 추적

                for shape in slide.shapes:
                    if shape.has_text_frame:
                        text_frame = shape.text_frame
                        text = text_frame.text

                        # 각 플레이스홀더를 데이터로 치환 (한 번만)
                        for key, value in data.items():
                            placeholder = f"{{{{{key}}}}}"
                            if placeholder in text and placeholder not in processed_placeholders:
                                new_text = text.replace(placeholder, str(value))
                                if text != new_text:  # 변경사항이 있는 경우만 업데이트
                                    text_frame.clear()  # 기존 텍스트 삭제
                                    p = text_frame.paragraphs[0]
                                    p.text = new_text
                                    # 폰트 크기를 10pt로 설정
                                    for run in p.runs:
                                        run.font.size = Pt(10)
                                    # 추가되는 단락들의 폰트 크기도 설정
                                    if "\n" in new_text:
                                        for line in new_text.split("\n")[1:]:
                                            if line.strip():
                                                new_p = text_frame.add_paragraph()
                                                new_p.text = line
                                                for run in new_p.runs:
                                                    run.font.size = Pt(10)
                                processed_placeholders.add(placeholder)  # 처리된 플레이스홀더 기록

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
        template_type = request.args.get('template', 'default') # Default to 'default' if no template is specified
        # 템플릿 타입에 따라 다른 템플릿 파일 사용
        template_path = os.path.join(TEMPLATE_FOLDER, f'template_{template_type}.pptx')

        if not os.path.exists(template_path):
            template_path = default_template_path # Fallback to default if custom template doesn't exist

        return send_file(template_path, as_attachment=True)
    except Exception as e:
        logging.error(f"파일 다운로드 중 오류 발생: {str(e)}")
        return jsonify({'error': '파일 다운로드 중 오류가 발생했습니다.'}), 500