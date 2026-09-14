"""Input -> output tests for POST /api/chat/stream (Server-Sent Events)."""
from __future__ import annotations

from types import SimpleNamespace

from backend.tests.conftest import TEST_USER, FakeGemini, make_match, parse_sse

MARKER = '<<<MIMO_GOI_Y>>>'


def stream(client, message='Giải thích (a+b)^2', **extra):
    response = client.post('/api/chat/stream', json={'message': message, **extra})
    assert response.status_code == 200
    assert response.headers['content-type'].startswith('text/event-stream')
    return parse_sse(response.text)


def joined_text(events):
    return ''.join(event['text'] for event in events if event['type'] == 'chunk')


def test_empty_message_rejected(client):
    assert client.post('/api/chat/stream', json={'message': '  '}).status_code == 400


def test_requires_login(anon_client):
    assert anon_client.post('/api/chat/stream', json={'message': 'hi'}).status_code == 401


def test_marker_is_hidden_and_suggestions_parsed(client, app_mod, monkeypatch):
    monkeypatch.setattr(app_mod, 'search_knowledge', lambda *a, **k: [make_match(score=0.88)])
    # Marker bị cắt ngang giữa hai chunk để kiểm tra phần giữ lại đuôi.
    fake = FakeGemini(chunks=[
        'Câu này nhiều bạn hay nhầm lắm! ',
        '$(a+b)^2 = a^2 + 2ab + b^2$ [1].\n<<<MIMO',
        '_GOI_Y>>>{"quick_replies":["Cho em gợi ý thêm","Vì sao có 2ab ạ?"],"understanding":"hiểu sơ"}',
    ])
    monkeypatch.setattr(app_mod, 'gemini_client', fake)

    events = stream(client)

    assert joined_text(events) == 'Câu này nhiều bạn hay nhầm lắm! $(a+b)^2 = a^2 + 2ab + b^2$ [1].\n'
    assert all(MARKER not in event.get('text', '') for event in events)
    done = events[-1]
    assert done['type'] == 'done'
    assert done['quick_replies'] == ['Cho em gợi ý thêm', 'Vì sao có 2ab ạ?']
    assert done['understanding'] == 'hiểu sơ'
    assert done['sources'][0]['score'] == 0.88


def test_answer_without_marker_is_emitted_fully(client, app_mod, monkeypatch):
    monkeypatch.setattr(app_mod, 'gemini_client', FakeGemini(chunks=['Xin chào ', 'em nhé!']))

    events = stream(client, message='xin chào')

    assert joined_text(events) == 'Xin chào em nhé!'
    assert events[-1] == {'type': 'done', 'content': 'Xin chào em nhé!', 'sources': [], 'quick_replies': [], 'understanding': None}


def test_invalid_suggestion_payload_is_ignored(client, app_mod, monkeypatch):
    monkeypatch.setattr(app_mod, 'gemini_client', FakeGemini(chunks=[f'Trả lời.{MARKER}{{"understanding":"siêu giỏi", oops']))

    done = stream(client)[-1]

    assert done['quick_replies'] == []
    assert done['understanding'] is None


def test_sources_deduplicated_and_filtered(client, app_mod, monkeypatch):
    matches = [
        make_match(score=0.9),
        make_match(score=0.8),  # trùng source + pdf_page -> bỏ
        make_match(score=0.7, pdf_page=20),
        make_match(score=0.3, pdf_page=30),  # dưới ngưỡng
    ]
    monkeypatch.setattr(app_mod, 'search_knowledge', lambda *a, **k: matches)
    monkeypatch.setattr(app_mod, 'gemini_client', FakeGemini(chunks=['$(a+b)^2 = a^2 + 2ab + b^2$ [1].']))

    sources = stream(client)[-1]['sources']

    assert [(s['pdf_page'], s['score']) for s in sources] == [(14, 0.9), (20, 0.7)]


def test_answer_without_citations_gets_no_sources(client, app_mod, monkeypatch):
    monkeypatch.setattr(app_mod, 'search_knowledge', lambda *a, **k: [make_match(score=0.9)])
    monkeypatch.setattr(app_mod, 'gemini_client', FakeGemini(chunks=['Em nghỉ ngơi một chút nhé [7].']))

    done = stream(client, message='em mệt quá')[-1]

    assert done['sources'] == [] and done['content'] == 'Em nghỉ ngơi một chút nhé.'


def test_off_topic_citation_is_removed_from_answer_and_sources(client, app_mod, monkeypatch):
    monkeypatch.setattr(app_mod, 'search_knowledge', lambda *a, **k: [make_match(score=0.9)])
    monkeypatch.setattr(app_mod, 'gemini_client', FakeGemini(chunks=['Chào em! Hai anh ấy đều là huyền thoại bóng đá [1]. Mình quay lại học bình phương một tổng nhé [1]?']))

    done = stream(client, message='Messi với Ronaldo ai giỏi hơn')[-1]

    assert done['sources'] == []
    assert done['content'] == 'Hai anh ấy đều là huyền thoại bóng đá. Mình quay lại học bình phương một tổng nhé?'


