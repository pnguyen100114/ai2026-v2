"""Input -> output tests for password sign-in, the client-IP rate limit, safety guardrails and input limits."""
from __future__ import annotations

from types import SimpleNamespace

import unicodedata

import pytest
from sqlalchemy import create_engine, update

from backend import accounts, db, safety
from backend.tests.conftest import FakeGemini, make_match, parse_sse

MARKER = '<<<MIMO_GOI_Y>>>'


@pytest.fixture
def auth_client(anon_client, monkeypatch, tmp_path):
    # Real account code on a throwaway SQLite file.
    engine = create_engine(f"sqlite:///{(tmp_path / 'auth.db').as_posix()}", connect_args={'check_same_thread': False})
    monkeypatch.setattr(db, 'engine', engine)
    db.init_db()
    db._rate_windows.clear()
    return anon_client


def sign_in(client, **body):
    return client.post('/api/auth/email', json={'email': 'an@example.com', **body})


def test_register_then_login_requires_the_right_password(auth_client):
    registered = sign_in(auth_client, mode='register', name='An', grade=7, password='bimat123')
    assert registered.status_code == 200 and registered.json()['user']['grade'] == 7
    assert 'password' not in str(registered.json()['user']).lower()

    assert sign_in(auth_client, mode='login', password='sai-mat-khau').status_code == 401
    assert sign_in(auth_client, mode='login').status_code == 401
    assert sign_in(auth_client, email='AN@example.com', mode='login', password='bimat123').status_code == 200


def test_quiz_evidence_and_attempt_metadata_are_persisted(auth_client):
    user = db.create_user('quiz-evidence@example.com', 'An', 8, 'bimat123')
    learning_profile = {'concepts': {'toan8.bien-doi': {
        'mastery': 0.62,
        'evidence': [{'difficulty': 3, 'time_spent_seconds': 42, 'error_tags': ['sign_error']}],
    }}}
    db.save_quiz_attempt(user, {
        'question_id': 'quiz-evidence-1',
        'answer': 'x',
        'is_correct': False,
        'hints_used': 2,
        'difficulty': 3,
        'time_spent_seconds': 42,
        'expected_time_seconds': 30,
        'error_tags': ['sign_error'],
        'mastery': 0.62,
    }, learning_profile)

    with db.engine.connect() as connection:
        attempt = connection.execute(
            db.select(db.quiz_attempts).where(db.quiz_attempts.c.question_id == 'quiz-evidence-1')
        ).mappings().one()
    assert attempt['hints_used'] == 2
    assert attempt['difficulty'] == 3
    assert attempt['time_spent_seconds'] == 42
    assert attempt['expected_time_seconds'] == 30
    assert attempt['error_tags'] == ['sign_error']
    assert db.get_user(user['id'])['learningProfile'] == learning_profile


def test_legacy_quiz_attempt_table_is_migrated_for_adaptive_evidence(monkeypatch, tmp_path):
    legacy_engine = create_engine(
        f"sqlite:///{(tmp_path / 'legacy-quiz.db').as_posix()}",
        connect_args={'check_same_thread': False},
    )
    monkeypatch.setattr(db, 'engine', legacy_engine)
    with legacy_engine.begin() as connection:
        connection.exec_driver_sql('''
            CREATE TABLE quiz_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id VARCHAR(36) NOT NULL,
                question_id VARCHAR(80) NOT NULL,
                answer TEXT NOT NULL,
                is_correct BOOLEAN NOT NULL,
                hints_used INTEGER NOT NULL DEFAULT 0,
                mastery FLOAT,
                created_at DATETIME NOT NULL
            )
        ''')
    db.init_db()
    columns = {column['name'] for column in db.inspect(legacy_engine).get_columns('quiz_attempts')}
    assert {'difficulty', 'time_spent_seconds', 'expected_time_seconds', 'error_tags'} <= columns


@pytest.mark.parametrize('body, status', [
    ({'mode': 'register', 'name': 'An', 'password': '123'}, 400),   # quá ngắn
    ({'mode': 'register', 'name': ' ', 'password': 'bimat123'}, 400),
    ({'mode': 'login', 'password': 'bimat123'}, 404),               # chưa có tài khoản
])
def test_sign_in_invalid_input(auth_client, body, status):
    assert sign_in(auth_client, **body).status_code == status


