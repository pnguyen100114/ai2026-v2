from __future__ import annotations

import os
import base64
import json
import logging
import re
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse, Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types
from pydantic import BaseModel, Field, field_validator

try:
    from backend.accounts import router as accounts_router
    from backend.answer_cleanup import clean_answer, cited_numbers
    from backend.ai_roadmap import build_roadmap_prompt, parse_generated_roadmap
    from backend.db import (
        check_chat_rate, check_rate, current_user, get_ai_roadmap, get_generated_question, has_quiz_attempt, init_db, lesson_history,
        recent_question_texts, save_ai_roadmap, save_chat_turn, save_generated_question, save_quiz_attempt, signed_source_url,
        utc_now, verify_source_signature,
    )
    from backend.learning import (
        build_quiz_prompt, concept_id_for, concept_state, grade_answer, parse_generated_question,
        public_question, target_difficulty,
    )
    from backend.safety import SAFETY_OPENING, SAFETY_PROMPT, SAFETY_QUICK_REPLIES, detect_risk, leaks_answer, safety_addendum
except ImportError:  # pragma: no cover
    from accounts import router as accounts_router
    from answer_cleanup import clean_answer, cited_numbers
    from ai_roadmap import build_roadmap_prompt, parse_generated_roadmap
    from db import (
        check_chat_rate, check_rate, current_user, get_ai_roadmap, get_generated_question, has_quiz_attempt, init_db, lesson_history,
        recent_question_texts, save_ai_roadmap, save_chat_turn, save_generated_question, save_quiz_attempt, signed_source_url,
        utc_now, verify_source_signature,
    )
    from learning import (
        build_quiz_prompt, concept_id_for, concept_state, grade_answer, parse_generated_question,
        public_question, target_difficulty,
    )
    from safety import SAFETY_OPENING, SAFETY_PROMPT, SAFETY_QUICK_REPLIES, detect_risk, leaks_answer, safety_addendum

try:
    from backend.speech import TRANSCRIBE_PROMPT, speakable_text, synthesize_mp3
except ImportError:  # pragma: no cover
    from speech import TRANSCRIBE_PROMPT, speakable_text, synthesize_mp3

try:
    from backend.rag import page_store
    from backend.rag.books import build_catalog_roadmap, canonical_subject, lesson_page_filter, resolve_book_file
    from backend.rag.curriculum import build_roadmap, get_curriculum
    from backend.rag.retriever import RAG_SCORE_THRESHOLD, search_knowledge
except ImportError:  # pragma: no cover
    from rag import page_store
    from rag.books import build_catalog_roadmap, canonical_subject, lesson_page_filter, resolve_book_file
    from rag.curriculum import build_roadmap, get_curriculum
    from rag.retriever import RAG_SCORE_THRESHOLD, search_knowledge

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

logger = logging.getLogger('gia_su_ai')
app = FastAPI(title='Gia Su AI v2 Backend', version='1.0.0')
DATA_DIR = Path(__file__).resolve().parent / 'data'
# Comma-separated list of frontend origins, e.g. "https://gia-su-ai.vercel.app". Auth uses Bearer headers, not cookies.
ALLOWED_ORIGINS = [origin.strip() for origin in os.getenv('ALLOWED_ORIGINS', '*').split(',') if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=['*'],
    allow_headers=['*'],
)
init_db()
app.include_router(accounts_router)

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
# Cheapest model that still tutors well and still cites its sources ([1] is what builds the
# "Xem trang" links). $0.25/1M in, $1.50/1M out against gemini-3.5-flash's $1.50/$9.00 - about
# 6x cheaper per answer. gemini-2.5-flash-lite is cheaper still but 404s for new projects.
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-3.1-flash-lite')
# Free-tier quota is counted per model, so when one runs out the next one usually still answers.
GEMINI_FALLBACK_MODELS = [model.strip() for model in os.getenv('GEMINI_FALLBACK_MODELS', 'gemini-3.5-flash-lite,gemini-3.5-flash').split(',') if model.strip()]

# A tutoring answer needs a few hundred tokens; without a ceiling one rambling reply can cost
# several times a normal one. Structured replies get their own, larger budget because a cut-off
# JSON is not a shorter answer, it is an unparseable one.
MAX_OUTPUT_TOKENS = int(os.getenv('MAX_OUTPUT_TOKENS', '800'))
MAX_JSON_OUTPUT_TOKENS = int(os.getenv('MAX_JSON_OUTPUT_TOKENS', '4096'))
QUOTA_COOLDOWN_SECONDS = 300
# Ngưỡng để một đoạn sách được HIỆN RA làm nguồn trích dẫn, khắt khe hơn ngưỡng đưa vào prompt.
#
# Đo thật trên kho hiện tại (bao-cao/bo-test/do_nguong.py) thì điểm của lời chào và điểm của
# câu hỏi thật CHỒNG LÊN NHAU, không ngưỡng nào tách được:
#
#     0.686  "Hai tam giác bằng nhau theo trường hợp cạnh - góc - cạnh khi nào?"  ← câu thật
#     0.691  "Ok em hiểu rồi"                                                     ← lời chào
#     0.693  "Em cảm ơn nhiều ạ"                                                  ← lời chào
#     0.698  "Phân tích x² - 6x + 9 thành nhân tử"                                ← câu thật
#
# Đặt 0.68 thì lời cảm ơn cũng được gắn một trang SGK; đặt 0.70 thì hai câu hỏi thật mất
# trích dẫn. Nên ngưỡng không phải là chỗ để giải bài toán này - phải xem tin nhắn có phải
# CÂU HỎI HỌC TẬP hay không trước đã (xem _la_cau_hoi_hoc_tap). Có cổng đó rồi thì ngưỡng
# hạ về 0.65 được, vừa giữ trích dẫn cho câu thật vừa không bịa nguồn cho lời chào.
CHAT_SOURCE_MIN_SCORE = float(os.getenv('CHAT_SOURCE_MIN_SCORE', str(max(RAG_SCORE_THRESHOLD, 0.65))))

# Dấu hiệu một tin nhắn là câu hỏi học tập chứ không phải chào hỏi, cảm ơn hay tán gẫu.
# Gồm từ để hỏi và động từ ra đề - "Phân tích x² - 6x + 9" không có dấu hỏi nào nhưng vẫn là
# một câu hỏi bài.
_TU_HOI_BAI = re.compile(
    r'\?|\b('
    r'gì|nào|sao|mấy|bao nhiêu|đâu|ai|'
    r'phân tích|so sánh|tính|giải|chứng minh|nêu|trình bày|phát biểu|định nghĩa|'
    r'khai triển|rút gọn|tìm|vẽ|kể|viết|đặt câu|cho ví dụ|ví dụ|khác nhau|nghĩa là'
    r')\b',
    re.IGNORECASE)


