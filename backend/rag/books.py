"""Textbook catalog: the single source of truth for subject, grade, chapters, lessons and pages.

OCR'd PDFs give no reliable structure (the "Bài N" regex also matches exercises and the table of contents),
so chapter/lesson titles and printed start pages are copied here from each book's MỤC LỤC.

- `page` of a lesson is the PRINTED page number in its volume (what the student sees on the paper book).
- A PDF page number = printed page - page_offset (these scans have one cover page before printed page 1).
- Lessons of a volume we have no PDF for keep `page=None`: they still appear in the roadmap, without book pages.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

SERIES_KNTT = 'Kết nối tri thức với cuộc sống'

# Canonical subject values are the ones the frontend and stored chats use.
SUBJECT_ALIASES: dict[str, list[str]] = {
    'Toán': ['Toán', 'Toán học', 'Toan'],
    'Ngữ văn': ['Ngữ văn', 'Ngữ Văn', 'NV'],
    'Tiếng Anh': ['Tiếng Anh', 'Tiếng anh'],
    'KHTN': ['KHTN', 'Khoa học tự nhiên'],
    'LSDL': ['LSDL', 'Lịch sử và Địa lí', 'Lịch sử và Địa lý'],
}


def _fold(text: Any) -> str:
    value = unicodedata.normalize('NFKD', str(text or '').replace('đ', 'd').replace('Đ', 'D'))
    return re.sub(r'\s+', ' ', value.encode('ascii', 'ignore').decode().lower()).strip()


def canonical_subject(subject: Any) -> str:
    key = _fold(subject)
    for canonical, names in SUBJECT_ALIASES.items():
        if key in (_fold(name) for name in names):
            return canonical
    return str(subject or '').strip()


def subject_variants(subject: Any) -> list[str]:
    """Every spelling a subject may have been stored with in Pinecone metadata."""
    canonical = canonical_subject(subject)
    return SUBJECT_ALIASES.get(canonical, [canonical])


@dataclass(frozen=True)
class Book:
    id: str
    subject: str
    grade: int
    volume: int
    title: str
    # File in backend/data first; aliases are names the same book was ingested under earlier.
    files: tuple[str, ...]
    page_offset: int = -1
    # Last printed page present in the PDF (partial scans stop mid-book).
    last_page: int | None = None


@dataclass(frozen=True)
class Lesson:
    chapter: int
    chapter_title: str
    lesson: int
    title: str
    volume: int
    page: int | None


@dataclass
class Course:
    subject: str
    grade: int
    series: str
    # (chapter number, chapter title, volume, [(lesson number, title, printed start page or None)])
    outline: list[tuple[int, str, int, list[tuple[int, str, int | None]]]] = field(default_factory=list)
    # False where our lessons are sections numbered through the course (Ngữ văn, Tiếng Anh), not the
    # book's own "Bài N": the student then sees the book's unit, never our running number.
    numbered_lessons: bool = True

    def lessons(self) -> list[Lesson]:
        return [
            Lesson(chapter=chapter, chapter_title=chapter_title, lesson=number, title=title, volume=volume, page=page)
            for chapter, chapter_title, volume, lessons in self.outline
            for number, title, page in lessons
        ]

    def book_unit(self, lesson: Lesson) -> int | None:
        """The book's "Bài N" a lesson belongs to: its own number, or its chapter's for section-level courses."""
        if self.numbered_lessons:
            return lesson.lesson
        unit = re.match(r'Bài (\d+)\.', lesson.chapter_title)
        return int(unit.group(1)) if unit else None

    def label(self, lesson: Lesson, separator: str = ': ') -> str:
        """How a lesson is named to the student: "Bài 7: Tập hợp các số thực", "Bài 1: Bài học đường đời
        đầu tiên" (Ngữ văn, section of Bài 1), "Unit 1 – A Closer Look 1" (Tiếng Anh, no Bài at all)."""
        unit = self.book_unit(lesson)
        return f'Bài {unit}{separator}{lesson.title}' if unit is not None else lesson.title


# `page_offset` is printed page - PDF page; it was measured from the folio numbers in each scan
# and falls back to -1 (one cover page) where the folios were not extractable.
# `last_page` is only for partial scans that stop mid-book; a complete PDF leaves it None.
BOOKS: list[Book] = [
    # --- Toán ---
    Book(id='toan6-tap1', subject='Toán', grade=6, volume=1, title='Toán 6 – Tập một',
         files=('TOAN6 -TAP 1.pdf', 'TOAN -TAP 1.pdf', 'toan6-tap1.pdf'), page_offset=-1),
    Book(id='toan6-tap2', subject='Toán', grade=6, volume=2, title='Toán 6 – Tập hai',
         files=('TOAN6-TAP 2.pdf',), page_offset=-1),
    Book(id='toan7-tap1', subject='Toán', grade=7, volume=1, title='Toán 7 – Tập một',
         files=('TOAN7 - TAP 1.pdf',), page_offset=-1),
    Book(id='toan7-tap2', subject='Toán', grade=7, volume=2, title='Toán 7 – Tập hai',
         files=('TOAN7- TAP 2.pdf',), page_offset=-1),
    Book(id='toan8-tap1', subject='Toán', grade=8, volume=1, title='Toán 8 – Tập một',
         files=('TOAN8-Tap1.pdf', 'toan8-tap1.pdf'), page_offset=0),
    Book(id='toan8-tap2', subject='Toán', grade=8, volume=2, title='Toán 8 – Tập hai',
         files=('TOAN8-Tap2.pdf',), page_offset=-1),
    Book(id='toan9-tap1', subject='Toán', grade=9, volume=1, title='Toán 9 – Tập một',
         files=('TOAN9-Tap1.pdf',), page_offset=-1),
    Book(id='toan9-tap2', subject='Toán', grade=9, volume=2, title='Toán 9 – Tập hai',
         files=('Toan9-tap2.pdf', 'TOAN9-Tap2.pdf'), page_offset=-1),

    # --- Ngữ văn ---
    # "NV - TAP 1/2.pdf" carries no grade in the name; identified as grade 6 from its contents
    # ("Bài 1. Tôi và các bạn", "Bài học đường đời đầu tiên").
    Book(id='nv6-tap1', subject='Ngữ văn', grade=6, volume=1, title='Ngữ văn 6 – Tập một',
         files=('NV - TAP 1.pdf', 'NV6 - TAP 1.pdf'), page_offset=-1),
    Book(id='nv6-tap2', subject='Ngữ văn', grade=6, volume=2, title='Ngữ văn 6 – Tập hai',
         files=('NV - TAP 2.pdf', 'NV6 - TAP 2.pdf'), page_offset=-1),
    Book(id='nv7-tap1', subject='Ngữ văn', grade=7, volume=1, title='Ngữ văn 7 – Tập một',
         files=('NV7 - TAP 1.pdf',), page_offset=-1),
    Book(id='nv7-tap2', subject='Ngữ văn', grade=7, volume=2, title='Ngữ văn 7 – Tập hai',
         files=('NV7 - TAP 2.pdf',), page_offset=-1),
    Book(id='nv8-tap1', subject='Ngữ văn', grade=8, volume=1, title='Ngữ văn 8 – Tập một',
         files=('NV8-Tap1.pdf',), page_offset=-1),
    Book(id='nv8-tap2', subject='Ngữ văn', grade=8, volume=2, title='Ngữ văn 8 – Tập hai',
         files=('NV8-Tap2.pdf',), page_offset=-2),
    Book(id='nv9-tap1', subject='Ngữ văn', grade=9, volume=1, title='Ngữ văn 9 – Tập một',
         files=('NV9-Tap1.pdf',), page_offset=-1),
    Book(id='nv9-tap2', subject='Ngữ văn', grade=9, volume=2, title='Ngữ văn 9 – Tập hai',
         files=('NV9-Tap2.pdf',), page_offset=-1),

    # --- Tiếng Anh (Global Success) ---
    Book(id='ta6-tap1', subject='Tiếng Anh', grade=6, volume=1, title='Tiếng Anh 6 – Tập một',
         files=('TA6 -TAP 1.pdf',), page_offset=-1),
    Book(id='ta6-tap2', subject='Tiếng Anh', grade=6, volume=2, title='Tiếng Anh 6 – Tập hai',
         files=('TA6 -TAP 2.pdf',), page_offset=-2),
    Book(id='ta7', subject='Tiếng Anh', grade=7, volume=0, title='Tiếng Anh 7',
         files=('TA7.pdf',), page_offset=-1),
    Book(id='ta8', subject='Tiếng Anh', grade=8, volume=0, title='Tiếng Anh 8',
         files=('TA8.pdf',), page_offset=-2),
    Book(id='ta9', subject='Tiếng Anh', grade=9, volume=0, title='Tiếng Anh 9',
         files=('TA9.pdf',), page_offset=-2),

    # --- KHTN ---
    Book(id='khtn6', subject='KHTN', grade=6, volume=0, title='Khoa học tự nhiên 6',
         files=('KHTN 6.pdf', 'KHTN6.pdf', 'KHTN.pdf'), page_offset=-1, last_page=192),
    Book(id='khtn7', subject='KHTN', grade=7, volume=0, title='Khoa học tự nhiên 7',
         files=('KHTN 7.pdf',), page_offset=-1),
    Book(id='khtn8', subject='KHTN', grade=8, volume=0, title='Khoa học tự nhiên 8',
         files=('KHTN 8.pdf',), page_offset=-1),
    Book(id='khtn9', subject='KHTN', grade=9, volume=0, title='Khoa học tự nhiên 9',
         files=('KHTN 9.pdf',), page_offset=-1),

    # --- Lịch sử và Địa lí ---
    Book(id='lsdl6', subject='LSDL', grade=6, volume=0, title='Lịch sử và Địa lí 6',
         files=('LSDL 6.pdf',), page_offset=-1),
    Book(id='lsdl7', subject='LSDL', grade=7, volume=0, title='Lịch sử và Địa lí 7',
         files=('LSDL 7.pdf',), page_offset=-1),
    Book(id='lsdl8', subject='LSDL', grade=8, volume=0, title='Lịch sử và Địa lí 8',
         files=('lsdl 8.pdf', 'LSDL 8.pdf'), page_offset=-1),
    Book(id='lsdl9', subject='LSDL', grade=9, volume=0, title='Lịch sử và Địa lí 9',
         files=('LSDL 9.pdf',), page_offset=-1),
]

# The eight sections of every Global Success unit, in book order.
GS_SECTIONS = ('Getting Started', 'A Closer Look 1', 'A Closer Look 2', 'Communication',
               'Skills 1', 'Skills 2', 'Looking Back', 'Project')


def _gs_units(volume: int, first_lesson: int, units: list[tuple[int, str, Any]]) -> list[tuple[int, str, int, list[tuple[int, str, int | None]]]]:
    """Outline chapters for Global Success units: (unit, name, pages), pages being the eight section
    start pages, or only the unit's first page when the scan does not reach the unit."""
    chapters = []
    lesson = first_lesson
    for unit, name, pages in units:
        starts = pages if isinstance(pages, tuple) else (pages,) + (None,) * (len(GS_SECTIONS) - 1)
        chapters.append((unit, f'Unit {unit}: {name}', volume, [
            (lesson + index, f'Unit {unit} – {section}', page)
            for index, (section, page) in enumerate(zip(GS_SECTIONS, starts))
        ]))
        lesson += len(GS_SECTIONS)
    return chapters


