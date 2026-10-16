"""Adaptive practice: Gemini writes each question for the student's current roadmap lesson.

The question bank is not hardcoded: the prompt is built from the lesson the student picked,
their grade, the textbook context from RAG and their mastery/common errors for that concept.
Generated questions are stored server-side so the answer never reaches the browser.
"""
from __future__ import annotations

import json
import re
import statistics
import time
import unicodedata
from typing import Any

try:
    from backend.rag.books import canonical_subject
except ImportError:  # pragma: no cover
    from rag.books import canonical_subject


DIFFICULTY_LABELS = {
    1: 'Khởi động',
    2: 'Củng cố',
    3: 'Vận dụng',
    4: 'Nâng cao',
    5: 'Thử thách',
}
DEFAULT_MASTERY = 0.35
MAX_COMMON_ERRORS = 5
MAX_MASTERY_EVIDENCE = 30
GENERIC_ERROR = 'sai hoặc chưa khớp đáp án'
MASTERY_PRIOR_WEIGHT = 4.0
MIN_TIME_SECONDS = 1
MAX_TIME_SECONDS = 7200

ERROR_TAGS: dict[str, dict[str, str]] = {
    'Toán': {
        'concept_misunderstanding': 'Chưa nắm ý nghĩa khái niệm',
        'formula_confusion': 'Nhầm công thức hoặc tính chất',
        'sign_error': 'Sai dấu khi biến đổi',
        'algebraic_transformation': 'Biến đổi đại số chưa đúng',
        'calculation_error': 'Sai phép tính',
        'condition_omission': 'Bỏ sót điều kiện',
        'misread_question': 'Bỏ sót dữ kiện/yêu cầu',
        'reasoning_gap': 'Thiếu bước lập luận',
        'careless_error': 'Lỗi bất cẩn có bằng chứng',
    },
    'Ngữ văn': {
        'reading_comprehension': 'Chưa nắm ý văn bản',
        'evidence_selection': 'Chọn dẫn chứng chưa phù hợp',
        'interpretation': 'Diễn giải ý chưa chính xác',
        'writing_structure': 'Bố cục bài viết chưa rõ',
        'grammar_usage': 'Dùng từ/ngữ pháp chưa phù hợp',
        'prompt_response': 'Chưa đáp ứng đủ yêu cầu đề',
    },
    'Tiếng Anh': {
        'vocabulary_confusion': 'Nhầm nghĩa hoặc cách dùng từ',
        'grammar_confusion': 'Nhầm cấu trúc ngữ pháp',
        'tense_error': 'Chọn thì chưa phù hợp',
        'reading_comprehension': 'Chưa nắm ý bài đọc',
        'listening_comprehension': 'Chưa bắt được thông tin nghe',
        'spelling_error': 'Sai chính tả',
        'prompt_response': 'Chưa đáp ứng đủ yêu cầu đề',
    },
    'KHTN': {
        'concept_misunderstanding': 'Chưa nắm ý nghĩa khái niệm',
        'formula_confusion': 'Nhầm công thức hoặc quy tắc',
        'unit_conversion': 'Đổi đơn vị chưa đúng',
        'calculation_error': 'Sai phép tính',
        'cause_effect': 'Nhầm quan hệ nguyên nhân - kết quả',
        'data_interpretation': 'Đọc số liệu chưa chính xác',
        'misread_question': 'Bỏ sót dữ kiện/yêu cầu',
    },
    'LSDL': {
        'chronology': 'Nhầm trình tự thời gian',
        'cause_effect': 'Nhầm quan hệ nguyên nhân - kết quả',
        'source_interpretation': 'Diễn giải tư liệu chưa chính xác',
        'map_reading': 'Đọc bản đồ/lược đồ chưa đúng',
        'geographic_concept': 'Chưa nắm khái niệm địa lí',
        'misread_question': 'Bỏ sót dữ kiện/yêu cầu',
    },
}


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
    try:
        mastery = float(state.get('mastery', DEFAULT_MASTERY))
    except (TypeError, ValueError):
        mastery = DEFAULT_MASTERY
    state['mastery'] = max(0.0, min(1.0, mastery))
    state['evidence_count'] = len(state.get('evidence') or [])
    state['priority_error_tags'] = recurring_error_tags(state, _subject_for_concept(concept_id))
    return state