def _la_cau_hoi_hoc_tap(message: str) -> bool:
    """Tin nhắn này có đáng gắn trích dẫn SGK không.

    "Em cảm ơn nhiều ạ" vẫn khớp kha khá với một trang sách bất kì (0.69), nên nếu chỉ xét
    điểm thì Mimo sẽ gắn cho nó một trang SGK - tức bịa nguồn. Chặn ở đây rẻ và chắc hơn
    nhiều so với việc chỉnh ngưỡng.
    """
    return bool(_TU_HOI_BAI.search(message or ''))


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


MESSAGE_MAX_LENGTH = 2000
# Base64 data URL; the client shrinks photos to ~1600px JPEG, which is far below this (~6 MB image).
IMAGE_DATA_MAX_LENGTH = 8_000_000
HISTORY_MAX_MESSAGES = 20


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=MESSAGE_MAX_LENGTH)
    student: StudentInput | None = None
    context: dict[str, Any] | None = None
    messages: list[dict[str, str]] | None = None
    image_data: str | None = Field(default=None, max_length=IMAGE_DATA_MAX_LENGTH)
    image_mime_type: str | None = Field(default=None, max_length=40)
    # Where to store this turn in the chat history.
    session: dict[str, Any] | None = None
    user_message_id: str | None = None
    assistant_message_id: str | None = None
    replaces_message_id: str | None = None

    @field_validator('messages')
    @classmethod
    def keep_recent_history(cls, value: list[dict[str, str]] | None) -> list[dict[str, str]] | None:
        # Only the last few turns reach the prompt; long chats must not be rejected or bloat the request.
        return value[-HISTORY_MAX_MESSAGES:] if value else value


class RoadmapRequest(BaseModel):
    student: StudentInput


class QuizNextRequest(BaseModel):
    student: StudentInput
    context: dict[str, Any] | None = None


class QuizAnswerRequest(BaseModel):
    question_id: str = Field(..., min_length=1)
    answer: str = ''
    hints_used: int = Field(default=0, ge=0, le=3)


class SpeechRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=20_000)


# ~60 s of 16 kHz mono WAV recorded by the browser, base64-encoded.
AUDIO_DATA_MAX_LENGTH = 3_000_000
AUDIO_MIME_TYPES = {'audio/wav', 'audio/x-wav', 'audio/webm', 'audio/ogg', 'audio/mp4', 'audio/mpeg', 'audio/aac'}


class TranscribeRequest(BaseModel):
    audio_data: str = Field(..., min_length=16, max_length=AUDIO_DATA_MAX_LENGTH)
    mime_type: str = Field(default='audio/wav', max_length=40)


SOURCE_THUMB_WIDTH = 320


def _source_pdf(source: str) -> Path | None:
    requested = Path(source).name
    if not requested.lower().endswith('.pdf'):
        return None
    # The catalog knows other names a book was ingested under ("KHTN 6.pdf" is backend/data/KHTN.pdf).
    return resolve_book_file(requested, DATA_DIR)


@app.get('/api/sources/page')
def source_page(source: str = Query(..., min_length=1), page: int = Query(..., ge=1), thumb: bool = False, exp: int | None = None, sig: str | None = None):
    # Only pages Mimo cited to a signed-in student (signed links) can be rendered: no scraping the book, no render floods.
    if not verify_source_signature(source, page, exp, sig):
        raise HTTPException(status_code=403, detail='Link xem trang sách đã hết hạn, em tải lại trang nhé.')

    # Deployed there are no PDFs on disk (2.1 GB that never reach GitHub), only the pages
    # rendered ahead of time by rag/render_pages.py. Hand the browser a signed Supabase link:
    # the bucket is private, so the student's own request is still the only one that opens it.
    remote_url = page_store.signed_url(source, page, thumb)
    if remote_url is not None:
        # 307 keeps <img src> following along; the cache window stays well inside PAGE_URL_TTL.
        return RedirectResponse(remote_url, status_code=307, headers={'Cache-Control': 'private, max-age=600'})

    # Local machine (or a book uploaded later than the last render run): render from the PDF.
    pdf_path = _source_pdf(source)
    if pdf_path is None:
        raise HTTPException(status_code=404, detail='Không tìm thấy sách trong thư mục dữ liệu.')
    try:
        import pymupdf
        with pymupdf.open(pdf_path) as document:
            if page > document.page_count:
                raise HTTPException(status_code=404, detail='Trang sách không tồn tại.')
            book_page = document[page - 1]
            if thumb:
                # Small JPEG shown under an answer so figures are visible without opening the full page (~15 KB vs ~1 MB).
                scale = SOURCE_THUMB_WIDTH / book_page.rect.width
                image_bytes = book_page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False).tobytes('jpg', jpg_quality=75)
                media_type = 'image/jpeg'
            else:
                image_bytes = book_page.get_pixmap(matrix=pymupdf.Matrix(1.6, 1.6), alpha=False).tobytes('png')
                media_type = 'image/png'
        return Response(content=image_bytes, media_type=media_type, headers={'Cache-Control': 'private, max-age=86400'})
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'Không thể tạo ảnh xem trước trang sách: {exc}') from exc

@app.get('/api/health')
def health() -> dict[str, Any]:
    rag_status: dict[str, Any] = {'configured': True}
    try:
        from backend.rag import vector_store
        rag_status.update(vector_store.stats())
    except Exception as exc:
        rag_status = {'configured': False, 'error': str(exc)}

    # vector_store.stats() mở kết nối riêng, nên nó xanh kể cả khi retriever KHÔNG mở được
    # kho lúc khởi động. Đúng tình huống đó thì mọi câu hỏi trả về "Mimo chưa mở được sách
    # giáo khoa" trong khi /api/health vẫn báo ổn - không có cách nào nhìn ra từ bên ngoài.
    # Ở đây soi thẳng trạng thái mà search_knowledge thật sự dùng.
    try:
        try:
            from backend.rag import retriever
        except ImportError:  # pragma: no cover
            from rag import retriever
        rag_status['retriever'] = retriever.STORE_BACKEND or 'failed'
        if retriever.STORE_BACKEND is None:
            rag_status['retriever_error'] = str(retriever._store_error)
    except Exception as exc:
        rag_status['retriever'] = 'import_failed'
        rag_status['retriever_error'] = str(exc)

    # Hai biến này phải khớp đúng lúc nạp sách. Nguy hiểm nhất là EMBEDDING_DIMENSION còn
    # sót trên dashboard từ thời Pinecone: retriever cắt/đệm vector về đúng số đó, rồi
    # pgvector từ chối vì cột là vector(1536) - MỌI câu hỏi hỏng, còn /api/health vẫn xanh.
    rag_status['embedding_model'] = os.getenv('EMBEDDING_MODEL') or 'gemini-embedding-001'
    rag_status['embedding_dimension'] = int(os.getenv('EMBEDDING_DIMENSION', '1536'))
    rag_status['gemini_key'] = bool(GEMINI_API_KEY)
    # Hai ngưỡng này quyết định câu trả lời có trích dẫn hay không, mà từ ngoài thì không có
    # cách nào biết bản đang chạy dùng số nào - đã mất một lần dò mò vì đúng chuyện đó.
    rag_status['score_threshold'] = RAG_SCORE_THRESHOLD
    rag_status['source_min_score'] = CHAT_SOURCE_MIN_SCORE

    return {'status': 'ok', 'service': 'Gia Su AI v2 backend', 'rag': rag_status}