def test_prompt_numbers_sources_in_same_order_as_done_sources(client, app_mod, monkeypatch):
    matches = [make_match(score=0.9), make_match(score=0.8), make_match(score=0.7, pdf_page=20, page=18)]
    monkeypatch.setattr(app_mod, 'search_knowledge', lambda *a, **k: matches)
    fake = FakeGemini(chunks=['$(a+b)^2 = a^2 + 2ab + b^2$ [1][2].'])
    monkeypatch.setattr(app_mod, 'gemini_client', fake)

    sources = stream(client)[-1]['sources']

    prompt = fake.calls[0]['contents']
    assert '[1] Toan 8 tap 1.pdf | trang 12' in prompt
    assert '[2] Toan 8 tap 1.pdf | trang 18' in prompt and '[3]' not in prompt
    assert [s['page'] for s in sources] == [12, 18]


def test_prompt_contains_student_input(client, app_mod, monkeypatch):
    monkeypatch.setattr(app_mod, 'search_knowledge', lambda *a, **k: [make_match()])
    fake = FakeGemini(chunks=['ok'])
    monkeypatch.setattr(app_mod, 'gemini_client', fake)

    stream(
        client,
        message='Khai triển (x+3)^2',
        student={'name': 'Chi', 'grade': 7, 'subject': 'Toán'},
        context={'currentLesson': 'Bài 3', 'currentTopic': 'Hằng đẳng thức'},
        messages=[{'role': 'user', 'content': 'Em chưa hiểu'}, {'role': 'assistant', 'content': ''}],
    )

    prompt = fake.calls[0]['contents']
    for expected in ('Học sinh: Chi, lớp 7, đang học môn Toán', 'Bài đang học: Bài 3 – chủ đề: Hằng đẳng thức',
                     'Học sinh: Em chưa hiểu', 'Tin nhắn hiện tại của học sinh: Khai triển (x+3)^2'):
        assert expected in prompt
    assert 'Mimo: \n' not in prompt  # tin nhắn rỗng trong lịch sử bị bỏ qua


def test_prompt_adds_lesson_pages_earlier_lesson_chats_and_quiz_progress(client, app_mod, monkeypatch):
    lesson_page = make_match(score=0.8, pdf_page=7, page=6, text='Đơn thức là biểu thức đại số chỉ gồm một số hoặc một biến, hoặc có dạng tích của những số và biến.')
    queries = []

    def fake_search(query, **kwargs):
        queries.append(query)
        return [lesson_page] if query == 'Đơn thức' else [make_match(score=0.9)]

    seen = {}

    def fake_lesson_history(user_id, subject, lesson, exclude_session_id=None):
        seen.update(subject=subject, lesson=lesson, exclude=exclude_session_id)
        return [{'role': 'user', 'content': 'Em hay quên hệ số của đơn thức'}]

    monkeypatch.setattr(app_mod, 'search_knowledge', fake_search)
    monkeypatch.setattr(app_mod, 'lesson_history', fake_lesson_history)
    fake = FakeGemini(chunks=['Đơn thức là biểu thức đại số chỉ gồm một số hoặc một biến [2].'])
    monkeypatch.setattr(app_mod, 'gemini_client', fake)
    concept =app_mod.concept_id_for('Toán', 8, 'Đơn thức')
    profile = {'concepts': {concept: {'mastery': 0.4, 'attempts': 5, 'correct': 2, 'common_errors': ['quên nhân hệ số']}}}
    app_mod.app.dependency_overrides[app_mod.current_user] = lambda: {**TEST_USER, 'learningProfile': profile}

    for _ in range(2):
        events = stream(client, message='Cho em ví dụ khác', student={'grade': 8, 'subject': 'Toán'},
                        session={'id': 's1', 'lesson': 'Bài 1: Đơn thức'}, context={'currentLesson': 'Bài 1: Đơn thức', 'currentTopic': 'Đơn thức'})

    prompt = fake.calls[-1]['contents']
    assert '[2] Đơn thức là biểu thức đại số' in prompt  # lesson page (missed by the short follow-up), labelled with its citation number
    assert '[2] Toan 8 tap 1.pdf | trang 6' in prompt and [s['page'] for s in events[-1]['sources']] == [12, 6]
    assert 'Học sinh: Em hay quên hệ số của đơn thức' in prompt
    assert 'mức nắm bài 40%, đúng 2/5 câu; lỗi hay gặp: quên nhân hệ số.' in prompt
    assert seen == {'subject': 'Toán', 'lesson': 'Bài 1: Đơn thức', 'exclude': 's1'}
    assert queries.count('Đơn thức') == 1  # lesson pages cached across messages


