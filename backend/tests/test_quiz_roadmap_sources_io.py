"""Input -> output tests for quiz, roadmap, health and source preview endpoints."""
from __future__ import annotations

import json
from urllib.parse import parse_qs, urlsplit

import pytest

from backend.db import signed_source_url
from backend.tests.conftest import TEST_USER, FakeGemini, make_match

STUDENT = {'name': 'An', 'grade': 6, 'subject': 'Toán'}
# No textbook in backend/rag/books.py: roadmaps come from RAG metadata or the AI outline.
NO_BOOK_STUDENT = {'name': 'An', 'grade': 7, 'subject': 'Ngữ văn'}
LESSON_CONTEXT = {'currentLesson': 'Bài 1: Tập hợp', 'currentTopic': 'Tập hợp'}
CONCEPT_ID = 'toan6.tap-hop'
GENERATED = {
    'question': 'Cho A = {1; 2; 3}. Khẳng định nào đúng?',
    'options': ['1 ∈ A', '4 ∈ A', '2 ∉ A'],
    'answer': '1 ∈ A',
    'hint': 'Xem số nào được liệt kê trong dấu ngoặc nhọn.',
    'explanation': 'Số 1 có trong danh sách phần tử của A nên 1 ∈ A.',
    'misconceptions': {'2 ∉ A': 'nhầm ký hiệu ∈ và ∉'},
}


def as_student_with(app_mod, profile):
    # Progress is read from the signed-in account, never from the request body.
    app_mod.app.dependency_overrides[app_mod.current_user] = lambda: {**TEST_USER, 'learningProfile': profile}


def ask_quiz(client, app_mod, *, profile=None, context=LESSON_CONTEXT, reply=GENERATED):
    fake = FakeGemini(text=json.dumps(reply, ensure_ascii=False))
    app_mod.gemini_client = fake
    if profile is not None:
        as_student_with(app_mod, profile)
    response = client.post('/api/quiz/next', json={'student': STUDENT, 'context': context})
    return response, fake


# ---------------------------------------------------------------- quiz

@pytest.mark.parametrize('mastery, difficulty', [
    (None, 2),  # mặc định 0.35 -> độ khó 2
    (0.0, 1),
    (1.0, 5),
])
def test_quiz_next_generates_question_for_current_lesson(client, app_mod, mastery, difficulty):
    profile = {} if mastery is None else {'concepts': {CONCEPT_ID: {'mastery': mastery}}}

    response, fake = ask_quiz(client, app_mod, profile=profile)
    body = response.json()

    assert response.status_code == 200
    question = body['question']
    assert question['concept_id'] == CONCEPT_ID
    assert question['concept'] == 'Tập hợp'
    assert question['difficulty'] == difficulty
    assert question['options'] == GENERATED['options']
    assert not {'answer', 'explanation', 'misconceptions'} & question.keys()  # không lộ đáp án
    assert body['profile'] == profile
    forged = client.post('/api/quiz/next', json={'student': STUDENT, 'context': LESSON_CONTEXT, 'profile': {'concepts': {CONCEPT_ID: {'mastery': 1.0 if difficulty != 5 else 0.0}}}})
    assert forged.json()['question']['difficulty'] == difficulty  # hồ sơ gửi từ trình duyệt bị bỏ qua
    prompt = fake.calls[0]['contents']
    assert 'lớp 6' in prompt and 'Bài 1: Tập hợp' in prompt and f'mức {difficulty}/5' in prompt


def test_quiz_prompt_is_personalized_with_errors_and_recent_questions(client, app_mod):
    profile = {'concepts': {CONCEPT_ID: {'mastery': 0.3, 'attempts': 4, 'correct': 1, 'common_errors': ['nhầm ký hiệu ∈ và ∉']}}}
    ask_quiz(client, app_mod)

    response, fake = ask_quiz(client, app_mod, profile=profile)

    prompt = fake.calls[0]['contents']
    assert 'nhầm ký hiệu ∈ và ∉' in prompt
    assert GENERATED['question'] in prompt  # câu đã hỏi -> tránh lặp
    assert 'luyện lại lỗi' in response.json()['question']['reason']


@pytest.mark.parametrize('context, status', [
    ({}, 400),                                    # chưa chọn bài trong lộ trình
    ({'currentLesson': '', 'currentTopic': ''}, 400),
])
def test_quiz_next_requires_a_lesson(client, app_mod, context, status):
    response, fake = ask_quiz(client, app_mod, context=context)
    assert response.status_code == status
    assert fake.calls == []