COURSES: list[Course] = [
    Course(subject='Toán', grade=6, series=SERIES_KNTT, outline=[
        (1, 'Tập hợp các số tự nhiên', 1, [
            (1, 'Tập hợp', 5), (2, 'Cách ghi số tự nhiên', 9), (3, 'Thứ tự trong tập hợp các số tự nhiên', 13),
            (4, 'Phép cộng và phép trừ số tự nhiên', 15), (5, 'Phép nhân và phép chia số tự nhiên', 17),
            (6, 'Luỹ thừa với số mũ tự nhiên', 22), (7, 'Thứ tự thực hiện các phép tính', 25),
        ]),
        (2, 'Tính chia hết trong tập hợp các số tự nhiên', 1, [
            (8, 'Quan hệ chia hết và tính chất', 29), (9, 'Dấu hiệu chia hết', 34), (10, 'Số nguyên tố', 38),
            (11, 'Ước chung. Ước chung lớn nhất', 44), (12, 'Bội chung. Bội chung nhỏ nhất', 49),
        ]),
        (3, 'Số nguyên', 1, [
            (13, 'Tập hợp các số nguyên', 57), (14, 'Phép cộng và phép trừ số nguyên', 62), (15, 'Quy tắc dấu ngoặc', 67),
            (16, 'Phép nhân số nguyên', 70), (17, 'Phép chia hết. Ước và bội của một số nguyên', 73),
        ]),
        (4, 'Một số hình phẳng trong thực tiễn', 1, [
            (18, 'Hình tam giác đều. Hình vuông. Hình lục giác đều', 77),
            (19, 'Hình chữ nhật. Hình thoi. Hình bình hành. Hình thang cân', 83),
            (20, 'Chu vi và diện tích của một số tứ giác đã học', 90),
        ]),
        (5, 'Tính đối xứng của hình phẳng trong tự nhiên', 1, [
            (21, 'Hình có trục đối xứng', 98), (22, 'Hình có tâm đối xứng', 103),
        ]),
        (6, 'Phân số', 2, [
            (23, 'Mở rộng khái niệm phân số. Phân số bằng nhau', 4), (24, 'So sánh phân số. Hỗn số dương', 9),
            (25, 'Phép cộng và phép trừ phân số', 15), (26, 'Phép nhân và phép chia phân số', 19),
            (27, 'Hai bài toán về phân số', 22),
        ]),
        (7, 'Số thập phân', 2, [
            (28, 'Số thập phân', 28), (29, 'Tính toán với số thập phân', 31), (30, 'Làm tròn và ước lượng', 35),
            (31, 'Một số bài toán về tỉ số và tỉ số phần trăm', 38),
        ]),
        (8, 'Những hình hình học cơ bản', 2, [
            (32, 'Điểm và đường thẳng', 43), (33, 'Điểm nằm giữa hai điểm. Tia', 48),
            (34, 'Đoạn thẳng. Độ dài đoạn thẳng', 51), (35, 'Trung điểm của đoạn thẳng', 55),
            (36, 'Góc', 58), (37, 'Số đo góc', 61),
        ]),
        (9, 'Dữ liệu và xác suất thực nghiệm', 2, [
            (38, 'Dữ liệu và thu thập dữ liệu', 68), (39, 'Bảng thống kê và biểu đồ tranh', 73),
            (40, 'Biểu đồ cột', 77), (41, 'Biểu đồ cột kép', 82),
            (42, 'Kết quả có thể và sự kiện trong trò chơi, thí nghiệm', 89), (43, 'Xác suất thực nghiệm', 94),
        ]),
    ]),
    Course(subject='Toán', grade=7, series=SERIES_KNTT, outline=[
        (1, 'Số hữu tỉ', 1, [
            (1, 'Tập hợp các số hữu tỉ', 5), (2, 'Cộng, trừ, nhân, chia số hữu tỉ', 10),
            (3, 'Luỹ thừa với số mũ tự nhiên của một số hữu tỉ', 16),
            (4, 'Thứ tự thực hiện các phép tính. Quy tắc chuyển vế', 20),
        ]),
        (2, 'Số thực', 1, [
            (5, 'Làm quen với số thập phân vô hạn tuần hoàn', 26), (6, 'Số vô tỉ. Căn bậc hai số học', 29),
            (7, 'Tập hợp các số thực', 33),
        ]),
        (3, 'Góc và đường thẳng song song', 1, [
            (8, 'Góc ở vị trí đặc biệt. Tia phân giác của một góc', 40),
            (9, 'Hai đường thẳng song song và dấu hiệu nhận biết', 46),
            (10, 'Tiên đề Euclid. Tính chất của hai đường thẳng song song', 51),
            (11, 'Định lí và chứng minh định lí', 55),
        ]),
        (4, 'Tam giác bằng nhau', 1, [
            (12, 'Tổng các góc trong một tam giác', 60),
            (13, 'Hai tam giác bằng nhau. Trường hợp bằng nhau thứ nhất của tam giác', 63),
            (14, 'Trường hợp bằng nhau thứ hai và thứ ba của tam giác', 70),
            (15, 'Các trường hợp bằng nhau của tam giác vuông', 75),
            (16, 'Tam giác cân. Đường trung trực của đoạn thẳng', 80),
        ]),
        (5, 'Thu thập và biểu diễn dữ liệu', 1, [
            (17, 'Thu thập và phân loại dữ liệu', 88), (18, 'Biểu đồ hình quạt tròn', 93),
            (19, 'Biểu đồ đoạn thẳng', 100),
        ]),
        (6, 'Tỉ lệ thức và đại lượng tỉ lệ', 2, [
            (20, 'Tỉ lệ thức', 4), (21, 'Tính chất của dãy tỉ số bằng nhau', 8),
            (22, 'Đại lượng tỉ lệ thuận', 11), (23, 'Đại lượng tỉ lệ nghịch', 15),
        ]),
        (7, 'Biểu thức đại số và đa thức một biến', 2, [
            (24, 'Biểu thức đại số', 22), (25, 'Đa thức một biến', 25),
            (26, 'Phép cộng và phép trừ đa thức một biến', 31), (27, 'Phép nhân đa thức một biến', 36),
            (28, 'Phép chia đa thức một biến', 39),
        ]),
        (8, 'Làm quen với biến cố và xác suất của biến cố', 2, [
            (29, 'Làm quen với biến cố', 47), (30, 'Làm quen với xác suất của biến cố', 51),
        ]),
        (9, 'Quan hệ giữa các yếu tố trong một tam giác', 2, [
            (31, 'Quan hệ giữa góc và cạnh đối diện trong một tam giác', 59),
            (32, 'Quan hệ giữa đường vuông góc và đường xiên', 63),
            (33, 'Quan hệ giữa ba cạnh của một tam giác', 66),
            (34, 'Sự đồng quy của ba đường trung tuyến, ba đường phân giác trong một tam giác', 72),
            (35, 'Sự đồng quy của ba đường trung trực, ba đường cao trong một tam giác', 77),
        ]),
        (10, 'Một số hình khối trong thực tiễn', 2, [
            (36, 'Hình hộp chữ nhật và hình lập phương', 85),
            (37, 'Hình lăng trụ đứng tam giác và hình lăng trụ đứng tứ giác', 94),
        ]),
    ]),
    Course(subject='Toán', grade=8, series=SERIES_KNTT, outline=[
        (1, 'Đa thức', 1, [
            (1, 'Đơn thức', 5), (2, 'Đa thức', 11), (3, 'Phép cộng và phép trừ đa thức', 15),
            (4, 'Phép nhân đa thức', 19), (5, 'Phép chia đa thức cho đơn thức', 22),
        ]),
        (2, 'Hằng đẳng thức đáng nhớ và ứng dụng', 1, [
            (6, 'Hiệu hai bình phương. Bình phương của một tổng hay một hiệu', 29),
            (7, 'Lập phương của một tổng hay một hiệu', 34),
            (8, 'Tổng và hiệu hai lập phương', 37), (9, 'Phân tích đa thức thành nhân tử', 42),
        ]),
        (3, 'Tứ giác', 1, [
            (10, 'Tứ giác', 48), (11, 'Hình thang cân', 52), (12, 'Hình bình hành', 57),
            (13, 'Hình chữ nhật', 64), (14, 'Hình thoi và hình vuông', 67),
        ]),
        (4, 'Định lí Thalès', 1, [
            (15, 'Định lí Thalès trong tam giác', 76), (16, 'Đường trung bình của tam giác', 81),
            (17, 'Tính chất đường phân giác của tam giác', 84),
        ]),
        (5, 'Dữ liệu và biểu đồ', 1, [
            (18, 'Thu thập và phân loại dữ liệu', 90), (19, 'Biểu diễn dữ liệu bằng bảng, biểu đồ', 93),
            (20, 'Phân tích số liệu thống kê dựa vào biểu đồ', 99),
        ]),
        (6, 'Phân thức đại số', 2, [
            (21, 'Phân thức đại số', 4), (22, 'Tính chất cơ bản của phân thức đại số', 8),
            (23, 'Phép cộng và phép trừ phân thức đại số', 15), (24, 'Phép nhân và phép chia phân thức đại số', 20),
        ]),
        (7, 'Phương trình bậc nhất và hàm số bậc nhất', 2, [
            (25, 'Phương trình bậc nhất một ẩn', 27), (26, 'Giải bài toán bằng cách lập phương trình', 33),
            (27, 'Khái niệm hàm số và đồ thị của hàm số', 40), (28, 'Hàm số bậc nhất và đồ thị của hàm số bậc nhất', 47),
            (29, 'Hệ số góc của đường thẳng', 51),
        ]),
        (8, 'Mở đầu về tính xác suất của biến cố', 2, [
            (30, 'Kết quả có thể và kết quả thuận lợi', 59), (31, 'Cách tính xác suất của biến cố bằng tỉ số', 63),
            (32, 'Mối liên hệ giữa xác suất thực nghiệm với xác suất và ứng dụng', 67),
        ]),
        (9, 'Tam giác đồng dạng', 2, [
            (33, 'Hai tam giác đồng dạng', 78), (34, 'Ba trường hợp đồng dạng của hai tam giác', 83),
            (35, 'Định lí Pythagore và ứng dụng', 93), (36, 'Các trường hợp đồng dạng của hai tam giác vuông', 98),
            (37, 'Hình đồng dạng', 104),
        ]),
        (10, 'Một số hình khối trong thực tiễn', 2, [
            (38, 'Hình chóp tam giác đều', 112), (39, 'Hình chóp tứ giác đều', 117),
        ]),
    ]),
    Course(subject='Toán', grade=9, series=SERIES_KNTT, outline=[
        (1, 'Phương trình và hệ hai phương trình bậc nhất hai ẩn', 1, [
            (1, 'Khái niệm phương trình và hệ hai phương trình bậc nhất hai ẩn', 5),
            (2, 'Giải hệ hai phương trình bậc nhất hai ẩn', 11),
            (3, 'Giải bài toán bằng cách lập hệ phương trình', 21),
        ]),
        (2, 'Phương trình và bất phương trình bậc nhất một ẩn', 1, [
            (4, 'Phương trình quy về phương trình bậc nhất một ẩn', 26),
            (5, 'Bất đẳng thức và tính chất', 31),
            (6, 'Bất phương trình bậc nhất một ẩn', 38),
        ]),
        (3, 'Căn bậc hai và căn bậc ba', 1, [
            (7, 'Căn bậc hai và căn thức bậc hai', 44),
            (8, 'Khai căn bậc hai với phép nhân và phép chia', 49),
            (9, 'Biến đổi đơn giản và rút gọn biểu thức chứa căn thức bậc hai', 54),
            (10, 'Căn bậc ba và căn thức bậc ba', 60),
        ]),
        (4, 'Hệ thức lượng trong tam giác vuông', 1, [
            (11, 'Tỉ số lượng giác của góc nhọn', 66),
            (12, 'Một số hệ thức giữa cạnh, góc trong tam giác vuông và ứng dụng', 74),
        ]),
        (5, 'Đường tròn', 1, [
            (13, 'Mở đầu về đường tròn', 83), (14, 'Cung và dây của một đường tròn', 87),
            (15, 'Độ dài của cung tròn. Diện tích hình quạt tròn và hình vành khuyên', 91),
            (16, 'Vị trí tương đối của đường thẳng và đường tròn', 99),
            (17, 'Vị trí tương đối của hai đường tròn', 104),
        ]),
        (6, 'Hàm số y = ax² (a ≠ 0). Phương trình bậc hai một ẩn', 2, [
            (18, 'Hàm số y = ax² (a ≠ 0)', 4), (19, 'Phương trình bậc hai một ẩn', 10),
            (20, 'Định lí Viète và ứng dụng', 21), (21, 'Giải bài toán bằng cách lập phương trình', 25),
        ]),
        (7, 'Tần số và tần số tương đối', 2, [
            (22, 'Bảng tần số và biểu đồ tần số', 32),
            (23, 'Bảng tần số tương đối và biểu đồ tần số tương đối', 38),
            (24, 'Bảng tần số, tần số tương đối ghép nhóm và biểu đồ', 46),
        ]),
        (8, 'Xác suất của biến cố trong một số mô hình xác suất đơn giản', 2, [
            (25, 'Phép thử ngẫu nhiên và không gian mẫu', 56),
            (26, 'Xác suất của biến cố liên quan tới phép thử', 60),
        ]),
        (9, 'Đường tròn ngoại tiếp và đường tròn nội tiếp', 2, [
            (27, 'Góc nội tiếp', 67), (28, 'Đường tròn ngoại tiếp và đường tròn nội tiếp của một tam giác', 72),
            (29, 'Tứ giác nội tiếp', 80), (30, 'Đa giác đều', 84),
        ]),
        (10, 'Một số hình khối trong thực tiễn', 2, [
            (31, 'Hình trụ và hình nón', 93), (32, 'Hình cầu', 101),
        ]),
    ]),
    Course(subject='KHTN', grade=6, series=SERIES_KNTT, outline=[
        (1, 'Mở đầu về Khoa học tự nhiên', 0, [
            (1, 'Giới thiệu về Khoa học tự nhiên', 7), (2, 'An toàn trong phòng thực hành', 11), (3, 'Sử dụng kính lúp', 13),
            (4, 'Sử dụng kính hiển vi quang học', 15), (5, 'Đo chiều dài', 17), (6, 'Đo khối lượng', 20),
            (7, 'Đo thời gian', 22), (8, 'Đo nhiệt độ', 24),
        ]),
        (2, 'Chất quanh ta', 0, [
            (9, 'Sự đa dạng của chất', 28), (10, 'Các thể của chất và sự chuyển thể', 30), (11, 'Oxygen. Không khí', 36),
        ]),
        (3, 'Một số vật liệu, nguyên liệu, nhiên liệu, lương thực – thực phẩm thông dụng', 0, [
            (12, 'Một số vật liệu', 42), (13, 'Một số nguyên liệu', 46), (14, 'Một số nhiên liệu', 50),
            (15, 'Một số lương thực, thực phẩm', 52),
        ]),
        (4, 'Hỗn hợp. Tách chất ra khỏi hỗn hợp', 0, [
            (16, 'Hỗn hợp các chất', 56), (17, 'Tách chất khỏi hỗn hợp', 60),
        ]),
        (5, 'Tế bào', 0, [
            (18, 'Tế bào – Đơn vị cơ bản của sự sống', 64), (19, 'Cấu tạo và chức năng các thành phần của tế bào', 67),
            (20, 'Sự lớn lên và sinh sản của tế bào', 70), (21, 'Thực hành: Quan sát và phân biệt một số loại tế bào', 73),
        ]),
        (6, 'Từ tế bào đến cơ thể', 0, [
            (22, 'Cơ thể sinh vật', 75), (23, 'Tổ chức cơ thể đa bào', 79),
            (24, 'Thực hành: Quan sát và mô tả cơ thể đơn bào, cơ thể đa bào', 83),
        ]),
        (7, 'Đa dạng thế giới sống', 0, [
            (25, 'Hệ thống phân loại sinh vật', 86), (26, 'Khoá lưỡng phân', 90), (27, 'Vi khuẩn', 92),
            (28, 'Thực hành: Làm sữa chua và quan sát vi khuẩn', 96), (29, 'Virus', 98), (30, 'Nguyên sinh vật', 102),
            (31, 'Thực hành: Quan sát nguyên sinh vật', 106), (32, 'Nấm', 108), (33, 'Thực hành: Quan sát các loại nấm', 112),
            (34, 'Thực vật', 115), (35, 'Thực hành: Quan sát và phân biệt một số nhóm thực vật', 123), (36, 'Động vật', 125),
            (37, 'Thực hành: Quan sát và nhận biết một số nhóm động vật ngoài thiên nhiên', 133),
            (38, 'Đa dạng sinh học', 135), (39, 'Tìm hiểu sinh vật ngoài thiên nhiên', 139),
        ]),
        (8, 'Lực trong đời sống', 0, [
            (40, 'Lực là gì?', 144), (41, 'Biểu diễn lực', 147), (42, 'Biến dạng của lò xo', 151),
            (43, 'Trọng lượng, lực hấp dẫn', 154), (44, 'Lực ma sát', 157), (45, 'Lực cản của nước', 160),
        ]),
        (9, 'Năng lượng', 0, [
            (46, 'Năng lượng và sự truyền năng lượng', 162), (47, 'Một số dạng năng lượng', 165),
            (48, 'Sự chuyển hoá năng lượng', 168), (49, 'Năng lượng hao phí', 171), (50, 'Năng lượng tái tạo', 173),
            (51, 'Tiết kiệm năng lượng', 176),
        ]),
        (10, 'Trái Đất và bầu trời', 0, [
            (52, 'Chuyển động nhìn thấy của Mặt Trời. Thiên thể', 179), (53, 'Mặt Trăng', 183), (54, 'Hệ Mặt Trời', 187),
            (55, 'Ngân Hà', 190),
        ]),
    ]),
    Course(subject='KHTN', grade=7, series=SERIES_KNTT, outline=[
        (1, 'Mở đầu', 0, [
            (1, 'Phương pháp và kĩ năng học tập môn Khoa học tự nhiên', 6),
        ]),
        (2, 'Chương I. Nguyên tử. Sơ lược về bảng tuần hoàn các nguyên tố hoá học', 0, [
            (2, 'Nguyên tử', 14), (3, 'Nguyên tố hoá học', 19),
            (4, 'Sơ lược về bảng tuần hoàn các nguyên tố hoá học', 23),
        ]),
        (3, 'Chương II. Phân tử. Liên kết hoá học', 0, [
            (5, 'Phân tử – Đơn chất – Hợp chất', 32), (6, 'Giới thiệu về liên kết hoá học', 36),
            (7, 'Hoá trị và công thức hoá học', 40),
        ]),
        (4, 'Chương III. Tốc độ', 0, [
            (8, 'Tốc độ chuyển động', 45), (9, 'Đo tốc độ', 49), (10, 'Đồ thị quãng đường – thời gian', 53),
            (11, 'Thảo luận về ảnh hưởng của tốc độ trong an toàn giao thông', 56),
        ]),
        (5, 'Chương IV. Âm thanh', 0, [
            (12, 'Sóng âm', 60), (13, 'Độ to và độ cao của âm', 64), (14, 'Phản xạ âm, chống ô nhiễm tiếng ồn', 68),
        ]),
        (6, 'Chương V. Ánh sáng', 0, [
            (15, 'Năng lượng ánh sáng. Tia sáng, vùng tối', 72), (16, 'Sự phản xạ ánh sáng', 78),
            (17, 'Ảnh của vật qua gương phẳng', 82),
        ]),
        (7, 'Chương VI. Từ', 0, [
            (18, 'Nam châm', 86), (19, 'Từ trường', 90), (20, 'Chế tạo nam châm điện đơn giản', 96),
        ]),
        (8, 'Chương VII. Trao đổi chất và chuyển hoá năng lượng ở sinh vật', 0, [
            (21, 'Khái quát về trao đổi chất và chuyển hoá năng lượng', 99), (22, 'Quang hợp ở thực vật', 101),
            (23, 'Một số yếu tố ảnh hưởng đến quang hợp', 104), (24, 'Thực hành: Chứng minh quang hợp ở cây xanh', 108),
            (25, 'Hô hấp tế bào', 111), (26, 'Một số yếu tố ảnh hưởng đến hô hấp tế bào', 113),
            (27, 'Thực hành: Hô hấp ở thực vật', 116), (28, 'Trao đổi khí ở sinh vật', 118),
            (29, 'Vai trò của nước và chất dinh dưỡng đối với sinh vật', 122),
            (30, 'Trao đổi nước và chất dinh dưỡng ở thực vật', 127),
            (31, 'Trao đổi nước và chất dinh dưỡng ở động vật', 131),
            (32, 'Thực hành: Chứng minh thân vận chuyển nước và lá thoát hơi nước', 136),
        ]),
        (9, 'Chương VIII. Cảm ứng ở sinh vật', 0, [
            (33, 'Cảm ứng ở sinh vật và tập tính ở động vật', 138),
            (34, 'Vận dụng hiện tượng cảm ứng ở sinh vật vào thực tiễn', 141),
            (35, 'Thực hành: Cảm ứng ở sinh vật', 145),
        ]),
        (10, 'Chương IX. Sinh trưởng và phát triển ở sinh vật', 0, [
            (36, 'Khái quát về sinh trưởng và phát triển ở sinh vật', 148),
            (37, 'Ứng dụng sinh trưởng và phát triển ở sinh vật vào thực tiễn', 151),
            (38, 'Thực hành: Quan sát, mô tả sự sinh trưởng và phát triển ở một số sinh vật', 156),
        ]),
        (11, 'Chương X. Sinh sản ở sinh vật', 0, [
            (39, 'Sinh sản vô tính ở sinh vật', 158), (40, 'Sinh sản hữu tính ở sinh vật', 164),
            (41, 'Một số yếu tố ảnh hưởng và điều hoà, điều khiển sinh sản ở sinh vật', 169),
            (42, 'Cơ thể sinh vật là một thể thống nhất', 173),
        ]),
    ]),
    Course(subject='KHTN', grade=8, series=SERIES_KNTT, outline=[
        (1, 'Mở đầu', 0, [
            (1, 'Sử dụng một số hoá chất, thiết bị cơ bản trong phòng thí nghiệm', 6),
        ]),
        (2, 'Chương I. Phản ứng hoá học', 0, [
            (2, 'Phản ứng hoá học', 11), (3, 'Mol và tỉ khối chất khí', 16), (4, 'Dung dịch và nồng độ', 20),
            (5, 'Định luật bảo toàn khối lượng và phương trình hoá học', 24),
            (6, 'Tính theo phương trình hoá học', 28), (7, 'Tốc độ phản ứng và chất xúc tác', 31),
        ]),
        (3, 'Chương II. Một số hợp chất thông dụng', 0, [
            (8, 'Acid', 35), (9, 'Base. Thang pH', 39), (10, 'Oxide', 44), (11, 'Muối', 48),
            (12, 'Phân bón hoá học', 53),
        ]),
        (4, 'Chương III. Khối lượng riêng và áp suất', 0, [
            (13, 'Khối lượng riêng', 56), (14, 'Thực hành xác định khối lượng riêng', 59),
            (15, 'Áp suất trên một bề mặt', 64), (16, 'Áp suất chất lỏng. Áp suất khí quyển', 67),
            (17, 'Lực đẩy Archimedes', 73),
        ]),
        (5, 'Chương IV. Tác dụng làm quay của lực', 0, [
            (18, 'Tác dụng làm quay của lực. Moment lực', 76), (19, 'Đòn bẩy và ứng dụng', 79),
        ]),
        (6, 'Chương V. Điện', 0, [
            (20, 'Hiện tượng nhiễm điện do cọ xát', 84), (21, 'Dòng điện, nguồn điện', 88),
            (22, 'Mạch điện đơn giản', 91), (23, 'Tác dụng của dòng điện', 95),
            (24, 'Cường độ dòng điện và hiệu điện thế', 99),
            (25, 'Thực hành đo cường độ dòng điện và hiệu điện thế', 102),
        ]),
        (7, 'Chương VI. Nhiệt', 0, [
            (26, 'Năng lượng nhiệt và nội năng', 105), (27, 'Thực hành đo năng lượng nhiệt bằng joulemeter', 109),
            (28, 'Sự truyền nhiệt', 112), (29, 'Sự nở vì nhiệt', 118),
        ]),
        (8, 'Chương VII. Sinh học cơ thể người', 0, [
            (30, 'Khái quát về cơ thể người', 123), (31, 'Hệ vận động ở người', 125),
            (32, 'Dinh dưỡng và tiêu hoá ở người', 128), (33, 'Máu và hệ tuần hoàn của cơ thể người', 135),
            (34, 'Hệ hô hấp ở người', 142), (35, 'Hệ bài tiết ở người', 146),
            (36, 'Điều hoà môi trường trong của cơ thể người', 150),
            (37, 'Hệ thần kinh và các giác quan ở người', 152), (38, 'Hệ nội tiết ở người', 157),
            (39, 'Da và điều hoà thân nhiệt ở người', 160), (40, 'Sinh sản ở người', 165),
        ]),
        (9, 'Chương VIII. Sinh vật và môi trường', 0, [
            (41, 'Môi trường và các nhân tố sinh thái', 170), (42, 'Quần thể sinh vật', 174),
            (43, 'Quần xã sinh vật', 177), (44, 'Hệ sinh thái', 180), (45, 'Sinh quyển', 185),
            (46, 'Cân bằng tự nhiên', 188), (47, 'Bảo vệ môi trường', 191),
        ]),
    ]),
    Course(subject='KHTN', grade=9, series=SERIES_KNTT, outline=[
        (1, 'Mở đầu', 0, [
            (1, 'Nhận biết một số dụng cụ, hoá chất. Thuyết trình một vấn đề khoa học', 6),
        ]),
        (2, 'Chương I. Năng lượng cơ học', 0, [
            (2, 'Động năng. Thế năng', 15), (3, 'Cơ năng', 18), (4, 'Công và công suất', 21),
        ]),
        (3, 'Chương II. Ánh sáng', 0, [
            (5, 'Khúc xạ ánh sáng', 25), (6, 'Phản xạ toàn phần', 30), (7, 'Lăng kính', 34),
            (8, 'Thấu kính', 40), (9, 'Thực hành đo tiêu cự của thấu kính hội tụ', 47),
            (10, 'Kính lúp. Bài tập thấu kính', 50),
        ]),
        (4, 'Chương III. Điện', 0, [
            (11, 'Điện trở. Định luật Ohm', 53), (12, 'Đoạn mạch nối tiếp, song song', 60),
            (13, 'Năng lượng của dòng điện và công suất điện', 64),
        ]),
        (5, 'Chương IV. Điện từ', 0, [
            (14, 'Cảm ứng điện từ. Nguyên tắc tạo ra dòng điện xoay chiều', 67),
            (15, 'Tác dụng của dòng điện xoay chiều', 72),
        ]),
        (6, 'Chương V. Năng lượng với cuộc sống', 0, [
            (16, 'Vòng năng lượng trên Trái Đất. Năng lượng hoá thạch', 75),
            (17, 'Một số dạng năng lượng tái tạo', 80),
        ]),
        (7, 'Chương VI. Kim loại. Sự khác nhau cơ bản giữa phi kim và kim loại', 0, [
            (18, 'Tính chất chung của kim loại', 87), (19, 'Dãy hoạt động hoá học', 92),
            (20, 'Tách kim loại và việc sử dụng hợp kim', 95),
            (21, 'Sự khác nhau cơ bản giữa phi kim và kim loại', 100),
        ]),
        (8, 'Chương VII. Giới thiệu về chất hữu cơ. Hydrocarbon và nguồn nhiên liệu', 0, [
            (22, 'Giới thiệu về hợp chất hữu cơ', 103), (23, 'Alkane', 107), (24, 'Alkene', 111),
            (25, 'Nguồn nhiên liệu', 114),
        ]),
        (9, 'Chương VIII. Ethylic alcohol và acetic acid', 0, [
            (26, 'Ethylic alcohol', 118), (27, 'Acetic acid', 123),
        ]),
        (10, 'Chương IX. Lipid. Carbohydrate. Protein. Polymer', 0, [
            (28, 'Lipid', 128), (29, 'Carbohydrate. Glucose và saccharose', 131),
            (30, 'Tinh bột và cellulose', 135), (31, 'Protein', 138), (32, 'Polymer', 141),
        ]),
        (11, 'Chương X. Khai thác tài nguyên từ vỏ Trái Đất', 0, [
            (33, 'Sơ lược về hoá học vỏ Trái Đất và khai thác tài nguyên từ vỏ Trái Đất', 146),
            (34, 'Khai thác đá vôi. Công nghiệp silicate', 149),
            (35, 'Khai thác nhiên liệu hoá thạch. Nguồn carbon. Chu trình carbon và sự ấm lên toàn cầu', 153),
        ]),
        (12, 'Chương XI. Di truyền học Mendel. Cơ sở phân tử của hiện tượng di truyền', 0, [
            # The MỤC LỤC prints 169 for Bài 39; its heading is on printed page 170.
            (36, 'Khái quát về di truyền học', 159), (37, 'Các quy luật di truyền của Mendel', 162),
            (38, 'Nucleic acid và gene', 166), (39, 'Tái bản DNA và phiên mã tạo RNA', 170),
            (40, 'Dịch mã và mối quan hệ từ gene đến tính trạng', 173), (41, 'Đột biến gene', 178),
        ]),
        (13, 'Chương XII. Di truyền nhiễm sắc thể', 0, [
            (42, 'Nhiễm sắc thể và bộ nhiễm sắc thể', 181), (43, 'Nguyên phân và giảm phân', 186),
            (44, 'Nhiễm sắc thể giới tính và cơ chế xác định giới tính', 191), (45, 'Di truyền liên kết', 194),
            (46, 'Đột biến nhiễm sắc thể', 197),
        ]),
        (14, 'Chương XIII. Di truyền học với con người và đời sống', 0, [
            (47, 'Di truyền học với con người', 201), (48, 'Ứng dụng công nghệ di truyền vào đời sống', 207),
        ]),
        (15, 'Chương XIV. Tiến hoá', 0, [
            (49, 'Khái niệm tiến hoá và các hình thức chọn lọc', 211), (50, 'Cơ chế tiến hoá', 214),
            (51, 'Sự phát sinh và phát triển sự sống trên Trái Đất', 219),
        ]),
    ]),
    # Global Success has no "Bài": every unit section (Getting Started, A Closer Look 1...) is one
    # lesson, numbered through the course, and its title carries the unit because every unit has an
    # "A Closer Look 1". A unit past the end of a partial scan would keep only its first page.
    Course(subject='Tiếng Anh', grade=6, series='Global Success', numbered_lessons=False, outline=[
        *_gs_units(1, 1, [
            (1, 'My New School', (6, 8, 9, 11, 12, 13, 14, 15)),
            (2, 'My House', (16, 17, 18, 20, 22, 23, 24, 25)),
            (3, 'My Friends', (26, 28, 29, 31, 32, 33, 34, 35)),
        ]),
        (101, 'Review 1', 1, [(25, 'Review 1', 36)]),
        *_gs_units(1, 26, [
            (4, 'My Neighbourhood', (38, 40, 41, 43, 44, 45, 46, 47)),
            (5, 'Natural Wonders of Viet Nam', (48, 50, 51, 53, 54, 55, 56, 57)),
            (6, 'Our Tet Holiday', (58, 60, 61, 63, 64, 65, 66, 67)),
        ]),
        (102, 'Review 2', 1, [(50, 'Review 2', 68)]),
        # Tập hai restarts its page numbers: Unit 7 starts on page 6.
        *_gs_units(2, 51, [
            (7, 'Television', (6, 8, 9, 11, 12, 13, 14, 15)),
            (8, 'Sports and Games', (16, 18, 19, 21, 22, 23, 24, 25)),
            (9, 'Cities of the World', (26, 28, 29, 30, 32, 33, 34, 35)),
        ]),
        (103, 'Review 3', 2, [(75, 'Review 3', 36)]),
        *_gs_units(2, 76, [
            (10, 'Our Houses in the Future', (38, 40, 41, 43, 44, 45, 46, 47)),
            (11, 'Our Greener World', (48, 50, 51, 53, 54, 55, 56, 57)),
            (12, 'Robots', (58, 60, 61, 63, 64, 65, 66, 67)),
        ]),
        (104, 'Review 4', 2, [(100, 'Review 4', 68)]),
    ]),
    Course(subject='Tiếng Anh', grade=7, series='Global Success', numbered_lessons=False, outline=[
        *_gs_units(0, 1, [
            (1, 'Hobbies', (8, 10, 11, 13, 14, 15, 16, 17)),
            (2, 'Healthy Living', (18, 20, 21, 22, 23, 24, 26, 27)),
            (3, 'Community Service', (28, 30, 31, 32, 34, 35, 36, 37)),
        ]),
        (101, 'Review 1', 0, [(25, 'Review 1', 38)]),
        *_gs_units(0, 26, [
            (4, 'Music and Arts', (40, 42, 43, 45, 46, 47, 48, 49)),
            (5, 'Food and Drink', (50, 52, 53, 55, 56, 57, 58, 59)),
            (6, 'A Visit to a School', (60, 62, 63, 64, 66, 67, 68, 69)),
        ]),
        (102, 'Review 2', 0, [(50, 'Review 2', 70)]),
        *_gs_units(0, 51, [
            (7, 'Traffic', (72, 74, 75, 76, 78, 79, 80, 81)),
            (8, 'Films', (82, 84, 85, 86, 87, 89, 90, 91)),
            (9, 'Festivals Around the World', (92, 94, 95, 96, 97, 99, 100, 101)),
        ]),
        (103, 'Review 3', 0, [(75, 'Review 3', 102)]),
        *_gs_units(0, 76, [
            (10, 'Energy Sources', (104, 106, 107, 109, 110, 111, 112, 113)),
            (11, 'Travelling in the Future', (114, 116, 117, 119, 120, 121, 122, 123)),
            (12, 'English-Speaking Countries', (124, 126, 127, 128, 130, 131, 132, 133)),
        ]),
        (104, 'Review 4', 0, [(100, 'Review 4', 134)]),
    ]),
    Course(subject='Tiếng Anh', grade=8, series='Global Success', numbered_lessons=False, outline=[
        *_gs_units(0, 1, [
            (1, 'Leisure Time', (8, 10, 11, 12, 14, 15, 16, 17)),
            (2, 'Life in the Countryside', (18, 20, 21, 22, 24, 25, 26, 27)),
            (3, 'Teenagers', (28, 30, 31, 32, 33, 35, 36, 37)),
        ]),
        (101, 'Review 1', 0, [(25, 'Review 1', 38)]),
        *_gs_units(0, 26, [
            (4, 'Ethnic Groups of Viet Nam', (40, 42, 43, 44, 45, 47, 48, 49)),
            (5, 'Our Customs and Traditions', (50, 52, 53, 54, 55, 57, 58, 59)),
            (6, 'Lifestyles', (60, 62, 63, 64, 65, 67, 68, 69)),
        ]),
        (102, 'Review 2', 0, [(50, 'Review 2', 70)]),
        *_gs_units(0, 51, [
            (7, 'Environmental Protection', (72, 74, 75, 76, 77, 79, 80, 81)),
            (8, 'Shopping', (82, 84, 85, 86, 87, 89, 90, 91)),
            (9, 'Natural Disasters', (92, 94, 95, 96, 97, 99, 100, 101)),
        ]),
        (103, 'Review 3', 0, [(75, 'Review 3', 102)]),
        *_gs_units(0, 76, [
            (10, 'Communication in the Future', (104, 106, 107, 108, 109, 110, 112, 113)),
            (11, 'Science and Technology', (114, 116, 117, 119, 120, 121, 122, 123)),
            (12, 'Life on Other Planets', (124, 126, 127, 129, 130, 131, 132, 133)),
        ]),
        (104, 'Review 4', 0, [(100, 'Review 4', 134)]),
    ]),
    Course(subject='Tiếng Anh', grade=9, series='Global Success', numbered_lessons=False, outline=[
        *_gs_units(0, 1, [
            (1, 'Local Community', (8, 10, 11, 12, 13, 15, 16, 17)),
            (2, 'City Life', (18, 20, 21, 22, 23, 25, 26, 27)),
            (3, 'Healthy Living for Teens', (28, 30, 31, 32, 33, 34, 36, 37)),
        ]),
        (101, 'Review 1', 0, [(25, 'Review 1', 38)]),
        *_gs_units(0, 26, [
            (4, 'Remembering the Past', (40, 42, 43, 44, 45, 47, 48, 49)),
            (5, 'Our Experiences', (50, 52, 53, 54, 55, 56, 58, 59)),
            (6, 'Vietnamese Lifestyle: Then and Now', (60, 62, 63, 64, 65, 67, 68, 69)),
        ]),
        (102, 'Review 2', 0, [(50, 'Review 2', 70)]),
        *_gs_units(0, 51, [
            (7, 'Natural Wonders of the World', (72, 74, 75, 76, 77, 79, 80, 81)),
            (8, 'Tourism', (82, 84, 85, 86, 87, 88, 90, 91)),
            (9, 'World Englishes', (92, 94, 95, 96, 97, 99, 100, 101)),
        ]),
        (103, 'Review 3', 0, [(75, 'Review 3', 102)]),
        *_gs_units(0, 76, [
            (10, 'Planet Earth', (104, 106, 107, 108, 109, 110, 112, 113)),
            (11, 'Electronic Devices', (114, 116, 117, 118, 120, 121, 122, 123)),
            (12, 'Career Choices', (124, 126, 127, 128, 129, 131, 132, 133)),
        ]),
        (104, 'Review 4', 0, [(100, 'Review 4', 134)]),
    ]),
    # Ngữ văn: one "Bài" spans 20–30 pages, so each section (Tri thức ngữ văn, a reading text, Thực hành
    # tiếng Việt, Viết, Nói và nghe, Củng cố) is a lesson; the chapter is the book's own "Bài N".
    Course(subject='Ngữ văn', grade=6, series=SERIES_KNTT, numbered_lessons=False, outline=[
        (1, 'Bài 1. Tôi và các bạn', 1, [
            (1, 'Tôi và các bạn – Tri thức ngữ văn', 10),
            (2, 'Bài học đường đời đầu tiên', 12),
            (3, 'Tôi và các bạn – Thực hành tiếng Việt', 20),
            (4, 'Nếu cậu muốn có một người bạn...', 21),
            (5, 'Tôi và các bạn – Thực hành tiếng Việt (2)', 26),
            (6, 'Bắt nạt', 27),
            (7, 'Viết: Viết bài văn kể lại một trải nghiệm của em – Tôi và các bạn', 28),
            (8, 'Nói và nghe: Kể lại một trải nghiệm của em', 32),
            (9, 'Tôi và các bạn – Củng cố, mở rộng', 33),
            (10, 'Những người bạn', 34),
        ]),
        (2, 'Bài 2. Gõ cửa trái tim', 1, [
            (11, 'Gõ cửa trái tim – Tri thức ngữ văn', 38),
            (12, 'Chuyện cổ tích về loài người', 40),
            (13, 'Gõ cửa trái tim – Thực hành tiếng Việt', 43),
            (14, 'Mây và sóng', 44),
            (15, 'Gõ cửa trái tim – Thực hành tiếng Việt (2)', 47),
            (16, 'Bức tranh của em gái tôi', 48),
            (17, 'Viết: Viết đoạn văn ghi lại cảm xúc về một bài thơ có yếu tố tự sự và miêu tả', 52),
            (18, 'Nói và nghe: Trình bày ý kiến về một vấn đề trong đời sống gia đình', 55),
            (19, 'Gõ cửa trái tim – Củng cố, mở rộng', 56),
            (20, 'Những cánh buồm', 57),
        ]),
        (3, 'Bài 3. Yêu thương và chia sẻ', 1, [
            (21, 'Yêu thương và chia sẻ – Tri thức ngữ văn', 59),
            (22, 'Cô bé bán diêm', 61),
            (23, 'Yêu thương và chia sẻ – Thực hành tiếng Việt', 66),
            (24, 'Gió lạnh đầu mùa', 67),
            (25, 'Yêu thương và chia sẻ – Thực hành tiếng Việt (2)', 74),
            (26, 'Con chào mào', 75),
            (27, 'Viết: Viết bài văn kể lại một trải nghiệm của em – Yêu thương và chia sẻ', 77),
            (28, 'Nói và nghe: Kể về một trải nghiệm của em', 82),
            (29, 'Yêu thương và chia sẻ – Củng cố, mở rộng', 83),
            (30, 'Lắc-ki thực sự may mắn', 84),
        ]),
        (4, 'Bài 4. Quê hương yêu dấu', 1, [
            (31, 'Quê hương yêu dấu – Tri thức ngữ văn', 88),
            (32, 'Chùm ca dao về quê hương đất nước', 90),
            (33, 'Quê hương yêu dấu – Thực hành tiếng Việt', 92),
            (34, 'Chuyện cổ nước mình', 93),
            (35, 'Cây tre Việt Nam', 95),
            (36, 'Quê hương yêu dấu – Thực hành tiếng Việt (2)', 99),
            (37, 'Viết: Tập làm một bài thơ lục bát', 100),
            (38, 'Viết: Viết đoạn văn thể hiện cảm xúc về một bài thơ lục bát', 101),
            (39, 'Nói và nghe: Trình bày suy nghĩ về tình cảm của con người với quê hương', 104),
            (40, 'Quê hương yêu dấu – Củng cố, mở rộng', 106),
            (41, 'Hành trình của bầy ong', 106),
        ]),
        (5, 'Bài 5. Những nẻo đường xứ sở', 1, [
            (42, 'Những nẻo đường xứ sở – Tri thức ngữ văn', 108),
            (43, 'Cô Tô', 110),
            (44, 'Những nẻo đường xứ sở – Thực hành tiếng Việt', 113),
            (45, 'Hang Én', 114),
            (46, 'Những nẻo đường xứ sở – Thực hành tiếng Việt (2)', 118),
            (47, 'Cửu Long Giang ta ơi', 119),
            (48, 'Viết: Viết bài văn tả cảnh sinh hoạt', 122),
            (49, 'Nói và nghe: Chia sẻ một trải nghiệm về nơi em sống hoặc từng đến', 126),
            (50, 'Những nẻo đường xứ sở – Củng cố, mở rộng', 127),
            (51, 'Nghìn năm tháp Khương Mỹ', 128),
        ]),
        (101, 'Ôn tập học kì I', 1, [
            (52, 'Ôn tập học kì I', 131),
        ]),
        (6, 'Bài 6. Chuyện kể về những người anh hùng', 2, [
            (53, 'Chuyện kể về những người anh hùng – Tri thức ngữ văn', 4),
            (54, 'Thánh Gióng', 6),
            (55, 'Chuyện kể về những người anh hùng – Thực hành tiếng Việt', 9),
            (56, 'Sơn Tinh, Thuỷ Tinh', 10),
            (57, 'Chuyện kể về những người anh hùng – Thực hành tiếng Việt (2)', 13),
            (58, 'Ai ơi mồng 9 tháng 4', 14),
            (59, 'Viết: Viết bài văn thuyết minh thuật lại một sự kiện', 16),
            (60, 'Nói và nghe: Kể lại một truyền thuyết', 20),
            (61, 'Chuyện kể về những người anh hùng – Củng cố, mở rộng', 21),
            (62, 'Bánh chưng, bánh giầy', 22),
        ]),
        (7, 'Bài 7. Thế giới cổ tích', 2, [
            (63, 'Thế giới cổ tích – Tri thức ngữ văn', 24),
            (64, 'Thạch Sanh', 26),
            (65, 'Thế giới cổ tích – Thực hành tiếng Việt', 30),
            (66, 'Cây khế', 32),
            (67, 'Thế giới cổ tích – Thực hành tiếng Việt (2)', 35),
            (68, 'Vua chích choè', 36),
            (69, 'Viết: Viết bài văn đóng vai nhân vật kể lại một truyện cổ tích', 41),
            (70, 'Nói và nghe: Kể lại một truyện cổ tích bằng lời một nhân vật', 46),
            (71, 'Thế giới cổ tích – Củng cố, mở rộng', 47),
            (72, 'Sọ Dừa', 48),
        ]),
        (8, 'Bài 8. Khác biệt và gần gũi', 2, [
            (73, 'Khác biệt và gần gũi – Tri thức ngữ văn', 52),
            (74, 'Xem người ta kìa!', 54),
            (75, 'Khác biệt và gần gũi – Thực hành tiếng Việt', 56),
            (76, 'Hai loại khác biệt', 58),
            (77, 'Khác biệt và gần gũi – Thực hành tiếng Việt (2)', 61),
            (78, 'Bài tập làm văn', 63),
            (79, 'Viết: Viết bài văn trình bày ý kiến về một hiện tượng (vấn đề) mà em quan tâm', 66),
            (80, 'Nói và nghe: Trình bày ý kiến về một hiện tượng (vấn đề) đời sống', 70),
            (81, 'Khác biệt và gần gũi – Củng cố, mở rộng', 71),
            (82, 'Tiếng cười không muốn nghe', 73),
        ]),
        (9, 'Bài 9. Trái Đất – ngôi nhà chung', 2, [
            (83, 'Trái Đất – ngôi nhà chung – Tri thức ngữ văn', 76),
            (84, 'Trái Đất – cái nôi của sự sống', 78),
            (85, 'Trái Đất – ngôi nhà chung – Thực hành tiếng Việt', 81),
            (86, 'Các loài chung sống với nhau như thế nào?', 82),
            (87, 'Trái Đất – ngôi nhà chung – Thực hành tiếng Việt (2)', 86),
            (88, 'Trái Đất', 87),
            (89, 'Viết: Viết biên bản một cuộc họp, cuộc thảo luận', 88),
            (90, 'Viết: Tóm tắt bằng sơ đồ nội dung của một văn bản đơn giản', 91),
            (91, 'Nói và nghe: Thảo luận về giải pháp khắc phục nạn ô nhiễm môi trường', 92),
            (92, 'Trái Đất – ngôi nhà chung – Củng cố, mở rộng', 94),
            (93, 'Sinh vật trên Trái Đất được hình thành như thế nào?', 96),
        ]),
        (10, 'Bài 10. Cuốn sách tôi yêu', 2, [
            (94, 'Cuốn sách tôi yêu – Tri thức ngữ văn', 98),
            (95, 'Thách thức đầu tiên: Mỗi ngày một cuốn sách', 99),
            (96, 'Viết: Sáng tạo sản phẩm nghệ thuật', 103),
            (97, 'Viết: Viết bài văn trình bày ý kiến về một hiện tượng đời sống được gợi ra từ cuốn sách đã đọc', 104),
            (98, 'Nói và nghe: Giới thiệu sản phẩm minh hoạ sách', 106),
            (99, 'Nói và nghe: Trình bày ý kiến về một vấn đề trong đời sống được gợi ra từ cuốn sách đã đọc', 106),
        ]),
        (102, 'Ôn tập học kì II', 2, [
            (100, 'Ôn tập học kì II', 108),
        ]),
    ]),
    Course(subject='Ngữ văn', grade=7, series=SERIES_KNTT, numbered_lessons=False, outline=[
        (1, 'Bài 1. Bầu trời tuổi thơ', 1, [
            (1, 'Bầu trời tuổi thơ – Tri thức ngữ văn', 9),
            (2, 'Bầy chim chìa vôi', 11),
            (3, 'Bầu trời tuổi thơ – Thực hành tiếng Việt', 17),
            (4, 'Đi lấy mật', 18),
            (5, 'Bầu trời tuổi thơ – Thực hành tiếng Việt (2)', 24),
            (6, 'Ngàn sao làm việc', 25),
            (7, 'Viết: Tóm tắt văn bản theo những yêu cầu khác nhau về độ dài', 27),
            (8, 'Nói và nghe: Trao đổi về một vấn đề mà em quan tâm', 30),
            (9, 'Bầu trời tuổi thơ – Củng cố, mở rộng', 32),
            (10, 'Ngôi nhà trên cây', 33),
        ]),
        (2, 'Bài 2. Khúc nhạc tâm hồn', 1, [
            (11, 'Khúc nhạc tâm hồn – Tri thức ngữ văn', 38),
            (12, 'Đồng dao mùa xuân', 40),
            (13, 'Khúc nhạc tâm hồn – Thực hành tiếng Việt', 42),
            (14, 'Gặp lá cơm nếp', 43),
            (15, 'Trở gió', 44),
            (16, 'Khúc nhạc tâm hồn – Thực hành tiếng Việt (2)', 47),
            (17, 'Viết: Tập làm một bài thơ bốn chữ hoặc năm chữ', 48),
            (18, 'Viết: Viết đoạn văn ghi lại cảm xúc sau khi đọc một bài thơ bốn chữ hoặc năm chữ', 50),
            (19, 'Nói và nghe: Trình bày suy nghĩ về một vấn đề đời sống (được gợi ra từ tác phẩm văn học đã đọc)', 53),
            (20, 'Khúc nhạc tâm hồn – Củng cố, mở rộng', 55),
            (21, 'Chiều sông Thương', 56),
        ]),
        (3, 'Bài 3. Cội nguồn yêu thương', 1, [
            (22, 'Cội nguồn yêu thương – Tri thức ngữ văn', 57),
            (23, 'Vừa nhắm mắt vừa mở cửa sổ', 59),
            (24, 'Cội nguồn yêu thương – Thực hành tiếng Việt', 64),
            (25, 'Người thầy đầu tiên', 65),
            (26, 'Cội nguồn yêu thương – Thực hành tiếng Việt (2)', 72),
            (27, 'Quê hương', 73),
            (28, 'Viết: Viết bài văn phân tích đặc điểm nhân vật trong một tác phẩm văn học', 74),
            (29, 'Nói và nghe: Trình bày ý kiến về một vấn đề đời sống (được gợi ra từ một nhân vật văn học)', 81),
            (30, 'Cội nguồn yêu thương – Củng cố, mở rộng', 83),
            (31, 'Trong lòng mẹ', 84),
        ]),
        (4, 'Bài 4. Giai điệu đất nước', 1, [
            (32, 'Giai điệu đất nước – Tri thức ngữ văn', 88),
            (33, 'Mùa xuân nho nhỏ', 90),
            (34, 'Giai điệu đất nước – Thực hành tiếng Việt', 92),
            (35, 'Gò Me', 93),
            (36, 'Giai điệu đất nước – Thực hành tiếng Việt (2)', 95),
            (37, 'Bài thơ “Đường núi” của Nguyễn Đình Thi', 96),
            (38, 'Viết: Viết bài văn biểu cảm về con người hoặc sự việc', 98),
            (39, 'Nói và nghe: Trình bày ý kiến về những hoạt động thiện nguyện vì cộng đồng', 101),
            (40, 'Giai điệu đất nước – Củng cố, mở rộng', 103),
            (41, 'Chiều biên giới', 104),
        ]),
        (5, 'Bài 5. Màu sắc trăm miền', 1, [
            (42, 'Màu sắc trăm miền – Tri thức ngữ văn', 105),
            (43, 'Tháng Giêng, mơ về trăng non rét ngọt', 107),
            (44, 'Màu sắc trăm miền – Thực hành tiếng Việt', 110),
            (45, 'Chuyện cơm hến', 111),
            (46, 'Màu sắc trăm miền – Thực hành tiếng Việt (2)', 116),
            (47, 'Hội lồng tồng', 117),
            (48, 'Viết: Viết văn bản tường trình', 120),
            (49, 'Nói và nghe: Trình bày ý kiến về vấn đề văn hoá truyền thống trong xã hội hiện đại', 123),
            (50, 'Màu sắc trăm miền – Củng cố, mở rộng', 126),
            (51, 'Những khuôn cửa dấu yêu', 126),
        ]),
        (101, 'Ôn tập học kì I', 1, [
            (52, 'Ôn tập học kì I', 130),
        ]),
        (6, 'Bài 6. Bài học cuộc sống', 2, [
            (53, 'Bài học cuộc sống – Tri thức ngữ văn', 4),
            (54, 'Đẽo cày giữa đường', 6),
            (55, 'Ếch ngồi đáy giếng', 7),
            (56, 'Con mối và con kiến', 8),
            (57, 'Bài học cuộc sống – Thực hành tiếng Việt', 10),
            (58, 'Một số câu tục ngữ Việt Nam', 12),
            (59, 'Bài học cuộc sống – Thực hành tiếng Việt (2)', 13),
            (60, 'Con hổ có nghĩa', 14),
            (61, 'Viết: Viết bài văn nghị luận về một vấn đề trong đời sống (trình bày ý kiến tán thành)', 16),
            (62, 'Nói và nghe: Kể lại một truyện ngụ ngôn', 21),
            (63, 'Bài học cuộc sống – Củng cố, mở rộng', 22),
            (64, 'Thiên nga, cá măng và tôm hùm', 23),
        ]),
        (7, 'Bài 7. Thế giới viễn tưởng', 2, [
            (65, 'Thế giới viễn tưởng – Tri thức ngữ văn', 25),
            (66, 'Cuộc chạm trán trên đại dương', 27),
            (67, 'Thế giới viễn tưởng – Thực hành tiếng Việt', 34),
            (68, 'Đường vào trung tâm vũ trụ', 35),
            (69, 'Thế giới viễn tưởng – Thực hành tiếng Việt (2)', 41),
            (70, 'Dấu ấn Hồ Khanh', 42),
            (71, 'Viết: Viết bài văn kể lại sự việc có thật liên quan đến một nhân vật lịch sử', 45),
            (72, 'Nói và nghe: Thảo luận về vai trò của công nghệ đối với đời sống con người', 48),
            (73, 'Thế giới viễn tưởng – Củng cố, mở rộng', 50),
            (74, 'Chiếc đũa thần', 51),
        ]),
        (8, 'Bài 8. Trải nghiệm để trưởng thành', 2, [
            (75, 'Trải nghiệm để trưởng thành – Tri thức ngữ văn', 54),
            (76, 'Bản đồ dẫn đường', 56),
            (77, 'Trải nghiệm để trưởng thành – Thực hành tiếng Việt', 59),
            (78, 'Hãy cầm lấy và đọc', 61),
            (79, 'Trải nghiệm để trưởng thành – Thực hành tiếng Việt (2)', 64),
            (80, 'Nói với con', 65),
            (81, 'Viết: Viết bài văn nghị luận về một vấn đề trong đời sống (trình bày ý kiến phản đối)', 67),
            (82, 'Nói và nghe: Trình bày ý kiến về một vấn đề đời sống', 71),
            (83, 'Trải nghiệm để trưởng thành – Củng cố, mở rộng', 73),
            (84, 'Câu chuyện về con đường', 74),
        ]),
        (9, 'Bài 9. Hoà điệu với tự nhiên', 2, [
            (85, 'Hoà điệu với tự nhiên – Tri thức ngữ văn', 76),
            (86, 'Thuỷ tiên tháng Một', 78),
            (87, 'Hoà điệu với tự nhiên – Thực hành tiếng Việt', 83),
            (88, 'Lễ rửa làng của người Lô Lô', 84),
            (89, 'Bản tin về hoa anh đào', 87),
            (90, 'Hoà điệu với tự nhiên – Thực hành tiếng Việt (2)', 90),
            (91, 'Viết: Viết bài văn thuyết minh về quy tắc hoặc luật lệ trong trò chơi hay hoạt động', 91),
            (92, 'Nói và nghe: Giải thích quy tắc hoặc luật lệ trong một trò chơi hay hoạt động', 95),
            (93, 'Hoà điệu với tự nhiên – Củng cố, mở rộng', 97),
            (94, '“Thân thiện với môi trường”', 98),
        ]),
        (10, 'Bài 10. Trang sách và cuộc sống', 2, [
            (95, 'Trang sách và cuộc sống – Tri thức ngữ văn', 101),
            (96, 'Thách thức đầu tiên: Chinh phục những cuốn sách mới', 103),
            (97, 'Viết: Thách thức thứ hai: Từ ý tưởng đến sản phẩm', 109),
            (98, 'Viết: Viết bài văn phân tích một nhân vật văn học yêu thích trong cuốn sách đã đọc', 112),
            (99, 'Nói và nghe: Về đích: Ngày hội với sách', 115),
        ]),
        (102, 'Ôn tập học kì II', 2, [
            (100, 'Ôn tập học kì II', 117),
        ]),
    ]),
    Course(subject='Ngữ văn', grade=8, series=SERIES_KNTT, numbered_lessons=False, outline=[
        (1, 'Bài 1. Câu chuyện của lịch sử', 1, [
            (1, 'Câu chuyện của lịch sử – Tri thức ngữ văn', 8),
            (2, 'Lá cờ thêu sáu chữ vàng', 10),
            (3, 'Câu chuyện của lịch sử – Thực hành tiếng Việt', 16),
            (4, 'Quang Trung đại phá quân Thanh', 17),
            (5, 'Câu chuyện của lịch sử – Thực hành tiếng Việt (2)', 24),
            (6, 'Ta đi tới', 25),
            (7, 'Viết: Viết bài văn kể lại một chuyến đi (tham quan một di tích lịch sử, văn hoá)', 28),
            (8, 'Nói và nghe: Trình bày bài giới thiệu ngắn về một cuốn sách (cuốn truyện lịch sử)', 33),
            (9, 'Câu chuyện của lịch sử – Củng cố, mở rộng', 34),
            (10, 'Minh sư', 35),
        ]),
        (2, 'Bài 2. Vẻ đẹp cổ điển', 1, [
            (11, 'Vẻ đẹp cổ điển – Tri thức ngữ văn', 38),
            (12, 'Thu điếu', 40),
            (13, 'Vẻ đẹp cổ điển – Thực hành tiếng Việt', 42),
            (14, 'Thiên Trường vãn vọng', 43),
            (15, 'Vẻ đẹp cổ điển – Thực hành tiếng Việt (2)', 45),
            (16, 'Ca Huế trên sông Hương', 46),
            (17, 'Viết: Viết bài văn phân tích một tác phẩm văn học (bài thơ thất ngôn bát cú hoặc tứ tuyệt Đường luật)', 48),
            (18, 'Nói và nghe: Trình bày ý kiến về một vấn đề xã hội (một sản phẩm văn hoá truyền thống trong cuộc sống hiện tại)', 53),
            (19, 'Vẻ đẹp cổ điển – Củng cố, mở rộng', 55),
            (20, 'Qua Đèo Ngang', 56),
        ]),
        (3, 'Bài 3. Lời sông núi', 1, [
            (21, 'Lời sông núi – Tri thức ngữ văn', 57),
            (22, 'Hịch tướng sĩ', 59),
            (23, 'Lời sông núi – Thực hành tiếng Việt', 64),
            (24, 'Tinh thần yêu nước của nhân dân ta', 65),
            (25, 'Lời sông núi – Thực hành tiếng Việt (2)', 68),
            (26, 'Nam quốc sơn hà', 69),
            (27, 'Viết: Viết bài văn nghị luận về một vấn đề đời sống (con người trong mối quan hệ với xã hội, cộng đồng, đất nước)', 71),
            (28, 'Nói và nghe: Thảo luận về một vấn đề trong đời sống phù hợp với lứa tuổi (ý thức trách nhiệm với cộng đồng của học sinh)', 75),
            (29, 'Lời sông núi – Củng cố, mở rộng', 77),
            (30, 'Chiếu dời đô', 78),
        ]),
        (4, 'Bài 4. Tiếng cười trào phúng trong thơ', 1, [
            (31, 'Tiếng cười trào phúng trong thơ – Tri thức ngữ văn', 80),
            (32, 'Lễ xướng danh khoa Đinh Dậu', 82),
            (33, 'Tiếng cười trào phúng trong thơ – Thực hành tiếng Việt', 84),
            (34, 'Lai Tân', 85),
            (35, 'Tiếng cười trào phúng trong thơ – Thực hành tiếng Việt (2)', 86),
            (36, 'Một số giọng điệu của tiếng cười trong thơ trào phúng', 88),
            (37, 'Viết: Viết bài văn phân tích một tác phẩm văn học (thơ trào phúng)', 91),
            (38, 'Nói và nghe: Trình bày ý kiến về một vấn đề xã hội (ý nghĩa của tiếng cười trong đời sống)', 96),
            (39, 'Tiếng cười trào phúng trong thơ – Củng cố, mở rộng', 97),
            (40, 'Vịnh cây vông', 98),
        ]),
        (5, 'Bài 5. Những câu chuyện hài', 1, [
            (41, 'Những câu chuyện hài – Tri thức ngữ văn', 99),
            (42, 'Trưởng giả học làm sang', 101),
            (43, 'Những câu chuyện hài – Thực hành tiếng Việt', 107),
            (44, 'Chùm truyện cười dân gian Việt Nam', 108),
            (45, 'Chùm ca dao trào phúng', 111),
            (46, 'Những câu chuyện hài – Thực hành tiếng Việt (2)', 113),
            (47, 'Viết: Viết bài văn nghị luận về một vấn đề đời sống (một thói xấu của con người trong xã hội hiện đại)', 114),
            (48, 'Nói và nghe: Trình bày ý kiến về một vấn đề xã hội (một thói xấu của con người trong xã hội hiện đại)', 118),
            (49, 'Những câu chuyện hài – Củng cố, mở rộng', 120),
            (50, 'Giá không có ruồi!', 120),
        ]),
        (101, 'Ôn tập học kì I', 1, [
            (51, 'Ôn tập học kì I', 124),
        ]),
        (6, 'Bài 6. Chân dung cuộc sống', 2, [
            (52, 'Chân dung cuộc sống – Tri thức ngữ văn', 4),
            (53, 'Mắt sói', 6),
            (54, 'Chân dung cuộc sống – Thực hành tiếng Việt', 14),
            (55, 'Lặng lẽ Sa Pa', 15),
            (56, 'Chân dung cuộc sống – Thực hành tiếng Việt (2)', 23),
            (57, 'Bếp lửa', 24),
            (58, 'Viết: Viết bài văn phân tích một tác phẩm (truyện) – Chân dung cuộc sống', 26),
            (59, 'Nói và nghe: Giới thiệu về một cuốn sách (truyện)', 31),
            (60, 'Chân dung cuộc sống – Củng cố, mở rộng', 32),
            (61, 'Chiếc lá cuối cùng', 33),
        ]),
        (7, 'Bài 7. Tin yêu và ước vọng', 2, [
            (62, 'Tin yêu và ước vọng – Tri thức ngữ văn', 36),
            (63, 'Đồng chí', 38),
            (64, 'Tin yêu và ước vọng – Thực hành tiếng Việt', 40),
            (65, 'Lá đỏ', 40),
            (66, 'Những ngôi sao xa xôi', 42),
            (67, 'Tin yêu và ước vọng – Thực hành tiếng Việt (2)', 48),
            (68, 'Viết: Tập làm một bài thơ tự do', 49),
            (69, 'Viết: Viết đoạn văn ghi lại cảm nghĩ về một bài thơ tự do', 51),
            (70, 'Nói và nghe: Thảo luận ý kiến về một vấn đề đời sống phù hợp với lứa tuổi (được gợi ra từ tác phẩm văn học đã học)', 54),
            (71, 'Tin yêu và ước vọng – Củng cố, mở rộng', 56),
            (72, 'Bài thơ về tiểu đội xe không kính', 57),
        ]),
        (8, 'Bài 8. Nhà văn và trang viết', 2, [
            (73, 'Nhà văn và trang viết – Tri thức ngữ văn', 59),
            (74, 'Nhà thơ của quê hương làng cảnh Việt Nam', 61),
            (75, 'Nhà văn và trang viết – Thực hành tiếng Việt', 66),
            (76, 'Đọc văn – cuộc chơi tìm ý nghĩa', 67),
            (77, 'Nhà văn và trang viết – Thực hành tiếng Việt (2)', 69),
            (78, 'Xe đêm', 71),
            (79, 'Viết: Viết bài văn phân tích một tác phẩm (truyện) – Nhà văn và trang viết', 77),
            (80, 'Nói và nghe: Trình bày ý kiến về một vấn đề xã hội (văn học trong đời sống hiện nay)', 81),
            (81, 'Nhà văn và trang viết – Củng cố, mở rộng', 82),
            (82, '“Nắng mới” – sự thành thực của một tâm hồn giàu mơ mộng', 83),
        ]),
        (9, 'Bài 9. Hôm nay và ngày mai', 2, [
            (83, 'Hôm nay và ngày mai – Tri thức ngữ văn', 86),
            (84, 'Miền châu thổ sông Cửu Long cần chuyển đổi từ sống chung sang chào đón lũ', 89),
            (85, 'Hôm nay và ngày mai – Thực hành tiếng Việt', 93),
            (86, 'Choáng ngợp và đau đớn những cảnh báo từ loạt phim “Hành tinh của chúng ta”', 94),
            (87, 'Diễn từ ứng khẩu của thủ lĩnh da đỏ Xi-át-tơn', 98),
            (88, 'Hôm nay và ngày mai – Thực hành tiếng Việt (2)', 101),
            (89, 'Viết: Viết văn bản thuyết minh giải thích một hiện tượng tự nhiên', 102),
            (90, 'Viết: Viết văn bản kiến nghị về một vấn đề của đời sống', 105),
            (91, 'Nói và nghe: Thảo luận về một vấn đề trong đời sống phù hợp với lứa tuổi (tổ chức hợp lí nề nếp sinh hoạt của bản thân)', 109),
            (92, 'Hôm nay và ngày mai – Củng cố, mở rộng', 111),
            (93, '“Dấu chân sinh thái” của mỗi người và thông điệp từ Trái Đất', 111),
        ]),
        (10, 'Bài 10. Sách – người bạn đồng hành', 2, [
            (94, 'Sách – người bạn đồng hành – Tri thức ngữ văn', 115),
            (95, 'Thách thức đầu tiên: Đọc như một hành trình', 117),
            (96, 'Viết: Viết bài thuyết minh giới thiệu cuốn sách yêu thích', 122),
            (97, 'Viết: Viết một nhan đề và sáng tạo một tác phẩm mới', 125),
            (98, 'Nói và nghe: Về đích: Ngày hội với sách', 127),
        ]),
        (102, 'Ôn tập học kì II', 2, [
            (99, 'Ôn tập học kì II', 128),
        ]),
    ]),
    Course(subject='Ngữ văn', grade=9, series=SERIES_KNTT, numbered_lessons=False, outline=[
        (1, 'Bài 1. Thế giới kì ảo', 1, [
            (1, 'Thế giới kì ảo – Tri thức ngữ văn', 8),
            (2, 'Chuyện người con gái Nam Xương', 10),
            (3, 'Thế giới kì ảo – Thực hành tiếng Việt', 17),
            (4, 'Dế chọi', 18),
            (5, 'Thế giới kì ảo – Thực hành tiếng Việt (2)', 22),
            (6, 'Sơn Tinh – Thuỷ Tinh', 24),
            (7, 'Viết: Viết bài văn nghị luận về một vấn đề cần giải quyết (con người trong mối quan hệ với tự nhiên)', 27),
            (8, 'Nói và nghe: Trình bày ý kiến về một sự việc có tính thời sự (con người trong mối quan hệ với tự nhiên)', 33),
            (9, 'Thế giới kì ảo – Củng cố, mở rộng', 34),
            (10, 'Ngọc nữ về tay chân chủ', 35),
        ]),
        (2, 'Bài 2. Những cung bậc tâm trạng', 1, [
            (11, 'Những cung bậc tâm trạng – Tri thức ngữ văn', 39),
            (12, 'Nỗi niềm chinh phụ', 41),
            (13, 'Những cung bậc tâm trạng – Thực hành tiếng Việt', 44),
            (14, 'Tiếng đàn mưa', 46),
            (15, 'Những cung bậc tâm trạng – Thực hành tiếng Việt (2)', 47),
            (16, 'Một thể thơ độc đáo của người Việt', 49),
            (17, 'Viết: Viết bài văn nghị luận phân tích một tác phẩm văn học (thơ song thất lục bát)', 52),
            (18, 'Nói và nghe: Thảo luận về một vấn đề đáng quan tâm trong đời sống phù hợp với lứa tuổi (được gợi ra từ tác phẩm văn học) – Những cung bậc tâm trạng', 58),
            (19, 'Những cung bậc tâm trạng – Củng cố, mở rộng', 59),
            (20, 'Nỗi sầu oán của người cung nữ', 60),
        ]),
        (3, 'Bài 3. Hồn nước nằm trong tiếng mẹ cha', 1, [
            (21, 'Hồn nước nằm trong tiếng mẹ cha – Tri thức ngữ văn', 63),
            (22, 'Kim – Kiều gặp gỡ', 66),
            (23, 'Hồn nước nằm trong tiếng mẹ cha – Thực hành tiếng Việt', 70),
            (24, 'Lục Vân Tiên đánh cướp, cứu Kiều Nguyệt Nga', 71),
            (25, 'Hồn nước nằm trong tiếng mẹ cha – Thực hành tiếng Việt (2)', 74),
            (26, 'Tự tình (bài 2)', 75),
            (27, 'Viết: Viết bài văn nghị luận về một vấn đề cần giải quyết (trong đời sống của học sinh hiện nay)', 77),
            (28, 'Nói và nghe: Trình bày ý kiến về một vấn đề có tính thời sự trong đời sống của lứa tuổi học sinh hiện nay', 82),
            (29, 'Hồn nước nằm trong tiếng mẹ cha – Củng cố, mở rộng', 83),
            (30, 'Kiều ở lầu Ngưng Bích', 85),
        ]),
        (4, 'Bài 4. Khám phá vẻ đẹp văn chương', 1, [
            (31, 'Khám phá vẻ đẹp văn chương – Tri thức ngữ văn', 87),
            (32, '“Người con gái Nam Xương” – một bi kịch của con người', 89),
            (33, 'Khám phá vẻ đẹp văn chương – Thực hành tiếng Việt', 93),
            (34, 'Từ “Thằng quỷ nhỏ” của Nguyễn Nhật Ánh nghĩ về những phẩm chất của một tác phẩm viết cho thiếu nhi', 95),
            (35, 'Khám phá vẻ đẹp văn chương – Thực hành tiếng Việt (2)', 100),
            (36, 'Ngày xưa', 102),
            (37, 'Viết: Viết bài văn nghị luận phân tích một tác phẩm văn học (truyện)', 103),
            (38, 'Nói và nghe: Thảo luận về một vấn đề đáng quan tâm trong đời sống phù hợp với lứa tuổi (Làm thế nào để học tốt môn Ngữ văn?)', 108),
            (39, 'Khám phá vẻ đẹp văn chương – Củng cố, mở rộng', 110),
            (40, '“Hoàng Hạc lâu tống Mạnh Hạo Nhiên chi Quảng Lăng”, một bài thơ tiễn biệt tiêu biểu trong thơ Đường', 111),
        ]),
        (5, 'Bài 5. Đối diện với nỗi đau', 1, [
            (41, 'Đối diện với nỗi đau – Tri thức ngữ văn', 116),
            (42, 'Rô-mê-ô và Giu-li-ét', 118),
            (43, 'Đối diện với nỗi đau – Thực hành tiếng Việt', 121),
            (44, 'Lơ Xít', 123),
            (45, 'Bí ẩn của làn nước', 128),
            (46, 'Đối diện với nỗi đau – Thực hành tiếng Việt (2)', 130),
            (47, 'Viết: Viết bài văn nghị luận phân tích một tác phẩm văn học (kịch)', 132),
            (48, 'Nói và nghe: Thảo luận về một vấn đề đáng quan tâm trong đời sống phù hợp với lứa tuổi (được gợi ra từ tác phẩm văn học) – Đối diện với nỗi đau', 137),
            (49, 'Đối diện với nỗi đau – Củng cố, mở rộng', 138),
            (50, 'Âm mưu và tình yêu', 139),
        ]),
        (101, 'Ôn tập học kì I', 1, [
            (51, 'Ôn tập học kì I', 142),
        ]),
        (6, 'Bài 6. Giải mã những bí mật', 2, [
            (52, 'Giải mã những bí mật – Tri thức ngữ văn', 4),
            (53, 'Ba chàng sinh viên', 7),
            (54, 'Giải mã những bí mật – Thực hành tiếng Việt', 15),
            (55, 'Bài hát đồng sáu xu', 16),
            (56, 'Phạm Xuân Ẩn – tên người như cuộc đời', 24),
            (57, 'Giải mã những bí mật – Thực hành tiếng Việt (2)', 28),
            (58, 'Viết: Viết truyện kể sáng tạo', 30),
            (59, 'Nói và nghe: Kể một câu chuyện tưởng tượng', 35),
            (60, 'Giải mã những bí mật – Củng cố, mở rộng', 37),
            (61, 'Ba viên ngọc bích', 38),
        ]),
        (7, 'Bài 7. Hồn thơ muôn điệu', 2, [
            (62, 'Hồn thơ muôn điệu – Tri thức ngữ văn', 44),
            (63, 'Tiếng Việt', 46),
            (64, 'Hồn thơ muôn điệu – Thực hành tiếng Việt', 50),
            (65, 'Mưa xuân', 51),
            (66, 'Hồn thơ muôn điệu – Thực hành tiếng Việt (2)', 54),
            (67, 'Một kiểu phát biểu luận đề độc đáo của Xuân Diệu ở bài thơ “Vội vàng”', 55),
            (68, 'Viết: Tập làm một bài thơ tám chữ', 58),
            (69, 'Viết: Viết đoạn văn ghi lại cảm nghĩ về một bài thơ tám chữ', 60),
            (70, 'Nói và nghe: Thảo luận về một vấn đề đáng quan tâm trong đời sống phù hợp với lứa tuổi (được gợi ra từ tác phẩm văn học) – Hồn thơ muôn điệu', 63),
            (71, 'Hồn thơ muôn điệu – Củng cố, mở rộng', 64),
            (72, 'Miền quê', 65),
        ]),
        (8, 'Bài 8. Tiếng nói của lương tri', 2, [
            (73, 'Tiếng nói của lương tri – Tri thức ngữ văn', 66),
            (74, 'Đấu tranh cho một thế giới hoà bình', 68),
            (75, 'Tiếng nói của lương tri – Thực hành tiếng Việt', 71),
            (76, 'Biến đổi khí hậu – mối đe doạ sự tồn vong của hành tinh chúng ta', 72),
            (77, 'Tiếng nói của lương tri – Thực hành tiếng Việt (2)', 76),
            (78, 'Bài ca chúc Tết thanh niên', 77),
            (79, 'Viết: Viết bài văn nghị luận về một vấn đề cần giải quyết (trong đời sống xã hội)', 79),
            (80, 'Nói và nghe: Trình bày ý kiến về một sự việc có tính thời sự (trong đời sống của cộng đồng, đất nước, nhân loại)', 84),
            (81, 'Tiếng nói của lương tri – Củng cố, mở rộng', 85),
            (82, 'Chuẩn bị hành trang', 86),
        ]),
        (9, 'Bài 9. Đi và suy ngẫm', 2, [
            (83, 'Đi và suy ngẫm – Tri thức ngữ văn', 89),
            (84, 'Yên Tử, núi thiêng', 91),
            (85, 'Đi và suy ngẫm – Thực hành tiếng Việt', 95),
            (86, 'Văn hoá hoa – cây cảnh', 96),
            (87, 'Đi và suy ngẫm – Thực hành tiếng Việt (2)', 100),
            (88, 'Tình sông núi', 102),
            (89, 'Viết: Viết bài thuyết minh về một danh lam thắng cảnh hay một di tích lịch sử', 104),
            (90, 'Nói và nghe: Thuyết minh về một danh lam thắng cảnh hay một di tích lịch sử', 108),
            (91, 'Đi và suy ngẫm – Củng cố, mở rộng', 109),
            (92, 'Khu Trung tâm Hoàng thành Thăng Long – Hà Nội', 110),
        ]),
        (10, 'Bài 10. Văn học – lịch sử tâm hồn', 2, [
            (93, 'Văn học – lịch sử tâm hồn – Tri thức ngữ văn', 113),
            (94, 'Thách thức đầu tiên: Đọc để trưởng thành', 116),
            (95, 'Văn học Việt Nam từ khu vực ra thế giới, từ truyền thống đến hiện đại', 117),
            (96, 'Văn hoá đọc với nhà văn và độc giả trong thời đại công nghệ số', 121),
            (97, 'Bên mộ cụ Nguyễn Du', 124),
            (98, 'Viết: Quảng bá giá trị của sách', 125),
            (99, 'Nói và nghe: Phát triển văn hoá đọc', 128),
        ]),
        (102, 'Ôn tập học kì II', 2, [
            (100, 'Ôn tập học kì II', 131),
        ]),
    ]),
    Course(subject='LSDL', grade=6, series=SERIES_KNTT, outline=[
        (1, 'Lịch sử – Chương 1. Vì sao phải học lịch sử?', 0, [
            (1, 'Lịch sử và cuộc sống', 9),
            (2, 'Dựa vào đâu để biết và phục dựng lại lịch sử?', 11),
            (3, 'Thời gian trong lịch sử', 14),
        ]),
        (2, 'Lịch sử – Chương 2. Xã hội nguyên thuỷ', 0, [
            (4, 'Nguồn gốc loài người', 17),
            (5, 'Xã hội nguyên thuỷ', 20),
            (6, 'Sự chuyển biến và phân hoá của xã hội nguyên thuỷ', 24),
        ]),
        (3, 'Lịch sử – Chương 3. Xã hội cổ đại', 0, [
            (7, 'Ai Cập và Lưỡng Hà cổ đại', 29),
            (8, 'Ấn Độ cổ đại', 34),
            (9, 'Trung Quốc cổ đại', 39),
            (10, 'Hy Lạp và La Mã cổ đại', 44),
        ]),
        (4, 'Lịch sử – Chương 4. Đông Nam Á từ những thế kỉ tiếp giáp đầu Công nguyên đến thế kỉ X', 0, [
            (11, 'Các quốc gia sơ kì ở Đông Nam Á', 51),
            (12, 'Sự hình thành và bước đầu phát triển của các vương quốc phong kiến ở Đông Nam Á (từ thế kỉ VII đến thế kỉ X)', 54),
            (13, 'Giao lưu văn hoá ở Đông Nam Á từ đầu Công nguyên đến thế kỉ X', 56),
        ]),
        (5, 'Lịch sử – Chương 5. Việt Nam từ khoảng thế kỉ VII trước Công nguyên đến đầu thế kỉ X', 0, [
            (14, 'Nhà nước Văn Lang, Âu Lạc', 60),
            (15, 'Chính sách cai trị của các triều đại phong kiến phương Bắc và sự chuyển biến của xã hội Âu Lạc', 65),
            (16, 'Các cuộc khởi nghĩa tiêu biểu giành độc lập trước thế kỉ X', 70),
            (17, 'Cuộc đấu tranh bảo tồn và phát triển văn hoá dân tộc của người Việt', 78),
            (18, 'Bước ngoặt lịch sử đầu thế kỉ X', 80),
            (19, 'Vương quốc Chăm-pa từ thế kỉ II đến thế kỉ X', 86),
            (20, 'Vương quốc Phù Nam', 91),
        ]),
        (6, 'Địa lí – Bài mở đầu', 0, [
            (0, 'Bài mở đầu', 98),
        ]),
        (7, 'Địa lí – Chương 1. Bản đồ – phương tiện thể hiện bề mặt Trái Đất', 0, [
            (1, 'Hệ thống kinh, vĩ tuyến. Toạ độ địa lí', 102),
            (2, 'Bản đồ. Một số lưới kinh, vĩ tuyến. Phương hướng trên bản đồ', 104),
            (3, 'Tỉ lệ bản đồ. Tính khoảng cách thực tế dựa vào tỉ lệ bản đồ', 106),
            (4, 'Kí hiệu và bảng chú giải bản đồ. Tìm đường đi trên bản đồ', 108),
            (5, 'Lược đồ trí nhớ', 113),
        ]),
        (8, 'Địa lí – Chương 2. Trái Đất – hành tinh của hệ Mặt Trời', 0, [
            (6, 'Trái Đất trong hệ Mặt Trời', 116),
            (7, 'Chuyển động tự quay quanh trục của Trái Đất và hệ quả', 118),
            (8, 'Chuyển động của Trái Đất quanh Mặt Trời và hệ quả', 122),
            (9, 'Xác định phương hướng ngoài thực tế', 125),
        ]),
        (9, 'Địa lí – Chương 3. Cấu tạo của Trái Đất. Vỏ Trái Đất', 0, [
            (10, 'Cấu tạo của Trái Đất. Các mảng kiến tạo', 129),
            (11, 'Quá trình nội sinh và quá trình ngoại sinh. Hiện tượng tạo núi', 131),
            (12, 'Núi lửa và động đất', 133),
            (13, 'Các dạng địa hình chính trên Trái Đất. Khoáng sản', 135),
            (14, 'Thực hành: Đọc lược đồ địa hình tỉ lệ lớn và lát cắt địa hình đơn giản', 139),
        ]),
        (10, 'Địa lí – Chương 4. Khí hậu và biến đổi khí hậu', 0, [
            (15, 'Lớp vỏ khí của Trái Đất. Khí áp và gió', 142),
            (16, 'Nhiệt độ không khí. Mây và mưa', 146),
            (17, 'Thời tiết và khí hậu. Biến đổi khí hậu', 150),
            (18, 'Thực hành: Phân tích biểu đồ nhiệt độ, lượng mưa', 153),
        ]),
        (11, 'Địa lí – Chương 5. Nước trên Trái Đất', 0, [
            (19, 'Thuỷ quyển và vòng tuần hoàn lớn của nước', 156),
            (20, 'Sông và hồ. Nước ngầm và băng hà', 158),
            (21, 'Biển và đại dương', 163),
        ]),
        (12, 'Địa lí – Chương 6. Đất và sinh vật trên Trái Đất', 0, [
            (22, 'Lớp đất trên Trái Đất', 168),
            (23, 'Sự sống trên Trái Đất', 171),
            (24, 'Rừng nhiệt đới', 173),
            (25, 'Sự phân bố các đới thiên nhiên trên Trái Đất', 175),
            (26, 'Thực hành: Tìm hiểu môi trường tự nhiên địa phương', 177),
        ]),
        (13, 'Địa lí – Chương 7. Con người và thiên nhiên', 0, [
            (27, 'Dân số và sự phân bố dân cư trên thế giới', 180),
            (28, 'Mối quan hệ giữa con người và thiên nhiên', 184),
            (29, 'Bảo vệ tự nhiên và khai thác thông minh các tài nguyên thiên nhiên vì sự phát triển bền vững', 187),
            (30, 'Thực hành: Tìm hiểu mối quan hệ giữa con người và thiên nhiên ở địa phương', 189),
        ]),
    ]),
    Course(subject='LSDL', grade=7, series=SERIES_KNTT, outline=[
        (1, 'Lịch sử – Chương 1. Tây Âu từ thế kỉ V đến nửa đầu thế kỉ XVI', 0, [
            (1, 'Quá trình hình thành và phát triển của chế độ phong kiến ở Tây Âu', 9),
            (2, 'Các cuộc phát kiến địa lí và sự hình thành quan hệ sản xuất tư bản chủ nghĩa ở Tây Âu', 14),
            (3, 'Phong trào Văn hoá Phục hưng và Cải cách tôn giáo', 18),
        ]),
        (2, 'Lịch sử – Chương 2. Trung Quốc và Ấn Độ thời trung đại', 0, [
            (4, 'Trung Quốc từ thế kỉ III TCN đến giữa thế kỉ XIX', 24),
            (5, 'Ấn Độ từ thế kỉ IV đến giữa thế kỉ XIX', 29),
        ]),
        (3, 'Lịch sử – Chương 3. Đông Nam Á từ nửa sau thế kỉ X đến nửa đầu thế kỉ XVI', 0, [
            (6, 'Các vương quốc phong kiến Đông Nam Á từ nửa sau thế kỉ X đến nửa đầu thế kỉ XVI', 35),
            (7, 'Vương quốc Lào', 39),
            (8, 'Vương quốc Cam-pu-chia', 42),
        ]),
        (4, 'Lịch sử – Chương 4. Đất nước dưới thời các vương triều Ngô – Đinh – Tiền Lê (939 – 1009)', 0, [
            (9, 'Đất nước buổi đầu độc lập (939 – 967)', 45),
            (10, 'Đại Cồ Việt thời Đinh và Tiền Lê (968 – 1009)', 48),
        ]),
        (5, 'Lịch sử – Chương 5. Đại Việt thời Lý – Trần – Hồ (1009 – 1407)', 0, [
            (11, 'Nhà Lý xây dựng và phát triển đất nước (1009 – 1225)', 52),
            (12, 'Cuộc kháng chiến chống quân xâm lược Tống (1075 – 1077)', 58),
            (13, 'Đại Việt thời Trần (1226 – 1400)', 62),
            (14, 'Ba lần kháng chiến chống quân xâm lược Mông – Nguyên', 68),
            (15, 'Nước Đại Ngu thời Hồ (1400 – 1407)', 74),
        ]),
        (6, 'Lịch sử – Chương 6. Khởi nghĩa Lam Sơn và Đại Việt thời Lê sơ (1418 – 1527)', 0, [
            (16, 'Khởi nghĩa Lam Sơn (1418 – 1427)', 78),
            (17, 'Đại Việt thời Lê sơ (1428 – 1527)', 83),
        ]),
        (7, 'Lịch sử – Chương 7. Vùng đất phía Nam Việt Nam từ đầu thế kỉ X đến đầu thế kỉ XVI', 0, [
            (18, 'Vương quốc Chăm-pa và vùng đất Nam Bộ từ đầu thế kỉ X đến đầu thế kỉ XVI', 90),
        ]),
        (8, 'Địa lí – Chương 1. Châu Âu', 0, [
            (1, 'Vị trí địa lí, đặc điểm tự nhiên châu Âu', 96),
            (2, 'Đặc điểm dân cư, xã hội châu Âu', 101),
            (3, 'Khai thác, sử dụng và bảo vệ thiên nhiên ở châu Âu', 104),
            (4, 'Liên minh châu Âu', 107),
        ]),
        (9, 'Địa lí – Chương 2. Châu Á', 0, [
            (5, 'Vị trí địa lí, đặc điểm tự nhiên châu Á', 109),
            (6, 'Đặc điểm dân cư, xã hội châu Á', 115),
            (7, 'Bản đồ chính trị châu Á, các khu vực của châu Á', 118),
            (8, 'Thực hành: Tìm hiểu về các nền kinh tế lớn và kinh tế mới nổi của châu Á', 126),
        ]),
        (10, 'Địa lí – Chương 3. Châu Phi', 0, [
            (9, 'Vị trí địa lí, đặc điểm tự nhiên châu Phi', 127),
            (10, 'Đặc điểm dân cư, xã hội châu Phi', 133),
            (11, 'Phương thức con người khai thác, sử dụng và bảo vệ thiên nhiên ở châu Phi', 135),
            (12, 'Thực hành: Tìm hiểu khái quát Cộng hoà Nam Phi', 138),
        ]),
        (11, 'Địa lí – Chương 4. Châu Mỹ', 0, [
            (13, 'Vị trí địa lí, phạm vi châu Mỹ. Sự phát kiến ra châu Mỹ', 139),
            (14, 'Đặc điểm tự nhiên Bắc Mỹ', 142),
            (15, 'Đặc điểm dân cư, xã hội, phương thức khai thác tự nhiên bền vững ở Bắc Mỹ', 145),
            (16, 'Đặc điểm tự nhiên Trung và Nam Mỹ', 149),
            (17, 'Đặc điểm dân cư, xã hội Trung và Nam Mỹ, khai thác, sử dụng và bảo vệ rừng A-ma-dôn', 152),
        ]),
        (12, 'Địa lí – Chương 5. Châu Đại Dương và châu Nam Cực', 0, [
            (18, 'Châu Đại Dương', 156),
            (19, 'Châu Nam Cực', 162),
        ]),
        (13, 'Chủ đề chung', 0, [
            (1, 'Các cuộc đại phát kiến địa lí', 166),
            (2, 'Đô thị: Lịch sử và hiện tại', 170),
        ]),
    ]),
    Course(subject='LSDL', grade=8, series=SERIES_KNTT, outline=[
        (1, 'Lịch sử – Chương 1. Châu Âu và Bắc Mỹ từ nửa sau thế kỉ XVI đến thế kỉ XVIII', 0, [
            (1, 'Cách mạng tư sản Anh và Chiến tranh giành độc lập của 13 thuộc địa Anh ở Bắc Mỹ', 8),
            (2, 'Cách mạng tư sản Pháp cuối thế kỉ XVIII', 12),
            (3, 'Cách mạng công nghiệp (nửa sau thế kỉ XVIII – giữa thế kỉ XIX)', 15),
        ]),
        (2, 'Lịch sử – Chương 2. Đông Nam Á từ nửa sau thế kỉ XVI đến giữa thế kỉ XIX', 0, [
            (4, 'Đông Nam Á từ nửa sau thế kỉ XVI đến giữa thế kỉ XIX', 19),
        ]),
        (3, 'Lịch sử – Chương 3. Việt Nam từ đầu thế kỉ XVI đến thế kỉ XVIII', 0, [
            (5, 'Cuộc xung đột Nam – Bắc triều và Trịnh – Nguyễn', 23),
            (6, 'Công cuộc khai phá vùng đất phía Nam từ thế kỉ XVI đến thế kỉ XVIII', 28),
            (7, 'Khởi nghĩa nông dân ở Đàng Ngoài thế kỉ XVIII', 31),
            (8, 'Phong trào Tây Sơn', 35),
            (9, 'Tình hình kinh tế, văn hoá, tôn giáo trong các thế kỉ XVI – XVIII', 42),
        ]),
        (4, 'Lịch sử – Chương 4. Châu Âu và nước Mỹ từ cuối thế kỉ XVIII đến đầu thế kỉ XX', 0, [
            (10, 'Sự hình thành chủ nghĩa đế quốc ở các nước Âu – Mỹ (cuối thế kỉ XIX – đầu thế kỉ XX)', 46),
            (11, 'Phong trào công nhân từ cuối thế kỉ XVIII đến đầu thế kỉ XX và sự ra đời của chủ nghĩa xã hội khoa học', 50),
            (12, 'Chiến tranh thế giới thứ nhất (1914 – 1918) và Cách mạng tháng Mười Nga năm 1917', 54),
        ]),
        (5, 'Lịch sử – Chương 5. Sự phát triển của khoa học, kĩ thuật, văn học, nghệ thuật trong các thế kỉ XVIII – XIX', 0, [
            (13, 'Sự phát triển của khoa học, kĩ thuật, văn học, nghệ thuật trong các thế kỉ XVIII – XIX', 58),
        ]),
        (6, 'Lịch sử – Chương 6. Châu Á từ nửa sau thế kỉ XIX đến đầu thế kỉ XX', 0, [
            (14, 'Trung Quốc và Nhật Bản từ nửa sau thế kỉ XIX đến đầu thế kỉ XX', 62),
            (15, 'Ấn Độ và Đông Nam Á từ nửa sau thế kỉ XIX đến đầu thế kỉ XX', 67),
        ]),
        (7, 'Lịch sử – Chương 7. Việt Nam từ thế kỉ XIX đến đầu thế kỉ XX', 0, [
            (16, 'Việt Nam dưới thời Nguyễn (nửa đầu thế kỉ XIX)', 71),
            (17, 'Cuộc kháng chiến chống thực dân Pháp xâm lược từ năm 1858 đến năm 1884', 77),
            (18, 'Phong trào chống Pháp trong những năm 1885 – 1896', 84),
            (19, 'Phong trào yêu nước chống Pháp ở Việt Nam từ đầu thế kỉ XX đến năm 1917', 88),
        ]),
        (8, 'Địa lí – Chương 1. Vị trí địa lí và phạm vi lãnh thổ, địa hình và khoáng sản Việt Nam', 0, [
            (1, 'Vị trí địa lí và phạm vi lãnh thổ Việt Nam', 95),
            (2, 'Địa hình Việt Nam', 99),
            (3, 'Khoáng sản Việt Nam', 111),
        ]),
        (9, 'Địa lí – Chương 2. Khí hậu và thuỷ văn Việt Nam', 0, [
            (4, 'Khí hậu Việt Nam', 115),
            (5, 'Thực hành: Đọc biểu đồ khí hậu', 120),
            (6, 'Thuỷ văn Việt Nam', 121),
            (7, 'Vai trò của tài nguyên khí hậu và tài nguyên nước đối với sự phát triển kinh tế – xã hội của nước ta', 128),
            (8, 'Tác động của biến đổi khí hậu đối với tự nhiên Việt Nam', 132),
        ]),
        (10, 'Địa lí – Chương 3. Thổ nhưỡng và sinh vật Việt Nam', 0, [
            (9, 'Thổ nhưỡng Việt Nam', 136),
            (10, 'Sinh vật Việt Nam', 143),
        ]),
        (11, 'Địa lí – Chương 4. Biển đảo Việt Nam', 0, [
            (11, 'Phạm vi Biển Đông. Vùng biển đảo và đặc điểm tự nhiên vùng biển đảo Việt Nam', 147),
            (12, 'Môi trường và tài nguyên biển đảo Việt Nam', 152),
        ]),
        (12, 'Chủ đề chung', 0, [
            (1, 'Văn minh châu thổ sông Hồng và sông Cửu Long', 155),
            (2, 'Bảo vệ chủ quyền, các quyền và lợi ích hợp pháp của Việt Nam ở Biển Đông', 162),
        ]),
    ]),
    # The Lịch sử and Địa lí parts share one page sequence but each restarts at Bài 1, and the three
    # "Chủ đề chung" units are numbered 1–3 on their own. Chapter titles carry the part, since the roadmap shows them as they are.
    Course(subject='LSDL', grade=9, series=SERIES_KNTT, outline=[
        (1, 'Lịch sử – Chương 1. Thế giới từ năm 1918 đến năm 1945', 0, [
            (1, 'Nước Nga và Liên Xô từ năm 1918 đến năm 1945', 7),
            (2, 'Châu Âu và nước Mỹ từ năm 1918 đến năm 1945', 10),
            (3, 'Châu Á từ năm 1918 đến năm 1945', 14),
            (4, 'Chiến tranh thế giới thứ hai (1939 – 1945)', 18),
        ]),
        (2, 'Lịch sử – Chương 2. Việt Nam từ năm 1918 đến năm 1945', 0, [
            (5, 'Phong trào dân tộc dân chủ trong những năm 1918 – 1930', 22),
            (6, 'Hoạt động của Nguyễn Ái Quốc và sự thành lập Đảng Cộng sản Việt Nam', 26),
            (7, 'Phong trào cách mạng Việt Nam thời kì 1930 – 1939', 30),
            (8, 'Cách mạng tháng Tám năm 1945', 34),
        ]),
        (3, 'Lịch sử – Chương 3. Thế giới từ năm 1945 đến năm 1991', 0, [
            (9, 'Chiến tranh lạnh (1947 – 1989)', 41),
            (10, 'Liên Xô và Đông Âu từ năm 1945 đến năm 1991', 44),
            (11, 'Nước Mỹ và Tây Âu từ năm 1945 đến năm 1991', 49),
            (12, 'Khu vực Mỹ La-tinh và châu Á từ năm 1945 đến năm 1991', 52),
        ]),
        (4, 'Lịch sử – Chương 4. Việt Nam từ năm 1945 đến năm 1975', 0, [
            (13, 'Việt Nam trong năm đầu sau Cách mạng tháng Tám năm 1945', 61),
            (14, 'Việt Nam kháng chiến chống thực dân Pháp xâm lược giai đoạn 1946 – 1950', 67),
            (15, 'Việt Nam kháng chiến chống thực dân Pháp xâm lược giai đoạn 1951 – 1954', 73),
            (16, 'Việt Nam kháng chiến chống Mỹ, cứu nước, thống nhất đất nước giai đoạn 1954 – 1965', 80),
            (17, 'Việt Nam kháng chiến chống Mỹ, cứu nước, thống nhất đất nước giai đoạn 1965 – 1975', 85),
        ]),
        (5, 'Lịch sử – Chương 5. Thế giới từ năm 1991 đến nay', 0, [
            (18, 'Trật tự thế giới mới từ năm 1991 đến nay. Liên bang Nga và nước Mỹ từ năm 1991 đến nay', 93),
            (19, 'Châu Á từ năm 1991 đến nay', 96),
        ]),
        (6, 'Lịch sử – Chương 6. Việt Nam từ năm 1976 đến nay', 0, [
            (20, 'Việt Nam từ năm 1976 đến nay', 101),
        ]),
        (7, 'Lịch sử – Chương 7. Cách mạng khoa học – kĩ thuật và xu thế toàn cầu hoá', 0, [
            (21, 'Cách mạng khoa học – kĩ thuật và xu thế toàn cầu hoá', 111),
        ]),
        (8, 'Địa lí – Chương 1. Địa lí dân cư Việt Nam', 0, [
            (1, 'Dân tộc và dân số', 117),
            (2, 'Phân bố dân cư và các loại hình quần cư', 120),
            (3, 'Lao động và việc làm', 123),
            (4, 'Thực hành: Tìm hiểu vấn đề việc làm ở địa phương và phân hoá thu nhập theo vùng', 127),
        ]),
        (9, 'Địa lí – Chương 2. Địa lí các ngành kinh tế', 0, [
            (5, 'Nông nghiệp', 129),
            (6, 'Lâm nghiệp và thuỷ sản', 136),
            (7, 'Thực hành: Viết báo cáo về một mô hình sản xuất nông nghiệp có hiệu quả', 141),
            (8, 'Công nghiệp', 142),
            (9, 'Thực hành: Xác định một số hình thức tổ chức lãnh thổ công nghiệp ở nước ta', 151),
            (10, 'Dịch vụ', 152),
            (11, 'Thực hành: Tìm hiểu xu hướng phát triển ngành thương mại, du lịch', 157),
        ]),
        (10, 'Địa lí – Chương 3. Địa lí các vùng kinh tế – xã hội', 0, [
            (12, 'Vùng Trung du và miền núi phía Bắc', 158),
            (13, 'Vùng Đồng bằng sông Hồng', 166),
            (14, 'Vùng Bắc Trung Bộ', 176),
            (15, 'Thực hành: Tìm hiểu vấn đề phòng, chống thiên tai và ứng phó với biến đổi khí hậu ở vùng Bắc Trung Bộ', 185),
            (16, 'Vùng Duyên hải Nam Trung Bộ và Tây Nguyên', 186),
            (17, 'Vùng Đông Nam Bộ', 195),
            (18, 'Thực hành: Phân tích ý nghĩa của việc tăng cường kết nối liên vùng đối với sự phát triển của vùng Đông Nam Bộ', 204),
            (19, 'Vùng Đồng bằng sông Cửu Long', 205),
            (20, 'Thực hành: Tìm hiểu về tác động của biến đổi khí hậu đối với vùng Đồng bằng sông Cửu Long', 213),
            (21, 'Phát triển tổng hợp kinh tế và bảo vệ tài nguyên, môi trường biển, đảo', 214),
        ]),
        (11, 'Chủ đề chung', 0, [
            (1, 'Đô thị: Lịch sử và hiện tại', 221),
            (2, 'Văn minh châu thổ sông Hồng và sông Cửu Long', 225),
            (3, 'Bảo vệ chủ quyền, các quyền và lợi ích hợp pháp của Việt Nam ở Biển Đông', 230),
        ]),
    ]),
]