@app.get('/api/health/probe')
def health_probe(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    """Chạy thật một lần tìm kiếm SGK rồi trả về đúng câu lỗi nếu hỏng.

    /api/health chỉ nói kho có mở được không. Nó không nói được vì sao mọi câu hỏi trả về
    "Mimo chưa mở được sách giáo khoa": lỗi thật bị nuốt trong chat/stream và chỉ hiện ở
    log của Render. Endpoint này gọi đúng hàm mà câu hỏi dùng và đưa lỗi ra ngoài.

    Bắt buộc đăng nhập vì mỗi lần gọi là một lượt embedding tính vào quota Gemini.
    """
    try:
        matches = search_knowledge('hằng đẳng thức đáng nhớ', subject='Toán', grade=8, top_k=3)
    except Exception as exc:
        logger.exception('health probe: tìm kiếm SGK thất bại')
        return {
            'ok': False,
            'error_type': type(exc).__name__,
            'error': str(exc)[:900],
        }
    return {
        'ok': True,
        'matches': len(matches),
        'top_score': round(matches[0]['score'], 3) if matches else None,
        'top_source': matches[0]['source'] if matches else None,
    }


def _gemini_contents(prompt: str, request: ChatRequest) -> Any:
    if not request.image_data:
        return prompt
    try:
        encoded = request.image_data.split(',', 1)[-1]
        image_bytes = base64.b64decode(encoded)
        return [
            types.Part.from_text(text=prompt),
            types.Part.from_bytes(data=image_bytes, mime_type=request.image_mime_type or 'image/jpeg'),
        ]
    except (ValueError, TypeError):
        return prompt


def _stream_event(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


SUGGESTION_MARKER = '<<<MIMO_GOI_Y>>>'
UNDERSTANDING_LEVELS = ('mất gốc', 'hiểu sơ', 'đã hiểu')


def _parse_suggestions(raw: str) -> dict[str, Any]:
    """Parse the JSON line Gemini appends after SUGGESTION_MARKER; tolerate missing or malformed output."""
    cleaned = raw.strip().strip('`').strip()
    start, end = cleaned.find('{'), cleaned.rfind('}')
    try:
        payload = json.loads(cleaned[start:end + 1]) if start >= 0 and end > start else {}
    except json.JSONDecodeError:
        payload = {}
    replies = payload.get('quick_replies') if isinstance(payload.get('quick_replies'), list) else []
    understanding = payload.get('understanding')
    return {
        # Chips are plain buttons: LaTeX delimiters would show up as raw "$".
        'quick_replies': [str(item).replace('$', '').strip() for item in replies if str(item).replace('$', '').strip() and not leaks_answer(str(item))][:3],
        'understanding': understanding if understanding in UNDERSTANDING_LEVELS else None,
    }


IMAGE_TEXT_MAX_LENGTH = 1500


def _parse_image_text(raw: str) -> str:
    """The problem Gemini copied out of the student's photo, so later turns still know it without the image."""
    cleaned = raw.strip().strip('`').strip()
    start, end = cleaned.find('{'), cleaned.rfind('}')
    try:
        payload = json.loads(cleaned[start:end + 1]) if start >= 0 and end > start else {}
    except json.JSONDecodeError:
        return ''
    value = payload.get('image_text') if isinstance(payload, dict) else None
    return value.strip()[:IMAGE_TEXT_MAX_LENGTH] if isinstance(value, str) else ''


def _is_quota_error(exc: Exception) -> bool:
    text = str(exc)
    return '429' in text or 'RESOURCE_EXHAUSTED' in text or 'quota' in text.lower()


LESSON_CONTEXT_PAGES = 2
LESSON_PAGES_CACHE_SIZE = 256
_lesson_pages_cache: dict[tuple[str, int, str], list[dict[str, Any]]] = {}


def _page_key(item: dict[str, Any]) -> tuple[Any, Any]:
    return item.get('source'), item.get('pdf_page') or item.get('page')


def _lesson_pages(subject: str, grade: int, topic: str) -> list[dict[str, Any]]:
    """Textbook pages for a lesson topic, cached per process: one embedding per lesson instead of one per message."""
    key = (subject, grade, topic)
    if key not in _lesson_pages_cache:
        try:
            # Catalog books: only the lesson's own pages, not look-alike pages from other lessons.
            pages = search_knowledge(topic, subject=subject, grade=grade, top_k=4, extra_filter=lesson_page_filter(subject, grade, topic))
        except Exception:
            logger.exception('RAG retrieval failed for lesson pages')
            return []
        if len(_lesson_pages_cache) >= LESSON_PAGES_CACHE_SIZE:
            _lesson_pages_cache.pop(next(iter(_lesson_pages_cache)))
        _lesson_pages_cache[key] = [item for item in pages if float(item.get('score', 0.0)) >= RAG_SCORE_THRESHOLD]
    return _lesson_pages_cache[key]


def _lesson_progress(user: dict[str, Any], subject: str, grade: int, topic: str) -> str:
    if not topic:
        return 'chưa có.'
    state = concept_state(user.get('learningProfile') or {}, concept_id_for(subject, grade, topic))
    attempts = int(state.get('attempts') or 0)
    if attempts == 0:
        return 'em chưa làm câu luyện tập nào.'
    errors = [str(error) for error in (state.get('common_errors') or []) if str(error).strip()]
    return (
        f"mức nắm bài {round(state['mastery'] * 100)}%, đúng {int(state.get('correct') or 0)}/{attempts} câu"
        + (f"; lỗi hay gặp: {'; '.join(errors[:3])}." if errors else '.')
    )


_quota_exhausted_until: dict[str, float] = {}


def _gemini_models() -> list[str]:
    """Primary model first, then fallbacks; models that just ran out of quota are skipped for a while."""
    chain = list(dict.fromkeys([GEMINI_MODEL, *GEMINI_FALLBACK_MODELS]))
    now = time.monotonic()
    return [model for model in chain if _quota_exhausted_until.get(model, 0.0) <= now] or chain


def _mark_quota_exhausted(model: str, exc: Exception) -> None:
    logger.warning('Gemini model %s is out of quota, trying the next one: %s', model, str(exc)[:300])
    _quota_exhausted_until[model] = time.monotonic() + QUOTA_COOLDOWN_SECONDS


def _with_output_cap(config: Any, limit: int) -> Any:
    """Give a request an output ceiling, keeping whatever else the caller asked for."""
    if config is None:
        return types.GenerateContentConfig(max_output_tokens=limit)
    if getattr(config, 'max_output_tokens', None) is None:
        config.max_output_tokens = limit
    return config


def _generate_content(**kwargs: Any) -> Any:
    kwargs['config'] = _with_output_cap(kwargs.get('config'), MAX_OUTPUT_TOKENS)
    last_quota_error: Exception | None = None
    for model in _gemini_models():
        try:
            return gemini_client.models.generate_content(model=model, **kwargs)
        except Exception as exc:
            if not _is_quota_error(exc):
                raise
            _mark_quota_exhausted(model, exc)
            last_quota_error = exc
    raise last_quota_error  # type: ignore[misc]


def _stream_gemini_text(contents: Any):
    """Yield answer text; switch model on a quota error only if nothing has been streamed yet."""
    last_quota_error: Exception | None = None
    for model in _gemini_models():
        started = False
        try:
            for chunk in gemini_client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(max_output_tokens=MAX_OUTPUT_TOKENS),
            ):
                text = getattr(chunk, 'text', None) or ''
                if text:
                    started = True
                    yield text
            return
        except Exception as exc:
            if started or not _is_quota_error(exc):
                raise
            _mark_quota_exhausted(model, exc)
            last_quota_error = exc
    raise last_quota_error  # type: ignore[misc]


def _quota_fallback(message: str, subject: str, grade: int) -> str:
    topic_hint = 'xác định dữ kiện, yêu cầu và quy tắc trong bài' if subject != 'Toán' else 'ghi ra dữ kiện đã cho, điều cần tìm và kiến thức liên quan'
    return (
        f'Hôm nay nhiều bạn hỏi Mimo quá nên Mimo đang hơi quá tải một chút 😅 Trong lúc chờ, em thử cách này nhé:\n\n'
        f'Với bài {subject} lớp {grade}, bước đầu tiên là **{topic_hint}**.\n\n'
        'Em thử viết ra bước đầu tiên của bài, lát nữa gửi lại để Mimo kiểm tra cùng em nhé?'
    )


@app.post('/api/speech/tts')
async def speech_tts(request: SpeechRequest, user: dict[str, Any] = Depends(current_user)) -> Response:
    """Read an answer aloud with a Vietnamese neural voice (browsers often only have English voices)."""
    check_rate(f"tts:{user['id']}", 30, 600)
    text = speakable_text(request.text)
    if not text:
        raise HTTPException(status_code=400, detail='Không có nội dung để đọc.')
    try:
        audio = await synthesize_mp3(text)
    except Exception as exc:
        logger.warning('TTS failed: %s', str(exc)[:300])
        raise HTTPException(status_code=503, detail='Mimo chưa đọc được lúc này, em thử lại sau nhé.') from exc
    return Response(content=audio, media_type='audio/mpeg', headers={'Cache-Control': 'private, max-age=3600'})


@app.post('/api/speech/transcribe')
def speech_transcribe(request: TranscribeRequest, user: dict[str, Any] = Depends(current_user)) -> dict[str, str]:
    """Turn a recorded voice question into text; works in every browser, unlike the Web Speech API."""
    check_rate(f"stt:{user['id']}", 20, 400)
    mime_type = request.mime_type.split(';', 1)[0].strip().lower()
    if mime_type not in AUDIO_MIME_TYPES:
        raise HTTPException(status_code=400, detail='Định dạng ghi âm chưa được hỗ trợ.')
    try:
        audio = base64.b64decode(request.audio_data.split(',', 1)[-1], validate=True)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail='File ghi âm bị lỗi, em ghi lại nhé.') from exc
    if gemini_client is None:
        raise HTTPException(status_code=503, detail='Mimo đang được bảo trì nên chưa nghe được, em gõ câu hỏi nhé.')
    try:
        response = _generate_content(contents=[
            types.Part.from_text(text=TRANSCRIBE_PROMPT),
            types.Part.from_bytes(data=audio, mime_type=mime_type),
        ])
    except Exception as exc:
        if _is_quota_error(exc):
            raise HTTPException(status_code=429, detail='Mimo đang quá tải, em gõ câu hỏi giúp Mimo nhé!') from exc
        logger.exception('Gemini transcription failed')
        raise HTTPException(status_code=502, detail='Mimo chưa nghe rõ, em nói lại hoặc gõ câu hỏi nhé.') from exc
    text = (getattr(response, 'text', None) or '').strip().strip('"“”').strip()
    return {'text': text[:MESSAGE_MAX_LENGTH]}


