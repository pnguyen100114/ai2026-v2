"""Textbook catalog (subjects, lessons, printed pages) and the Vietnamese speech endpoints."""
from __future__ import annotations

import base64
from urllib.parse import parse_qs, urlsplit

import pytest

from backend.db import signed_source_url
from backend.rag import books
from backend.speech import speakable_text
from backend.tests.conftest import FakeGemini


# ---------------------------------------------------------------- catalog

@pytest.mark.parametrize('name, subject', [
    ('Khoa học tự nhiên', 'KHTN'), ('khtn', 'KHTN'), ('Toán học', 'Toán'), ('Lịch sử và Địa lý', 'LSDL'), ('Vật lý', 'Vật lý'),
])
def test_canonical_subject(name, subject):
    assert books.canonical_subject(name) == subject


def test_every_course_is_numbered_continuously_and_pages_increase():
    for course in books.COURSES:
        lessons = course.lessons()
        assert [item.lesson for item in lessons] == list(range(1, len(lessons) + 1)), course.subject
        for volume in {item.volume for item in lessons}:
            pages = [item.page for item in lessons if item.volume == volume and item.page is not None]
            assert pages == sorted(pages) and len(pages) == len(set(pages)), (course.subject, course.grade, volume)


@pytest.mark.parametrize('source', ['KHTN.pdf', 'KHTN 6.pdf', 'khtn 6.PDF', 'backend/data/KHTN.pdf'])
def test_find_book_follows_aliases(source):
    assert books.find_book(source).id == 'khtn6'


def test_enrich_match_replaces_ocr_lesson_and_page():
    # Stored by the old ingest: every KHTN chunk was labelled "Bài 40" and pages were not offset.
    payload = {'source': 'KHTN 6.pdf', 'pdf_page': 103, 'page': 103, 'lesson': 8, 'chapter': 0, 'subject': 'Khoa học tự nhiên', 'title': 'Bài 40. Lực là gì?'}
    enriched = books.enrich_match(payload)
    assert enriched['page'] == 102 and enriched['subject'] == 'KHTN' and enriched['grade'] == 6
    assert (enriched['chapter'], enriched['lesson'], enriched['title']) == (7, 30, 'Nguyên sinh vật')
    assert enriched['lesson_title'] == 'Bài 30. Nguyên sinh vật' and enriched['book_title'] == 'Khoa học tự nhiên 6'


def test_enrich_match_leaves_unknown_books_alone():
    payload = {'source': 'Ngu van 7.pdf', 'pdf_page': 10, 'page': 10, 'lesson': 2}
    assert books.enrich_match(dict(payload)) == payload


def test_catalog_roadmap_lists_all_lessons_with_pages_only_where_the_pdf_has_them():
    roadmap = books.build_catalog_roadmap('Toán', 6)
    lessons = [lesson for chapter in roadmap['chapters'] for lesson in chapter['lessons']]
    assert roadmap['source'] == 'rag' and roadmap['subject'] == 'Toán' and roadmap['grade'] == 6
    assert len(roadmap['chapters']) == 9 and len(lessons) == 43
    assert lessons[0] == {'id': 'lesson_1_1', 'lesson': 1, 'title': 'Tập hợp', 'volume': 1, 'status': 'locked', 'progress': 0,
                          'sources': [{'source': 'Toán 6 – Tập một', 'page': 5}]}
    assert lessons[13]['sources'] == [{'source': 'Toán 6 – Tập một', 'page': 62}]  # last lesson in the partial scan
    assert lessons[14]['sources'] == [] and lessons[30]['sources'] == []  # after the scan ends / volume 2


def test_catalog_roadmap_accepts_subject_alias():
    assert books.build_catalog_roadmap('Khoa học tự nhiên', 6)['chapters'][7]['lessons'][0]['title'] == 'Lực là gì?'
    assert books.build_catalog_roadmap('Ngữ văn', 6) is None


@pytest.mark.parametrize('topic', ['Lực là gì?', 'Bài 40: Lực là gì?', 'luc la gi?'])
def test_lesson_page_filter_limits_search_to_the_lesson_pages(topic):
    assert books.lesson_page_filter('KHTN', 6, topic) == {
        'source': {'$in': ['KHTN.pdf', 'KHTN 6.pdf']},
        'page': {'$gte': 145, '$lte': 147},  # printed 144-146 -> PDF pages
    }


@pytest.mark.parametrize('subject, grade, topic', [
    ('KHTN', 6, 'Bài 41: Lực là gì?'),       # number does not match
    ('Toán', 6, 'Phân số'),                   # not a lesson title
    ('Toán', 6, 'Số thập phân'),              # volume 2: no PDF
    ('Ngữ văn', 6, 'Bài 1: Bầu trời tuổi thơ'),
])
def test_lesson_page_filter_none_without_book_pages(subject, grade, topic):
    assert books.lesson_page_filter(subject, grade, topic) is None


