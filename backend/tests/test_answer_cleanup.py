"""Input -> output tests for cleaning a finished chat answer."""
from __future__ import annotations

import pytest

from backend.answer_cleanup import cited_numbers, clean_answer

SQUARE = 'Bình phương của một tổng: (A + B)^2 = A^2 + 2AB + B^2 với A, B là các biểu thức tùy ý.'
SIMILE = 'So sánh là đối chiếu sự vật, sự việc này với sự vật, sự việc khác có nét tương đồng để làm tăng sức gợi hình, gợi cảm.'
TOPIC = 'Bài 3. Hằng đẳng thức đáng nhớ Hằng đẳng thức đáng nhớ'


def clean(text, message='bình phương của một tổng là gì', passages=(SQUARE,), topic=TOPIC):
    return clean_answer(text, message=message, passages=list(passages), pages=[29] * len(passages), topic=topic)


@pytest.mark.parametrize('answer, expected', [
    # Knowledge from the book keeps its citation.
    ('Ta có $(A+B)^2 = A^2 + 2AB + B^2$ [1].', 'Ta có $(A+B)^2 = A^2 + 2AB + B^2$ [1].'),
    ('Bình phương của một tổng bằng tổng các bình phương cộng hai lần tích [1].', 'Bình phương của một tổng bằng tổng các bình phương cộng hai lần tích [1].'),
    # Questions and invitations to the student are not sourced.
    ('Em thử khai triển $(2x+y)^2$ xem sao nhé [1]?', 'Em thử khai triển $(2x+y)^2$ xem sao nhé?'),
    ('Em muốn tìm hiểu hằng đẳng thức không nào? [1]', 'Em muốn tìm hiểu hằng đẳng thức không nào?'),
    # Small talk and "we are studying <lesson>" reminders are not sourced.
    ('Hai anh đều là huyền thoại bóng đá, người hâm mộ tranh cãi mãi [1].', 'Hai anh đều là huyền thoại bóng đá, người hâm mộ tranh cãi mãi.'),
    ('Hôm nay mình học Bài 3 về hằng đẳng thức đáng nhớ nha [1].', 'Hôm nay mình học Bài 3 về hằng đẳng thức đáng nhớ nha.'),
    ('Em đang học hằng đẳng thức để biến đổi biểu thức đại số nhanh hơn [1].', 'Em đang học hằng đẳng thức để biến đổi biểu thức đại số nhanh hơn.'),
    ('Mình cùng làm quen với khái niệm nhé: bình phương của một tổng bằng tổng các bình phương cộng hai lần tích [1].',
     'Mình cùng làm quen với khái niệm nhé: bình phương của một tổng bằng tổng các bình phương cộng hai lần tích [1].'),
    # A citation typed inside a formula is moved right after it.
    ('Ta có:\n$$(A+B)^2 = A^2 + 2AB + B^2 [1]$$', 'Ta có:\n$$(A+B)^2 = A^2 + 2AB + B^2$$ [1]'),
    # "Trang mấy?" answered with the cited page keeps the citation; a wrong page does not.
    ('Bài này bắt đầu ở trang 29 em nhé [1]!', 'Bài này bắt đầu ở trang 29 em nhé [1]!'),
    ('Bài này bắt đầu ở trang 40 em nhé [1]!', 'Bài này bắt đầu ở trang 40 em nhé!'),
    # In an invitation only a citation right after the quoted formula stays.
    ('Em thử áp dụng $(A+B)^2 = A^2 + 2AB + B^2$ [1] để khai triển $(x+2)^2$ xem sao nhé [1]!',
     'Em thử áp dụng $(A+B)^2 = A^2 + 2AB + B^2$ [1] để khai triển $(x+2)^2$ xem sao nhé!'),
    # A bare symbol is not a formula.
    ('Em đoán xem $A$ và $B$ là gì nhé [1]!', 'Em đoán xem $A$ và $B$ là gì nhé!'),
    # Out-of-range numbers, stray bracketed words and leaked foreign script disappear.
    ('Công thức $(A+B)^2 = A^2 + 2AB + B^2$ [5].', 'Công thức $(A+B)^2 = A^2 + 2AB + B^2$.'),
    ('Dùng $(A - B)^2 = A^2 - 2AB + B^2$ [giả định dạng].', 'Dùng $(A - B)^2 = A^2 - 2AB + B^2$.'),
    ('Axit có nguyên tử hiđ్రో liên kết với gốc axit.', 'Axit có nguyên tử hiđ liên kết với gốc axit.'),
    # Formulas and markdown links are never touched.
    ('Khoảng $[1; 2]$ và [trang web](https://example.com).', 'Khoảng $[1; 2]$ và [trang web](https://example.com).'),
])
def test_clean_answer(answer, expected):
    assert clean(answer) == expected


def test_each_citation_is_checked_against_its_own_page():
    assert clean('So sánh là đối chiếu sự vật này với sự vật khác có nét tương đồng [1][2].', passages=(SIMILE, SQUARE), topic='') == \
        'So sánh là đối chiếu sự vật này với sự vật khác có nét tương đồng [1].'
    assert clean('So sánh là đối chiếu sự vật này với sự vật khác có nét tương đồng [1, 2].', passages=(SIMILE, SQUARE), topic='') == \
        'So sánh là đối chiếu sự vật này với sự vật khác có nét tương đồng.'


@pytest.mark.parametrize('message, expected', [
    ('axit là gì', 'Câu hỏi hay đấy! Axit là chất chua.'),
    ('chào Mimo', 'Chào em, câu hỏi hay đấy! Axit là chất chua.'),
    ('chao mimo', 'Chào em, câu hỏi hay đấy! Axit là chất chua.'),
])
def test_unasked_greeting_is_removed(message, expected):
    assert clean('Chào em, câu hỏi hay đấy! Axit là chất chua.', message=message, passages=()) == expected


def test_cited_numbers_ignores_math_and_invalid_numbers():
    assert cited_numbers('A [2] B [1][2] $[3]$ C [9]', source_count=3) == [2, 1]
