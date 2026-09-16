"""Render every SGK page to JPEG once and upload the images to Supabase Storage.

The 2.1 GB of scans in backend/data cannot go to GitHub, so a deployed backend has no PDF to
render from. This script does the rasterising here, on a machine that has the PDFs, and leaves
the deployed backend nothing to do but sign a link (see page_store.py).

Cách dùng:
    python backend/rag/render_pages.py                      # tất cả sách, bỏ qua trang đã upload
    python backend/rag/render_pages.py "TOAN6 -TAP 1.pdf"   # chỉ một cuốn
    python backend/rag/render_pages.py --force              # render lại cả những trang đã có
    python backend/rag/render_pages.py --dry-run            # chỉ ước lượng dung lượng, không upload

Chạy lại được bất cứ lúc nào: mặc định chỉ upload những trang còn thiếu, nên mạng đứt giữa
chừng thì chạy lại là chạy tiếp.
"""

from __future__ import annotations

import os
import sys
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path

import httpx
import pymupdf
from dotenv import load_dotenv

# Run as a plain script ("python backend/rag/render_pages.py") sys.path[0] is backend/rag, which
# is too deep to see the backend package the rest of the imports go through.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Console mặc định trên Windows là cp1252, không in được tiếng Việt có dấu.
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

try:
    from backend.rag import page_store
except ImportError:  # pragma: no cover
    from rag import page_store

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / '.env')

DATA_DIR = Path(__file__).resolve().parent.parent / 'data'

# 1.0x ≈ 96 DPI: chữ SGK vẫn đọc rõ khi phóng to, mà cả bộ đo được 633 MB nên vừa gói Supabase
# miễn phí (1 GB). Đổi hai số này thì phải chạy lại với --force.
RENDER_SCALE = float(os.getenv('PAGE_RENDER_SCALE', '1.0'))
RENDER_QUALITY = int(os.getenv('PAGE_RENDER_QUALITY', '72'))
# Must match SOURCE_THUMB_WIDTH in app.py: the same thumbnail used to sit under every answer.
THUMB_WIDTH = 320
THUMB_QUALITY = 75

# Home upstream, not Supabase, is the limit here; a handful of parallel uploads saturates it.
UPLOAD_WORKERS = int(os.getenv('PAGE_UPLOAD_WORKERS', '6'))
# Cap on rendered-but-not-yet-uploaded images, so a slow link cannot fill memory with JPEGs.
MAX_PENDING = UPLOAD_WORKERS * 4


def render_page(page: pymupdf.Page, thumb: bool) -> bytes:
    if thumb:
        scale = THUMB_WIDTH / page.rect.width
        quality = THUMB_QUALITY
    else:
        scale = RENDER_SCALE
        quality = RENDER_QUALITY
    pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
    return pixmap.tobytes('jpg', jpg_quality=quality)


def _drain(pending: set, limit: int, failures: list[str]) -> set:
    """Collect finished uploads until fewer than `limit` are still in flight."""
    while len(pending) >= limit:
        done, pending = wait(pending, return_when=FIRST_COMPLETED)
        for future in done:
            error = future.exception()
            if error is not None:
                failures.append(str(error))
    return pending