def test_roadmap_endpoint_uses_catalog_without_rag_or_gemini(client, app_mod, monkeypatch):
    monkeypatch.setattr(app_mod, 'get_curriculum', lambda subject, grade: pytest.fail('RAG should not be queried'))
    body = client.post('/api/roadmap/generate', json={'student': {'grade': 6, 'subject': 'KHTN'}}).json()
    assert body['roadmap']['title'] == 'Lộ trình KHTN 6'
    assert [chapter['title'] for chapter in body['roadmap']['chapters']][:2] == ['Mở đầu về Khoa học tự nhiên', 'Chất quanh ta']
    assert client.get('/api/roadmap/khtn_6').json()['roadmap'] == body['roadmap']


def test_lesson_pages_and_quiz_search_use_lesson_filter(client, app_mod, monkeypatch):
    calls = []
    monkeypatch.setattr(app_mod, 'search_knowledge', lambda *args, **kwargs: calls.append(kwargs) or [])
    client.post('/api/chat/stream', json={'message': 'Cho em ví dụ khác', 'student': {'grade': 6, 'subject': 'KHTN'}, 'context': {'currentTopic': 'Lực là gì?'}})
    assert calls[0].get('extra_filter') is None  # the student's own question searches the whole book
    assert calls[1]['extra_filter']['page'] == {'$gte': 145, '$lte': 147}


def test_source_page_opens_the_file_of_an_aliased_book(client, app_mod, tmp_path, monkeypatch):
    import pymupdf
    document = pymupdf.open()
    document.new_page()
    document.save(tmp_path / 'KHTN.pdf')
    document.close()
    monkeypatch.setattr(app_mod, 'DATA_DIR', tmp_path)
    params = {key: values[0] for key, values in parse_qs(urlsplit(signed_source_url('KHTN 6.pdf', 1)).query).items()}
    assert client.get('/api/sources/page', params=params).status_code == 200


# ---------------------------------------------------------------- speech

@pytest.mark.parametrize('markdown, spoken', [
    ('Ta có $x^2 + 2x = 0$ [1].', 'Ta có x bình phương cộng 2x bằng 0.'),
    ('$$\\frac{1}{2} \\cdot \\sqrt{9}$$', '1 phần 2 nhân căn bậc hai của 9'),
    ('**Chú ý:** $a^{n} \\ne -3$ 😊', 'Chú ý: a mũ n khác âm 3'),
    ('- Bước 1\n- Bước 2\n\nXong!', 'Bước 1 Bước 2. Xong!'),
])
def test_speakable_text_reads_math_in_vietnamese(markdown, spoken):
    assert speakable_text(markdown) == spoken


def test_tts_returns_mp3(client, app_mod, monkeypatch):
    spoken = []

    async def fake_synthesize(text):
        spoken.append(text)
        return b'ID3fake'

    monkeypatch.setattr(app_mod, 'synthesize_mp3', fake_synthesize)
    response = client.post('/api/speech/tts', json={'text': 'Vậy $x^2 = 4$ [1] nhé 👍'})
    assert response.status_code == 200 and response.headers['content-type'] == 'audio/mpeg' and response.content == b'ID3fake'
    assert spoken == ['Vậy x bình phương bằng 4 nhé']


def test_tts_errors(client, app_mod, monkeypatch):
    async def broken(text):
        raise RuntimeError('offline')

    monkeypatch.setattr(app_mod, 'synthesize_mp3', broken)
    assert client.post('/api/speech/tts', json={'text': 'Chào em'}).status_code == 503
    assert client.post('/api/speech/tts', json={'text': '😊 [1]'}).status_code == 400


WAV = 'data:audio/wav;base64,' + base64.b64encode(b'RIFF' + b'\x00' * 64).decode()


def test_transcribe_sends_audio_to_gemini(client, app_mod):
    fake = FakeGemini(text='"Em chưa hiểu x^2 + 2x"\n')
    app_mod.gemini_client = fake
    response = client.post('/api/speech/transcribe', json={'audio_data': WAV, 'mime_type': 'audio/wav'})
    assert response.json() == {'text': 'Em chưa hiểu x^2 + 2x'}
    prompt, audio = fake.calls[0]['contents']
    assert 'tiếng Việt' in prompt.text and audio.inline_data.mime_type == 'audio/wav'


@pytest.mark.parametrize('payload, status', [
    ({'audio_data': WAV, 'mime_type': 'video/mp4'}, 400),
    ({'audio_data': 'không phải base64 !!!!', 'mime_type': 'audio/wav'}, 400),
    ({'audio_data': WAV, 'mime_type': 'audio/wav'}, 503),  # no Gemini configured
])
def test_transcribe_invalid_input(client, payload, status):
    assert client.post('/api/speech/transcribe', json=payload).status_code == status


def test_transcribe_quota(client, app_mod):
    app_mod.gemini_client = FakeGemini(error=RuntimeError('429 RESOURCE_EXHAUSTED'))
    assert client.post('/api/speech/transcribe', json={'audio_data': WAV}).status_code == 429


def test_speech_requires_login(anon_client):
    assert anon_client.post('/api/speech/tts', json={'text': 'a'}).status_code == 401
    assert anon_client.post('/api/speech/transcribe', json={'audio_data': WAV}).status_code == 401