def test_turn_is_persisted_when_message_ids_given(client, app_mod, monkeypatch):
    monkeypatch.setattr(app_mod, 'gemini_client', FakeGemini(chunks=[f'Đáp án gợi ý.  {MARKER}{{"quick_replies":["Tiếp"],"understanding":"đã hiểu"}}']))

    stream(client, session={'id': 's1'}, user_message_id='u1', assistant_message_id='a1', replaces_message_id='old')

    (args, kwargs), = app_mod.save_chat_turn.calls
    assert args[0]['id'] == 'user-test-1'
    assert kwargs['session'] == {'id': 's1'}
    assert kwargs['replaces_message_id'] == 'old'
    assert kwargs['user_message']['id'] == 'u1'
    assert kwargs['user_message']['content'] == 'Giải thích (a+b)^2'
    assistant = kwargs['assistant_message']
    assert (assistant['id'], assistant['content'], assistant['understanding'], assistant['model']) == ('a1', 'Đáp án gợi ý.', 'đã hiểu', 'gemini-test')
    assert assistant['quick_replies'] == ['Tiếp']


def test_not_persisted_without_message_ids(client, app_mod, monkeypatch):
    monkeypatch.setattr(app_mod, 'gemini_client', FakeGemini(chunks=['ok']))
    stream(client)
    assert app_mod.save_chat_turn.calls == []


def test_retrieval_error_emits_error_event(client, app_mod, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError('pinecone down')
    monkeypatch.setattr(app_mod, 'search_knowledge', boom)
    monkeypatch.setattr(app_mod, 'gemini_client', FakeGemini(chunks=['không được gọi']))

    events = stream(client)

    assert [event['type'] for event in events] == ['error']


def test_without_gemini_emits_maintenance_message(client):
    events = stream(client)

    assert [event['type'] for event in events] == ['chunk', 'done']
    assert 'bảo trì' in events[0]['text']


def test_quota_error_emits_fallback_answer(client, app_mod, monkeypatch):
    monkeypatch.setattr(app_mod, 'gemini_client', FakeGemini(error=RuntimeError('429 RESOURCE_EXHAUSTED')))

    events = stream(client, user_message_id='u1', assistant_message_id='a1', session={'id': 's1'},
                    student={'grade': 8, 'subject': 'Toán'})

    assert [event['type'] for event in events] == ['chunk', 'done']
    assert 'quá tải' in events[0]['text'] and 'lớp 8' in events[0]['text']
    assert events[1]['quick_replies'] == ['Em thử viết bước đầu nhé', 'Cho em một ví dụ khác']
    assert len(app_mod.save_chat_turn.calls) == 1


class QuotaThenAnswer(FakeGemini):
    """First model is out of quota, the next one answers."""

    def generate_content_stream(self, model, contents):
        self.calls.append({'model': model, 'contents': contents})
        if model == 'gemini-test':
            raise RuntimeError('429 RESOURCE_EXHAUSTED')
        for chunk in self.chunks:
            yield SimpleNamespace(text=chunk)


def test_quota_error_falls_back_to_next_model_and_skips_exhausted_one(client, app_mod, monkeypatch):
    monkeypatch.setattr(app_mod, 'GEMINI_FALLBACK_MODELS', ['gemini-backup'])
    fake = QuotaThenAnswer(chunks=['Trả lời từ model dự phòng.'])
    monkeypatch.setattr(app_mod, 'gemini_client', fake)

    first = stream(client)
    second = stream(client)

    assert joined_text(first) == joined_text(second) == 'Trả lời từ model dự phòng.'
    assert [call['model'] for call in fake.calls] == ['gemini-test', 'gemini-backup', 'gemini-backup']


def test_other_gemini_error_emits_error_event(client, app_mod, monkeypatch):
    monkeypatch.setattr(app_mod, 'gemini_client', FakeGemini(chunks=['Đang nói dở'], error=ConnectionError('reset')))

    events = stream(client)

    assert events[-1]['type'] == 'error'
    assert 'Thử lại' in events[-1]['message']


def test_image_is_sent_to_gemini_as_bytes(client, app_mod, monkeypatch):
    fake = FakeGemini(chunks=['Mimo đọc được đề rồi.'])
    monkeypatch.setattr(app_mod, 'gemini_client', fake)

    stream(client, message='Đề bài trong ảnh', image_data='data:image/png;base64,aGVsbG8=', image_mime_type='image/png')

    prompt_part, image_part = fake.calls[0]['contents']
    assert 'Đề bài trong ảnh' in prompt_part.text
    assert (image_part.inline_data.data, image_part.inline_data.mime_type) == (b'hello', 'image/png')


def test_rate_limit_returns_429(client, monkeypatch):
    import backend.db as db_module
    monkeypatch.setattr(db_module, 'CHAT_RATE_PER_MINUTE', 2)
    codes = [client.post('/api/chat/stream', json={'message': 'hi'}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