# Subject codes as they appear in PDF file names, longest first so "lsdl" wins over "ls".
_FILENAME_SUBJECTS: list[tuple[str, str]] = [
    ('khtn', 'KHTN'),
    ('lsdl', 'LSDL'),
    ('toan', 'Toán'),
    ('nv', 'Ngữ văn'),
    ('ta', 'Tiếng Anh'),
]


def parse_book_filename(source: Any) -> tuple[str, int, int] | None:
    """(subject, grade, volume) read from a file name like "TOAN7 - TAP 1.pdf".

    Keeps the catalog working when the same book is re-saved under another spelling, which
    happens every time a new batch of scans is dropped into backend/data.
    """
    key = _fold(str(source or '').replace('\\', '/').rsplit('/', 1)[-1])
    if not key:
        return None
    key = re.sub(r'\.pdf$', '', key)

    subject = next((name for code, name in _FILENAME_SUBJECTS if key.startswith(code)), None)
    if subject is None:
        return None

    grade_match = re.search(r'([6-9])', key)
    if grade_match is None:
        return None
    grade = int(grade_match.group(1))

    volume_match = re.search(r'tap\s*([12])', key)
    volume = int(volume_match.group(1)) if volume_match else 0

    return subject, grade, volume


def find_book(source: Any) -> Book | None:
    """Book for a PDF file name as stored in Pinecone metadata or passed in a preview link."""
    key = _fold(str(source or '').replace('\\', '/').rsplit('/', 1)[-1])
    if not key:
        return None
    exact = next((book for book in BOOKS if key in (_fold(name) for name in book.files)), None)
    if exact is not None:
        return exact

    # No alias matched: fall back to what the file name says it is.
    parsed = parse_book_filename(source)
    if parsed is None:
        return None
    subject, grade, volume = parsed
    return next(
        (book for book in BOOKS if book.subject == subject and book.grade == grade and book.volume == volume),
        None,
    )


