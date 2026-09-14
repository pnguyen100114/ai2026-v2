"""Input -> output tests for helpers that turn raw Gemini text into structured data."""
from __future__ import annotations

import pytest

from backend.app import _parse_image_text, _parse_suggestions


@pytest.mark.parametrize('raw, expected', [
    ('{"quick_replies":["A","B"],"understanding":"đã hiểu"}', {'quick_replies': ['A', 'B'], 'understanding': 'đã hiểu'}),
    ('```{"quick_replies":[" A ","","B","C","D"],"understanding":"mất gốc"}```', {'quick_replies': ['A', 'B', 'C'], 'understanding': 'mất gốc'}),
    ('\nrác {"quick_replies":["A"]} rác', {'quick_replies': ['A'], 'understanding': None}),
    ('{"quick_replies":"A","understanding":"giỏi"}', {'quick_replies': [], 'understanding': None}),
    ('{hỏng json', {'quick_replies': [], 'understanding': None}),
    ('', {'quick_replies': [], 'understanding': None}),
])
def test_parse_suggestions(raw, expected):
    assert _parse_suggestions(raw) == expected


@pytest.mark.parametrize('raw, expected', [
    ('{"quick_replies":[],"image_text":" Bài 1:\\n$x+1=2$ "}', 'Bài 1:\n$x+1=2$'),
    ('{"quick_replies":[]}', ''),
    ('{"image_text":5}', ''),
    ('{hỏng json', ''),
    ('{"image_text":"' + 'a' * 2000 + '"}', 'a' * 1500),
])
def test_parse_image_text(raw, expected):
    assert _parse_image_text(raw) == expected