def test_register_with_existing_email_does_not_log_in(auth_client):
    sign_in(auth_client, mode='register', name='An', password='bimat123')
    response = sign_in(auth_client, mode='register', name='Kẻ gian', password='khac1234')
    assert response.status_code == 409 and 'token' not in response.json()


def test_change_password_requires_current_password(auth_client):
    token = sign_in(auth_client, mode='register', name='An', password='bimat123').json()['token']
    headers = {'Authorization': f'Bearer {token}'}

    def change(current, new):
        return auth_client.post('/api/me/password', json={'currentPassword': current, 'newPassword': new}, headers=headers)

    assert change('sai-mat-khau', 'moi12345').status_code == 400
    assert change('bimat123', '123').status_code == 400          # quá ngắn
    assert change('bimat123', 'bimat123').status_code == 400     # trùng mật khẩu cũ
    assert auth_client.post('/api/me/password', json={'currentPassword': 'bimat123', 'newPassword': 'moi12345'}).status_code == 401
    assert change('bimat123', 'moi12345').status_code == 200
    assert sign_in(auth_client, mode='login', password='bimat123').status_code == 401
    assert sign_in(auth_client, mode='login', password='moi12345').status_code == 200


def test_legacy_account_without_password_is_claimed_on_first_login(auth_client):
    user = db.create_user('cu@example.com', 'Cũ', 8, 'tam-thoi')
    with db.engine.begin() as conn:
        conn.execute(update(db.users).where(db.users.c.id == user['id']).values(password_hash=None))
    assert sign_in(auth_client, email='cu@example.com', mode='login', password='moi12345').status_code == 200
    assert sign_in(auth_client, email='cu@example.com', mode='login', password='khac1234').status_code == 401


def test_password_guessing_is_rate_limited_per_email(auth_client):
    sign_in(auth_client, mode='register', name='An', password='bimat123')
    for _ in range(3):  # successful sign-ins never count towards the lock
        assert sign_in(auth_client, mode='login', password='bimat123').status_code == 200
    codes = [sign_in(auth_client, mode='login', password=f'doan{i}xx').status_code for i in range(6)]
    assert codes == [401] * 5 + [429]
    assert sign_in(auth_client, mode='login', password='bimat123').status_code == 429  # locked for a moment


def test_forged_forwarded_for_is_ignored_without_trusted_proxy(auth_client, monkeypatch):
    monkeypatch.setattr(accounts, 'TRUSTED_PROXY_HOPS', 0)
    codes = [auth_client.post('/api/auth/email', json={'email': f'khong{i}@example.com', 'mode': 'login'},
                              headers={'X-Forwarded-For': f'1.2.3.{i}'}).status_code for i in range(31)]
    assert codes[-1] == 429


@pytest.mark.parametrize('hops, header, expected', [
    (0, '9.9.9.9', 'testclient'),
    (1, 'gia-mao, 5.6.7.8', '5.6.7.8'),
    (2, 'gia-mao, 5.6.7.8, 10.0.0.1', '5.6.7.8'),
])
def test_client_ip_uses_only_trusted_hops(monkeypatch, hops, header, expected):
    monkeypatch.setattr(accounts, 'TRUSTED_PROXY_HOPS', hops)
    request = SimpleNamespace(headers={'x-forwarded-for': header}, client=SimpleNamespace(host='testclient'))
    assert accounts.client_ip(request) == expected


def test_blank_profile_name_rejected(auth_client):
    token = sign_in(auth_client, mode='register', name='An', password='bimat123').json()['token']
    assert auth_client.patch('/api/me', json={'name': '   '}, headers={'Authorization': f'Bearer {token}'}).status_code == 422


# ---------------------------------------------------------------- progress