def find_course(subject: Any, grade: Any) -> Course | None:
    try:
        grade_value = int(grade)
    except (TypeError, ValueError):
        return None
    canonical = canonical_subject(subject)
    return next((course for course in COURSES if course.subject == canonical and course.grade == grade_value), None)


def course_book(course: Course, volume: int) -> Book | None:
    return next((book for book in BOOKS if book.subject == course.subject and book.grade == course.grade and book.volume == volume), None)


def _page_range(course: Course, lesson: Lesson) -> tuple[int, int] | None:
    """Printed pages [start, end] of a lesson that exist in the PDF we have."""
    book = course_book(course, lesson.volume)
    if book is None or lesson.page is None or (book.last_page is not None and lesson.page > book.last_page):
        return None
    later = [item.page for item in course.lessons() if item.volume == lesson.volume and item.page and item.page > lesson.page]
    end = min(later) - 1 if later else (book.last_page or lesson.page + 3)
    if book.last_page is not None:
        end = min(end, book.last_page)
    return lesson.page, max(lesson.page, end)


def lesson_at(book: Book, pdf_page: int) -> Lesson | None:
    """The lesson a PDF page belongs to (the last lesson starting at or before that printed page)."""
    course = find_course(book.subject, book.grade)
    if course is None:
        return None
    printed = pdf_page + book.page_offset
    candidates = [item for item in course.lessons() if item.volume == book.volume and item.page is not None and item.page <= printed]
    # Where two sections start on one page, the later one (the reading text, not the Củng cố above it) wins.
    return max(reversed(candidates), key=lambda item: item.page) if candidates else None


