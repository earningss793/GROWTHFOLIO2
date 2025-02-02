import PyPDF2
import docx
import json
import os
import logging
import anthropic
from anthropic import Anthropic

def extract_text_from_file(filepath):
    logging.debug(f"Processing file: {filepath}")

    # 파일 존재 여부 확인
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {filepath}")

    # 파일 확장자 확인 (대소문자 구분 없이)
    file_extension = os.path.splitext(filepath)[1].lower().lstrip('.')
    logging.debug(f"File extension detected: {file_extension}")

    try:
        if file_extension == 'pdf':
            return extract_from_pdf(filepath)
        elif file_extension == 'docx':
            return extract_from_docx(filepath)
        elif file_extension == 'txt':
            return extract_from_txt(filepath)
        else:
            raise ValueError(f"지원하지 않는 파일 형식입니다: {file_extension}")
    except Exception as e:
        logging.error(f"파일 처리 중 오류 발생: {str(e)}")
        raise
def extract_from_pdf(filepath):
    try:
        text = ""
        with open(filepath, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text()
        return text
    except Exception as e:
        logging.error(f"PDF 파일 처리 중 오류 발생: {str(e)}")
        raise ValueError(f"PDF 파일 처리 중 오류가 발생했습니다: {str(e)}")

def extract_from_docx(filepath):
    try:
        doc = docx.Document(filepath)
        text = []
        for para in doc.paragraphs:
            text.append(para.text)
        return '\n'.join(text)
    except Exception as e:
        logging.error(f"DOCX 파일 처리 중 오류 발생: {str(e)}")
        raise ValueError(f"DOCX 파일 처리 중 오류가 발생했습니다: {str(e)}")

def extract_from_txt(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            return file.read()
    except UnicodeDecodeError:
        # UTF-8로 읽기 실패시 다른 인코딩 시도
        try:
            with open(filepath, 'r', encoding='cp949') as file:
                return file.read()
        except Exception as e:
            logging.error(f"텍스트 파일 처리 중 인코딩 오류 발생: {str(e)}")
            raise ValueError("텍스트 파일의 인코딩을 확인해주세요.")
    except Exception as e:
        logging.error(f"텍스트 파일 처리 중 오류 발생: {str(e)}")
        raise ValueError(f"텍스트 파일 처리 중 오류가 발생했습니다: {str(e)}")

def analyze_resume(client, text_content):
    # the newest Anthropic model is "claude-3-5-sonnet-20241022" which was released October 22, 2024
    prompt = f"""분석할 이력서 내용입니다. 다음 형식에 맞춰 JSON으로 변환해주세요.
    각 프로젝트별로 구체적인 업무 내용 5가지와 수치화된 성과 3가지를 포함해야 합니다:

    {text_content}

    다음은 원하는 출력 형식의 예시입니다:
    {{
        "work_experience": [
            {{
                "start_date": "2023.10",
                "end_date": "2024.08",
                "company": "빅플래닛메이드엔터",
                "team": "비주얼컨텐츠팀",
                "responsibilities": [
                    {{
                        "project": "프로젝트 1: 앨범 프로모션 컨텐츠",
                        "details": [
                            "아티스트 앨범 발매에 맞춘 컨텐츠 기획 및 제작.",
                            "앨범의 타이틀곡에 대한 홍보 영상 제작 및 배포.",
                            "소셜 미디어용 짧은 숏폼 컨텐츠 제작.",
                            "앨범 프로모션 관련 행사 자료 시각화 및 디자인.",
                            "팬들과 소통할 수 있는 디지털 이벤트 기획."
                        ],
                        "results": [
                            "앨범 프로모션 컨텐츠 조회수 100만 회 기록.",
                            "SNS 채널 평균 CTR 12.5% 달성.",
                            "담당 기간 전 대비 앨범 매출 25% 증가."
                        ]
                    }}
                ]
            }}
        ]
    }}

    주의사항:
    1. 각 프로젝트의 업무 내용(details)은 반드시 5개의 구체적인 문장으로 작성해주세요.
    2. 각 프로젝트의 성과(results)는 반드시 3개의 수치화된 결과로 작성해주세요.
    3. 입력된 내용을 바탕으로 현실적인 수치와 성과를 추정하여 작성해주세요.
    4. 모든 프로젝트를 분리하여 각각 자세히 분석해주세요.
    """

    try:
        logging.info("Claude API 호출 시작")
        logging.debug(f"텍스트 길이: {len(text_content)} 글자")

        # API 호출 시도
        try:
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            logging.info("Claude API 호출 성공")

            # 응답 검증 및 처리
            if not response or not hasattr(response, 'content'):
                raise ValueError("API 응답이 비어있습니다")

            # 로그에 응답 내용 출력 (디버깅용)
            logging.debug(f"API 응답 내용: {response.content}")

            # content 필드에서 첫 번째 메시지 추출
            content = response.content[0].text if isinstance(response.content, list) else response.content

            try:
                # JSON 문자열 시작과 끝 위치 찾기
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start == -1 or json_end == 0:
                    raise ValueError("JSON 데이터를 찾을 수 없습니다")

                json_str = content[json_start:json_end]
                result = json.loads(json_str)

                if not result.get('work_experience'):
                    raise ValueError("필수 데이터가 누락되었습니다")
                return result

            except json.JSONDecodeError as je:
                logging.error(f"JSON 파싱 오류: {str(je)}")
                logging.error(f"파싱 시도한 문자열: {json_str}")
                raise ValueError("API 응답을 파싱할 수 없습니다")

        except anthropic.APIError as ae:
            logging.error(f"Claude API 오류: {str(ae)}")
            raise ValueError("API 서버 오류가 발생했습니다")
        except anthropic.RateLimitError:
            logging.error("API 호출 한도 초과")
            raise ValueError("잠시 후 다시 시도해주세요 (호출 한도 초과)")

    except Exception as e:
        logging.error(f"이력서 분석 중 오류 발생: {str(e)}")
        raise ValueError(f"이력서 분석 중 오류가 발생했습니다: {str(e)}")