def test_progress_reports_real_streak_today_and_lessons(auth_client):
    from datetime import timedelta
    from sqlalchemy import insert

    body = sign_in(auth_client, mode='register', name='An', grade=8, password='bimat123').json()
    token, user_id = body['token'], body['user']['id']
    headers = {'Authorization': f'Bearer {token}'}
    empty = auth_client.get('/api/progress', params={'subject': 'Toán', 'grade': 8}, headers=headers).json()
    assert empty == {'streak': 0, 'activeToday': False, 'today': {'questions': 0, 'quizzes': 0, 'quizCorrect': 0},
                     'studiedLessons': [], 'concepts': {}, 'masteredThreshold': 0.7}

    now = db._now()
    with db.engine.begin() as conn:
        for index, (days_ago, lesson, subject) in enumerate([(0, 'Bài 1: Đơn thức', 'Toán'), (1, 'Bài 2: Đa thức', 'Toán'), (2, 'Bài 1: Đơn thức', 'Toán'), (4, 'Bài 3', 'Toán'), (0, 'Bài 9: Tế bào', 'KHTN')]):
            at = now - timedelta(days=days_ago)
            conn.execute(insert(db.chat_sessions).values(id=f's{index}', user_id=user_id, title='t', subject=subject, grade='Lớp 8', lesson=lesson, created_at=at, updated_at=at))
            conn.execute(insert(db.messages).values(id=f'm{index}', session_id=f's{index}', user_id=user_id, role='user', content='hỏi', created_at=at))
        conn.execute(insert(db.quiz_attempts).values(user_id=user_id, question_id='q1', answer='a', is_correct=True, created_at=now))
        conn.execute(db.update(db.users).where(db.users.c.id == user_id).values(learning_profile={'concepts': {
            'toan8.don-thuc': {'concept': 'Đơn thức', 'mastery': 0.8, 'attempts': 3},
            'khtn8.te-bao': {'concept': 'Tế bào', 'mastery': 0.2, 'attempts': 1},
        }}))
    # Test này ghi thẳng vào bảng users bằng SQL, không qua db.py, nên phải tự bỏ bản nhớ hồ
    # sơ học sinh (xem get_user). Code thật không cần dòng này: mọi đường ghi đều tự gọi.
    db.forget_user(user_id)

    progress = auth_client.get('/api/progress', params={'subject': 'Toán', 'grade': 8}, headers=headers).json()

    assert progress['streak'] == 3  # hôm nay, hôm qua, hôm kia; ngày thứ 4 bị đứt
    assert progress['activeToday'] is True
    assert progress['today'] == {'questions': 2, 'quizzes': 1, 'quizCorrect': 1}
    assert progress['studiedLessons'] == ['Bài 1: Đơn thức', 'Bài 2: Đa thức', 'Bài 3']
    assert progress['concepts'] == {'Đơn thức': {'mastery': 0.8, 'attempts': 3}}


def test_progress_requires_login_and_valid_grade(auth_client):
    assert auth_client.get('/api/progress', params={'subject': 'Toán', 'grade': 8}).status_code == 401
    token = sign_in(auth_client, mode='register', name='An', password='bimat123').json()['token']
    assert auth_client.get('/api/progress', params={'subject': 'Toán', 'grade': 12}, headers={'Authorization': f'Bearer {token}'}).status_code == 422


# ---------------------------------------------------------------- safety & limits

@pytest.mark.parametrize('message, risk', [
    ('mấy bạn trong lớp hay trêu em', safety.HARM),
    ('may ban trong lop bat nat em', safety.HARM),
    ('em không muốn sống nữa', safety.SELF_HARM),
    ('em muon tu tu', safety.SELF_HARM),
    ('từ từ giải thích cho em', None),
    ('bài này khó muốn chết', None),
    ('Giải thích (a+b)^2', None),
    # Unaccented, teen spelling and decomposed (NFD) text: how kids actually type.
    ('em muon tu sat', safety.SELF_HARM),
    ('em muốn chết', safety.SELF_HARM),
    ('em mun chet', safety.SELF_HARM),
    ('em buồn quá muốn chết', safety.SELF_HARM),
    ('em chán lắm, muốn chết', safety.SELF_HARM),
    ('e ko muốn sống nữa', safety.SELF_HARM),
    ('em k muon song nua', safety.SELF_HARM),
    ('em chán sống lắm', safety.SELF_HARM),
    ('em muon tu sat vi khong hieu dao ham', safety.SELF_HARM),
    (unicodedata.normalize('NFD', 'em không muốn sống nữa'), safety.SELF_HARM),
    ('em bi ep lam viec', safety.HARM),
    # Hyperbole and ordinary maths stay lessons.
    ('mệt quá muốn chết', None),
    ('đói muốn chết rồi', None),
    ('học toán chán muốn chết', None),
    ('em không thích sống ở quê', None),
    ('đường thẳng đi qua từ hai điểm', None),
])
def test_detect_risk(message, risk):
    assert safety.detect_risk(message) == risk


