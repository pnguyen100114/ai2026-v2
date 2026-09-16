"""Gemini embeddings for ingest, with a disk cache and a rate limiter.

Two things make a full-textbook ingest survivable on the free tier:

- Every vector is cached on disk by (model, dimension, text). Re-running ingest after a
  crash, a quota stop or a chunking tweak costs nothing for text that was embedded before.
- The free tier counts EACH TEXT of a batch against the per-minute request quota
  (measured: `embed_content_free_tier_requests, limit: 100`), so batching does not raise the
  ceiling - it only removes per-request latency. We therefore pace to EMBED_RPM texts/minute
  instead of sleeping a fixed second between single-text calls.
"""
import array
import hashlib
import os
import re
import sqlite3
import threading
import time

from collections import deque
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types


# ==========================================
# LOAD ENV
# ==========================================

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "gemini-embedding-001"
)

EMBEDDING_DIMENSION = int(
    os.getenv(
        "EMBEDDING_DIMENSION",
        "1536"
    )
)

# Texts per minute. 100 = free tier. Raise it after enabling billing (Tier 1 is far higher).
EMBED_RPM = int(os.getenv("EMBED_RPM", "100"))

# Texts per request. The quota counts texts, not requests, so this only saves latency.
# Never larger than the per-minute allowance, or every batch would start already over budget.
EMBED_BATCH_SIZE = max(1, min(
    int(os.getenv("EMBED_BATCH_SIZE", "50")),
    EMBED_RPM if EMBED_RPM > 0 else 100,
))

EMBED_CACHE_PATH = Path(
    os.getenv("EMBED_CACHE_PATH", "")
    or Path(__file__).resolve().parent / ".embed_cache.sqlite3"
)


class DailyQuotaExhausted(RuntimeError):
    """The day's embedding allowance is gone; waiting minutes will not help, only tomorrow will.

    Its own type so ingest can stop the whole run instead of moving to the next book and
    re-parsing hundreds of MB of PDF just to fail again on the first request.
    """


# ==========================================
# CHECK API KEY
# ==========================================

if not GEMINI_API_KEY:
    raise ValueError(
        "Chưa có GEMINI_API_KEY trong .env"
    )


# ==========================================
# GEMINI CLIENT
# ==========================================

client = genai.Client(
    api_key=GEMINI_API_KEY
)


# ==========================================
# DISK CACHE
# ==========================================

_cache_lock = threading.Lock()


def _cache_connection():
    connection = sqlite3.connect(str(EMBED_CACHE_PATH), timeout=30)
    connection.execute(
        "CREATE TABLE IF NOT EXISTS embeddings ("
        "  key TEXT PRIMARY KEY,"
        "  vector BLOB NOT NULL,"
        "  created_at REAL NOT NULL"
        ")"
    )
    return connection


def _cache_key(text):
    digest = hashlib.sha256(
        f"{EMBEDDING_MODEL}|{EMBEDDING_DIMENSION}|{text}".encode("utf-8")
    ).hexdigest()
    return digest


def cache_get_many(texts):
    """Cached vectors for these texts, as {index in texts: vector}."""
    if not texts:
        return {}

    keys = [_cache_key(text) for text in texts]

    found = {}

    with _cache_lock:
        connection = _cache_connection()
        try:
            # SQLite caps variables per statement; ask in slices.
            for start in range(0, len(keys), 400):
                window = keys[start:start + 400]
                placeholders = ",".join("?" * len(window))
                rows = connection.execute(
                    f"SELECT key, vector FROM embeddings WHERE key IN ({placeholders})",
                    window,
                ).fetchall()
                by_key = {key: blob for key, blob in rows}
                for offset, key in enumerate(window):
                    blob = by_key.get(key)
                    if blob is not None:
                        found[start + offset] = list(array.array("f", blob))
        finally:
            connection.close()

    return found


def cache_put_many(pairs):
    """Store [(text, vector), ...]."""
    if not pairs:
        return

    with _cache_lock:
        connection = _cache_connection()
        try:
            connection.executemany(
                "INSERT OR REPLACE INTO embeddings (key, vector, created_at) VALUES (?, ?, ?)",
                [
                    (_cache_key(text), array.array("f", vector).tobytes(), time.time())
                    for text, vector in pairs
                ],
            )
            connection.commit()
        finally:
            connection.close()