@pytest.mark.parametrize('reply', [
    {**GENERATED, 'answer': 'không có trong phương án'},
    {**GENERATED, 'options': ['1 ∈ A', '1 ∈ A']},
    'không phải json',
])
def test_quiz_next_rejects_invalid_generation(client, app_mod, reply):
    fake = FakeGemini(text=reply if isinstance(reply, str) else json.dumps(reply, ensure_ascii=False))
    app_mod.gemini_client = fake
    response = client.post('/api/quiz/next', json={'student': STUDENT, 'context': LESSON_CONTEXT})
    assert response.status_code == 502
    assert app_mod.question_store == {}


def test_quiz_next_without_gemini(client):
    assert client.post('/api/quiz/next', json={'student': STUDENT, 'context': LESSON_CONTEXT}).status_code == 503


def test_quiz_next_quota(client, app_mod):
    app_mod.gemini_client = FakeGemini(error=RuntimeError('429 RESOURCE_EXHAUSTED'))
    assert client.post('/api/quiz/next', json={'student': STUDENT, 'context': LESSON_CONTEXT}).status_code == 429


@pytest.mark.parametrize('answer, hints_used, correct, mastery, error', [
    ('1 ∈ A', 0, True, 0.45, None),
    ('  1 ∈ a ', 0, True, 0.45, None),   # chuẩn hóa hoa/thường, khoảng trắng
    ('1 ∈ A', 2, True, 0.39, None),       # dùng gợi ý -> cộng ít điểm hơn
    ('2 ∉ A', 0, False, 0.25, 'nhầm ký hiệu ∈ và ∉'),  # ghi nhận lỗi sai cụ thể
    ('4 ∈ A', 0, False, 0.25, 'sai hoặc chưa khớp đáp án'),
])
def test_quiz_answer_grades_and_updates_mastery(client, app_mod, answer, hints_used, correct, mastery, error):
    question_id = ask_quiz(client, app_mod)[0].json()['question']['question_id']

    body = client.post('/api/quiz/answer', json={
        'question_id': question_id, 'answer': answer, 'hints_used': hints_used,
        'profile': {'concepts': {'gia-mao': {'mastery': 1}}},  # bị bỏ qua
    }).json()

    assert body['is_correct'] is correct
    assert body['mastery'] == mastery
    assert body['next_action'] == ('practice' if correct else 'remedial')
    assert body['recommendation']['kind'] == ('quiz' if correct else 'lesson')
    assert list(body['profile']['concepts']) == [CONCEPT_ID]
    state = body['profile']['concepts'][CONCEPT_ID]
    assert state['attempts'] == 1
    assert state.get('common_errors', []) == ([error] if error else [])

    (args, _), = app_mod.save_quiz_attempt.calls
    assert args[1] == {'question_id': question_id, 'answer': answer, 'is_correct': correct,
                       'hints_used': hints_used, 'mastery': mastery}


def test_quiz_streak_moves_to_progression(client, app_mod):
    profile = {'concepts': {CONCEPT_ID: {'mastery': 0.5, 'streak': 1}}}
    question_id = ask_quiz(client, app_mod, profile=profile)[0].json()['question']['question_id']

    body = client.post('/api/quiz/answer', json={'question_id': question_id, 'answer': '1 ∈ A'}).json()

    assert body['next_action'] == 'progression'
    assert body['next_difficulty'] == 4  # câu mức 3 (mastery 0.5) -> tăng lên 4


def test_quiz_answer_cannot_be_submitted_twice(client, app_mod):
    question_id = ask_quiz(client, app_mod)[0].json()['question']['question_id']
    assert client.post('/api/quiz/answer', json={'question_id': question_id, 'answer': '1 ∈ A'}).status_code == 200
    again = client.post('/api/quiz/answer', json={'question_id': question_id, 'answer': '1 ∈ A'})
    assert again.status_code == 409
    assert len(app_mod.save_quiz_attempt.calls) == 1


def test_quiz_answer_rejects_other_users_question(client, app_mod):
    question_id = ask_quiz(client, app_mod)[0].json()['question']['question_id']
    app_mod.question_store[question_id]['user_id'] = 'someone-else'
    assert client.post('/api/quiz/answer', json={'question_id': question_id, 'answer': '1 ∈ A'}).status_code == 404