@pytest.mark.parametrize('message, earlier, risk', [
    # Mimo's own safety quick replies have no risk words; they continue the disclosure.
    ('Em nên nói với ai ạ?', ['em muốn chết'], safety.SELF_HARM),
    ('Em muốn kể thêm', ['mấy bạn hay trêu em', 'Em nên nói với ai ạ?'], safety.HARM),
    # The student chose to go back to the lesson, now and in the turns after.
    ('Mình học tiếp nhé', ['mấy bạn hay trêu em'], None),
    ('Giải x + 2 = 5', ['mấy bạn hay trêu em', 'Mình học tiếp nhé'], None),
    # Long ago in the chat no longer counts.
    ('Giải x + 2 = 5', ['mấy bạn hay trêu em', 'a', 'b', 'c'], None),
    ('Giải x + 2 = 5', [], None),
])
def test_conversation_risk_carries_over_recent_disclosure(message, earlier, risk):
    assert safety.conversation_risk(message, earlier) == risk


@pytest.mark.parametrize('reply, leaks', [
    ('Em tính ra x = 6 rồi', True), ('Em nghĩ là 5', True), ('Kết quả bằng -3 ạ', True),
    ('khai triển ra là x^2 + 4x + 4 ạ', True), ('Em được 2x + 1', True), ('Kết quả là a - b ạ', True),
    ('Vì sao có 2ab ạ?', False), ('Cho em gợi ý thêm', False), ('Bài 2 là gì ạ?', False), ('Khai triển (x+2)^2 thế nào ạ?', False),
    ('Còn bình phương của một hiệu là sao ạ?', False), ('tách thành 100 cộng 1 ạ', True), ('Em tính ra (x-2)(x+2) rồi ạ', True),
    ('Đó là hằng đẳng thức ạ', True), ('Biểu thức đó không phải đơn thức ạ', True), ('Là sao ạ', False),
    ('Có phải hằng đẳng thức không ạ', False), ('Đó là gì vậy Mimo?', False), ('Là bình phương của một tổng đúng không?', False),
    ('Có dùng Mimo ơi', True), ('Dạ không ạ', True), ('Không dùng đúng không Mimo?', False), ('Không hiểu lắm ạ', False),
    ('Có ví dụ khác không ạ', False), ('Đổi thành gì ạ?', False),
])
def test_leaks_answer(reply, leaks):
    assert safety.leaks_answer(reply) is leaks


def stream(client, message, **extra):
    response = client.post('/api/chat/stream', json={'message': message, **extra})
    assert response.status_code == 200
    return parse_sse(response.text)


def test_bullying_answer_gets_adult_note_no_sources_and_safe_replies(client, app_mod, monkeypatch):
    monkeypatch.setattr(app_mod, 'search_knowledge', lambda *a, **k: [make_match()])
    fake = FakeGemini(chunks=[f'Đừng để tâm, học giỏi lên nhé!{MARKER}{{"quick_replies":["Em sẵn sàng học"]}}'])
    monkeypatch.setattr(app_mod, 'gemini_client', fake)

    events = stream(client, 'mấy bạn hay trêu em', user_message_id='u1', assistant_message_id='a1', session={'id': 's1'})

    text = ''.join(e['text'] for e in events if e['type'] == 'chunk')
    assert '111' in text and 'thầy cô' in text
    assert events[-1]['sources'] == [] and events[-1]['quick_replies'] == safety.SAFETY_QUICK_REPLIES[safety.HARM]
    assert 'AN TOÀN VÀ CẢM XÚC' in fake.calls[0]['contents']
    (_, kwargs), = app_mod.save_chat_turn.calls
    assert '111' in kwargs['assistant_message']['content']


