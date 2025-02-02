import os
import json
import anthropic
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from pptx import Presentation
from utils import analyze_resume
import logging

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configure folders
OUTPUT_FOLDER = 'output'
TEMPLATE_FOLDER = 'templates/pptx'

# Create necessary folders
for folder in [OUTPUT_FOLDER, TEMPLATE_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

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

        # Generate PowerPoint using template if available
        template_path = os.path.join(TEMPLATE_FOLDER, 'template.pptx')
        pptx_path = generate_portfolio(analysis_result, template_path if os.path.exists(template_path) else None)

        return render_template('result.html', 
                            analysis=analysis_result,
                            pptx_path=pptx_path)

    except ValueError as e:
        logging.error(f"Value error in analyze: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logging.error(f"Unexpected error in analyze: {str(e)}")
        return jsonify({'error': '이력서 분석 중 오류가 발생했습니다.'}), 500

def find_placeholder_by_text(slide, placeholder_text):
    """템플릿 슬라이드에서 특정 플레이스홀더가 포함된 shape를 찾습니다."""
    for shape in slide.shapes:
        if hasattr(shape, "text"):
            # {{placeholder}} 형식의 텍스트를 찾음
            if "{{" + placeholder_text + "}}" in shape.text:
                return shape
    return None

def replace_placeholders(text_frame, analysis_data):
    """텍스트 프레임 내의 플레이스홀더를 실제 데이터로 대체합니다."""
    if not text_frame:
        return

    for paragraph in text_frame.paragraphs:
        if "{{company}}" in paragraph.text:
            paragraph.text = paragraph.text.replace("{{company}}", analysis_data.get('company', ''))
        if "{{team}}" in paragraph.text:
            paragraph.text = paragraph.text.replace("{{team}}", analysis_data.get('team', ''))
        if "{{project}}" in paragraph.text:
            paragraph.text = paragraph.text.replace("{{project}}", analysis_data.get('project', ''))

        # details와 results는 리스트이므로 bullet point로 처리
        if "{{details}}" in paragraph.text:
            base_text = paragraph.text.split("{{details}}")[0]
            paragraph.text = base_text
            for detail in analysis_data.get('details', []):
                new_paragraph = text_frame.add_paragraph()
                new_paragraph.text = f"• {detail}"
                new_paragraph.level = paragraph.level + 1

        if "{{results}}" in paragraph.text:
            base_text = paragraph.text.split("{{results}}")[0]
            paragraph.text = base_text
            for result in analysis_data.get('results', []):
                new_paragraph = text_frame.add_paragraph()
                new_paragraph.text = f"• {result}"
                new_paragraph.level = paragraph.level + 1

def generate_portfolio(analysis_result, template_path=None):
    try:
        # Use template if available, otherwise create new presentation
        if template_path and os.path.exists(template_path):
            prs = Presentation(template_path)
            logging.info("템플릿 파일을 사용하여 포트폴리오 생성")

            # 각 경력 정보에 대해
            for exp in analysis_result['work_experience']:
                # 템플릿의 각 슬라이드를 순회하며 플레이스홀더 찾기
                for slide in prs.slides:
                    # 회사 정보, 팀 정보 등 기본 정보 처리
                    for shape in slide.shapes:
                        if hasattr(shape, "text_frame"):
                            replace_placeholders(shape.text_frame, {
                                'company': exp['company'],
                                'team': exp['team'],
                                'project': '',  # 프로젝트는 responsibilities에서 처리
                                'details': [],
                                'results': []
                            })

                    # 프로젝트별 상세 정보 처리
                    for resp in exp['responsibilities']:
                        for shape in slide.shapes:
                            if hasattr(shape, "text_frame"):
                                replace_placeholders(shape.text_frame, {
                                    'project': resp['project'],
                                    'details': resp['details'],
                                    'results': resp['results']
                                })

        else:
            # 템플릿이 없는 경우 새로운 프레젠테이션 생성
            prs = Presentation()
            logging.info("새로운 포트폴리오 생성")

            # Create title slide
            title_slide_layout = prs.slide_layouts[0]
            slide = prs.slides.add_slide(title_slide_layout)
            title = slide.shapes.title
            subtitle = slide.placeholders[1]
            title.text = "포트폴리오"
            subtitle.text = f"{analysis_result['work_experience'][0]['company']}"

            # Add experience slides
            for exp in analysis_result['work_experience']:
                for resp in exp['responsibilities']:
                    bullet_slide_layout = prs.slide_layouts[1]
                    slide = prs.slides.add_slide(bullet_slide_layout)

                    title = slide.shapes.title
                    body = slide.placeholders[1]

                    title.text = resp['project']
                    tf = body.text_frame

                    tf.text = "주요 업무"
                    for detail in resp['details']:
                        p = tf.add_paragraph()
                        p.text = detail
                        p.level = 1

                    p = tf.add_paragraph()
                    p.text = "\n성과"
                    for result in resp['results']:
                        p = tf.add_paragraph()
                        p.text = result
                        p.level = 1

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
        return send_file(os.path.join(OUTPUT_FOLDER, filename),
                        as_attachment=True)
    except Exception as e:
        logging.error(f"파일 다운로드 중 오류 발생: {str(e)}")
        return jsonify({'error': '파일 다운로드 중 오류가 발생했습니다.'}), 500

if __name__ == '__main__':
    app.run(debug=True)