@pytest.mark.parametrize('payload, status', [
    ({'question_id': 'khong-ton-tai', 'answer': 'x'}, 404),
    ({'question_id': '', 'answer': 'x'}, 422),
    ({'question_id': 'q-1', 'hints_used': 4}, 422),
    ({'question_id': 'q-1', 'hints_used': -1}, 422),
])
def test_quiz_answer_invalid_input(client, payload, status):
    assert client.post('/api/quiz/answer', json=payload).status_code == status


def test_quiz_requires_login(anon_client):
    assert anon_client.post('/api/quiz/next', json={'student': STUDENT}).status_code == 401


# ---------------------------------------------------------------- roadmap

def test_roadmap_generate_success(client, app_mod, monkeypatch):
    curriculum = [make_match(score=0.876, lesson=f'Bài {i}') for i in range(12)]
    seen = {}
    monkeypatch.setattr(app_mod, 'get_curriculum', lambda subject, grade: seen.update(get=(subject, grade)) or curriculum)
    monkeypatch.setattr(app_mod, 'build_roadmap', lambda cur, subject, grade: {'id': f'toan_{grade}', 'items': len(cur)})

    body = client.post('/api/roadmap/generate', json={'student': {'grade': 9, 'subject': 'Toán'}}).json()

    assert seen['get'] == ('Toán', 9)
    assert body['roadmap'] == {'id': 'toan_9', 'items': 12}
    assert len(body['sources']) == 10
    assert body['sources'][0] == {'source': 'Toan 8 tap 1.pdf', 'page': 12, 'chapter': 'Chương 1', 'lesson': 'Bài 0', 'score': 0.88}


def test_roadmap_generate_not_found(client, app_mod, monkeypatch):
    monkeypatch.setattr(app_mod, 'get_curriculum', lambda subject, grade: [])
    assert client.post('/api/roadmap/generate', json={'student': NO_BOOK_STUDENT}).status_code == 404  # không SGK, không Gemini


AI_OUTLINE = {'chapters': [
    {'chapter': 1, 'title': 'Chương I: Tập hợp các số tự nhiên', 'lessons': [{'lesson': 1, 'title': 'Bài 1. Tập hợp'}, {'lesson': 2, 'title': 'Cách ghi số tự nhiên'}, {'title': 'Tập hợp'}]},
    {'chapter': 2, 'title': 'Tính chia hết', 'lessons': ['Quan hệ chia hết', '']},
    {'chapter': 3, 'title': 'Rỗng', 'lessons': []},
]}


def test_roadmap_falls_back_to_ai_outline_when_no_textbook(client, app_mod, monkeypatch):
    monkeypatch.setattr(app_mod, 'get_curriculum', lambda subject, grade: [])
    fake = FakeGemini(text=json.dumps(AI_OUTLINE, ensure_ascii=False))
    app_mod.gemini_client = fake

    body = client.post('/api/roadmap/generate', json={'student': NO_BOOK_STUDENT}).json()
    again = client.post('/api/roadmap/generate', json={'student': NO_BOOK_STUDENT}).json()

    roadmap = body['roadmap']
    assert roadmap['source'] == 'ai' and roadmap['grade'] == 7 and roadmap['subject'] == 'Ngữ văn'
    assert [(c['chapter'], c['title']) for c in roadmap['chapters']] == [(1, 'Tập hợp các số tự nhiên'), (2, 'Tính chia hết')]
    assert [(l['lesson'], l['title']) for c in roadmap['chapters'] for l in c['lessons']] == [
        (1, 'Tập hợp'), (2, 'Cách ghi số tự nhiên'), (3, 'Quan hệ chia hết'),  # bỏ trùng/rỗng, đánh số liên tục
    ]
    assert 'lớp 7' in fake.calls[0]['contents']
    assert again['roadmap'] == roadmap and len(fake.calls) == 1  # lưu lại, không gọi Gemini lần hai


def test_roadmap_uses_ai_outline_when_textbook_lacks_lesson_structure(client, app_mod, monkeypatch):
    curriculum = [make_match(lesson=None) for _ in range(50)] + [make_match(lesson=f'Bài {i}') for i in (4, 8, 40)]
    monkeypatch.setattr(app_mod, 'get_curriculum', lambda subject, grade: curriculum)
    app_mod.gemini_client = FakeGemini(text=json.dumps(AI_OUTLINE, ensure_ascii=False))
    assert client.post('/api/roadmap/generate', json={'student': NO_BOOK_STUDENT}).json()['roadmap']['source'] == 'ai'