@app.post('/api/quiz/next')
def next_quiz(request: QuizNextRequest, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    """Gemini writes one question for the student's current roadmap lesson, at a difficulty matching their mastery."""
    student = request.student
    context = request.context or {}
    subject = student.subject or 'Toán'
    grade = int(student.grade)
    lesson = str(context.get('currentLesson') or '').strip()
    topic = str(context.get('currentTopic') or lesson).strip()
    if not topic:
        raise HTTPException(status_code=400, detail='Em chọn một bài trong Lộ trình học trước, Mimo sẽ soạn câu luyện tập đúng bài đó nhé.')
    if gemini_client is None:
        raise HTTPException(status_code=503, detail='Mimo đang được bảo trì nên chưa soạn được câu luyện tập. Em quay lại sau nhé!')
    check_chat_rate(user)

    concept_id = concept_id_for(subject, grade, topic)
    # Progress lives on the server; a profile sent by the browser could be stale (other device) or forged.
    profile = user.get('learningProfile') or {}
    state = concept_state(profile, concept_id)
    difficulty = target_difficulty(state['mastery'])
    try:
        matches = search_knowledge(f'{lesson} {topic}'.strip(), subject=subject, grade=grade, top_k=4, extra_filter=lesson_page_filter(subject, grade, topic))
    except Exception:
        logger.exception('RAG retrieval failed for quiz generation')
        matches = []
    context_text = '\n\n'.join(item['text'] for item in matches if item.get('text') and float(item.get('score', 0.0)) >= RAG_SCORE_THRESHOLD)
    prompt = build_quiz_prompt(
        subject=subject, grade=grade, lesson=lesson, topic=topic, difficulty=difficulty, state=state,
        goal=str((user.get('onboarding') or {}).get('goal') or ''),
        context_text=context_text, recent_questions=recent_question_texts(user['id'], concept_id),
    )
    try:
        response = _generate_content(
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type='application/json', max_output_tokens=MAX_JSON_OUTPUT_TOKENS),
        )
        question = parse_generated_question(getattr(response, 'text', None) or '', subject=subject, concept_id=concept_id, concept=topic, difficulty=difficulty)
    except ValueError as exc:
        logger.warning('Unusable generated quiz question: %s', exc)
        raise HTTPException(status_code=502, detail='Mimo soạn câu hỏi chưa ổn, em bấm tạo lại nhé.') from exc
    except Exception as exc:
        if _is_quota_error(exc):
            raise HTTPException(status_code=429, detail='Hôm nay nhiều bạn luyện tập quá, Mimo hơi quá tải. Em thử lại sau ít phút nhé!') from exc
        logger.exception('Gemini quiz generation failed')
        raise HTTPException(status_code=502, detail='Mimo chưa soạn được câu luyện tập, em thử lại nhé.') from exc
    question_id = save_generated_question(user, question)
    return {'success': True, 'question': public_question(question_id, question, state), 'profile': profile}