def process_book(pdf_path: Path, client: httpx.Client, pool: ThreadPoolExecutor | None,
                 force: bool, dry_run: bool) -> tuple[int, int, int, list[str]]:
    """Render and upload one book. Returns (uploaded, skipped, bytes, failures)."""
    prefix = page_store.book_prefix(pdf_path.name)
    existing = set() if (force or dry_run) else page_store.existing_keys(prefix, client)

    uploaded = skipped = total_bytes = 0
    failures: list[str] = []
    pending: set = set()
    started = time.time()

    with pymupdf.open(pdf_path) as document:
        page_count = document.page_count
        print(f'\n{pdf_path.name}  →  {prefix}/  ({page_count} trang, đã có {len(existing)} ảnh)')

        for number in range(1, page_count + 1):
            wanted = [(page_store.object_key(pdf_path.name, number, thumb), thumb) for thumb in (False, True)]
            todo = [(key, thumb) for key, thumb in wanted if force or key not in existing]
            if not todo:
                skipped += 1
                continue

            page = document[number - 1]
            for key, thumb in todo:
                try:
                    image = render_page(page, thumb)
                except Exception as exc:  # a damaged page should not stop the other 3,600
                    failures.append(f'{key}: render lỗi ({exc})')
                    continue
                total_bytes += len(image)
                uploaded += 1
                if dry_run:
                    continue
                pending = _drain(pending, MAX_PENDING, failures)
                pending.add(pool.submit(page_store.upload, key, image, client))

            if number % 25 == 0 or number == page_count:
                elapsed = max(time.time() - started, 0.001)
                print(f'  {number}/{page_count} trang · {total_bytes / 1024 / 1024:.0f} MB · '
                      f'{number / elapsed:.1f} trang/giây', flush=True)

    if not dry_run:
        _drain(pending, 1, failures)
    return uploaded, skipped, total_bytes, failures


def main() -> None:
    argv = sys.argv[1:]
    flags = {arg for arg in argv if arg.startswith('--')}
    names = [arg for arg in argv if not arg.startswith('--')]
    force = '--force' in flags
    dry_run = '--dry-run' in flags

    unknown = flags - {'--force', '--dry-run'}
    if unknown:
        print('Không hiểu tham số:', ', '.join(sorted(unknown)))
        return

    if not dry_run and not page_store.configured():
        print('Thiếu SUPABASE_URL hoặc SUPABASE_SERVICE_KEY trong backend/.env.')
        print('Xem hướng dẫn lấy hai giá trị này ở DEPLOY.md, mục "Ảnh trang SGK".')
        return

    pdf_files = [DATA_DIR / Path(name).name for name in names] if names else sorted(DATA_DIR.glob('*.pdf'))
    missing = [path.name for path in pdf_files if not path.exists()]
    if missing:
        print('Không tìm thấy trong backend/data:', ', '.join(missing))
        return
    if not pdf_files:
        print('Không có file PDF nào trong backend/data.')
        return

    print(f'{len(pdf_files)} cuốn sách · render {RENDER_SCALE}x chất lượng {RENDER_QUALITY}'
          + (' · CHẠY THỬ, không upload' if dry_run else f' · bucket "{page_store.PAGE_BUCKET}"'))

    totals = [0, 0, 0]
    failures: list[str] = []
    client = httpx.Client(timeout=httpx.Timeout(60.0, connect=10.0)) if not dry_run else None
    pool = ThreadPoolExecutor(max_workers=UPLOAD_WORKERS) if not dry_run else None

    try:
        if not dry_run:
            page_store.ensure_bucket(client)
        for pdf_path in pdf_files:
            try:
                uploaded, skipped, size, book_failures = process_book(pdf_path, client, pool, force, dry_run)
            except Exception as exc:  # one unreadable scan should not end the run
                failures.append(f'{pdf_path.name}: {exc}')
                print(f'  ✗ {pdf_path.name}: {exc}')
                continue
            totals = [totals[0] + uploaded, totals[1] + skipped, totals[2] + size]
            failures.extend(book_failures)
    finally:
        if pool is not None:
            pool.shutdown(wait=True)
        if client is not None:
            client.close()

    print('\n--------------------------------------')
    verb = 'Sẽ upload' if dry_run else 'Đã upload'
    print(f'{verb}: {totals[0]} ảnh · {totals[2] / 1024 / 1024:.0f} MB')
    print(f'Bỏ qua (đã có sẵn): {totals[1]} trang')
    if failures:
        print(f'\n⚠ {len(failures)} lỗi:')
        for line in failures[:20]:
            print('  -', line)
        if len(failures) > 20:
            print(f'  ... và {len(failures) - 20} lỗi nữa. Chạy lại script để upload tiếp phần thiếu.')
    elif not dry_run:
        print('Xong, không có lỗi.')


if __name__ == '__main__':
    main()