@pytest.mark.parametrize('gemini', [None, FakeGemini(error=RuntimeError('429 RESOURCE_EXHAUSTED')), FakeGemini(error=ConnectionError('reset'))])
def test_self_harm_message_always_gets_hotline(client, app_mod, monkeypatch, gemini):
    def down(*args, **kwargs):
        raise RuntimeError('pinecone down')
    monkeypatch.setattr(app_mod, 'search_knowledge', down)
    monkeypatch.setattr(app_mod, 'gemini_client', gemini)

    events = stream(client, 'em không muốn sống nữa')

    assert [e['type'] for e in events] == ['chunk', 'done']
    assert '111' in events[0]['text'] and '115' in events[0]['text']


def test_safety_quick_reply_stays_in_safety_mode(client, app_mod, monkeypatch):
    retrievals = []
    monkeypatch.setattr(app_mod, 'search_knowledge', lambda *a, **k: retrievals.append(k) or [make_match(grade=7, score=0.95)])
    monkeypatch.setattr(app_mod, 'gemini_client', FakeGemini(error=RuntimeError('429 RESOURCE_EXHAUSTED')))
    history = [{'role': 'user', 'content': 'em muốn chết'}, {'role': 'assistant', 'content': 'Mimo ở đây với em.'}]

    events = stream(client, 'Em nên nói với ai ạ?', messages=history)

    text = ''.join(e['text'] for e in events if e['type'] == 'chunk')
    assert '111' in text and 'Mimo không tìm thấy' not in text and 'bước đầu tiên' not in text
    assert events[-1]['quick_replies'] == safety.SAFETY_QUICK_REPLIES[safety.SELF_HARM]
    assert all(k.get('grade') is not None for k in retrievals)  # no "which grade is this lesson in" search


def test_quick_replies_revealing_the_answer_are_dropped(client, app_mod, monkeypatch):
    monkeypatch.setattr(app_mod, 'gemini_client', FakeGemini(chunks=[f'Em tính x nhé?{MARKER}{{"quick_replies":["Em tính ra x = 6 rồi","Cho em gợi ý thêm"]}}']))
    assert stream(client, '2x + 5 = 17')[-1]['quick_replies'] == ['Cho em gợi ý thêm']


@pytest.mark.parametrize('payload', [
    {'message': 'x' * 2001},
    {'message': 'ảnh', 'image_data': 'a' * 8_000_001},
])
def test_oversized_chat_input_rejected(client, payload):
    assert client.post('/api/chat/stream', json=payload).status_code == 422


def test_long_history_is_trimmed_not_rejected(client, app_mod, monkeypatch):
    fake = FakeGemini(chunks=['ok'])
    monkeypatch.setattr(app_mod, 'gemini_client', fake)
    history = [{'role': 'user', 'content': f'Giải thích bài học số {i}'} for i in range(200)]
    stream(client, 'hỏi tiếp', messages=history)
    assert 'bài học số 199' in fake.calls[0]['contents'] and 'bài học số 150' not in fake.calls[0]['contents']


def test_admin_password_reset(auth_client, capsys):
    from backend import reset_password

    sign_in(auth_client, mode='register', name='An', password='bimat123')
    assert reset_password.main(['reset', 'AN@example.com', 'moi-mat-khau']) == 0
    assert reset_password.main(['reset', 'khong-co@example.com', 'moi-mat-khau']) == 1
    assert reset_password.main(['reset', 'an@example.com', '123']) == 1
    assert sign_in(auth_client, mode='login', password='bimat123').status_code == 401
    assert sign_in(auth_client, mode='login', password='moi-mat-khau').status_code == 200


# ---------------------------------------------------------------- "Trang này không đúng?"

CITED = {'source': 'TOAN8-TAP 1.pdf', 'title': 'Toán 8 – Tập một', 'lesson_title': 'Bài 6. Hiệu hai bình phương', 'page': 34, 'pdf_page': 35}


