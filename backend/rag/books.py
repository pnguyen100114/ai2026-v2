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

    def lessons(self) -> list[Lesson]:
        return [
            Lesson(chapter=chapter, chapter_title=chapter_title, lesson=number, title=title, volume=volume, page=page)
            for chapter, chapter_title, volume, lessons in self.outline
            for number, title, page in lessons
        ]


# `page_offset` is printed page - PDF page; it was measured from the folio numbers in each scan
# and falls back to -1 (one cover page) where the folios were not extractable.
# `last_page` is only for partial scans that stop mid-book; a complete PDF leaves it None.
BOOKS: list[Book] = [
    # --- Toán ---
    Book(id='toan6-tap1', subject='Toán', grade=6, volume=1, title='Toán 6 – Tập một',
         files=('TOAN6 -TAP 1.pdf', 'TOAN -TAP 1.pdf', 'toan6-tap1.pdf'), page_offset=-1, last_page=62),
    Book(id='toan6-tap2', subject='Toán', grade=6, volume=2, title='Toán 6 – Tập hai',
         files=('TOAN6-TAP 2.pdf',), page_offset=-1),
    Book(id='toan7-tap1', subject='Toán', grade=7, volume=1, title='Toán 7 – Tập một',
         files=('TOAN7 - TAP 1.pdf',), page_offset=-1),
    Book(id='toan7-tap2', subject='Toán', grade=7, volume=2, title='Toán 7 – Tập hai',
         files=('TOAN7- TAP 2.pdf',), page_offset=-1),
    Book(id='toan8-tap1', subject='Toán', grade=8, volume=1, title='Toán 8 – Tập một',
         files=('TOAN8-Tap1.pdf', 'toan8-tap1.pdf'), page_offset=-1, last_page=37),
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
         files=('NV8-Tap2.pdf',), page_offset=-1),
    Book(id='nv9-tap1', subject='Ngữ văn', grade=9, volume=1, title='Ngữ văn 9 – Tập một',
         files=('NV9-Tap1.pdf',), page_offset=0),
    Book(id='nv9-tap2', subject='Ngữ văn', grade=9, volume=2, title='Ngữ văn 9 – Tập hai',
         files=('NV9-Tap2.pdf',), page_offset=-1),

    # --- Tiếng Anh (Global Success) ---
    Book(id='ta6-tap1', subject='Tiếng Anh', grade=6, volume=1, title='Tiếng Anh 6 – Tập một',
         files=('TA6 -TAP 1.pdf',), page_offset=-1),
    Book(id='ta6-tap2', subject='Tiếng Anh', grade=6, volume=2, title='Tiếng Anh 6 – Tập hai',
         files=('TA6 -TAP 2.pdf',), page_offset=-1),
    Book(id='ta7', subject='Tiếng Anh', grade=7, volume=0, title='Tiếng Anh 7',
         files=('TA7.pdf',), page_offset=-1),
    Book(id='ta8', subject='Tiếng Anh', grade=8, volume=0, title='Tiếng Anh 8',
         files=('TA8.pdf',), page_offset=-1),
    Book(id='ta9', subject='Tiếng Anh', grade=9, volume=0, title='Tiếng Anh 9',
         files=('TA9.pdf',), page_offset=-1),

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
         files=('LSDL 8.pdf',), page_offset=-1),
    Book(id='lsdl9', subject='LSDL', grade=9, volume=0, title='Lịch sử và Địa lí 9',
         files=('LSDL 9.pdf',), page_offset=-1),
]

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
            (13, 'Tập hợp các số nguyên', 57), (14, 'Phép cộng và phép trừ số nguyên', 62), (15, 'Quy tắc dấu ngoặc', 66),
            (16, 'Phép nhân số nguyên', 70), (17, 'Phép chia hết. Ước và bội của một số nguyên', 73),
        ]),
        (4, 'Một số hình phẳng trong thực tiễn', 1, [
            (18, 'Hình tam giác đều. Hình vuông. Hình lục giác đều', 77),
            (19, 'Hình chữ nhật. Hình thoi. Hình bình hành. Hình thang cân', 82),
            (20, 'Chu vi và diện tích của một số tứ giác đã học', 90),
        ]),
        (5, 'Tính đối xứng của hình phẳng trong tự nhiên', 1, [
            (21, 'Hình có trục đối xứng', 98), (22, 'Hình có tâm đối xứng', 103),
        ]),
        (6, 'Phân số', 2, [
            (23, 'Mở rộng phân số. Phân số bằng nhau', None), (24, 'So sánh phân số. Hỗn số dương', None),
            (25, 'Phép cộng và phép trừ phân số', None), (26, 'Phép nhân và phép chia phân số', None),
            (27, 'Hai bài toán về phân số', None),
        ]),
        (7, 'Số thập phân', 2, [
            (28, 'Số thập phân', None), (29, 'Tính toán với số thập phân', None), (30, 'Làm tròn và ước lượng', None),
            (31, 'Một số bài toán về tỉ số và tỉ số phần trăm', None),
        ]),
        (8, 'Những hình hình học cơ bản', 2, [
            (32, 'Điểm và đường thẳng', None), (33, 'Điểm nằm giữa hai điểm. Tia', None),
            (34, 'Đoạn thẳng. Độ dài đoạn thẳng', None), (35, 'Trung điểm của đoạn thẳng', None),
            (36, 'Góc', None), (37, 'Số đo góc', None),
        ]),
        (9, 'Dữ liệu và xác suất thực nghiệm', 2, [
            (38, 'Dữ liệu và thu thập dữ liệu', None), (39, 'Bảng thống kê và biểu đồ tranh', None),
            (40, 'Biểu đồ cột', None), (41, 'Biểu đồ cột kép', None),
            (42, 'Kết quả có thể và sự kiện trong trò chơi, thí nghiệm', None), (43, 'Xác suất thực nghiệm', None),
        ]),
    ]),
    Course(subject='Toán', grade=8, series=SERIES_KNTT, outline=[
        (1, 'Đa thức', 1, [
            (1, 'Đơn thức', 5), (2, 'Đa thức', 11), (3, 'Phép cộng và phép trừ đa thức', 15),
            (4, 'Phép nhân đa thức', 19), (5, 'Phép chia đa thức cho đơn thức', 22),
        ]),
        (2, 'Hằng đẳng thức đáng nhớ và ứng dụng', 1, [
            (6, 'Hiệu hai bình phương. Bình phương của một tổng hay một hiệu', 29),
            (7, 'Lập phương của một tổng. Lập phương của một hiệu', 34),
            (8, 'Tổng và hiệu hai lập phương', 37), (9, 'Phân tích đa thức thành nhân tử', None),
        ]),
        (3, 'Tứ giác', 1, [
            (10, 'Tứ giác', None), (11, 'Hình thang cân', None), (12, 'Hình bình hành', None),
            (13, 'Hình chữ nhật', None), (14, 'Hình thoi và hình vuông', None),
        ]),
        (4, 'Định lí Thalès', 1, [
            (15, 'Định lí Thalès trong tam giác', None), (16, 'Đường trung bình của tam giác', None),
            (17, 'Tính chất đường phân giác của tam giác', None),
        ]),
        (5, 'Dữ liệu và biểu đồ', 1, [
            (18, 'Thu thập và phân loại dữ liệu', None), (19, 'Biểu diễn dữ liệu bằng bảng, biểu đồ', None),
            (20, 'Phân tích số liệu thống kê dựa vào biểu đồ', None),
        ]),
        (6, 'Phân thức đại số', 2, [
            (21, 'Phân thức đại số', None), (22, 'Tính chất cơ bản của phân thức đại số', None),
            (23, 'Phép cộng và phép trừ phân thức đại số', None), (24, 'Phép nhân và phép chia phân thức đại số', None),
        ]),
        (7, 'Phương trình bậc nhất và hàm số bậc nhất', 2, [
            (25, 'Phương trình bậc nhất một ẩn', None), (26, 'Giải bài toán bằng cách lập phương trình', None),
            (27, 'Khái niệm hàm số và đồ thị của hàm số', None), (28, 'Hàm số bậc nhất và đồ thị của hàm số bậc nhất', None),
            (29, 'Hệ số góc của đường thẳng', None),
        ]),
        (8, 'Mở đầu về tính xác suất của biến cố', 2, [
            (30, 'Kết quả có thể và kết quả thuận lợi', None), (31, 'Cách tính xác suất của biến cố bằng tỉ số', None),
            (32, 'Mối liên hệ giữa xác suất thực nghiệm với xác suất và ứng dụng', None),
        ]),
        (9, 'Tam giác đồng dạng', 2, [
            (33, 'Hai tam giác đồng dạng', None), (34, 'Ba trường hợp đồng dạng của hai tam giác', None),
            (35, 'Định lí Pythagore và ứng dụng', None), (36, 'Các trường hợp đồng dạng của hai tam giác vuông', None),
            (37, 'Hình đồng dạng', None),
        ]),
        (10, 'Một số hình khối trong thực tiễn', 2, [
            (38, 'Hình chóp tam giác đều', None), (39, 'Hình chóp tứ giác đều', None),
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
    return max(candidates, key=lambda item: item.page) if candidates else None


def find_lesson(subject: Any, grade: Any, topic: Any) -> tuple[Course, Lesson] | None:
    """Match a roadmap lesson title ("Tập hợp", "Bài 1: Tập hợp") to the catalog."""
    course = find_course(subject, grade)
    if course is None or not str(topic or '').strip():
        return None
    number = re.match(r'^\s*bài\s*(\d+)', str(topic), flags=re.IGNORECASE)
    wanted = _fold(re.sub(r'^\s*bài\s*\d+\s*[:.\-–]?\s*', '', str(topic), flags=re.IGNORECASE))
    for lesson in course.lessons():
        if _fold(lesson.title) == wanted and (number is None or int(number.group(1)) == lesson.lesson):
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
    if lesson is not None:
        payload.update({
            'chapter': lesson.chapter,
            'lesson': lesson.lesson,
            'title': lesson.title,
            'lesson_title': f'Bài {lesson.lesson}. {lesson.title}',
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