def target_difficulty(mastery: float) -> int:
    mastery = max(0.0, min(1.0, float(mastery)))
    return max(1, min(5, round(1 + mastery * 4)))


def _subject_for_concept(concept_id: str) -> str:
    prefix = concept_id.split('.', 1)[0]
    return next((subject for subject in ERROR_TAGS if _slug(subject) == re.sub(r'\d+$', '', prefix)), '')


def recurring_error_tags(state: dict[str, Any], subject: str) -> list[str]:
    allowed = ERROR_TAGS.get(subject, {})
    counts = state.get('error_counts') if isinstance(state.get('error_counts'), dict) else {}
    valid = [
        (tag, float(count))
        for tag, count in counts.items()
        if tag in allowed and isinstance(count, (int, float)) and count >= 1.5
    ]
    valid.sort(key=lambda item: (-item[1], item[0]))
    return [tag for tag, _ in valid[:3]]


def reference_time_seconds(profile: dict[str, Any], concept_id: str, difficulty: int) -> int | None:
    state = (profile.get('concepts') or {}).get(concept_id) or {}
    evidence = state.get('evidence') if isinstance(state.get('evidence'), list) else []
    times = [
        item['time_spent_seconds'] for item in evidence
        if isinstance(item, dict)
        and item.get('difficulty') == difficulty
        and isinstance(item.get('time_spent_seconds'), int)
        and MIN_TIME_SECONDS <= item['time_spent_seconds'] <= MAX_TIME_SECONDS
        and item.get('time_reliable', True)
    ]
    if len(times) < 3:
        return None
    return max(MIN_TIME_SECONDS, min(MAX_TIME_SECONDS, round(statistics.median(times))))


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
    error_tags: list[str] | None = None,
) -> str:
    errors = [str(item) for item in state.get('common_errors') or [] if str(item) != GENERIC_ERROR]
    history = (
        f"đã làm {int(state.get('attempts', 0))} câu, đúng {int(state.get('correct', 0))}, chuỗi đúng hiện tại {int(state.get('streak', 0))}"
        if state.get('attempts') else 'chưa làm câu nào về bài này'
    )
    recent_text = '\n'.join(f'- {item}' for item in recent_questions) or '- (chưa có)'
    subject = canonical_subject(subject)
    taxonomy = ERROR_TAGS.get(subject, {})
    focus_tags = [tag for tag in (error_tags or state.get('priority_error_tags') or []) if tag in taxonomy]
    focus_text = ', '.join(f'{tag}: {taxonomy[tag]}' for tag in focus_tags) or 'chưa đủ bằng chứng lỗi lặp lại'
    return f'''Bạn là Mimo, gia sư AI soạn MỘT câu hỏi trắc nghiệm luyện tập cho học sinh THCS Việt Nam.

HỌC SINH
- Môn {subject}, lớp {grade}.
- Bài đang học trong lộ trình: {lesson or topic}. Chủ đề: {topic}.
- Năng lực hiện tại với bài này: {round(state['mastery'] * 100)}% ({history}).
- Lỗi hay mắc gần đây: {'; '.join(errors) if errors else 'chưa ghi nhận'}.
- Dạng lỗi đã được ghi nhận lặp lại: {focus_text}. Nếu có tag, ưu tiên câu hỏi luyện đúng kỹ năng này; chỉ gắn tag khi phương án sai có bằng chứng phù hợp.
- Bộ tag lỗi hợp lệ của môn {subject}: {', '.join(f'{tag} ({description})' for tag, description in taxonomy.items()) or 'không có'}.
- Mục tiêu học tập: {goal or 'chưa nêu'}.

YÊU CẦU
- Độ khó mức {difficulty}/5 ({DIFFICULTY_LABELS[difficulty]}): 1 = nhận biết khái niệm, 3 = vận dụng trực tiếp, 5 = vận dụng cao nhưng vẫn trong chương trình lớp {grade}.
- Chỉ dùng kiến thức thuộc bài/chủ đề trên và chương trình {subject} lớp {grade}; TUYỆT ĐỐI không dùng kiến thức của lớp trên.
- Bám thuật ngữ, ký hiệu trong Context SGK bên dưới (nếu có).
- Nếu học sinh có lỗi hay mắc, ưu tiên câu hỏi giúp em sửa đúng lỗi đó.
- Không trùng ý với các câu đã hỏi gần đây.
- 3 hoặc 4 phương án, chỉ một phương án đúng; phương án sai phản ánh lỗi sai thường gặp.
- Trả thêm error_tags là object ánh xạ phương án sai sang MỘT tag trong bộ tag cho môn {subject}; chỉ gắn tag khi cách suy luận sai thật sự thể hiện lỗi đó. Không gắn tag cho đáp án đúng hoặc khi chưa đủ bằng chứng.
- Công thức toán viết bằng LaTeX đặt giữa hai dấu $, ví dụ $3x^2y$, $\\frac{{3}}{{4}}$ — giao diện
  render bằng KaTeX như phần giảng bài. Chữ thường không bọc trong $. Quy tắc này áp dụng cho CẢ
  question, TỪNG phương án trong options, answer, hint và explanation; không dùng \\( \\) hay \\[ \\].
- Gợi ý (hint) chỉ mở hướng làm, không lộ đáp án.

Câu đã hỏi gần đây:
{recent_text}

Context SGK:
{context_text or 'Không có context đủ tin cậy; soạn theo kiến thức chuẩn của bài trong chương trình lớp ' + str(grade) + '.'}

Chỉ trả về JSON hợp lệ đúng dạng:
{{"question":"...","options":["...","...","..."],"answer":"<chép nguyên văn một phương án>","hint":"...","explanation":"...","misconceptions":{{"<phương án sai>":"<giải thích lỗi cụ thể>"}},"error_tags":{{"<phương án sai>":"<tag hợp lệ của môn>"}}}}'''


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
    subject = canonical_subject(subject)
    taxonomy = ERROR_TAGS.get(subject, {})
    raw_tags = payload.get('error_tags') if isinstance(payload.get('error_tags'), dict) else {}
    error_tags = {
        option: str(raw_tags[option])
        for option in options
        if option != answer and raw_tags.get(option) in taxonomy
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
        'error_tags': error_tags,
        'expected_time_seconds': None,
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
        **({'expected_time_seconds': question['expected_time_seconds']}
           if question.get('expected_time_seconds') is not None else {}),
    }


