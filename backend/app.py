from __future__ import annotations

import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from pydantic import BaseModel, Field

try:
    from backend.rag.curriculum import build_roadmap, get_curriculum
    from backend.rag.retriever import RAG_SCORE_THRESHOLD, search_knowledge
except ImportError:  # pragma: no cover
    from rag.curriculum import build_roadmap, get_curriculum
    from rag.retriever import RAG_SCORE_THRESHOLD, search_knowledge

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

app = FastAPI(title='Gia Su AI v2 Backend', version='1.0.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception:  # pragma: no cover
        gemini_client = None
else:
    gemini_client = None


class StudentInput(BaseModel):
    name: str = 'Học sinh'
    age: int | None = None
    grade: int = 8
    subject: str = 'Toán'


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    student: StudentInput | None = None
    context: dict[str, Any] | None = None
    messages: list[dict[str, str]] | None = None


class RoadmapRequest(BaseModel):
    student: StudentInput


@app.get('/api/health')
def health() -> dict[str, Any]:
    return {'status': 'ok', 'service': 'Gia Su AI v2 backend', 'rag': 'pinecone+gemini'}


@app.post('/api/agent/chat')
def chat(request: ChatRequest):
    message = (request.message or '').strip()
    if not message:
        raise HTTPException(status_code=400, detail='Tin nhắn không được để trống.')

    student = request.student or StudentInput()
    context = request.context or {}
    history = request.messages or []
    subject = student.subject or context.get('subject') or 'Toán'
    grade = student.grade or context.get('grade') or 8

    try:
        matches = search_knowledge(message, subject=subject, grade=grade, top_k=5)
    except Exception as exc:
        return {
            'answer': 'Mình chưa thể kết nối dữ liệu học tập hiện tại. Vui lòng kiểm tra cấu hình Pinecone và Gemini.',
            'grounded': False,
            'sources': [],
            'error': str(exc),
        }

    if not matches:
        return {
            'answer': 'Mình chưa tìm thấy đủ thông tin trong tài liệu học tập hiện có để trả lời chính xác câu hỏi này.',
            'grounded': False,
            'sources': [],
        }

    top_match = matches[0]
    if float(top_match.get('score', 0.0)) < RAG_SCORE_THRESHOLD:
        return {
            'answer': 'Mình chưa tìm thấy đủ thông tin trong tài liệu học tập hiện có để trả lời chính xác câu hỏi này.',
            'grounded': False,
            'sources': [],
        }

    context_text = '\n\n'.join(match.get('text', '') for match in matches[:4] if match.get('text'))
    previous = []
    for item in history[-6:]:
        role = item.get('role', 'user')
        text = item.get('content', '')
        if role == 'assistant':
            previous.append(f'Gia sư AI: {text}')
        else:
            previous.append(f'Học sinh: {text}')

    prompt = f'''
Bạn là Gia Sư AI dành cho học sinh THCS.

Nhiệm vụ:
- Giải thích kiến thức bằng tiếng Việt, dễ hiểu cho học sinh THCS.
- Chỉ sử dụng thông tin từ ngữ cảnh RAG dưới đây.
- Nếu không tìm thấy dữ liệu phù hợp, hãy nói rõ rằng tài liệu hiện có không đủ thông tin.

Học sinh: {student.name}
Môn: {subject}
Lớp: {grade}
Bài hiện tại: {context.get('currentLesson') or 'Chưa xác định'}
Chủ đề hiện tại: {context.get('currentTopic') or 'Chưa xác định'}

Lịch sử hội thoại:
{chr(10).join(previous) if previous else 'Không có lịch sử.'}

Context từ Pinecone:
{context_text}

Yêu cầu của học sinh:
{message}

Trả lời bằng cách:
1. Giải thích ngắn gọn nhưng rõ ràng.
2. Đưa gợi ý từng bước nếu phù hợp.
3. Nếu có thể, cho ví dụ tương tự.
4. Không bịa kiến thức không có trong context.
5. Đặt câu hỏi kiểm tra hiểu biết ở cuối nếu phù hợp.
'''

    if gemini_client is None:
        answer = (
            'Mình đang ở chế độ dự phòng; cơ sở dữ liệu tri thức đang có, nhưng Gemini chưa được cấu hình ở backend. '
            'Vui lòng kiểm tra biến GEMINI_API_KEY trong backend/.env.'
        )
        grounded = False
    else:
        response = gemini_client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
        answer = getattr(response, 'text', None) or 'Mình không thể tạo câu trả lời lúc này.'
        grounded = True

    sources = [{
        'source': item.get('source') or 'Nguồn tài liệu',
        'page': item.get('page'),
        'chapter': item.get('chapter'),
        'lesson': item.get('lesson'),
        'score': round(float(item.get('score', 0.0)), 2),
    } for item in matches[:3]]

    return {
        'answer': answer,
        'grounded': grounded,
        'sources': sources,
    }


@app.post('/api/roadmap/generate')
def generate_roadmap(request: RoadmapRequest):
    student = request.student
    subject = student.subject or 'Toán'
    grade = int(student.grade)
    curriculum = get_curriculum(subject, grade)
    if not curriculum:
        raise HTTPException(status_code=404, detail='Không tìm thấy dữ liệu curriculum phù hợp trong RAG/Pinecone.')
    roadmap = build_roadmap(curriculum, subject, grade)
    return {'success': True, 'roadmap': roadmap, 'sources': [{
        'source': item.get('source'),
        'page': item.get('page'),
        'chapter': item.get('chapter'),
        'lesson': item.get('lesson'),
        'score': round(float(item.get('score', 0.0)), 2),
    } for item in curriculum[:10]]}


@app.get('/api/roadmap/{roadmap_id}')
def get_roadmap_by_id(roadmap_id: str):
    subject_name = roadmap_id.split('_')[0].replace('-', ' ')
    try:
        grade = int(roadmap_id.split('_')[-1])
    except ValueError:
        grade = 8
    curriculum = get_curriculum(subject_name.title(), grade)
    if not curriculum:
        raise HTTPException(status_code=404, detail='Không tìm thấy roadmap cho học sinh này.')
    return {'roadmap': build_roadmap(curriculum, subject_name.title(), grade)}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run('app:app', host='0.0.0.0', port=8000, reload=True)
