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
    # Công thức đủ cặp $ được giữ để chip vẽ bằng KaTeX; dấu $ lẻ thì bỏ.
    ('{"quick_replies":["Vì sao $3x^2 - 2y$ không phải ạ?","Còn $x + 1 thì sao?"]}',
     {'quick_replies': ['Vì sao $3x^2 - 2y$ không phải ạ?', 'Còn x + 1 thì sao?'], 'understanding': None}),
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


# Mô hình viết LaTeX với MỘT dấu \ trong dòng JSON. "\dots", "\cdot", "\le" làm json.loads hỏng cả dòng
# (17/10: mất đề chép từ ảnh lẫn gợi ý trả lời nhanh); "\frac", "\times" đọc được nhưng thành ký tự \f, \t.
@pytest.mark.parametrize('raw, expected', [
    (r'{"image_text":"Cho $A = \frac{1}{11} + \dots + \frac{1}{70}$"}', r'Cho $A = \frac{1}{11} + \dots + \frac{1}{70}$'),
    (r'{"image_text":"$x \le 5$\nBài 2: $2 \times 3$"}', r'$x \le 5$' + '\n' + r'Bài 2: $2 \times 3$'),
    (r'{"image_text":"Đã đúng: \frac{1}{2}"}', r'Đã đúng: \frac{1}{2}'),
])
def test_parse_image_text_keeps_single_backslash_latex(raw, expected):
    assert _parse_image_text(raw) == expected


def test_parse_suggestions_survives_latex_in_another_field():
    raw = r'{"quick_replies":["Vì sao $a \cdot b$?","Cho em ví dụ"],"understanding":"hiểu sơ","image_text":"$\dots$"}'
    assert _parse_suggestions(raw) == {'quick_replies': [r'Vì sao $a \cdot b$?', 'Cho em ví dụ'], 'understanding': 'hiểu sơ'}
