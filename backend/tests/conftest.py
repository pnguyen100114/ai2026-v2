"""Test harness: runs the FastAPI app fully offline.

Pinecone, Gemini and the database are replaced with in-memory fakes so every test
checks one input -> output pair deterministically, without network or quota.
"""
from __future__ import annotations

import json
import os
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# Must be set before backend.db is imported; load_dotenv never overrides existing variables.
os.environ['DATABASE_URL'] = ''
os.environ['AUTH_SECRET'] = 'test-secret'
os.environ['CHAT_RATE_PER_MINUTE'] = '1000'
os.environ['CHAT_RATE_PER_DAY'] = '1000'

# The real retriever connects to Pinecone at import time; swap in a stub module.
import backend.rag  # noqa: E402

_fake_retriever = types.ModuleType('backend.rag.retriever')
_fake_retriever.RAG_SCORE_THRESHOLD = 0.60
_fake_retriever.PINECONE_NAMESPACE = ''
_fake_retriever.index = None
_fake_retriever.search_knowledge = lambda *args, **kwargs: []
_fake_retriever.get_curriculum_from_rag = lambda *args, **kwargs: []
_fake_retriever.build_roadmap_from_curriculum = lambda *args, **kwargs: {}
sys.modules['backend.rag.retriever'] = _fake_retriever
backend.rag.retriever = _fake_retriever

import backend.db as db_module  # noqa: E402
import backend.app as app_module  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

TEST_USER = {'id': 'user-test-1', 'email': 'hocsinh@example.com', 'name': 'An', 'grade': 8}


class FakeGemini:
    """Mimics google.genai.Client: records the prompt, returns scripted text or raises."""

    def __init__(self, text: str = '', chunks: list[str] | None = None, error: Exception | None = None):
        self.text = text
        self.chunks = chunks or []
        self.error = error
        self.calls: list[dict[str, Any]] = []
        self.models = self

    def generate_content(self, model: str, contents: Any, config: Any = None):
        self.calls.append({'model': model, 'contents': contents, 'config': config})
        if self.error:
            raise self.error
        return SimpleNamespace(text=self.text)

    def generate_content_stream(self, model: str, contents: Any):
        self.calls.append({'model': model, 'contents': contents})
        for chunk in self.chunks:
            yield SimpleNamespace(text=chunk)
        if self.error:
            raise self.error


class Recorder:
    def __init__(self):
        self.calls: list[tuple[tuple, dict]] = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))


@pytest.fixture
def app_mod(monkeypatch):
    monkeypatch.setattr(app_module, 'gemini_client', None)
    monkeypatch.setattr(app_module, 'RAG_SCORE_THRESHOLD', 0.60)
    monkeypatch.setattr(app_module, 'CHAT_SOURCE_MIN_SCORE', 0.60)
    monkeypatch.setattr(app_module, 'GEMINI_MODEL', 'gemini-test')
    monkeypatch.setattr(app_module, 'GEMINI_FALLBACK_MODELS', [])
    monkeypatch.setattr(app_module, '_quota_exhausted_until', {})
    monkeypatch.setattr(app_module, '_lesson_pages_cache', {})
    monkeypatch.setattr(app_module, 'lesson_history', lambda *a, **k: [])
    monkeypatch.setattr(app_module, 'search_knowledge', lambda *a, **k: [])
    monkeypatch.setattr(app_module, 'save_chat_turn', Recorder())
    monkeypatch.setattr(app_module, 'save_quiz_attempt', Recorder())
    monkeypatch.setattr(app_module, 'has_quiz_attempt', lambda user_id, qid: any(args[1]['question_id'] == qid and args[0]['id'] == user_id for args, _ in app_module.save_quiz_attempt.calls))
    question_store: dict[str, dict[str, Any]] = {}

    def save_generated_question(user: dict[str, Any], question: dict[str, Any]) -> str:
        question_id = f'q-{len(question_store) + 1}'
        question_store[question_id] = {**question, 'user_id': user['id']}
        return question_id

    monkeypatch.setattr(app_module, 'save_generated_question', save_generated_question)
    monkeypatch.setattr(app_module, 'get_generated_question', lambda user_id, qid: question_store[qid] if question_store.get(qid, {}).get('user_id') == user_id else None)
    monkeypatch.setattr(app_module, 'recent_question_texts', lambda user_id, concept_id, limit=5: [q['question'] for q in question_store.values() if q['concept_id'] == concept_id])
    app_module.question_store = question_store
    roadmap_store: dict[tuple[str, int], dict[str, Any]] = {}
    monkeypatch.setattr(app_module, 'get_ai_roadmap', lambda subject, grade: roadmap_store.get((subject, grade)))
    monkeypatch.setattr(app_module, 'save_ai_roadmap', lambda subject, grade, roadmap: roadmap_store.setdefault((subject, grade), roadmap))
    app_module.roadmap_store = roadmap_store
    db_module._rate_windows.clear()
    return app_module


@pytest.fixture
def client(app_mod):
    app_mod.app.dependency_overrides[app_mod.current_user] = lambda: dict(TEST_USER)
    with TestClient(app_mod.app) as test_client:
        yield test_client
    app_mod.app.dependency_overrides.clear()


@pytest.fixture
def anon_client(app_mod):
    app_mod.app.dependency_overrides.clear()
    with TestClient(app_mod.app) as test_client:
        yield test_client


def make_match(score: float = 0.9, **overrides: Any) -> dict[str, Any]:
    match = {
        'score': score,
        'text': 'Bình phương một tổng: (a + b)^2 = a^2 + 2ab + b^2.',
        'source': 'Toan 8 tap 1.pdf',
        'page': 12,
        'pdf_page': 14,
        'chapter': 'Chương 1',
        'lesson': 'Bài 3',
        'title': 'Hằng đẳng thức đáng nhớ',
    }
    match.update(overrides)
    return match


def parse_sse(body: str) -> list[dict[str, Any]]:
    return [json.loads(line[len('data: '):]) for line in body.splitlines() if line.startswith('data: ')]
