import os
import json
import anthropic
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from pptx import Presentation
from utils import extract_text_from_file, analyze_resume
import logging

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize Anthropic client
client = anthropic.Anthropic(
    api_key=os.getenv('ANTHROPIC_API_KEY')
)

def allowed_file(filename):
    # 파일명에서 확장자 추출 (마지막 . 이후)
    extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    logging.debug(f"파일 확장자 검사: {filename} -> {extension}")
    return extension in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': '파일이 선택되지 않았습니다.'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '파일이 선택되지 않았습니다.'}), 400

    try:
        if file and allowed_file(file.filename):
            # 파일명 보안 처리 및 원본 확장자 유지
            original_extension = os.path.splitext(file.filename)[1]
            base_filename = secure_filename(os.path.splitext(file.filename)[0])
            filename = f"{base_filename}{original_extension}"

            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            logging.info(f"파일 업로드 완료: {filename}")
            logging.debug(f"저장된 파일 경로: {filepath}")

            # Extract text from file
            text_content = extract_text_from_file(filepath)
            logging.debug(f"텍스트 추출 완료: {len(text_content)} 글자")

            if not text_content.strip():
                raise ValueError("파일에서 텍스트를 추출할 수 없습니다.")

            # Analyze resume using Claude API
            analysis_result = analyze_resume(client, text_content)

            # Generate PowerPoint
            pptx_path = generate_portfolio(analysis_result)

            return render_template('result.html', 
                                analysis=analysis_result,
                                pptx_path=pptx_path)

        return jsonify({'error': '허용되지 않는 파일 형식입니다.'}), 400

    except ValueError as e:
        logging.error(f"Value error in upload_file: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logging.error(f"Unexpected error in upload_file: {str(e)}")
        return jsonify({'error': '파일 처리 중 오류가 발생했습니다.'}), 500

def generate_portfolio(analysis_result):
    try:
        prs = Presentation()

        # Title slide
        title_slide_layout = prs.slide_layouts[0]
        slide = prs.slides.add_slide(title_slide_layout)
        title = slide.shapes.title
        subtitle = slide.placeholders[1]
        title.text = "포트폴리오"
        subtitle.text = f"{analysis_result['work_experience'][0]['company']}"

        # Experience slides
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

        output_path = os.path.join(app.config['OUTPUT_FOLDER'], 'portfolio.pptx')
        prs.save(output_path)
        logging.info("포트폴리오 생성 완료")
        return output_path

    except Exception as e:
        logging.error(f"포트폴리오 생성 중 오류 발생: {str(e)}")
        raise ValueError("포트폴리오 생성 중 오류가 발생했습니다.")

@app.route('/download/<filename>')
def download_file(filename):
    try:
        return send_file(os.path.join(app.config['OUTPUT_FOLDER'], filename),
                        as_attachment=True)
    except Exception as e:
        logging.error(f"파일 다운로드 중 오류 발생: {str(e)}")
        return jsonify({'error': '파일 다운로드 중 오류가 발생했습니다.'}), 500

if __name__ == '__main__':
    app.run(debug=True)