def _normalize_answer(value: str) -> str:
    normalized = value.strip().lower().replace('²', '^2').replace('³', '^3')
    # Câu hỏi nay sinh ra kèm LaTeX, nên "$x^2$", "$x^{2}$" và "x^2" phải được coi là một:
    # đáp án đúng được so bằng chuỗi, lệch một dấu ngoặc là chấm sai một câu em làm đúng.
    normalized = normalized.replace('$', '').replace('{', '').replace('}', '').replace('\\', '')
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized


def grade_answer(
    question: dict[str, Any],
    answer: str,
    profile: dict[str, Any],
    hints_used: int = 0,
    *,
    time_spent_seconds: int | None = None,
    expected_time_seconds: int | None = None,
) -> dict[str, Any]:
    correct = _normalize_answer(answer) == _normalize_answer(question['answer'])
    concept_id = question['concept_id']
    subject = canonical_subject(question.get('subject') or _subject_for_concept(concept_id))
    taxonomy = ERROR_TAGS.get(subject, {})
    concepts = profile.setdefault('concepts', {})
    state = concepts.setdefault(concept_id, {
        'mastery': DEFAULT_MASTERY, 'attempts': 0, 'correct': 0, 'streak': 0,
        'common_errors': [], 'evidence': [], 'error_counts': {},
    })
    try:
        current_mastery = max(0.0, min(1.0, float(state.get('mastery', DEFAULT_MASTERY))))
    except (TypeError, ValueError):
        current_mastery = DEFAULT_MASTERY
    try:
        baseline_mastery = max(0.0, min(1.0, float(state.get('baseline_mastery', current_mastery))))
    except (TypeError, ValueError):
        baseline_mastery = current_mastery
    state.setdefault('baseline_mastery', baseline_mastery)
    raw_common_errors = state.get('common_errors')
    state['common_errors'] = [
        str(error)[:160] for error in raw_common_errors
        if isinstance(error, str) and error.strip()
    ][-MAX_COMMON_ERRORS:] if isinstance(raw_common_errors, list) else []
    state['concept'] = question['concept']
    previous_streak = max(0, int(state.get('streak', 0)))
    attempts = max(0, int(state.get('attempts', 0)))
    state['attempts'] = attempts + 1
    hints = max(0, min(3, int(hints_used)))
    difficulty = max(1, min(5, int(question.get('difficulty', 2))))

    valid_time = (
        time_spent_seconds
        if isinstance(time_spent_seconds, int) and MIN_TIME_SECONDS <= time_spent_seconds <= MAX_TIME_SECONDS
        else None
    )
    expected_time = (
        expected_time_seconds
        if isinstance(expected_time_seconds, int) and MIN_TIME_SECONDS <= expected_time_seconds <= MAX_TIME_SECONDS
        else None
    )
    time_reliable = not (
        valid_time is not None and expected_time is not None
        and valid_time < max(3, expected_time * 0.15)
    )

    # One event is deliberately low-weight against a four-event prior; a suspiciously
    # short attempt further reduces evidence, but never labels the learner as weak.
    score = (1.0 if correct else 0.0) + (difficulty - 3) * (0.025 if correct else 0.0125)
    if correct:
        score -= min(0.18, hints * 0.06)
    score = max(0.0, min(1.0, score))
    evidence_weight = 0.35 if not time_reliable else 1.0
    evidence = state.get('evidence') if isinstance(state.get('evidence'), list) else []
    event = {
        'score': round(score, 4),
        'weight': evidence_weight,
        'is_correct': correct,
        'difficulty': difficulty,
        'hints_used': hints,
        'time_spent_seconds': valid_time,
        'expected_time_seconds': expected_time,
        'time_reliable': time_reliable,
        'created_at': int(time.time()),
    }

    selected_tag = None
    if not correct:
        if state.get('correct') is None:
            state['correct'] = 0
        misconception = next(
            (str(text)[:160] for option, text in (question.get('misconceptions') or {}).items()
             if _normalize_answer(option) == _normalize_answer(answer) and isinstance(text, str)),
            '',
        )
        selected_tag = next(
            (tag for option, tag in (question.get('error_tags') or {}).items()
             if _normalize_answer(option) == _normalize_answer(answer) and tag in taxonomy),
            None,
        )
        errors = [item for item in state.get('common_errors') or [] if item != (misconception or GENERIC_ERROR)]
        state['common_errors'] = (errors + [misconception or GENERIC_ERROR])[-MAX_COMMON_ERRORS:]
        feedback = f'Chưa đúng lần này. {misconception + ". " if misconception else ""}Gợi ý: {question["hint"]}'
        state['streak'] = 0
    else:
        state['correct'] = int(state.get('correct', 0)) + 1
        state['streak'] = previous_streak + 1
        state['common_errors'] = (state.get('common_errors') or [])[1:]
        feedback = 'Chính xác. Em đã nắm được ý chính của kiến thức này.'

    raw_counts = state.get('error_counts') if isinstance(state.get('error_counts'), dict) else {}
    error_counts = {
        tag: max(0.0, min(20.0, float(count) * 0.9))
        for tag, count in raw_counts.items()
        if tag in taxonomy and isinstance(count, (int, float))
    }
    if selected_tag:
        error_counts[selected_tag] = min(20.0, error_counts.get(selected_tag, 0.0) + 1.0)
    state['error_counts'] = {tag: round(count, 3) for tag, count in error_counts.items() if count >= 0.1}
    if selected_tag:
        event['error_tags'] = [selected_tag]
    state['evidence'] = (evidence + [event])[-MAX_MASTERY_EVIDENCE:]
    scored_evidence = [
        item for item in state['evidence']
        if isinstance(item, dict)
        and isinstance(item.get('score'), (int, float))
        and isinstance(item.get('weight', 1.0), (int, float))
    ]
    weighted_score = sum(float(item['score']) * float(item.get('weight', 1.0)) for item in scored_evidence)
    evidence_weight_total = sum(float(item.get('weight', 1.0)) for item in scored_evidence)
    state['mastery'] = round(max(0.0, min(
        1.0,
        (baseline_mastery * MASTERY_PRIOR_WEIGHT + weighted_score)
        / (MASTERY_PRIOR_WEIGHT + evidence_weight_total),
    )), 2)

    priority_tags = recurring_error_tags(state, subject)
    next_difficulty = target_difficulty(state['mastery'])
    if priority_tags:
        next_difficulty = min(next_difficulty, max(1, difficulty))
        next_action = 'targeted_practice'
        reason = f'Em thường gặp lại lỗi {taxonomy[priority_tags[0]].lower()}. Mình luyện đúng dạng này thêm nhé.'
        title = f'Luyện thêm: {taxonomy[priority_tags[0]]}'
        action_type = 'quiz'
    elif not correct and state['mastery'] < 0.45:
        next_difficulty = max(1, min(difficulty, next_difficulty))
        next_action = 'remedial'
        reason = 'Mình củng cố kiến thức nền bằng một câu vừa sức trước nhé.'
        title = f'Ôn lại {question["concept"]}'
        action_type = 'lesson'
    elif correct and state['streak'] >= 2 and state['mastery'] >= 0.55:
        next_difficulty = min(5, max(next_difficulty, difficulty + 1))
        next_action = 'progression'
        reason = 'Em đang làm đúng ổn định; mình thử một câu khó hơn nhé.'
        title = 'Thử câu vận dụng tiếp theo'
        action_type = 'quiz'
    else:
        next_action = 'practice'
        reason = 'Mimo chọn câu tiếp theo theo kết quả gần đây và mức độ tự chủ của em.'
        title = 'Luyện thêm một câu cùng dạng'
        action_type = 'quiz'

    evidence_count = evidence_weight_total
    confidence = 'low' if evidence_count < 2 else 'medium' if evidence_count < 6 else 'high'
    assessment = {
        'mastery_score': round(state['mastery'] * 100),
        'confidence': confidence,
        'weak_topics': [question['concept']] if priority_tags else [],
        'recurring_errors': priority_tags,
        'recommended_difficulty': DIFFICULTY_LABELS[next_difficulty].lower(),
        'recommendation_reason': reason,
        'next_activity': 'targeted_practice' if priority_tags else action_type,
    }
    recommendation = {
        'kind': action_type,
        'title': title,
        'reason': reason,
        'action': {
            'type': action_type,
            'concept_id': concept_id,
            'difficulty': next_difficulty,
            **({'error_tag': priority_tags[0]} if priority_tags else {}),
        },
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
        'assessment': assessment,
        'profile': profile,
        'error_tags': [selected_tag] if selected_tag else [],
        'time_reliable': time_reliable,
        'time_spent_seconds': valid_time,
    }
