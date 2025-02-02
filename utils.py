import PyPDF2
import docx
import json

def extract_text_from_file(filepath):
    file_extension = filepath.split('.')[-1].lower()
    
    if file_extension == 'pdf':
        return extract_from_pdf(filepath)
    elif file_extension == 'docx':
        return extract_from_docx(filepath)
    elif file_extension == 'txt':
        return extract_from_txt(filepath)
    else:
        raise ValueError("Unsupported file format")

def extract_from_pdf(filepath):
    text = ""
    with open(filepath, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

def extract_from_docx(filepath):
    doc = docx.Document(filepath)
    text = []
    for para in doc.paragraphs:
        text.append(para.text)
    return '\n'.join(text)

def extract_from_txt(filepath):
    with open(filepath, 'r', encoding='utf-8') as file:
        return file.read()

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
    
    return json.loads(response.content)
