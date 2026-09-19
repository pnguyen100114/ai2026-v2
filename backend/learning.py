"""Adaptive practice: Gemini writes each question for the student's current roadmap lesson.

The question bank is not hardcoded: the prompt is built from the lesson the student picked,
their grade, the textbook context from RAG and their mastery/common errors for that concept.
Generated questions are stored server-side so the answer never reaches the browser.
"""
from __future__ import annotations

import json
import re
import unicodedata
from typing import Any


DIFFICULTY_LABELS = {
    1: 'Khởi động',
    2: 'Củng cố',
    3: 'Vận dụng',
    4: 'Nâng cao',
    5: 'Thử thách',
}
DEFAULT_MASTERY = 0.35
MAX_COMMON_ERRORS = 5
GENERIC_ERROR = 'sai hoặc chưa khớp đáp án'


def _slug(text: str) -> str:
    ascii_text = unicodedata.normalize('NFKD', text.replace('đ', 'd').replace('Đ', 'D')).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', ascii_text.lower()).strip('-')


def concept_id_for(subject: str, grade: int, topic: str) -> str:
    return f'{_slug(subject) or "mon-hoc"}{grade}.{_slug(topic)[:120] or "tong-hop"}'[:200]


def concept_prefix(subject: str, grade: int) -> str:
    """Every concept id of one subject/grade starts with this (see concept_id_for)."""
    return f'{_slug(subject) or "mon-hoc"}{grade}.'


def concept_state(profile: dict[str, Any], concept_id: str) -> dict[str, Any]:
    state = dict((profile.get('concepts') or {}).get(concept_id) or {})
    state['mastery'] = max(0.0, min(1.0, float(state.get('mastery', DEFAULT_MASTERY))))
    return state


def target_difficulty(mastery: float) -> int:
    return max(1, min(5, round(1 + mastery * 4)))


def build_quiz_prompt(
    *,
    subject: str,
    grade: int,
    lesson: str,
    topic: str,
    difficulty: int,
    state: dict[str, Any],
    goal: str,
    context_text: str,
    recent_questions: list[str],
) -> str:
    errors = [str(item) for item in state.get('common_errors') or [] if str(item) != GENERIC_ERROR]
    history = (
        f"đã làm {int(state.get('attempts', 0))} câu, đúng {int(state.get('correct', 0))}, chuỗi đúng hiện tại {int(state.get('streak', 0))}"
        if state.get('attempts') else 'chưa làm câu nào về bài này'
    )
    recent_text = '\n'.join(f'- {item}' for item in recent_questions) or '- (chưa có)'
    return f'''Bạn là Mimo, gia sư AI soạn MỘT câu hỏi trắc nghiệm luyện tập cho học sinh THCS Việt Nam.

HỌC SINH
- Môn {subject}, lớp {grade}.
- Bài đang học trong lộ trình: {lesson or topic}. Chủ đề: {topic}.
- Năng lực hiện tại với bài này: {round(state['mastery'] * 100)}% ({history}).
- Lỗi hay mắc gần đây: {'; '.join(errors) if errors else 'chưa ghi nhận'}.
- Mục tiêu học tập: {goal or 'chưa nêu'}.

YÊU CẦU
- Độ khó mức {difficulty}/5 ({DIFFICULTY_LABELS[difficulty]}): 1 = nhận biết khái niệm, 3 = vận dụng trực tiếp, 5 = vận dụng cao nhưng vẫn trong chương trình lớp {grade}.
- Chỉ dùng kiến thức thuộc bài/chủ đề trên và chương trình {subject} lớp {grade}; TUYỆT ĐỐI không dùng kiến thức của lớp trên.
- Bám thuật ngữ, ký hiệu trong Context SGK bên dưới (nếu có).
- Nếu học sinh có lỗi hay mắc, ưu tiên câu hỏi giúp em sửa đúng lỗi đó.
- Không trùng ý với các câu đã hỏi gần đây.
- 3 hoặc 4 phương án, chỉ một phương án đúng; phương án sai phản ánh lỗi sai thường gặp.
- Công thức toán viết bằng LaTeX đặt giữa hai dấu $, ví dụ $3x^2y$, $\\frac{{3}}{{4}}$ — giao diện
  render bằng KaTeX như phần giảng bài. Chữ thường không bọc trong $.
- Gợi ý (hint) chỉ mở hướng làm, không lộ đáp án.

Câu đã hỏi gần đây:
{recent_text}

Context SGK:
{context_text or 'Không có context đủ tin cậy; soạn theo kiến thức chuẩn của bài trong chương trình lớp ' + str(grade) + '.'}

Chỉ trả về JSON hợp lệ đúng dạng:
{{"question":"...","options":["...","...","..."],"answer":"<chép nguyên văn một phương án>","hint":"...","explanation":"...","misconceptions":{{"<phương án sai>":"<lỗi sai học sinh mắc khi chọn phương án này>"}}}}'''


