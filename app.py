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

def find_placeholder_by_text(slide, text_to_find):
    """템플릿 슬라이드에서 특정 텍스트가 포함된 placeholder를 찾습니다."""
    for shape in slide.shapes:
        if hasattr(shape, "text") and text_to_find.lower() in shape.text.lower():
            return shape
    return None

def generate_portfolio(analysis_result, template_path=None):
    try:
        # Use template if available, otherwise create new presentation
        if template_path and os.path.exists(template_path):
            prs = Presentation(template_path)
            logging.info("템플릿 파일을 사용하여 포트폴리오 생성")

            # 각 경력 정보에 대해
            for exp in analysis_result['work_experience']:
                # 템플릿의 각 슬라이드를 순회하며 적절한 위치 찾기
                for slide in prs.slides:
                    # 회사 정보를 입력할 placeholder 찾기
                    company_shape = find_placeholder_by_text(slide, "회사명")
                    if company_shape:
                        company_shape.text = exp['company']

                    # 팀 정보를 입력할 placeholder 찾기
                    team_shape = find_placeholder_by_text(slide, "팀명")
                    if team_shape:
                        team_shape.text = exp['team']

                    # 기간 정보를 입력할 placeholder 찾기
                    period_shape = find_placeholder_by_text(slide, "기간")
                    if period_shape:
                        period_shape.text = f"{exp['start_date']} ~ {exp['end_date']}"

                    # 프로젝트 정보를 입력할 placeholder 찾기
                    for resp in exp['responsibilities']:
                        project_shape = find_placeholder_by_text(slide, "프로젝트")
                        if project_shape:
                            # 프로젝트 상세 정보 입력
                            text_frame = project_shape.text_frame
                            text_frame.clear()  # 기존 텍스트 삭제

                            p = text_frame.paragraphs[0]
                            p.text = resp['project']

                            # 업무 내용 추가
                            p = text_frame.add_paragraph()
                            p.text = "주요 업무:"
                            for detail in resp['details']:
                                p = text_frame.add_paragraph()
                                p.text = f"• {detail}"
                                p.level = 1

                            # 성과 추가
                            p = text_frame.add_paragraph()
                            p.text = "\n성과:"
                            for result in resp['results']:
                                p = text_frame.add_paragraph()
                                p.text = f"• {result}"
                                p.level = 1
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