def cache_size():
    with _cache_lock:
        connection = _cache_connection()
        try:
            return connection.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]
        finally:
            connection.close()


# ==========================================
# RATE LIMIT
# ==========================================

# Timestamps of texts sent in the last 60s, so we pace to EMBED_RPM texts/minute.
_sent_at = deque()


def _throttle(count):
    if EMBED_RPM <= 0:
        return

    while True:
        now = time.monotonic()

        while _sent_at and now - _sent_at[0] >= 60.0:
            _sent_at.popleft()

        if len(_sent_at) + count <= EMBED_RPM:
            break

        # A batch larger than the whole per-minute allowance can never "fit"; send it on an
        # empty window and let the 429 backoff handle the rest, instead of looping forever.
        if not _sent_at:
            break

        wait = 60.0 - (now - _sent_at[0]) + 0.2

        print(f"  ⏳ Chờ {wait:.0f}s cho hạn mức {EMBED_RPM} text/phút...")

        time.sleep(max(wait, 1.0))

    stamp = time.monotonic()

    for _ in range(count):
        _sent_at.append(stamp)


def _retry_delay(error_text, attempt):
    """Honour the server's own 'Please retry in 13.8s' when it gives one."""
    match = re.search(r"retry in ([0-9.]+)s", error_text)

    if match:
        return float(match.group(1)) + 1.0

    return min(60.0, 5.0 * (2 ** attempt))


# ==========================================
# EMBED ONE BATCH (API CALL)
# ==========================================

def _embed_batch(texts):
    attempt = 0

    while True:
        _throttle(len(texts))

        try:
            result = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=texts,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT",
                    output_dimensionality=EMBEDDING_DIMENSION,
                ),
            )

            return [list(item.values) for item in result.embeddings]

        except Exception as error:

            error_text = str(error)

            is_quota = "429" in error_text or "RESOURCE_EXHAUSTED" in error_text

            if not is_quota:
                raise

            # A daily cap will not clear by waiting a minute; say so instead of looping forever.
            if "PerDay" in error_text or "per day" in error_text.lower():
                raise DailyQuotaExhausted(
                    "Gemini đã hết hạn mức embedding trong NGÀY. "
                    "Vector đã tạo được lưu trong cache nên mai chạy lại sẽ đi tiếp, không tốn lại. "
                    f"Chi tiết: {error_text[:200]}"
                ) from error

            delay = _retry_delay(error_text, attempt)

            print(f"  ⚠ Gemini giới hạn request, chờ {delay:.0f}s rồi thử lại...")

            time.sleep(delay)

            attempt += 1


# ==========================================
# CREATE ONE EMBEDDING
# ==========================================

def create_embedding(text):

    if not text or not text.strip():
        return []

    return create_embeddings([text])[0]


# ==========================================
# CREATE MANY EMBEDDINGS
# ==========================================

def create_embeddings(texts, progress=None):
    """Vectors for texts, in order. Cached texts cost no quota and no time."""

    if not texts:
        return []

    results = [None] * len(texts)

    cached = cache_get_many(texts)

    for position, vector in cached.items():
        results[position] = vector

    pending = [position for position in range(len(texts)) if results[position] is None]

    if cached:
        print(f"  ♻ Dùng lại {len(cached)} vector từ cache, cần tạo mới {len(pending)}")

    for start in range(0, len(pending), EMBED_BATCH_SIZE):

        window = pending[start:start + EMBED_BATCH_SIZE]

        batch_texts = [texts[position] for position in window]

        vectors = _embed_batch(batch_texts)

        if len(vectors) != len(window):
            raise RuntimeError(
                f"Gemini trả về {len(vectors)} vector cho {len(window)} text."
            )

        for position, vector in zip(window, vectors):
            results[position] = vector

        # Cache immediately: a crash on the next batch must not throw these away.
        cache_put_many(list(zip(batch_texts, vectors)))

        if progress is not None:
            progress(min(start + EMBED_BATCH_SIZE, len(pending)), len(pending))

    return results