def save_turn(user, session_id='s1', question='Hiệu hai bình phương là gì?', answer_id='a1', **extra):
    now = db._now()
    db.save_chat_turn(
        user, session={'id': session_id, 'title': 'Hằng đẳng thức', 'subject': 'Toán', 'grade': 'Lớp 8'},
        user_message={'id': f'q-{answer_id}', 'content': question, 'prompt': question, 'has_image': False, 'image_text': None, 'created_at': now},
        assistant_message={'id': answer_id, 'content': 'Hiệu hai bình phương: $a^2 - b^2 = (a-b)(a+b)$ [1].', 'sources': [CITED],
                           'quick_replies': [], 'understanding': None, 'model': 'test', 'latency_ms': 1, 'created_at': now},
        **extra,
    )


def report(client, token, **body):
    payload = {'message_id': 'a1', 'source': CITED['source'], 'pdf_page': CITED['pdf_page'], 'reason': 'wrong_page', **body}
    return client.post('/api/source-report', json=payload, headers={'Authorization': f'Bearer {token}'})


def test_source_report_records_the_cited_page_with_the_question(auth_client):
    token = sign_in(auth_client, mode='register', name='An', password='bimat123').json()['token']
    user = db.find_user_by_email('an@example.com')
    save_turn(user)

    assert report(auth_client, token).status_code == 200
    assert report(auth_client, token, reason='unrelated').status_code == 200  # changes the reason, not a second report

    (row,) = db.list_source_reports()
    assert (row['reason'], row['book_title'], row['page'], row['pdf_page']) == ('unrelated', 'Toán 8 – Tập một', 34, 35)
    assert row['question'] == 'Hiệu hai bình phương là gì?' and '[1]' in row['answer']


@pytest.mark.parametrize('body', [
    {'pdf_page': 99},                     # a page this answer did not cite
    {'message_id': 'khong-co'},
    {'reason': 'boring'},
])
def test_source_report_rejects_pages_the_answer_did_not_cite(auth_client, body):
    token = sign_in(auth_client, mode='register', name='An', password='bimat123').json()['token']
    save_turn(db.find_user_by_email('an@example.com'))
    assert report(auth_client, token, **body).status_code in (404, 422)
    assert db.list_source_reports() == []


def test_source_report_on_another_students_answer_is_refused(auth_client):
    save_turn(db.create_user('binh@example.com', 'Bình', 8, 'bimat123'))
    token = sign_in(auth_client, mode='register', name='An', password='bimat123').json()['token']
    assert report(auth_client, token).status_code == 404


def test_source_report_survives_retry_but_not_deleting_the_chat(auth_client):
    token = sign_in(auth_client, mode='register', name='An', password='bimat123').json()['token']
    user = db.find_user_by_email('an@example.com')
    save_turn(user)
    save_turn(user, session_id='s2', answer_id='b1')
    report(auth_client, token)
    report(auth_client, token, message_id='b1')

    # "Thử lại" deletes the reported answer; the report is what tells us the page was wrong.
    save_turn(user, answer_id='a2', replaces_message_id='q-a1')
    assert len(db.list_source_reports()) == 2

    db.delete_session(user['id'], 's1')
    assert [row['message_id'] for row in db.list_source_reports()] == ['b1']


def test_source_report_summary_puts_the_most_reported_page_first():
    from backend.source_reports import summarize

    base = {'source': 'X.pdf', 'book_title': 'Toán 8', 'lesson_title': None, 'pdf_page': 3, 'question': 'q'}
    rows = summarize([
        {**base, 'page': 1, 'reason': 'unrelated', 'user_id': 'u1'},
        {**base, 'page': 2, 'pdf_page': 4, 'reason': 'wrong_page', 'user_id': 'u1'},
        {**base, 'page': 1, 'reason': 'unrelated', 'user_id': 'u2'},
    ])
    assert [(row['page'], sum(row['reasons'].values()), len(row['students'])) for row in rows] == [(1, 2, 2), (2, 1, 1)]
