import os
import hashlib
import json
import re
import sys
import time
import uuid

from pathlib import Path
from dotenv import load_dotenv
from pypdf import PdfReader
from pinecone import Pinecone

try:
    from backend.rag.books import find_book, find_course, lesson_at
    from backend.rag.embeddings import DailyQuotaExhausted, cache_size, create_embeddings
except ImportError:  # pragma: no cover
    from books import find_book, find_course, lesson_at
    from embeddings import DailyQuotaExhausted, cache_size, create_embeddings


# ==========================================
# LOAD ENV
# ==========================================

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / '.env')

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX")

PINECONE_NAMESPACE = os.getenv(
    "PINECONE_NAMESPACE"
) or ""

EMBEDDING_DIMENSION = int(
    os.getenv("EMBEDDING_DIMENSION", "1536")
)
BOOK_PAGE_OFFSETS = json.loads(os.getenv('BOOK_PAGE_OFFSETS', '{}') or '{}')

# Bigger chunks than the original 1000/150: ~40% fewer vectors for the same book, and a
# 1800-character window holds a whole SGK section instead of half of one.
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

# Which books are already on Pinecone. Kept on disk on purpose: the old check ran a Pinecone
# query per file, and reads are what exhaust the free tier's 1 GB/month egress.
MANIFEST_PATH = Path(
    os.getenv("INGEST_MANIFEST_PATH", "")
    or Path(__file__).resolve().parent / ".ingest_manifest.json"
)


# ==========================================
# CHECK ENV
# ==========================================

if not PINECONE_API_KEY:
    raise ValueError(
        "Chưa có PINECONE_API_KEY trong .env"
    )

if not PINECONE_INDEX:
    raise ValueError(
        "Chưa có PINECONE_INDEX trong .env"
    )


# ==========================================
# PINECONE
# ==========================================

pc = Pinecone(
    api_key=PINECONE_API_KEY
)

index = pc.Index(
    PINECONE_INDEX
)


# ==========================================
# PROJECT PATH
# ==========================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

DATA_DIR = BASE_DIR / "data"


# ==========================================
# SAFE PINECONE ID
# ==========================================

def make_safe_id(text):
    """
    Pinecone chỉ cho phép ID chứa ASCII.

    Ví dụ:
    LSĐL_8_1_2_0_abc123
    ->
    LSDL_8_1_2_0_abc123
    """

    text = str(text)

    # Xử lý Đ / đ
    text = text.replace("Đ", "D")
    text = text.replace("đ", "d")

    # Chỉ giữ:
    # A-Z
    # a-z
    # 0-9
    # _
    # -
    text = re.sub(
        r"[^A-Za-z0-9_-]",
        "_",
        text
    )

    return text


# ==========================================
# STRIP WATERMARKS
# ==========================================

# Lines every page of a re-shared scan carries. Some PDFs in backend/data are image-only and
# the watermark is the ONLY text pypdf can extract, so without this they would upload hundreds
# of identical junk chunks. retriever.py used to filter these at query time, which is too late:
# the vectors are already stored and already competing with real content for top_k slots.
WATERMARK_PATTERNS = [
    r"https?://\S*blogtailieu\S*",
    r"\bblogtailieu\.com\S*",
    r"S[áa]ch\s+chia\s+s[ẻe]\s+t[ạa]i\b.*",
    r"\bgiao-an-lop-\d+\b",
    r"\bday-va-hoc\b",
]

# A page holding less than this many real characters is a cover, a photo or watermark-only.
MIN_PAGE_CHARS = int(os.getenv("MIN_PAGE_CHARS", "120"))


def strip_watermarks(text):
    """Remove re-sharing watermarks so they never reach an embedding."""
    for pattern in WATERMARK_PATTERNS:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)

    return re.sub(r"[ \t]+", " ", text)


# ==========================================
# CHUNK TEXT
# ==========================================