def find_lesson(subject: Any, grade: Any, topic: Any) -> tuple[Course, Lesson] | None:
    """Match a roadmap lesson title ("Tập hợp", "Bài 1: Tập hợp") to the catalog."""
    course = find_course(subject, grade)
    if course is None or not str(topic or '').strip():
        return None
    number = re.match(r'^\s*bài\s*(\d+)', str(topic), flags=re.IGNORECASE)
    wanted = _fold(re.sub(r'^\s*bài\s*\d+\s*[:.\-–]?\s*', '', str(topic), flags=re.IGNORECASE))
    for lesson in course.lessons():
        if _fold(lesson.title) == wanted and (number is None or int(number.group(1)) == course.book_unit(lesson)):
            return course, lesson
    return None


def lesson_page_filter(subject: Any, grade: Any, topic: Any) -> dict[str, Any] | None:
    """Pinecone filter restricting a search to the pages of one lesson (stored `page` is the PDF page)."""
    found = find_lesson(subject, grade, topic)
    if found is None:
        return None
    course, lesson = found
    pages = _page_range(course, lesson)
    book = course_book(course, lesson.volume)
    if pages is None or book is None:
        return None
    start, end = pages
    return {
        'source': {'$in': list(book.files)},
        'page': {'$gte': start - book.page_offset, '$lte': end - book.page_offset},
    }


