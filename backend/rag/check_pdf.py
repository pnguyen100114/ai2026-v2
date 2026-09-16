"""Kiểm tra nhanh một PDF có dùng được cho AI không, TRƯỚC khi nạp lên Pinecone.

Sách giáo khoa tải trên mạng thường là bản scan ảnh: mở ra người vẫn đọc được, nhưng máy
không trích được chữ nào ngoài watermark của trang chia sẻ. Nạp loại này lên chỉ tốn quota
và làm bẩn kết quả tìm kiếm.

Cách dùng:
    python -m backend.rag.check_pdf                      # kiểm tra mọi PDF trong backend/data
    python -m backend.rag.check_pdf "KHTN 8.pdf"         # kiểm tra một quyển
    python -m backend.rag.check_pdf "D:/Downloads/x.pdf" # kiểm tra file ở nơi khác
"""
import sys
from pathlib import Path

from pypdf import PdfReader

try:
    from backend.rag.ingest import MIN_PAGE_CHARS, strip_watermarks
except ImportError:  # pragma: no cover
    from ingest import MIN_PAGE_CHARS, strip_watermarks

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Dưới ngưỡng này coi như PDF không có chữ thật để dùng.
GOOD_PAGE_RATIO = 0.5


def check(pdf_path):
    """(tình trạng, số trang, số ký tự thật trung bình mỗi trang)"""
    reader = PdfReader(str(pdf_path))
    total = len(reader.pages)

    if total == 0:
        return "HỎNG", 0, 0

    # Lấy mẫu tối đa 20 trang rải đều giữa sách (bỏ bìa và phụ lục).
    step = max(1, int(total * 0.7) // 20)
    sampled = list(range(int(total * 0.15), int(total * 0.85), step)) or [0]

    lengths = []
    for position in sampled:
        try:
            raw = reader.pages[position].extract_text() or ""
        except Exception:
            raw = ""
        lengths.append(len(strip_watermarks(raw).strip()))

    good = sum(1 for length in lengths if length >= MIN_PAGE_CHARS)
    average = int(sum(lengths) / len(lengths))

    if good >= len(lengths) * GOOD_PAGE_RATIO:
        return "DÙNG ĐƯỢC", total, average
    if good == 0:
        return "SCAN ẢNH", total, average
    return "MỘT PHẦN", total, average


def main():
    arguments = sys.argv[1:]

    if arguments:
        paths = [Path(argument) if Path(argument).exists() else DATA_DIR / argument for argument in arguments]
    else:
        paths = sorted(DATA_DIR.glob("*.pdf"))

    if not paths:
        print("Không tìm thấy PDF nào trong:", DATA_DIR)
        return

    print(f"{'FILE':<24} {'TÌNH TRẠNG':<12} {'TRANG':>6} {'CHỮ/TRANG':>10}")
    print("-" * 56)

    unusable = []

    for path in paths:
        if not path.exists():
            # Also reached when a file is moved out mid-scan; it must not pass silently.
            print(f"{path.name:<24} {'KHÔNG THẤY':<12}")
            unusable.append(path.name)
            continue
        try:
            status, pages, average = check(path)
        except Exception as error:
            print(f"{path.name:<24} {'LỖI':<12} {str(error)[:30]}")
            unusable.append(path.name)
            continue

        print(f"{path.name:<24} {status:<12} {pages:>6} {average:>10}")

        if status != "DÙNG ĐƯỢC":
            unusable.append(path.name)

    print()

    if unusable:
        print("Những quyển KHÔNG nạp được (cần tìm bản PDF khác có chữ):")
        for name in unusable:
            print("  -", name)
        print()
        print("Cách tự kiểm tra: mở PDF, thử bôi đen một dòng chữ trong bài học.")
        print("Bôi đen được -> dùng được. Không bôi được -> đó là ảnh, máy không đọc nổi.")
    else:
        print("✓ Tất cả PDF đều có chữ, nạp được.")


if __name__ == "__main__":
    main()