def split_text(
    text,
    chunk_size=None,
    overlap=None
):

    chunk_size = CHUNK_SIZE if chunk_size is None else chunk_size

    overlap = CHUNK_OVERLAP if overlap is None else overlap

    text = text.replace(
        "\r\n",
        "\n"
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    text = text.strip()

    if not text:
        return []

    chunks = []

    start = 0

    while start < len(text):

        end = min(
            start + chunk_size,
            len(text)
        )

        chunk = text[
            start:end
        ].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = end - overlap

    return chunks


# ==========================================
# DETECT SUBJECT
# ==========================================

def detect_subject(filename):

    name = filename.lower()

    # TOÁN
    if "toan" in name:
        return "Toán"

    # NGỮ VĂN
    if (
        "nguvan" in name
        or "ngu-van" in name
        or "ngu van" in name
        or name.startswith("nv")
    ):
        return "Ngữ văn"

    # TIẾNG ANH
    if (
        "tienganh" in name
        or "tieng-anh" in name
        or "tieng anh" in name
        or name.startswith("ta")
    ):
        return "Tiếng Anh"

    # KHOA HỌC TỰ NHIÊN
    if (
        "khtn" in name
        or "khoa-hoc-tu-nhien" in name
        or "khoa hoc tu nhien" in name
    ):
        return "KHTN"

    # LỊCH SỬ VÀ ĐỊA LÍ
    if (
        "lsdl" in name
        or "lsđl" in name
        or "lichsu" in name
        or "lich-su" in name
        or "dia li" in name
        or "diali" in name
        or "dia-li" in name
    ):
        return "LSDL"

    return "Không xác định"


# ==========================================
# DETECT GRADE
# ==========================================

def detect_grade(filename):

    name = filename.lower()

    patterns = [

        r"toan\s*[-_ ]?([6789])",

        r"ta\s*[-_ ]?([6789])",

        r"nv\s*[-_ ]?([6789])",

        r"anh\s*[-_ ]?([6789])",

        r"khtn\s*[-_ ]?([6789])",

        r"lsdl\s*[-_ ]?([6789])",

        r"lop\s*[-_ ]?([6789])"

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            name
        )

        if match:

            return int(
                match.group(1)
            )

    return 0


# ==========================================
# DETECT VOLUME
# ==========================================

def detect_volume(filename):

    name = filename.lower()

    if (
        "tap1" in name
        or "tap 1" in name
        or "tập1" in name
        or "tập 1" in name
    ):

        return 1

    if (
        "tap2" in name
        or "tap 2" in name
        or "tập2" in name
        or "tập 2" in name
    ):

        return 2

    return 0


def detect_book_type(filename):
    name = filename.lower()
    if 'nangcao' in name or 'nang-cao' in name or 'nâng cao' in name:
        return 'nang_cao'
    if 'sbt' in name or 'bai tap' in name or 'bài tập' in name:
        return 'sbt'
    return 'sgk'


def get_page_offset(filename):
    return int(BOOK_PAGE_OFFSETS.get(filename, 0))


# ==========================================
# DETECT CHAPTER
# ==========================================

def detect_chapter(text):

    patterns = [

        r"Chương\s+(\d+)",

        r"CHƯƠNG\s+(\d+)",

        r"Chương\s+([IVXLCDM]+)",

        r"CHƯƠNG\s+([IVXLCDM]+)"

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text
        )

        if match:

            chapter_value = match.group(1)
            if chapter_value.isdigit():
                return int(chapter_value)

            roman_values = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
            total = 0
            previous = 0
            for symbol in reversed(chapter_value.upper()):
                value = roman_values[symbol]
                total += -value if value < previous else value
                previous = max(previous, value)
            return total

    return 0


# ==========================================
# DETECT LESSON
# ==========================================

def detect_lesson(text):

    patterns = [

        r"Bài\s+(\d+)",

        r"BÀI\s+(\d+)"

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text
        )

        if match:

            return int(
                match.group(1)
            )

    return 0


# ==========================================
# READ PDF
# ==========================================

def read_pdf(pdf_path):

    print()

    print("--------------------------------------")

    print(
        "Đang đọc:",
        pdf_path.name
    )

    print("--------------------------------------")

    reader = PdfReader(
        str(pdf_path)
    )

    pages = []

    for page_number, page in enumerate(
        reader.pages,
        start=1
    ):

        try:

            text = page.extract_text()

        except Exception:

            text = ""

        if text is None:

            text = ""

        pages.append({

            "page": page_number,

            "text": text

        })

    return pages


# ==========================================
# CREATE RECORDS
# ==========================================

def create_records(pdf_path):

    subject = detect_subject(
        pdf_path.name
    )

    grade = detect_grade(
        pdf_path.name
    )

    volume = detect_volume(
        pdf_path.name
    )
    book_type = detect_book_type(pdf_path.name)
    page_offset = get_page_offset(pdf_path.name)

    # Books in backend/rag/books.py: subject, grade, pages and lessons come from the catalog, not the file name.
    book = find_book(pdf_path.name)
    if book is not None:
        subject, grade, volume, page_offset = book.subject, book.grade, book.volume, book.page_offset

    course = find_course(book.subject, book.grade) if book is not None else None

    # Printed pages the MỤC LỤC knows about for THIS volume. A course can cover both volumes
    # while only one of them has page numbers (the other's are None), and lesson_at() then
    # matches nothing - filtering on it would drop every page of that volume.
    outline_pages = [
        item.page for item in course.lessons()
        if course is not None and item.volume == book.volume and item.page is not None
    ] if course is not None else []

    print()

    print("Thông tin PDF:")

    print(
        "  Subject:",
        subject
    )

    print(
        "  Grade:",
        grade
    )

    print(
        "  Volume:",
        volume
    )

    pages = read_pdf(
        pdf_path
    )

    # Only filter by the outline when it actually covers this PDF. A scan often gets replaced by
    # a longer one while the catalog still holds the old partial book's pages; trusting a stale
    # outline then silently drops most of the book (Toán 8 tập 1: 88 of 125 printed pages).
    printed_last = len(pages) + (book.page_offset if book is not None else 0)
    outline_last = max(outline_pages) if outline_pages else 0
    covered = min(outline_last, book.last_page or outline_last) if book is not None else 0
    has_outline = bool(outline_pages) and covered >= printed_last * 0.7

    if outline_pages and not has_outline:
        print(
            f"  ⚠ Mục lục chỉ có tới trang {outline_last} (last_page={book.last_page}) "
            f"trong khi sách in tới trang {printed_last} → nạp cả quyển, không lọc theo mục lục."
        )

    records = []

    skipped_pages = 0

    current_chapter = 0

    current_lesson = 0

    for page_data in pages:

        page_number = page_data[
            "page"
        ]

        text = strip_watermarks(
            page_data["text"]
        )

        # Image-only scans extract nothing but the watermark, so what is left is empty here.
        if len(text.strip()) < MIN_PAGE_CHARS:

            skipped_pages += 1

            continue

        # Bìa, lời nói đầu, mục lục (trước bài đầu tiên), trang quảng cáo bộ sách ở cuối: không phải nội dung bài học.
        # Chỉ lọc được khi sách đã có MỤC LỤC trong catalog; sách mới chưa có thì nạp cả quyển
        # (nếu lọc theo lesson_at khi chưa có mục lục thì mọi trang đều bị bỏ, ra 0 chunk).
        if book is not None and has_outline:

            printed_page = page_number + book.page_offset

            if lesson_at(book, page_number) is None or (book.last_page is not None and printed_page > book.last_page):

                continue

        # ------------------------------
        # DETECT CHAPTER
        # ------------------------------

        detected_chapter = detect_chapter(
            text
        )

        if detected_chapter:

            current_chapter = (
                detected_chapter
            )

        # ------------------------------
        # DETECT LESSON
        # ------------------------------

        detected_lesson = detect_lesson(
            text
        )

        if detected_lesson:

            current_lesson = (
                detected_lesson
            )

        # Only trust the catalog's lesson when its outline covers this book. With a stale partial
        # outline, lesson_at() returns the last lesson it knows for every page past its end, which
        # would label the whole rest of the book as that one lesson.
        catalog_lesson = lesson_at(book, page_number) if (book is not None and has_outline) else None

        if catalog_lesson is not None:

            current_chapter = catalog_lesson.chapter

            current_lesson = catalog_lesson.lesson

        # ------------------------------
        # SPLIT CHUNK
        # ------------------------------

        chunks = split_text(
            text
        )

        # ------------------------------
        # CREATE RECORD
        # ------------------------------

        for chunk_index, chunk in enumerate(
            chunks
        ):

            # ID gốc: sách trong danh mục có ID cố định nên nạp lại sẽ ghi đè, không nhân đôi
            raw_id = (

                f"{book.id}-p{page_number}-c{chunk_index}"

            ) if book is not None else (

                f"{subject}_"

                f"{grade}_"

                f"{volume}_"

                f"{page_number}_"

                f"{chunk_index}_"

                f"{uuid.uuid4().hex[:8]}"

            )

            # Chuyển thành ID ASCII
            record_id = make_safe_id(
                raw_id
            )

            metadata = {

                "subject":
                    subject,

                "grade":
                    grade,

                "volume":
                    volume,

                "chapter":
                    current_chapter,

                "lesson":
                    current_lesson,

                "page":
                    page_number,

                "page_offset":
                    page_offset,

                "book_type":
                    book_type,

                "title":
                    catalog_lesson.title if catalog_lesson is not None else pdf_path.stem.replace("-", " ").replace("_", " "),

                "book_title":
                    book.title if book is not None else pdf_path.stem,

                "source":
                    pdf_path.name,

                "content_type":
                    "theory",

                "text":
                    chunk

            }

            records.append({

                "id":
                    record_id,

                "text":
                    chunk,

                "metadata":
                    metadata

            })

    # A scan that is really just images: pypdf finds a watermark and nothing else on every page.
    if skipped_pages and skipped_pages >= len(pages) * 0.8:

        print(
            f"  ⚠ {skipped_pages}/{len(pages)} trang không có chữ thật "
            f"(PDF là bản scan ảnh hoặc chỉ có watermark) → quyển này cần OCR hoặc bản PDF khác."
        )

    return records


# ==========================================
# UPLOAD TO PINECONE
# ==========================================

def upload_records(records):

    # 100 vectors ~ 800 KB, well inside Pinecone's 2 MB request limit.
    batch_size = int(os.getenv("UPSERT_BATCH_SIZE", "100"))

    total = len(records)

    print()

    print(
        "Tổng số chunks:",
        total
    )

    for start in range(

        0,

        total,

        batch_size

    ):

        batch = records[
            start:start + batch_size
        ]

        texts = [

            record["text"]

            for record in batch

        ]

        print()

        print(
            "Gemini đang tạo embedding:",
            start + 1,
            "->",
            min(
                start + batch_size,
                total
            )
        )

        # ------------------------------
        # CREATE EMBEDDINGS
        # ------------------------------

        vectors = create_embeddings(
            texts
        )

        if len(vectors) != len(batch):

            raise RuntimeError(

                "Số embedding không khớp "
                "số chunks."

            )

        pinecone_vectors = []

        # ------------------------------
        # BUILD PINECONE VECTORS
        # ------------------------------

        for i, record in enumerate(
            batch
        ):

            vector = vectors[i]

            if len(vector) != EMBEDDING_DIMENSION:

                raise RuntimeError(

                    f"Embedding dimension sai: "

                    f"{len(vector)}. "

                    f"Expected: "

                    f"{EMBEDDING_DIMENSION}"

                )

            # Kiểm tra ID
            safe_id = make_safe_id(
                record["id"]
            )

            pinecone_vectors.append({

                "id":
                    safe_id,

                "values":
                    vector,

                "metadata":
                    record["metadata"]

            })

        # ------------------------------
        # UPLOAD
        # ------------------------------

        print(
            "Đang upload vào Pinecone..."
        )

        index.upsert(

            vectors=pinecone_vectors,

            namespace=PINECONE_NAMESPACE

        )

        print(
            "✓ Đã upload batch"
        )

        print(
            f"  Progress: "
            f"{min(start + batch_size, total)}"
            f"/{total}"
        )


def load_manifest():
    """{book key: {chunks, model, dimension, chunk_size, ingested_at}} of what is already uploaded."""
    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_manifest(manifest):
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def manifest_key(filename):
    """One key per book, so re-running under a file alias does not upload it twice."""
    book = find_book(filename)
    return book.id if book is not None else Path(filename).name


def file_fingerprint(pdf_path):
    """Cheap content fingerprint: size plus the head and tail of the file.

    Books get re-scanned and re-saved under new names, and a book id alone cannot tell that
    the PDF behind it changed - which would make ingest skip a book that never went up.
    """
    path = Path(pdf_path)

    try:
        size = path.stat().st_size
    except OSError:
        return ''

    digest = hashlib.sha256(str(size).encode())

    with path.open('rb') as handle:
        digest.update(handle.read(1 << 20))
        if size > (2 << 20):
            handle.seek(-(1 << 20), os.SEEK_END)
            digest.update(handle.read(1 << 20))

    return digest.hexdigest()[:32]


def already_ingested(pdf_path):
    """True when the local manifest says this exact PDF is on Pinecone with the current settings.

    Deliberately reads no data from Pinecone: the previous version ran a query per file, and
    on the free tier reads are metered (1 GB/month) while writes are not. When that budget ran
    out every ingest died with 429 before uploading anything.
    """
    entry = load_manifest().get(manifest_key(Path(pdf_path).name))

    if not entry:
        return False

    # Anything that changes the vectors - a different scan, model, dimension or chunk size -
    # means this book has to be built again.
    return (
        entry.get("fingerprint") == file_fingerprint(pdf_path)
        and entry.get("model") == os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
        and int(entry.get("dimension", 0)) == EMBEDDING_DIMENSION
        and int(entry.get("chunk_size", 0)) == CHUNK_SIZE
    )


def record_ingested(pdf_path, chunk_count):
    manifest = load_manifest()

    manifest[manifest_key(Path(pdf_path).name)] = {
        "file": Path(pdf_path).name,
        "fingerprint": file_fingerprint(pdf_path),
        "chunks": chunk_count,
        "model": os.getenv("EMBEDDING_MODEL", "gemini-embedding-001"),
        "dimension": EMBEDDING_DIMENSION,
        "chunk_size": CHUNK_SIZE,
        "ingested_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    save_manifest(manifest)


def delete_book_vectors(filename, page_count):
    """Remove a book's old vectors before re-uploading it.

    IDs are deterministic (`<book id>-p<page>-c<chunk>`), so they can be deleted without
    listing anything - deletes are writes, which the free tier does not meter.
    """
    book = find_book(filename)

    if book is None:
        return

    # Generous upper bound on chunks per page; a smaller chunk_size than today never exceeded this.
    ids = [
        make_safe_id(f"{book.id}-p{page}-c{chunk}")
        for page in range(1, page_count + 1)
        for chunk in range(0, 24)
    ]

    for start in range(0, len(ids), 1000):
        index.delete(ids=ids[start:start + 1000], namespace=PINECONE_NAMESPACE)


# ==========================================
# MAIN
# ==========================================

def main():

    print()

    print(
        "=========================================="
    )

    print(
        "       GEMINI + PINECONE RAG"
    )

    print(
        "=========================================="
    )

    print()

    print(
        "Pinecone Index:",
        PINECONE_INDEX
    )

    print(
        "Namespace:",
        PINECONE_NAMESPACE
    )

    print(
        "Embedding:",
        os.getenv(
            "EMBEDDING_MODEL"
        )
    )

    print(
        "Dimension:",
        EMBEDDING_DIMENSION
    )

    print()

    # ======================================
    # CHECK DATA DIRECTORY
    # ======================================

    if not DATA_DIR.exists():

        print(
            "Không tìm thấy thư mục:",
            DATA_DIR
        )

        return

    # ======================================
    # FIND PDF
    # ======================================

    # python -m backend.rag.ingest "TOAN -TAP 1.pdf"  -> chỉ nạp file đó
    # python -m backend.rag.ingest --force            -> nạp cả sách đã có trên Pinecone
    args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    force = "--force" in sys.argv[1:]

    pdf_files = [DATA_DIR / Path(arg).name for arg in args] if args else list(
        DATA_DIR.glob("*.pdf")
    )

    missing = [path.name for path in pdf_files if not path.exists()]

    if missing:

        print("Không tìm thấy:", ", ".join(missing))

        return

    if not force:

        skipped = [path for path in pdf_files if already_ingested(path)]

        for path in skipped:

            print("↷ Bỏ qua (đã có trên Pinecone, thêm --force để nạp lại):", path.name)

        pdf_files = [path for path in pdf_files if path not in skipped]

    if len(pdf_files) == 0:

        print(
            "Không tìm thấy PDF trong:"
        )

        print(
            DATA_DIR
        )

        return

    print(
        "Tìm thấy",
        len(pdf_files),
        "file PDF."
    )

    # ======================================
    # INGEST ONE BOOK AT A TIME
    # ======================================

    # Each book is built, uploaded and recorded before the next one starts, so stopping
    # halfway (quota, network, Ctrl+C) keeps everything already uploaded.

    total_uploaded = 0

    failed = []

    for position, pdf_file in enumerate(pdf_files, start=1):

        print()

        print("==========================================")

        print(f"[{position}/{len(pdf_files)}] {pdf_file.name}")

        print("==========================================")

        try:

            records = create_records(
                pdf_file
            )

            print(
                "→ Tạo được",
                len(records),
                "chunks"
            )

            if not records:

                print("⚠ Không lấy được chữ từ PDF này (có thể là bản scan, cần OCR). Bỏ qua.")

                failed.append((pdf_file.name, "không có text"))

                continue

            if force:

                pages = max(record["metadata"]["page"] for record in records)

                print("Xoá vector cũ của quyển này trước khi nạp lại...")

                delete_book_vectors(pdf_file.name, pages)

            upload_records(records)

            record_ingested(pdf_file, len(records))

            total_uploaded += len(records)

            print(f"✓ Xong {pdf_file.name}: {len(records)} chunks đã lên Pinecone.")

        except KeyboardInterrupt:

            print()

            print("⏹ Dừng theo yêu cầu. Các quyển đã xong vẫn giữ nguyên trên Pinecone.")

            break

        except DailyQuotaExhausted as error:

            # Stop the whole run: the next book would only re-parse a huge PDF and fail the same way.
            print()

            print("⏹", error)

            print(f"   Còn {len(pdf_files) - position} quyển chưa nạp. Mai chạy lại lệnh này là đi tiếp.")

            failed.append((pdf_file.name, "hết hạn mức trong ngày"))

            break

        except Exception as error:

            print()

            print(
                "❌ Lỗi file:",
                pdf_file.name
            )

            print(
                error
            )

            failed.append((pdf_file.name, str(error)[:150]))

    if failed:

        print()

        print("Các quyển chưa nạp được:")

        for name, reason in failed:

            print(f"  - {name}: {reason}")

    # ======================================
    # DONE
    # ======================================

    print()

    print(
        "=========================================="
    )

    print(
        "✓ HOÀN TẤT"
    )

    print(
        "=========================================="
    )

    print()

    print(
        "Đã upload",
        total_uploaded,
        "chunks vào Pinecone."
    )

    print(
        "Cache embedding:",
        cache_size(),
        "vector (chạy lại sẽ không tốn quota cho phần này)."
    )


# ==========================================
# RUN
# ==========================================

if __name__ == "__main__":

    main()