def enrich_match(payload: dict[str, Any]) -> dict[str, Any]:
    """Replace unreliable ingested metadata (lesson, chapter, page offset, subject name) with the catalog's."""
    book = find_book(payload.get('source'))
    pdf_page = payload.get('pdf_page')
    if book is None or pdf_page is None:
        return payload
    payload.update({
        'subject': book.subject,
        'grade': book.grade,
        'volume': book.volume,
        'page_offset': book.page_offset,
        'page': pdf_page + book.page_offset,
        'book_title': book.title,
    })
    lesson = lesson_at(book, pdf_page)
    course = find_course(book.subject, book.grade)
    if lesson is not None and course is not None:
        payload.update({
            'chapter': lesson.chapter,
            'lesson': lesson.lesson,
            'title': lesson.title,
            'lesson_title': course.label(lesson, '. '),
        })
    return payload


def build_catalog_roadmap(subject: Any, grade: Any) -> dict[str, Any] | None:
    """Roadmap straight from the textbook's table of contents; None when the catalog has no book for it."""
    course = find_course(subject, grade)
    if course is None:
        return None
    chapters = []
    for chapter_no, chapter_title, volume, _ in course.outline:
        book = course_book(course, volume)
        lessons = []
        for lesson in (item for item in course.lessons() if item.chapter == chapter_no):
            pages = _page_range(course, lesson)
            lessons.append({
                'id': f'lesson_{chapter_no}_{lesson.lesson}',
                'lesson': lesson.lesson,
                'title': lesson.title,
                # The frontend shows and stores this as the student's current lesson.
                'label': course.label(lesson),
                'volume': volume,
                'status': 'locked',
                'progress': 0,
                'sources': [{'source': book.title, 'page': pages[0]}] if pages and book else [],
            })
        chapters.append({'id': f'chapter_{chapter_no}', 'chapter': chapter_no, 'title': chapter_title, 'lessons': lessons})
    slug = re.sub(r'[^a-z0-9]+', '_', _fold(course.subject)).strip('_')
    return {
        'id': f'{slug}_{course.grade}',
        'subject': course.subject,
        'grade': course.grade,
        'title': f'Lộ trình {course.subject} {course.grade}',
        'series': course.series,
        'progress': 0,
        'source': 'rag',
        'chapters': chapters,
    }


def resolve_book_file(source: Any, data_dir: Any) -> Any:
    """The PDF in data_dir for a source name, following the catalog's aliases (e.g. "KHTN 6.pdf" -> "KHTN.pdf")."""
    from pathlib import Path

    directory = Path(data_dir)
    book = find_book(source)
    names = list(book.files) if book else [Path(str(source)).name]
    available = {_fold(path.name): path for path in directory.glob('*.pdf')}
    return next((available[_fold(name)] for name in names if _fold(name) in available), None)
