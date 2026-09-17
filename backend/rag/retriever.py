import os
import re
import time
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

try:
    from backend.rag import vector_store
    from backend.rag.books import COURSES, canonical_subject, course_book, enrich_match, find_book, find_course, subject_variants
except ImportError:  # pragma: no cover
    from rag import vector_store
    from rag.books import COURSES, canonical_subject, course_book, enrich_match, find_book, find_course, subject_variants

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'gemini-embedding-001')
EMBEDDING_DIMENSION = int(os.getenv('EMBEDDING_DIMENSION', '1536'))
RAG_SCORE_THRESHOLD = float(os.getenv('RAG_SCORE_THRESHOLD', '0.60'))

# Kho vector này nằm trong DATABASE_URL của chính dự án (xem rag/vector_store.py), không
# còn Pinecone nên đọc bao nhiêu cũng 0 đồng. Trần top_k giữ lại vì một lý do khác: mỗi
# match kéo theo ~2 KB text đi vào prompt gửi Gemini, và token đầu vào thì vẫn mất tiền.
RAG_MAX_TOP_K = int(os.getenv('RAG_MAX_TOP_K', '24'))
CURRICULUM_CACHE_TTL = float(os.getenv('CURRICULUM_CACHE_TTL', '3600'))

_curriculum_cache: Dict[Any, Any] = {}

if not GEMINI_API_KEY:
    raise RuntimeError('GEMINI_API_KEY chưa được cấu hình trong backend/.env')

try:
    STORE_BACKEND = vector_store.init_store()
    _store_error = None
except Exception as exc:  # pragma: no cover
    STORE_BACKEND = None
    _store_error = exc

gemini_client = genai.Client(api_key=GEMINI_API_KEY)


def _normalize_grade(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _make_filter(subject: Optional[str] = None, grade: Optional[int] = None, volume: Optional[int] = None, extra: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    filters: Dict[str, Any] = {}
    if subject:
        # Books were ingested with either the short code or the full subject name in metadata.
        variants = subject_variants(subject)
        filters['subject'] = variants[0] if len(variants) == 1 else {'$in': variants}
    if grade is not None:
        filters['grade'] = int(grade)
    if volume is not None:
        filters['volume'] = int(volume)
    filters.update(extra or {})
    return filters or None


def create_embedding(text: str) -> List[float]:
    if not text or not str(text).strip():
        return []
    response = gemini_client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            task_type='RETRIEVAL_QUERY',
            output_dimensionality=EMBEDDING_DIMENSION,
        ),
    )
    try:
        values = list(response.embeddings[0].values)
        if len(values) == EMBEDDING_DIMENSION:
            return values
        if len(values) > EMBEDDING_DIMENSION:
            return values[:EMBEDDING_DIMENSION]
        if len(values) < EMBEDDING_DIMENSION:
            return values + [0.0] * (EMBEDDING_DIMENSION - len(values))
        return []
    except Exception:
        return []


def _record_to_output(match: Dict[str, Any]) -> Dict[str, Any]:
    metadata = match.get('metadata') or {}
    pdf_page = _normalize_grade(metadata.get('page'))
    # books.py là nguồn chân lý, KHÔNG phải số đã nướng vào metadata lúc nạp. Sửa một độ lệch
    # sai trong books.py mà kho vẫn giữ số cũ thì trích dẫn tiếp tục lệch cho tới khi nạp lại
    # cả quyển - đúng chuyện đã xảy ra với TOAN8-Tap1 (nạp với -1, thực tế phải là 0, nên mọi
    # trích dẫn lệch một trang). Ưu tiên catalog thì sửa một dòng là cả kho đúng theo.
    book = find_book(metadata.get('source'))
    if book is not None:
        page_offset = book.page_offset
    else:
        # Sách chưa có trong danh mục: đành tin số lưu lúc nạp.
        page_offset = _normalize_grade(metadata.get('page_offset')) or 0
    payload = {
        'id': match.get('id'),
        'score': float(match.get('score', 0.0)),
        'subject': metadata.get('subject'),
        'grade': _normalize_grade(metadata.get('grade')),
        'volume': _normalize_grade(metadata.get('volume')),
        'chapter': _normalize_grade(metadata.get('chapter')),
        'lesson': _normalize_grade(metadata.get('lesson')),
        'page': (pdf_page + page_offset) if pdf_page is not None else None,
        'pdf_page': pdf_page,
        'page_offset': page_offset,
        'source': metadata.get('source'),
        'book_type': metadata.get('book_type', 'sgk'),
        'content_type': metadata.get('content_type', 'theory'),
        'text': metadata.get('text') or '',
        'title': metadata.get('title') or metadata.get('lesson_name') or '',
    }
    # Books in the catalog get their real lesson, chapter and printed page instead of the OCR guesses.
    return enrich_match(payload)


