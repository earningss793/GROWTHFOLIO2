import os
import json
import anthropic
from flask import Flask, render_template, request, jsonify, send_file
from pptx import Presentation
from utils import analyze_resume
import logging

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configure output folder
OUTPUT_FOLDER = 'output'

if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

# Initialize Anthropic client
client = anthropic.Anthropic(
    api_key=os.getenv('ANTHROPIC_API_KEY')
)

@app.route('/')
def index():
    return render_template('index.html')

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