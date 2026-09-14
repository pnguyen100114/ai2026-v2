"""Input -> output tests for helpers that turn raw Gemini text into structured data."""
from __future__ import annotations

import pytest

from backend.app import _parse_suggestions


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