def search_knowledge(query: str, subject: Optional[str] = None, grade: Optional[int] = None, top_k: int = 5, volume: Optional[int] = None, extra_filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    if not query or not str(query).strip():
        return []
    if STORE_BACKEND is None:
        raise RuntimeError(f'Không mở được kho vector SGK trong database: {_store_error}')

    query_vector = create_embedding(str(query))
    if not query_vector:
        raise RuntimeError('Embedding query thất bại. Vui lòng kiểm tra GEMINI_API_KEY hoặc mô hình embedding.')

    query_filter = _make_filter(subject=subject, grade=grade, volume=volume, extra=extra_filter)
    # Trần top_k: mỗi match thêm ~2 KB vào prompt gửi Gemini, và token đầu vào vẫn mất tiền.
    effective_top_k = max(1, min(int(top_k), RAG_MAX_TOP_K))
    matches = vector_store.search(query_vector, top_k=effective_top_k, query_filter=query_filter)

    filtered = []
    for match in matches:
        payload = _record_to_output(match)
        text = (payload.get('text') or '').lower()
        if 'blogtailieu' in text or 'day-va-hoc' in text or 'giao-an-lop-8' in text:
            continue
        if len((payload.get('text') or '').strip()) < 80:
            continue
        if payload['score'] >= 0:
            filtered.append(payload)
    return filtered


def search_lesson(lesson: Any, subject: Optional[str] = None, grade: Optional[int] = None, top_k: int = 10) -> List[Dict[str, Any]]:
    lesson_value = str(lesson).strip()
    if not lesson_value:
        return []
    query = f"Bài {lesson_value} trong chương trình {subject or 'môn học'} lớp {grade or ''}"
    return search_knowledge(query, subject=subject, grade=grade, top_k=top_k)


def search_topic(topic: str, subject: Optional[str] = None, grade: Optional[int] = None, top_k: int = 10) -> List[Dict[str, Any]]:
    if not topic or not str(topic).strip():
        return []
    return search_knowledge(f"{topic}", subject=subject, grade=grade, top_k=top_k)


def _curriculum_from_catalog(subject: Any, grade: Any) -> List[Dict[str, Any]]:
    """The table of contents as curriculum rows, with no vector search at all.

    books.py already holds every chapter, lesson and printed page copied from each book's
    MỤC LỤC, which is both more accurate than what a similarity search recovers and cheaper.
    """
    course = find_course(subject, grade)
    if course is None:
        return []

    rows: List[Dict[str, Any]] = []
    for lesson in course.lessons():
        book = course_book(course, lesson.volume)
        rows.append({
            'id': f'catalog_{course.grade}_{lesson.chapter}_{lesson.lesson}',
            'score': 1.0,
            'subject': course.subject,
            'grade': course.grade,
            'volume': lesson.volume,
            'chapter': lesson.chapter,
            'chapter_title': lesson.chapter_title,
            'lesson': lesson.lesson,
            'page': lesson.page,
            'pdf_page': (lesson.page - book.page_offset) if (lesson.page is not None and book) else None,
            'page_offset': book.page_offset if book else 0,
            'source': (book.files[0] if book else ''),
            'book_title': book.title if book else '',
            'book_type': 'sgk',
            'content_type': 'theory',
            'title': lesson.title,
            'lesson_title': f'Bài {lesson.lesson}. {lesson.title}',
            'text': f'Bài {lesson.lesson}. {lesson.title} — {lesson.chapter_title}',
        })
    return rows


def get_curriculum(subject: Optional[str] = None, grade: Optional[int] = None, top_k: int = 24) -> List[Dict[str, Any]]:
    subject_filter = str(subject).strip() if subject else None
    grade_filter = int(grade) if grade is not None else None

    # Sách đã có mục lục trong books.py thì không cần đụng tới kho vector.
    catalog = _curriculum_from_catalog(subject_filter, grade_filter)
    if catalog:
        return catalog

    cache_key = (canonical_subject(subject_filter), grade_filter, min(int(top_k), RAG_MAX_TOP_K))
    cached = _curriculum_cache.get(cache_key)
    if cached is not None and (time.monotonic() - cached[0]) < CURRICULUM_CACHE_TTL:
        return cached[1]

    query = f"Chương trình {subject_filter or 'môn học'} lớp {grade_filter or ''} bài học SGK curriculum"
    matches = search_knowledge(query, subject=subject_filter, grade=grade_filter, top_k=top_k)
    deduped: Dict[str, Dict[str, Any]] = {}
    for match in matches:
        key = (
            match.get('chapter'),
            match.get('lesson'),
            match.get('volume'),
            match.get('source'),
            match.get('page'),
            match.get('text')[:100] if match.get('text') else '',
        )
        deduped[key] = match
    ordered = sorted(deduped.values(), key=lambda item: (
        item.get('chapter') or 0,
        item.get('lesson') or 0,
        item.get('volume') or 0,
        item.get('page') or 0,
        item.get('source') or '',
    ))
    _curriculum_cache[cache_key] = (time.monotonic(), ordered)
    return ordered


def build_roadmap_from_curriculum(curriculum: List[Dict[str, Any]], subject: Optional[str] = None, grade: Optional[int] = None) -> Dict[str, Any]:
    chapters: Dict[int, Dict[str, Any]] = {}
    lessons_by_chapter: Dict[int, List[Dict[str, Any]]] = {}
    for item in curriculum:
        chapter_no = item.get('chapter') or 0
        if chapter_no not in chapters:
            chapters[chapter_no] = {'id': f'chapter_{chapter_no}', 'chapter': chapter_no, 'title': f'Chương {chapter_no}', 'lessons': []}
        lesson_no = item.get('lesson') or 0
        lesson_title = item.get('title') or item.get('text')[:80] or f'Bài {lesson_no}'
        lesson_payload = {
            'id': f'lesson_{chapter_no}_{lesson_no}',
            'lesson': lesson_no,
            'title': re.sub(r'\s+', ' ', lesson_title).strip() or f'Bài {lesson_no}',
            'volume': item.get('volume') or 0,
            'status': 'locked',
            'progress': 0,
            'sources': [{
                'source': item.get('source') or '',
                'page': item.get('page') or 0,
                'chapter': chapter_no,
                'lesson': lesson_no,
                'score': round(float(item.get('score', 0.0)), 2),
            }],
        }
        chapter_lessons = chapters[chapter_no]['lessons']
        existing = next((entry for entry in chapter_lessons if entry['lesson'] == lesson_no), None)
        if existing is None:
            chapter_lessons.append(lesson_payload)
        else:
            existing['sources'].append({
                'source': item.get('source') or '',
                'page': item.get('page') or 0,
                'chapter': chapter_no,
                'lesson': lesson_no,
                'score': round(float(item.get('score', 0.0)), 2),
            })
        lessons_by_chapter.setdefault(chapter_no, []).append(lesson_payload)

    normalized_chapters = []
    for chapter_no in sorted(chapters):
        chapter = chapters[chapter_no]
        chapter['lessons'] = sorted(chapter['lessons'], key=lambda item: (item.get('lesson') or 0, item.get('volume') or 0))
        normalized_chapters.append(chapter)

    roadmap = {
        'id': f"{(subject or 'subject').lower().replace(' ', '_')}_{grade or 0}",
        'subject': subject or 'Môn học',
        'grade': grade or 0,
        'title': f'Lộ trình {(subject or "môn học").strip()} {grade or ""}'.strip(),
        'progress': 0,
        'chapters': normalized_chapters,
    }
    return roadmap


def get_curriculum_from_rag(subject: str, grade: int) -> List[Dict[str, Any]]:
    return get_curriculum(subject=subject, grade=grade)


__all__ = [
    'RAG_SCORE_THRESHOLD',
    'STORE_BACKEND',
    'search_knowledge',
    'search_lesson',
    'search_topic',
    'get_curriculum',
    'get_curriculum_from_rag',
    'build_roadmap_from_curriculum',
]