def parse_generated_question(raw: str, *, subject: str, concept_id: str, concept: str, difficulty: int) -> dict[str, Any]:
    """Validate Gemini's JSON; raise ValueError when the question is unusable."""
    cleaned = (raw or '').strip()
    start, end = cleaned.find('{'), cleaned.rfind('}')
    try:
        payload = json.loads(cleaned[start:end + 1]) if start >= 0 and end > start else None
    except json.JSONDecodeError:
        payload = None
    if not isinstance(payload, dict):
        raise ValueError('Gemini không trả về JSON hợp lệ.')

    question = str(payload.get('question') or '').strip()
    options: list[str] = []
    for item in payload.get('options') if isinstance(payload.get('options'), list) else []:
        text = str(item).strip()
        if text and _normalize_answer(text) not in {_normalize_answer(option) for option in options}:
            options.append(text)
    answer = next((option for option in options if _normalize_answer(option) == _normalize_answer(str(payload.get('answer') or ''))), None)
    if not question or not 3 <= len(options) <= 4 or answer is None:
        raise ValueError('Câu hỏi thiếu nội dung, số phương án không hợp lệ hoặc đáp án không nằm trong phương án.')

    raw_misconceptions = payload.get('misconceptions') if isinstance(payload.get('misconceptions'), dict) else {}
    misconceptions = {
        option: str(raw_misconceptions[key]).strip()[:160]
        for key in raw_misconceptions
        for option in options
        if option != answer and _normalize_answer(str(key)) == _normalize_answer(option) and str(raw_misconceptions[key]).strip()
    }
    return {
        'subject': subject,
        'concept_id': concept_id,
        'concept': concept,
        'difficulty': difficulty,
        'type': 'choice',
        'question': question,
        'options': options,
        'answer': answer,
        'hint': str(payload.get('hint') or '').strip() or 'Em đọc lại kiến thức trọng tâm của bài rồi loại trừ từng phương án nhé.',
        'explanation': str(payload.get('explanation') or '').strip() or f'Đáp án đúng là: {answer}.',
        'misconceptions': misconceptions,
    }


def public_question(question_id: str, question: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    """What the browser may see: everything except the answer, explanation and misconceptions."""
    errors = [item for item in state.get('common_errors') or [] if item != GENERIC_ERROR]
    reason = (
        f"Mimo soạn câu này để em luyện lại lỗi: {errors[-1]}." if errors
        else f"Câu hỏi được soạn riêng cho bài {question['concept']}, vừa với năng lực hiện tại của em."
    )
    return {
        'question_id': question_id,
        'concept_id': question['concept_id'],
        'concept': question['concept'],
        'difficulty': question['difficulty'],
        'difficulty_label': DIFFICULTY_LABELS[question['difficulty']],
        'type': question['type'],
        'question': question['question'],
        'options': question['options'],
        'hint': question['hint'],
        'mastery': round(float(state['mastery']), 2),
        'reason': reason,
    }


def _normalize_answer(value: str) -> str:
    normalized = value.strip().lower().replace('²', '^2').replace('³', '^3')
    # Câu hỏi nay sinh ra kèm LaTeX, nên "$x^2$", "$x^{2}$" và "x^2" phải được coi là một:
    # đáp án đúng được so bằng chuỗi, lệch một dấu ngoặc là chấm sai một câu em làm đúng.
    normalized = normalized.replace('$', '').replace('{', '').replace('}', '').replace('\\', '')
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized


def grade_answer(question: dict[str, Any], answer: str, profile: dict[str, Any], hints_used: int = 0) -> dict[str, Any]:
    correct = _normalize_answer(answer) == _normalize_answer(question['answer'])
    concept_id = question['concept_id']
    concepts = profile.setdefault('concepts', {})
    state = concepts.setdefault(concept_id, {'mastery': DEFAULT_MASTERY, 'attempts': 0, 'correct': 0, 'streak': 0, 'common_errors': []})
    state['concept'] = question['concept']
    previous_streak = int(state.get('streak', 0))
    state['attempts'] = int(state.get('attempts', 0)) + 1
    if correct:
        state['correct'] = int(state.get('correct', 0)) + 1
        state['streak'] = previous_streak + 1
        delta = 0.10 if hints_used == 0 else 0.04
        feedback = 'Chính xác. Em đã nắm được ý chính của kiến thức này.'
        next_action = 'progression' if state['streak'] >= 2 else 'practice'
    else:
        state['streak'] = 0
        delta = -0.10
        misconception = next((text for option, text in (question.get('misconceptions') or {}).items() if _normalize_answer(option) == _normalize_answer(answer)), '')
        error = misconception or GENERIC_ERROR
        errors = [item for item in state.get('common_errors') or [] if item != error]
        state['common_errors'] = (errors + [error])[-MAX_COMMON_ERRORS:]
        feedback = f'Chưa đúng lần này. {misconception + ". " if misconception else ""}Gợi ý: {question["hint"]}'
        next_action = 'remedial'
    state['mastery'] = round(max(0.0, min(1.0, float(state.get('mastery', DEFAULT_MASTERY)) + delta)), 2)
    next_difficulty = max(1, min(5, question['difficulty'] + (1 if correct and state['streak'] >= 2 else -1 if not correct else 0)))
    recommendation = {
        'kind': 'quiz' if correct else 'lesson',
        'title': 'Thử câu vận dụng tiếp theo' if correct else f'Ôn lại {question["concept"]}',
        'reason': 'Em đã có chuỗi trả lời đúng.' if correct else 'Cần củng cố lại khái niệm trước khi tăng độ khó.',
        'action': {'type': 'quiz' if correct else 'lesson', 'concept_id': concept_id, 'difficulty': next_difficulty},
    }
    return {
        'is_correct': correct,
        'partial_score': 1.0 if correct else 0.0,
        'feedback': feedback,
        'explanation': question['explanation'],
        'mastery': state['mastery'],
        'next_difficulty': next_difficulty,
        'next_action': next_action,
        'recommendation': recommendation,
        'profile': profile,
    }
