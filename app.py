import os
import json
import anthropic
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from pptx import Presentation
from pptx.util import Pt
from utils import analyze_resume
import logging

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configure folders
OUTPUT_FOLDER = 'output'

# Create necessary folders
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

# Initialize Anthropic client
client = anthropic.Anthropic(
    api_key=os.environ.get('ANTHROPIC_API_KEY')
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
        # 새로운 프레젠테이션 생성
        prs = Presentation()

        # 타이틀 슬라이드 추가
        title_slide_layout = prs.slide_layouts[0]
        slide = prs.slides.add_slide(title_slide_layout)
        title = slide.shapes.title
        subtitle = slide.placeholders[1]

        # 타이틀 슬라이드 폰트 설정
        title.text_frame.paragraphs[0].font.name = 'Noto Sans KR'
        title.text_frame.paragraphs[0].font.size = Pt(44)
        title.text_frame.paragraphs[0].font.bold = True
        subtitle.text_frame.paragraphs[0].font.name = 'Noto Sans KR'
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
                title.text_frame.paragraphs[0].font.name = 'Noto Sans KR'
                title.text_frame.paragraphs[0].font.size = Pt(32)
                title.text_frame.paragraphs[0].font.bold = True

                # 본문 내용 설정
                body = slide.placeholders[1]
                tf = body.text_frame

                # 상세 내용 추가
                p = tf.add_paragraph()
                p.text = "프로젝트 상세"
                p.font.name = 'Noto Sans KR'
                p.font.size = Pt(18)
                p.font.bold = True
                p.space_before = Pt(12)
                p.space_after = Pt(6)

                p = tf.add_paragraph()
                p.text = data["details"]
                p.font.name = 'Noto Sans KR'
                p.font.size = Pt(14)
                p.space_after = Pt(12)

                # 성과 추가
                p = tf.add_paragraph()
                p.text = "주요 성과"
                p.font.name = 'Noto Sans KR'
                p.font.size = Pt(18)
                p.font.bold = True
                p.space_before = Pt(12)
                p.space_after = Pt(6)

                p = tf.add_paragraph()
                p.text = data["results"]
                p.font.name = 'Noto Sans KR'
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