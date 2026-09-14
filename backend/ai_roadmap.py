"""Fallback roadmap when RAG has no textbook for a subject/grade: Gemini outlines the GDPT 2018 curriculum.

The result is stored in the database so lesson titles stay stable (the student's current lesson is
matched by title) and Gemini is called once per subject/grade.
"""
from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

MAX_CHAPTERS = 12
MAX_LESSONS_PER_CHAPTER = 15


def _slug(text: str) -> str:
    ascii_text = unicodedata.normalize('NFKD', text.replace('đ', 'd').replace('Đ', 'D')).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '_', ascii_text.lower()).strip('_') or 'subject'


def build_roadmap_prompt(subject: str, grade: int) -> str:
    return f'''Bạn là chuyên gia chương trình giáo dục phổ thông Việt Nam (Chương trình GDPT 2018).
Liệt kê lộ trình học môn {subject} lớp {grade} theo đúng thứ tự trong sách giáo khoa hiện hành (ưu tiên bộ "Kết nối tri thức với cuộc sống"), cả năm học.

Yêu cầu:
- Chỉ gồm nội dung của môn {subject} lớp {grade}; không đưa kiến thức lớp khác.
- Mỗi chương gồm các bài học theo thứ tự; số bài đánh liên tục trong cả năm như SGK.
- Tên chương, tên bài ngắn gọn, đúng thuật ngữ SGK, không kèm chữ "Chương"/"Bài" ở đầu tên.
- Tối đa {MAX_CHAPTERS} chương, mỗi chương tối đa {MAX_LESSONS_PER_CHAPTER} bài; bỏ các bài ôn tập, luyện tập chung, hoạt động trải nghiệm.

Chỉ trả về JSON hợp lệ đúng dạng:
{{"chapters":[{{"chapter":1,"title":"...","lessons":[{{"lesson":1,"title":"..."}}]}}]}}'''


def _clean_title(value: Any, prefix: str) -> str:
    title = re.sub(r'\s+', ' ', str(value or '')).strip()
    # Strip "Chương 1:", "Chương IV." or "Bài 3 -". Roman numerals need a separator so "Bài Vi khuẩn" stays intact.
    return re.sub(rf'^{prefix}\s*(?:\d+\s*[:.\-–]?|[ivxlc]+\s*[:.\-–])?\s*', '', title, flags=re.IGNORECASE).strip()[:150]


def parse_generated_roadmap(raw: str, subject: str, grade: int) -> dict[str, Any]:
    """Validate Gemini's outline into the same shape as the RAG roadmap; raise ValueError when unusable."""
    cleaned = (raw or '').strip()
    start, end = cleaned.find('{'), cleaned.rfind('}')
    try:
        payload = json.loads(cleaned[start:end + 1]) if start >= 0 and end > start else None
    except json.JSONDecodeError:
        payload = None
    raw_chapters = payload.get('chapters') if isinstance(payload, dict) else None
    if not isinstance(raw_chapters, list):
        raise ValueError('Gemini không trả về danh sách chương hợp lệ.')

    chapters: list[dict[str, Any]] = []
    next_lesson = 1
    for raw_chapter in raw_chapters[:MAX_CHAPTERS]:
        if not isinstance(raw_chapter, dict):
            continue
        chapter_no = len(chapters) + 1
        lessons = []
        seen: set[str] = set()
        for raw_lesson in (raw_chapter.get('lessons') if isinstance(raw_chapter.get('lessons'), list) else [])[:MAX_LESSONS_PER_CHAPTER]:
            title = _clean_title(raw_lesson.get('title') if isinstance(raw_lesson, dict) else raw_lesson, 'bài')
            if not title or title.lower() in seen:
                continue
            seen.add(title.lower())
            lessons.append({
                'id': f'lesson_{chapter_no}_{next_lesson}',
                'lesson': next_lesson,
                'title': title,
                'volume': 0,
                'status': 'locked',
                'progress': 0,
                'sources': [],
            })
            next_lesson += 1
        if lessons:
            chapters.append({
                'id': f'chapter_{chapter_no}',
                'chapter': chapter_no,
                'title': _clean_title(raw_chapter.get('title'), 'chương') or f'Chương {chapter_no}',
                'lessons': lessons,
            })
    if not chapters:
        raise ValueError('Lộ trình không có bài học nào.')
    return {
        'id': f'{_slug(subject)}_{grade}',
        'subject': subject,
        'grade': grade,
        'title': f'Lộ trình {subject} {grade}',
        'progress': 0,
        'source': 'ai',
        'chapters': chapters,
    }
