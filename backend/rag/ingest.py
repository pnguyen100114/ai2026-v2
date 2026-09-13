import os
import re
import uuid

from pathlib import Path
from dotenv import load_dotenv
from pypdf import PdfReader
from pinecone import Pinecone

from embeddings import create_embeddings


# ==========================================
# LOAD ENV
# ==========================================

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX")

PINECONE_NAMESPACE = os.getenv(
    "PINECONE_NAMESPACE"
) or ""

EMBEDDING_DIMENSION = int(
    os.getenv("EMBEDDING_DIMENSION", "1536")
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
# CHUNK TEXT
# ==========================================

def split_text(
    text,
    chunk_size=1000,
    overlap=150
):

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


# ==========================================
# DETECT CHAPTER
# ==========================================

def detect_chapter(text):

    patterns = [

        r"Chương\s+(\d+)",

        r"CHƯƠNG\s+(\d+)"

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

    records = []

    current_chapter = 0

    current_lesson = 0

    for page_data in pages:

        page_number = page_data[
            "page"
        ]

        text = page_data[
            "text"
        ]

        if not text.strip():

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

            # ID gốc
            raw_id = (

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

    return records


# ==========================================
# UPLOAD TO PINECONE
# ==========================================

def upload_records(records):

    # Giảm batch để hạn chế lỗi quota
    batch_size = 20

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

    pdf_files = list(
        DATA_DIR.glob("*.pdf")
    )

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
    # CREATE RECORDS
    # ======================================

    all_records = []

    for pdf_file in pdf_files:

        try:

            records = create_records(
                pdf_file
            )

            print(
                "→ Tạo được",
                len(records),
                "chunks"
            )

            all_records.extend(
                records
            )

        except Exception as error:

            print()

            print(
                "❌ Lỗi file:",
                pdf_file.name
            )

            print(
                error
            )

    # ======================================
    # CHECK RECORDS
    # ======================================

    if len(all_records) == 0:

        print()

        print(
            "❌ Không lấy được "
            "nội dung PDF."
        )

        print()

        print(
            "Nếu PDF là bản scan/hình ảnh,"
        )

        print(
            "cần thêm OCR."
        )

        return

    # ======================================
    # UPLOAD
    # ======================================

    print()

    print(
        "=========================================="
    )

    print(
        "BẮT ĐẦU GEMINI → PINECONE"
    )

    print(
        "=========================================="
    )

    upload_records(
        all_records
    )

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
        len(all_records),
        "chunks vào Pinecone."
    )


# ==========================================
# RUN
# ==========================================

if __name__ == "__main__":

    main()