def test_roadmap_ai_fallback_also_covers_rag_errors(client, app_mod, monkeypatch):
    def broken(subject, grade):
        raise RuntimeError('Pinecone down')
    monkeypatch.setattr(app_mod, 'get_curriculum', broken)
    app_mod.gemini_client = FakeGemini(text=json.dumps(AI_OUTLINE, ensure_ascii=False))
    assert client.post('/api/roadmap/generate', json={'student': NO_BOOK_STUDENT}).json()['roadmap']['source'] == 'ai'


@pytest.mark.parametrize('text, status', [('không phải json', 502), ('{"chapters": [{"title": "A", "lessons": []}]}', 502)])
def test_roadmap_ai_fallback_invalid_output(client, app_mod, monkeypatch, text, status):
    monkeypatch.setattr(app_mod, 'get_curriculum', lambda subject, grade: [])
    app_mod.gemini_client = FakeGemini(text=text)
    assert client.post('/api/roadmap/generate', json={'student': NO_BOOK_STUDENT}).status_code == status
    assert app_mod.roadmap_store == {}


@pytest.mark.parametrize('roadmap_id, subject, grade', [
    ('toan_9', 'Toan', 9),
    ('vat-ly_9', 'Vat Ly', 9),
    ('ngu-van_abc', 'Ngu Van', 8),
])
def test_roadmap_by_id_parses_subject_and_grade(client, app_mod, monkeypatch, roadmap_id, subject, grade):
    monkeypatch.setattr(app_mod, 'get_curriculum', lambda s, g: [make_match()])
    monkeypatch.setattr(app_mod, 'build_roadmap', lambda cur, s, g: {'subject': s, 'grade': g})

    assert client.get(f'/api/roadmap/{roadmap_id}').json() == {'roadmap': {'subject': subject, 'grade': grade}}


# ---------------------------------------------------------------- health & sources

def test_health(client):
    body = client.get('/api/health').json()
    assert body['status'] == 'ok'
    assert body['rag'] == {'configured': True, 'namespace': 'default', 'vectors': 0}


@pytest.fixture
def book_dir(tmp_path, app_mod, monkeypatch):
    import pymupdf
    document = pymupdf.open()
    for number in range(2):
        document.new_page().insert_text((72, 72), f'Trang {number + 1}')
    document.save(tmp_path / 'Toan 8.pdf')
    document.close()
    monkeypatch.setattr(app_mod, 'DATA_DIR', tmp_path)
    return tmp_path


def signed(source, page, **extra):
    query = {key: values[0] for key, values in parse_qs(urlsplit(signed_source_url(source, page)).query).items()}
    return {**query, **extra}


@pytest.mark.parametrize('source', ['Toan 8.pdf', 'toan 8.pdf', '../../secret/Toan 8.pdf'])
def test_source_page_renders_png(client, book_dir, source):
    response = client.get('/api/sources/page', params=signed(source, 2))
    assert response.status_code == 200
    assert response.headers['content-type'] == 'image/png'
    assert response.content.startswith(b'\x89PNG')


def test_source_page_thumbnail_is_small_jpeg(client, book_dir):
    response = client.get('/api/sources/page', params=signed('Toan 8.pdf', 1, thumb='true'))
    assert response.status_code == 200
    assert response.headers['content-type'] == 'image/jpeg'
    assert response.content.startswith(b'\xff\xd8')
    full = client.get('/api/sources/page', params=signed('Toan 8.pdf', 1))
    assert len(response.content) < len(full.content)


@pytest.mark.parametrize('params, status', [
    (signed('Toan 8.pdf', 3), 404),   # vượt số trang
    (signed('Khong co.pdf', 1), 404),
    (signed('Toan 8.txt', 1), 404),
    ({'source': 'Toan 8.pdf', 'page': 0}, 422),
    ({'page': 1}, 422),
    ({'source': 'Toan 8.pdf', 'page': 1}, 403),              # không có chữ ký
    ({**signed('Toan 8.pdf', 1), 'page': 2}, 403),           # chữ ký của trang khác
    ({**signed('Toan 8.pdf', 1), 'sig': '0' * 32}, 403),     # chữ ký giả
    ({**signed('Toan 8.pdf', 1), 'exp': '1000'}, 403),       # hết hạn
])
def test_source_page_invalid_input(client, book_dir, params, status):
    assert client.get('/api/sources/page', params=params).status_code == status