@app.post('/api/quiz/answer')
def answer_quiz(request: QuizAnswerRequest, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    question = get_generated_question(user['id'], request.question_id)
    if question is None:
        raise HTTPException(status_code=404, detail='Không tìm thấy câu hỏi.')
    if has_quiz_attempt(user['id'], request.question_id):
        raise HTTPException(status_code=409, detail='Em đã trả lời câu này rồi, bấm "Câu khác" để luyện tiếp nhé.')
    result = grade_answer(question, request.answer, user.get('learningProfile') or {}, request.hints_used)
    save_quiz_attempt(user, {
        'question_id': request.question_id,
        'answer': request.answer,
        'is_correct': bool(result.get('is_correct')),
        'hints_used': request.hints_used,
        'mastery': result.get('mastery'),
    }, result.get('profile'))
    return {'success': True, **result}


@app.post('/api/chat/stream')
def chat_stream(request: ChatRequest, user: dict[str, Any] = Depends(current_user)):
    message = (request.message or '').strip()
    if not message:
        raise HTTPException(status_code=400, detail='Tin nhắn không được để trống.')
    check_chat_rate(user)
    started_at = time.monotonic()
    asked_at = utc_now()

    def persist(answer_text: str, done_payload: dict[str, Any]) -> None:
        if not request.user_message_id or not request.assistant_message_id:
            return
        user_content = f'{message}\n\n📷 Ảnh đề bài đã đính kèm.' if request.image_data else message
        save_chat_turn(
            user,
            session=request.session,
            replaces_message_id=request.replaces_message_id,
            user_message={
                'id': request.user_message_id, 'content': user_content, 'prompt': message, 'has_image': bool(request.image_data),
                'image_text': done_payload.get('image_text') or None, 'created_at': asked_at,
            },
            assistant_message={
                'id': request.assistant_message_id,
                'content': answer_text,
                'sources': done_payload.get('sources') or [],
                'quick_replies': done_payload.get('quick_replies') or [],
                'understanding': done_payload.get('understanding'),
                'model': GEMINI_MODEL,
                'latency_ms': int((time.monotonic() - started_at) * 1000),
                'created_at': utc_now(),
            },
        )

    student = request.student or StudentInput()
    context = request.context or {}
    subject = student.subject or context.get('subject') or 'Toán'
    grade = student.grade or context.get('grade') or 8
    lesson = str((request.session or {}).get('lesson') or context.get('currentLesson') or '').strip()
    topic = str(context.get('currentTopic') or '').strip()
    risk = detect_risk(message)

    try:
        matches = search_knowledge(message, subject=subject, grade=grade, top_k=5)
    except Exception as exc:
        logger.exception('RAG retrieval failed for chat message')
        matches = []
        retrieval_error = str(exc)
    else:
        retrieval_error = ''

    # Pages of the lesson being studied keep short follow-ups ("cho em ví dụ khác") anchored to the right part of the book.
    seen_pages = {_page_key(item) for item in matches[:3]}
    lesson_pages = [item for item in _lesson_pages(subject, int(grade), topic) if _page_key(item) not in seen_pages][:LESSON_CONTEXT_PAGES] if topic and not retrieval_error else []
    context_matches = sorted(matches[:3] + lesson_pages, key=lambda item: float(item.get('score', 0.0)), reverse=True)
    unique_matches: dict[tuple[Any, Any], dict[str, Any]] = {}
    # Lời chào và lời cảm ơn không được gắn trang sách, dù điểm tương đồng có cao tới đâu.
    if _la_cau_hoi_hoc_tap(message):
        for item in context_matches:
            if float(item.get('score', 0.0)) >= CHAT_SOURCE_MIN_SCORE:
                unique_matches.setdefault(_page_key(item), item)
    # Every citable passage gets a number, in the same order as the `sources` sent to the client,
    # so "[n]" in the answer points at sources[n-1] and at the passage labelled [n] in the prompt.
    cited_matches = list(unique_matches.values())
    numbers = {_page_key(item): number for number, item in enumerate(cited_matches, start=1)}
    context_text = '\n\n'.join(
        f"[{numbers[_page_key(match)]}] {match['text']}" if _page_key(match) in numbers else f"(tham khảo, không trích dẫn) {match['text']}"
        for match in context_matches if match.get('text')
    )
    source_text = '\n'.join(
        # Lesson names come from the textbook catalog; books outside it only have a reliable book + page.
        ' | '.join(filter(None, [f"[{number}] {item.get('book_title') or item.get('source') or 'SGK'}", item.get('lesson_title'), f"trang {item.get('page') or 'chưa rõ'}"]))
        for number, item in enumerate(cited_matches, start=1)
    )

    # Học sinh hỏi một BÀI HỌC mà kho không có đoạn nào đủ gần: phải nói thẳng là sách của em
    # không có bài đó. Nếu không, mô hình lấy trí nhớ của chính nó ra giảng, và cả lời hứa "chỉ
    # dạy theo sách giáo khoa" sụp ngay tại đó - học sinh không có cách nào biết câu trả lời
    # này không kiểm chứng được.
    #
    # KHÔNG gắn điều kiện vào điểm tương đồng. Đã đo: "Unit 1 Hobbies" (sách thiếu) đạt 0.715
    # còn "Hai tam giác cạnh-góc-cạnh" (sách có) chỉ 0.686 - hai nhóm chồng lên nhau nên không
    # ngưỡng nào tách được. Chính mô hình mới phân biệt được, vì nó đọc được nội dung đoạn
    # sách: thực tế nó đã tự từ chối gắn [n] cho những đoạn không liên quan (chỗ cited_numbers
    # bên dưới), chỉ là nó không nói cho em biết. Nên giao hẳn việc phán đoán cho nó.
    #
    # Không áp cho BÀI TẬP: một bài luyện tập hiếm khi có nguyên văn trong sách, nhưng vẫn giải
    # được bằng khái niệm trong sách, nên vẫn giúp bình thường.
    thieu_sach = (
        '\n\nKHI CÁC ĐOẠN SGK Ở TRÊN KHÔNG NÓI VỀ ĐIỀU EM HỎI\n'
        '- Nếu em hỏi một KHÁI NIỆM hoặc BÀI HỌC mà không đoạn nào ở trên thật sự dạy nó: vẫn '
        'giải thích đầy đủ cho em, nhưng MỞ ĐẦU bằng đúng một câu ngắn cho em biết phần này '
        f'không có trong sách {subject} lớp {grade} mà Mimo đang có, và nếu đoán được thì nói bài '
        'đó thuộc lớp nào. Sau câu đó thì dạy bình thường. Không gắn [n] cho câu trả lời này.\n'
        '- Nếu em nhờ giải một BÀI TẬP: hướng dẫn bình thường bằng khái niệm nền tảng của lớp em, '
        'không cần câu mở đầu đó - bài tập vốn không có nguyên văn trong sách.'
    ) if _la_cau_hoi_hoc_tap(message) and not risk else ''

    history = [item for item in (request.messages or []) if (item.get('content') or '').strip()]
    # The photo itself is only sent in the turn it was attached; later turns see the problem Gemini copied out of it.
    previous = [
        f"{'Học sinh' if item.get('role') == 'user' else 'Mimo'}: {(item.get('content') or '')[:800]}"
        + (f"\n(Nội dung đề bài trong ảnh em đã gửi: {str(item['image_text'])[:IMAGE_TEXT_MAX_LENGTH]})" if item.get('image_text') else '')
        for item in history[-8:]
    ]
    image_text_rule = '''
- image_text (CHỈ vì lượt này em có gửi ảnh): chép lại nguyên văn đề bài trong ảnh (chữ, số, công thức viết LaTeX, chỗ trống ghi "....."; hình vẽ thì mô tả ngắn các dữ kiện), tối đa 1500 ký tự, xuống dòng viết \\n để JSON vẫn nằm trên một dòng. Ảnh không có đề bài thì mô tả ngắn ảnh.''' if request.image_data else ''
    marker_example = '{"quick_replies":["...","..."],"understanding":"...","image_text":"..."}' if request.image_data else '{"quick_replies":["...","..."],"understanding":"..."}'
    earlier_lesson_turns = [
        f"{'Học sinh' if item['role'] == 'user' else 'Mimo'}: {item['content'][:300]}"
        for item in lesson_history(user['id'], subject, lesson, exclude_session_id=(request.session or {}).get('id'))
    ] if lesson else []
    progress_text = _lesson_progress(user, subject, int(grade), topic)
    student_name = student.name if student.name and student.name != 'Học sinh' else 'em'
    prompt = f'''Bạn là Mimo – trợ lý học tập AI thân thiện, như một người anh/chị lớn giỏi giang, kiên nhẫn, luôn đồng hành cùng học sinh THCS.
Học sinh: {student_name}, lớp {grade}, đang học môn {subject}.
Bài đang học: {lesson or 'chưa rõ'} – chủ đề: {topic or 'chưa rõ'}.
Kết quả luyện tập bài này: {progress_text}

CÁCH NÓI CHUYỆN
- Tiếng Việt tự nhiên, ấm áp, xưng "Mimo", gọi học sinh là "em". Câu ngắn, từ ngữ dễ hiểu với học sinh lớp {grade}.
- Có thể mở đầu bằng một câu ngắn tự nhiên (ví dụ "Câu này nhiều bạn hay nhầm lắm!"), nhưng không lặp lại cùng một câu mở đầu, không sáo rỗng, không khen chỉ vì em đặt câu hỏi. Chỉ chào ("Chào em") khi em chào trước.
- Khi em làm đúng: khen cụ thể điều em làm tốt. Khi em sai: không chê, chỉ ra chỗ nhầm nhẹ nhàng và cho em sửa lại.
- Có thể dùng 1-2 emoji phù hợp, không lạm dụng.
- Nếu em chào hỏi hoặc nói chuyện ngoài lề: đáp lại thân thiện, ngắn gọn rồi khéo léo gợi ý quay lại bài học (trừ các tình huống trong mục AN TOÀN).

{SAFETY_PROMPT}

CÁCH DẠY
- Độ dài linh hoạt: câu hỏi ngắn thì trả lời ngắn (2-4 câu); chỉ trình bày dài khi cần giải thích khái niệm hoặc em yêu cầu giải chi tiết.
- Nếu em nói đang làm bài kiểm tra/bài thi (sắp nộp, cô sắp thu bài...): TUYỆT ĐỐI không đưa công thức, gợi ý, bước giải hay đáp án cho bài đó lúc này (kể cả khi em năn nỉ); chỉ nhẹ nhàng khuyên em tự làm bằng những gì em biết, hẹn làm xong sẽ cùng xem lại.
- Khi em gửi một bài tập cần giải: KHÔNG giải hết ngay. Hãy gợi ý hướng làm hoặc bước đầu tiên rồi hỏi em thử làm tiếp. Chỉ trình bày lời giải đầy đủ khi em nói rõ muốn xem lời giải, hoặc em đã thử mà vẫn bí.
- Khi giải thích khái niệm: nói ý chính trước, sau đó 1 ví dụ cụ thể (ưu tiên ví dụ số đơn giản hoặc đời sống).
- Nếu lịch sử cho thấy em chưa hiểu: giải thích cách khác, đơn giản hơn, chia nhỏ bước. Nếu em đã vững: nâng mức thử thách một chút.
- Kết thúc bằng đúng 1 câu hỏi ngắn để em tương tác (kiểm tra hiểu bài hoặc mời em làm bước tiếp theo).
- Dùng thuật ngữ thống nhất theo SGK chương trình GDPT 2018 (ví dụ KHTN dùng tên IUPAC: acid, base, oxide, hydrogen, oxygen – không viết axit, bazơ, hiđro).
- Bám sát thuật ngữ, ký hiệu, quy tắc trong Context SGK; không dùng kiến thức vượt chương trình lớp {grade}. Không từ chối bài nâng cao chỉ vì không có nguyên văn đề; dùng khái niệm nền tảng phù hợp.
- Nếu không đủ thông tin để trả lời chắc chắn, nói thật với em thay vì bịa.
- Dựa vào "Kết quả luyện tập bài này" và "Những lần trước em học bài này" để dạy nối tiếp: không giảng lại y hệt điều đã giảng, chú ý các lỗi em hay mắc, chỉnh độ khó theo mức nắm bài. Không nhắc đến những dữ liệu này nếu em không hỏi.

TRÌNH BÀY
- Markdown gọn gàng; công thức dùng LaTeX `$...$` hoặc `$$...$$`, TUYỆT ĐỐI không bọc công thức hay số trong dấu backtick (`) vì em sẽ thấy ký hiệu thô. Không dùng tiêu đề lớn (#).
- Trích dẫn nguồn bằng số trong ngoặc vuông đặt ngay cuối câu dùng kiến thức từ nguồn đó, ví dụ "Bình phương của một tổng là $(a+b)^2 = a^2 + 2ab + b^2$ [1]." Nhiều nguồn thì viết [1][2].
- Số [n] phải là số ghi ở đầu đoạn Context SGK chứa đúng kiến thức em dùng; chỉ dùng số có trong "Nguồn được phép trích dẫn", đoạn ghi "không trích dẫn" thì không gắn số; không có nguồn thì không viết [n]. Không đặt [n] bên trong công thức.
- CHỈ gắn [n] cho câu trình bày kiến thức lấy từ SGK (định nghĩa, tính chất, công thức, quy tắc, ví dụ trong sách), mỗi kiến thức gắn một lần. KHÔNG gắn [n] cho câu chào hỏi, câu động viên, câu trả lời chuyện ngoài lề hay môn khác, câu nhắc tên bài đang học, câu gợi ý quay lại bài, câu hỏi hay lời mời em tự làm.
- Không viết tên sách, số trang hay số bài/chương trong câu trả lời – em bấm vào [n] để xem trang sách. Riêng khi em hỏi bài nằm ở trang nào thì được nói số trang ghi trong "Nguồn được phép trích dẫn".

SAU KHI TRẢ LỜI XONG, xuống dòng và viết đúng một dòng dạng:
{SUGGESTION_MARKER}{marker_example}
- quick_replies: 2-3 câu ngắn (tối đa 8 từ) mà EM có thể bấm để nói tiếp, viết theo giọng học sinh, phải liên quan trực tiếp đến nội dung vừa trao đổi (ví dụ "Cho em gợi ý thêm", "Cho em xem lời giải", "Vì sao lại đổi dấu ạ?"). TUYỆT ĐỐI không đưa đáp án hay kết quả của câu hỏi Mimo vừa hỏi vào quick_replies – em phải tự trả lời. Viết chữ thường, không dùng LaTeX hay ký hiệu $; nếu cần gọi thì gọi "Mimo".
- understanding: một trong "mất gốc", "hiểu sơ", "đã hiểu" – ước lượng mức hiểu của em dựa trên hội thoại; ghi null nếu hội thoại chưa có nội dung bài học để đánh giá (chào hỏi, tâm sự, chuyện ngoài lề).{image_text_rule}

Context SGK:
{context_text or f'Chưa có SGK phù hợp trong hệ thống: vẫn dạy bình thường theo kiến thức chuẩn của chương trình GDPT 2018 môn {subject} lớp {grade}, không trích dẫn tên sách hay số trang; câu nào không chắc thì nói thật.'}
Nguồn được phép trích dẫn:
{source_text or 'Không có nguồn đạt ngưỡng; không tự tạo tên sách hoặc số trang.'}{thieu_sach}
Những lần trước em học bài này (ở các cuộc trò chuyện khác):
{chr(10).join(earlier_lesson_turns) if earlier_lesson_turns else 'Chưa có.'}
Lịch sử hội thoại gần đây:
{chr(10).join(previous) if previous else 'Chưa có lịch sử.'}
Tin nhắn hiện tại của học sinh: {message}'''

    def finish_safely(text_so_far: str) -> Any:
        # Whatever happened (normal answer, quota, crash), a risky message must end with real-world help.
        extra = safety_addendum(risk, text_so_far) if text_so_far.strip() else SAFETY_OPENING + safety_addendum(risk, '')
        if extra:
            yield _stream_event({'type': 'chunk', 'text': extra})
        content = clean_answer(text_so_far + extra, message=message, passages=[]).strip()
        done_payload = {'type': 'done', 'content': content, 'sources': [], 'quick_replies': SAFETY_QUICK_REPLIES[risk], 'understanding': None}
        persist(content, done_payload)
        yield _stream_event(done_payload)

    def event_generator():
        if retrieval_error and not risk:
            yield _stream_event({'type': 'error', 'message': 'Mimo chưa mở được sách giáo khoa lúc này. Em thử gửi lại sau ít phút nhé.'})
            return
        if gemini_client is None:
            if risk:
                yield from finish_safely('')
                return
            yield _stream_event({'type': 'chunk', 'text': 'Mimo đang được thầy cô bảo trì một chút nên chưa trả lời được. Em quay lại sau nhé! 🙏'})
            yield _stream_event({'type': 'done', 'sources': [], 'quick_replies': []})
            return
        full_text = ''
        marker_at = -1
        try:
            emitted = 0
            for text in _stream_gemini_text(_gemini_contents(prompt, request)):
                full_text += text
                if marker_at >= 0:
                    continue
                marker_at = full_text.find(SUGGESTION_MARKER)
                # Hold back a tail that could be the beginning of the marker.
                safe_end = marker_at if marker_at >= 0 else max(emitted, len(full_text) - len(SUGGESTION_MARKER) + 1)
                if safe_end > emitted:
                    yield _stream_event({'type': 'chunk', 'text': full_text[emitted:safe_end]})
                    emitted = safe_end
            if marker_at < 0 and len(full_text) > emitted:
                yield _stream_event({'type': 'chunk', 'text': full_text[emitted:]})
            if risk:
                yield from finish_safely(full_text[:marker_at] if marker_at >= 0 else full_text)
                return
            meta_raw = full_text[marker_at + len(SUGGESTION_MARKER):] if marker_at >= 0 else ''
            meta = _parse_suggestions(meta_raw)
            if request.image_data:
                meta['image_text'] = _parse_image_text(meta_raw)
            # The streamed text is replaced by this cleaned copy when the answer is done.
            answer_text = clean_answer(
                full_text[:marker_at] if marker_at >= 0 else full_text,
                message=message, passages=[item.get('text') or '' for item in cited_matches],
                pages=[item.get('page') for item in cited_matches], topic=f'{lesson} {topic}',
            ).strip()
            # An answer that cites nothing (small talk, feelings) gets no sources, even if retrieval found pages.
            sources = [] if not cited_numbers(answer_text, len(cited_matches)) else [{
                'source': item.get('source') or 'Nguồn tài liệu',
                'title': item.get('book_title'),
                'lesson_title': item.get('lesson_title'),
                'page': item.get('page'),
                'pdf_page': item.get('pdf_page') or item.get('page'),
                'chapter': item.get('chapter'),
                'lesson': item.get('lesson'),
                'score': round(float(item.get('score', 0.0)), 2),
                'preview_url': signed_source_url(item.get('source'), item.get('pdf_page') or item.get('page')),
            } for item in cited_matches]
            done_payload = {'type': 'done', 'content': answer_text, 'sources': sources, **meta}
            persist(answer_text, done_payload)
            yield _stream_event(done_payload)
        except Exception as exc:
            if risk:
                logger.warning('Gemini failed on a safety-sensitive message, sending the safety reply: %s', str(exc)[:300])
                yield from finish_safely(full_text[:marker_at] if marker_at >= 0 else full_text)
                return
            if _is_quota_error(exc):
                fallback_text = _quota_fallback(message, subject, grade)
                done_payload = {'type': 'done', 'sources': [], 'quick_replies': ['Em thử viết bước đầu nhé', 'Cho em một ví dụ khác']}
                yield _stream_event({'type': 'chunk', 'text': fallback_text})
                persist(fallback_text, done_payload)
                yield _stream_event(done_payload)
            else:
                logger.exception('Gemini stream failed')
                yield _stream_event({'type': 'error', 'message': 'Mimo bị ngắt kết nối giữa chừng. Em bấm "Thử lại" nhé.'})

    return StreamingResponse(
        event_generator(),
        media_type='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'Connection': 'keep-alive', 'X-Accel-Buffering': 'no'},
    )


def _ai_roadmap(user: dict[str, Any], subject: str, grade: int) -> dict[str, Any]:
    """No textbook for this subject/grade in RAG: reuse or create a GDPT 2018 outline from Gemini."""
    cached = get_ai_roadmap(subject, grade)
    if cached:
        return cached
    if gemini_client is None:
        raise HTTPException(status_code=404, detail='Không tìm thấy dữ liệu curriculum phù hợp trong kho RAG.')
    check_chat_rate(user)
    try:
        response = _generate_content(
            contents=build_roadmap_prompt(subject, grade),
            config=types.GenerateContentConfig(response_mime_type='application/json', max_output_tokens=MAX_JSON_OUTPUT_TOKENS),
        )
        roadmap = parse_generated_roadmap(getattr(response, 'text', None) or '', subject, grade)
    except ValueError as exc:
        logger.warning('Unusable generated roadmap: %s', exc)
        raise HTTPException(status_code=502, detail='Mimo chưa soạn được lộ trình, em bấm "Tạo lại roadmap" nhé.') from exc
    except Exception as exc:
        if _is_quota_error(exc):
            raise HTTPException(status_code=429, detail='Mimo đang quá tải, em thử tạo lộ trình lại sau ít phút nhé!') from exc
        logger.exception('Gemini roadmap generation failed')
        raise HTTPException(status_code=502, detail='Mimo chưa soạn được lộ trình, em bấm "Tạo lại roadmap" nhé.') from exc
    return save_ai_roadmap(subject, grade, roadmap)


MIN_RAG_ROADMAP_LESSONS = 10


def _has_lesson_structure(curriculum: list[dict[str, Any]]) -> bool:
    """Textbooks ingested without reliable chapter/lesson metadata (scans, old ingest) yield a garbage roadmap."""
    return len({item.get('lesson') for item in curriculum if item.get('lesson')}) >= MIN_RAG_ROADMAP_LESSONS


@app.post('/api/roadmap/generate')
def generate_roadmap(request: RoadmapRequest, user: dict[str, Any] = Depends(current_user)):
    student = request.student
    subject = student.subject or 'Toán'
    grade = int(student.grade)
    # A textbook in the catalog: the roadmap is its table of contents, with printed pages.
    catalog_roadmap = build_catalog_roadmap(subject, grade)
    if catalog_roadmap is not None:
        return {'success': True, 'roadmap': catalog_roadmap, 'sources': []}
    try:
        curriculum = get_curriculum(subject, grade)
    except Exception:
        logger.exception('RAG curriculum retrieval failed')
        curriculum = []
    if not _has_lesson_structure(curriculum):
        return {'success': True, 'roadmap': _ai_roadmap(user, subject, grade), 'sources': []}
    roadmap = build_roadmap(curriculum, subject, grade)
    return {'success': True, 'roadmap': roadmap, 'sources': [{
        'source': item.get('source'),
        'page': item.get('page'),
        'chapter': item.get('chapter'),
        'lesson': item.get('lesson'),
        'score': round(float(item.get('score', 0.0)), 2),
    } for item in curriculum[:10]]}


@app.get('/api/roadmap/{roadmap_id}')
def get_roadmap_by_id(roadmap_id: str, user: dict[str, Any] = Depends(current_user)):
    subject_name = roadmap_id.split('_')[0].replace('-', ' ')
    try:
        grade = int(roadmap_id.split('_')[-1])
    except ValueError:
        grade = 8
    catalog_roadmap = build_catalog_roadmap(canonical_subject(subject_name), grade)
    if catalog_roadmap is not None:
        return {'roadmap': catalog_roadmap}
    curriculum = get_curriculum(subject_name.title(), grade)
    if not curriculum:
        raise HTTPException(status_code=404, detail='Không tìm thấy roadmap cho học sinh này.')
    return {'roadmap': build_roadmap(curriculum, subject_name.title(), grade)}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run('app:app', host='0.0.0.0', port=8000, reload=True)
