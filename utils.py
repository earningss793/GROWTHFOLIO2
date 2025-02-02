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
    prompt = f"""분석할 이력서 내용입니다. 다음 형식에 맞춰 JSON으로 변환해주세요:

    {text_content}

    JSON 형식:
    {{
        "work_experience": [
            {{
                "start_date": "시작일",
                "end_date": "종료일",
                "company": "회사명",
                "team": "팀명",
                "responsibilities": [
                    {{
                        "project": "프로젝트명",
                        "details": ["업무내용1", "업무내용2", ...],
                        "results": ["성과1", "성과2", ...]
                    }}
                ]
            }}
        ]
    }}
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

            # 응답 검증
            if not response or not response.content:
                raise ValueError("API 응답이 비어있습니다")

            # JSON 파싱 시도
            try:
                result = json.loads(response.content)
                if not result.get('work_experience'):
                    raise ValueError("필수 데이터가 누락되었습니다")
                return result
            except json.JSONDecodeError as je:
                logging.error(f"JSON 파싱 오류: {str(je)}")
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