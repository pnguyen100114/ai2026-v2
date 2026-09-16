"""Pre-rendered textbook page images kept in Supabase Storage.

backend/data holds 2.1 GB of SGK PDFs that never reach GitHub, so a deployed backend has no
PDF to render a page preview from. render_pages.py rasterises every page once and uploads the
JPEGs here; /api/sources/page then hands the student a short-lived signed URL instead of
opening a 150 MB scan. The bucket stays private: only a link this backend signed will open.
"""

from __future__ import annotations

import os
import re
import threading
import time
import unicodedata
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

try:
    from backend.rag.books import find_book
except ImportError:  # pragma: no cover
    from rag.books import find_book

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / '.env')

SUPABASE_URL = (os.getenv('SUPABASE_URL') or '').rstrip('/')
# Service role key: needed to upload and to sign links for a private bucket. Backend only, never
# shipped to the browser.
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY') or ''
PAGE_BUCKET = os.getenv('PAGE_BUCKET') or 'sgk-pages'
# Seconds a Supabase link stays valid. The browser follows the redirect immediately, so this only
# has to outlive one page load; short links limit the damage if one leaks.
PAGE_URL_TTL = int(os.getenv('PAGE_URL_TTL', '3600'))

_TIMEOUT = httpx.Timeout(20.0, connect=10.0)


def configured() -> bool:
    """False when the env vars are absent, which is the normal local setup: render from the PDFs instead."""
    return bool(SUPABASE_URL and SUPABASE_SERVICE_KEY)


def _headers() -> dict[str, str]:
    return {'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}', 'apikey': SUPABASE_SERVICE_KEY}


def _slug(text: Any) -> str:
    value = unicodedata.normalize('NFKD', str(text or '').replace('đ', 'd').replace('Đ', 'D'))
    ascii_only = value.encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', ascii_only).strip('-')


def book_prefix(source: Any) -> str:
    """Folder for a book in the bucket.

    Keyed by catalog id so the aliases a book was ingested under ("KHTN 6.pdf" and "KHTN.pdf")
    share one copy of the images instead of storing the same scan twice.
    """
    book = find_book(source)
    if book is not None:
        return book.id
    return _slug(Path(str(source or '')).stem) or 'khac'


def object_key(source: Any, page: Any, thumb: bool = False) -> str:
    return f'{book_prefix(source)}/p{int(page):04d}{"t" if thumb else ""}.jpg'


# ==========================================
# ĐỌC: ký link cho học sinh
# ==========================================

# Signing costs a round trip to Supabase, and one answer shows several thumbnails. Cache the
# links so a page of citations does not turn into a burst of sign calls.
_signed_cache: dict[str, tuple[float, str]] = {}
_cache_lock = threading.Lock()
_CACHE_MAX = 4000


def _cache_get(key: str, now: float) -> str | None:
    with _cache_lock:
        cached = _signed_cache.get(key)
        return cached[1] if cached and cached[0] > now else None


def _cache_put(key: str, url: str, now: float) -> None:
    with _cache_lock:
        # Re-sign a minute early so a cached link never reaches a browser already expired.
        _signed_cache[key] = (now + max(PAGE_URL_TTL - 60, 60), url)
        if len(_signed_cache) > _CACHE_MAX:
            for stale in [name for name, (expiry, _) in _signed_cache.items() if expiry <= now]:
                _signed_cache.pop(stale, None)
            while len(_signed_cache) > _CACHE_MAX:
                _signed_cache.pop(next(iter(_signed_cache)), None)


def signed_url(source: Any, page: Any, thumb: bool = False) -> str | None:
    """A temporary link to one rendered page, or None when the bucket has no such image."""
    if not configured():
        return None
    try:
        key = object_key(source, page, thumb)
    except (TypeError, ValueError):
        return None

    now = time.time()
    cached = _cache_get(key, now)
    if cached:
        return cached

    try:
        response = httpx.post(
            f'{SUPABASE_URL}/storage/v1/object/sign/{PAGE_BUCKET}/{key}',
            headers=_headers(),
            json={'expiresIn': PAGE_URL_TTL},
            timeout=_TIMEOUT,
        )
    except httpx.HTTPError:
        return None
    if response.status_code != 200:
        # 400/404 = the page was never uploaded (a book added after the last render run).
        return None

    try:
        path = str((response.json() or {}).get('signedURL') or '')
    except ValueError:
        return None
    if not path:
        return None

    url = f'{SUPABASE_URL}/storage/v1{path if path.startswith("/") else "/" + path}'
    _cache_put(key, url, now)
    return url


# ==========================================
# GHI: dùng bởi render_pages.py
# ==========================================


def ensure_bucket(client: httpx.Client | None = None) -> None:
    """Create the bucket, private, if it is not there yet."""
    owned = client is None
    client = client or httpx.Client(timeout=_TIMEOUT)
    try:
        existing = client.get(f'{SUPABASE_URL}/storage/v1/bucket/{PAGE_BUCKET}', headers=_headers())
        if existing.status_code == 200:
            return
        created = client.post(
            f'{SUPABASE_URL}/storage/v1/bucket',
            headers=_headers(),
            json={'name': PAGE_BUCKET, 'id': PAGE_BUCKET, 'public': False},
        )
        if created.status_code not in (200, 201, 409):
            raise RuntimeError(f'Không tạo được bucket "{PAGE_BUCKET}": {created.status_code} {created.text[:200]}')
    finally:
        if owned:
            client.close()


def existing_keys(prefix: str, client: httpx.Client | None = None) -> set[str]:
    """Object keys already in the bucket under one book, so an interrupted run can resume."""
    owned = client is None
    client = client or httpx.Client(timeout=_TIMEOUT)
    found: set[str] = set()
    offset = 0
    try:
        while True:
            response = client.post(
                f'{SUPABASE_URL}/storage/v1/object/list/{PAGE_BUCKET}',
                headers=_headers(),
                json={'prefix': f'{prefix}/', 'limit': 1000, 'offset': offset,
                      'sortBy': {'column': 'name', 'order': 'asc'}},
            )
            if response.status_code != 200:
                raise RuntimeError(f'Không đọc được danh sách ảnh đã có: {response.status_code} {response.text[:200]}')
            batch = response.json() or []
            for item in batch:
                name = str((item or {}).get('name') or '')
                # A folder placeholder carries no id; count only real objects.
                if name and item.get('id'):
                    found.add(f'{prefix}/{name}')
            if len(batch) < 1000:
                return found
            offset += len(batch)
    finally:
        if owned:
            client.close()


def upload(key: str, data: bytes, client: httpx.Client, attempts: int = 4) -> None:
    """Upload one JPEG, retrying: a run pushes thousands of files over a home connection."""
    last_error = ''
    for attempt in range(attempts):
        try:
            response = client.post(
                f'{SUPABASE_URL}/storage/v1/object/{PAGE_BUCKET}/{key}',
                headers={**_headers(), 'Content-Type': 'image/jpeg', 'x-upsert': 'true'},
                content=data,
            )
            if response.status_code in (200, 201):
                return
            last_error = f'{response.status_code} {response.text[:200]}'
        except httpx.HTTPError as exc:
            last_error = str(exc)
        time.sleep(min(2 ** attempt, 8))
    raise RuntimeError(f'Upload {key} thất bại: {last_error}')
