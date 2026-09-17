"""Kho vector SGK nằm ngay trong database của dự án - thay cho Pinecone.

Vì sao bỏ Pinecone: gói free của nó tính tiền theo LƯỢT ĐỌC (1 GB/tháng), mà mỗi match kéo
theo cả đoạn text ~2 KB. Học sinh hỏi vài nghìn câu là hết hạn mức, và hết hạn mức nghĩa là
cả sản phẩm ngừng trả lời. 4.765 chunk của bộ SGK chỉ nặng ~30 MB vector, nhỏ hơn rất nhiều
so với một database Postgres bình thường, nên nuôi nó ngay trong DB sẵn có là 0 đồng và
không còn đồng hồ đếm ngược nào cả.

Module dùng chung DATABASE_URL với backend/db.py và tự chọn một trong hai cách tìm kiếm:

- `pgvector`: Postgres có extension `vector`, để Postgres tự so khớp bằng toán tử `<=>`.
  Đây là đường chạy trên Render + Supabase.
- `memory`: SQLite ở máy dev, hoặc Postgres không bật được extension. Toàn bộ vector được đọc
  lên RAM một lần (28 MB, dạng float32) rồi so khớp ngay trong tiến trình. Với 4.765 vector,
  một câu hỏi mất ~2 ms nếu có numpy, ~400 ms nếu không - chậm hơn nhưng không bao giờ chết,
  nên không có tình huống nào làm tìm kiếm ngừng chạy.

Bộ lọc (`subject`, `grade`, `page`...) vẫn viết theo cú pháp Pinecone ($in, $gte, $lte) để
books.py và app.py không phải sửa gì; `_where_sql` dịch cú pháp đó sang SQL.
"""
from __future__ import annotations

import array
import math
import operator
import os
import sys
import threading
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from sqlalchemy import bindparam, text

try:
    import numpy as _np
except ImportError:  # pragma: no cover - vẫn chạy được, chỉ chậm hơn (xem _search_memory)
    _np = None

try:
    from backend.db import engine
except ImportError:  # pragma: no cover
    # Chạy thẳng `python backend/rag/ingest.py`: Python chỉ đặt backend/rag vào sys.path,
    # không có gốc repo, nên cả `backend.db` lẫn `db` đều không thấy. Thêm gốc repo vào.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from backend.db import engine

EMBEDDING_DIMENSION = int(os.getenv('EMBEDDING_DIMENSION', '1536'))

TABLE = 'sgk_chunks'

# Số vector tối thiểu để BẬT index HNSW. Dưới ngưỡng này thì KHÔNG có index vector là đúng.
#
# Lý do không phải tốc độ mà là ĐỘ CHÍNH XÁC. Gần như mọi truy vấn đều kèm bộ lọc
# (subject + grade), mà một lớp-môn chỉ chiếm 3-7% kho. pgvector lọc SAU khi đi index:
# nó lấy `hnsw.ef_search` hàng xóm gần nhất của CẢ kho rồi mới bỏ hàng không khớp lọc.
# Mặc định ef_search = 40, nhân 5% còn khoảng 2 hàng - hỏi 24 đoạn SGK chỉ nhận về 2,
# và không có lỗi nào báo ra cả.
#
# Không có index thì Postgres đi `sgk_chunks_book_idx` để lấy đúng ~164-330 hàng của
# lớp-môn đó rồi tính cosine trên chừng ấy hàng: luôn đủ 24 kết quả đúng, và nhanh hơn.
# HNSW chỉ bắt đầu có lãi khi kho lớn tới mức quét thẳng mới thành đắt.
HNSW_MIN_ROWS = int(os.getenv('HNSW_MIN_ROWS', '50000'))

# Chỉ dùng khi kho đã vượt ngưỡng trên. Kéo cao hơn mặc định (40) để bù phần hao hụt do lọc.
HNSW_EF_SEARCH = int(os.getenv('HNSW_EF_SEARCH', '200'))

# Metadata được tách thành cột riêng để lọc cho nhanh và để retriever dựng lại match.
COLUMNS = (
    'subject', 'grade', 'volume', 'chapter', 'lesson',
    'page', 'page_offset', 'source', 'book_type', 'content_type',
    'title', 'book_title', 'text',
)

_INT_COLUMNS = {'grade', 'volume', 'chapter', 'lesson', 'page', 'page_offset'}

_lock = threading.Lock()
_backend: Optional[str] = None
_hnsw_active = False
# None = gọi kiểu `vector` trần được; 'extensions' = phải gọi `extensions.vector`.
_vector_schema: Optional[str] = None
# (danh sách hàng, ma trận vector float32, độ dài mỗi vector) - xem _load_memory.
_memory_rows: Optional[Tuple[List[Dict[str, Any]], Any, Any]] = None


# ------------------------------------------------------------------ hạ tầng

def is_postgres() -> bool:
    return engine.dialect.name == 'postgresql'


def _vector_type() -> str:
    """Tên kiểu vector có gọi được, kèm schema nếu cần. Xem _has_pgvector."""
    return f'{_vector_schema}.vector' if _vector_schema else 'vector'


def _vector_ops() -> str:
    """Tên opclass cosine, kèm schema nếu cần (access method `hnsw` thì không cần)."""
    return f'{_vector_schema}.vector_cosine_ops' if _vector_schema else 'vector_cosine_ops'


def _has_pgvector(conn) -> bool:
    """Bật extension `vector` và CHỨNG MINH là dùng được. Không được cũng không sao, có `memory`.

    Không thể chỉ xem `CREATE EXTENSION` có báo lỗi hay không. Supabase cài extension vào
    schema `extensions`, mà schema đó có nằm trong `search_path` hay không thì tuỳ role đang
    kết nối. Lệnh tạo extension chạy trót lọt xong `CREATE TABLE ... embedding vector(1536)`
    vẫn chết vì "type vector does not exist" - và chết ở chỗ không có fallback nào đỡ.

    Nên ở đây ép kiểu thử một vector thật. Nếu gọi trần không được thì tra xem extension nằm
    ở schema nào rồi gọi kèm schema, thay vì bỏ cuộc và rơi về đường `memory` chậm hơn.
    """
    global _vector_schema

    try:
        conn.exec_driver_sql('CREATE EXTENSION IF NOT EXISTS vector')
    except Exception:
        pass  # Có thể đã có sẵn, hoặc role này không được phép tạo. Thử dùng luôn.

    _vector_schema = None
    try:
        conn.exec_driver_sql("SELECT '[1,2,3]'::vector")
        return True
    except Exception:
        pass

    try:
        row = conn.exec_driver_sql(
            "SELECT n.nspname FROM pg_extension e "
            "JOIN pg_namespace n ON n.oid = e.extnamespace WHERE e.extname = 'vector'"
        ).fetchone()
    except Exception:
        return False
    if not row:
        return False

    schema = str(row[0])
    try:
        conn.exec_driver_sql(f"SELECT '[1,2,3]'::{schema}.vector")
    except Exception:
        return False
    _vector_schema = schema
    return True


def backend_name() -> str:
    """'pgvector' hoặc 'memory'. Quyết định một lần rồi nhớ luôn."""
    global _backend
    if _backend is None:
        with _lock:
            if _backend is None:
                if is_postgres():
                    try:
                        with engine.begin() as conn:
                            _backend = 'pgvector' if _has_pgvector(conn) else 'memory'
                    except Exception:
                        _backend = 'memory'
                else:
                    _backend = 'memory'
    return _backend


def init_store() -> str:
    """Tạo bảng và index nếu chưa có. Gọi lại nhiều lần vẫn an toàn."""
    name = backend_name()
    if name == 'pgvector':
        vector_column = f'{_vector_type()}({EMBEDDING_DIMENSION})'
    elif is_postgres():
        vector_column = 'TEXT'
    else:
        vector_column = 'BLOB'

    with engine.begin() as conn:
        conn.exec_driver_sql(
            f'CREATE TABLE IF NOT EXISTS {TABLE} ('
            ' id TEXT PRIMARY KEY,'
            ' subject TEXT,'
            ' grade INTEGER,'
            ' volume INTEGER,'
            ' chapter INTEGER,'
            ' lesson INTEGER,'
            ' page INTEGER,'
            ' page_offset INTEGER,'
            ' source TEXT,'
            ' book_type TEXT,'
            ' content_type TEXT,'
            ' title TEXT,'
            ' book_title TEXT,'
            ' text TEXT,'
            f' embedding {vector_column}'
            ')'
        )
        conn.exec_driver_sql(f'CREATE INDEX IF NOT EXISTS {TABLE}_book_idx ON {TABLE} (subject, grade, volume)')
        conn.exec_driver_sql(f'CREATE INDEX IF NOT EXISTS {TABLE}_page_idx ON {TABLE} (source, page)')

    if name == 'pgvector':
        sync_vector_index()

    if is_postgres():
        # Bảng trong "public" của Supabase lộ ra REST API với anon key nếu không bật RLS.
        # Backend nối bằng chủ sở hữu bảng nên không bị chặn.
        try:
            with engine.begin() as conn:
                conn.exec_driver_sql(f'ALTER TABLE public.{TABLE} ENABLE ROW LEVEL SECURITY')
        except Exception:
            pass

    return name


def sync_vector_index() -> bool:
    """Bật index HNSW khi kho đủ lớn, tắt khi chưa. Trả về True nếu index đang bật.

    Xem HNSW_MIN_ROWS ở đầu file: với kho nhỏ, có index vector làm kết quả SAI chứ không
    phải chậm, nên ở đây "tối ưu" nghĩa là chủ động XOÁ index đi.
    """
    global _hnsw_active
    rows = count()
    try:
        with engine.begin() as conn:
            if rows >= HNSW_MIN_ROWS:
                # ef_construction cao hơn mặc định (64): dựng index lâu hơn một lần, nhưng
                # recall tốt hơn mãi mãi - đáng, vì kho chỉ dựng lại khi nạp sách mới.
                conn.exec_driver_sql(
                    f'CREATE INDEX IF NOT EXISTS {TABLE}_embedding_idx '
                    f'ON {TABLE} USING hnsw (embedding {_vector_ops()}) '
                    f'WITH (m = 16, ef_construction = 200)'
                )
                _hnsw_active = True
            else:
                conn.exec_driver_sql(f'DROP INDEX IF EXISTS {TABLE}_embedding_idx')
                _hnsw_active = False
    except Exception:
        # Không đổi được index thì thôi; tìm kiếm vẫn chạy, chỉ là không đúng ý muốn.
        pass
    return _hnsw_active


# ------------------------------------------------------------------ vector <-> cột

def _encode(vector: Sequence[float]) -> Any:
    values = ','.join(repr(float(value)) for value in vector)
    if backend_name() == 'pgvector':
        return f'[{values}]'
    if is_postgres():
        return values
    return array.array('f', [float(value) for value in vector]).tobytes()


def _decode_f32(stored: Any) -> array.array:
    """Đọc cột embedding ra float32, dùng cho đường `memory`.

    Khác biệt không nhỏ: cùng 4.765 vector 1536 chiều, giữ bằng list float của Python tốn
    225 MB, giữ bằng float32 chỉ tốn 28 MB. Render gói free có 512 MB cho cả tiến trình.
    """
    if stored is None:
        return array.array('f')
    if isinstance(stored, (bytes, bytearray, memoryview)):
        return array.array('f', bytes(stored))
    if isinstance(stored, str):
        return array.array('f', [float(part) for part in stored.strip('[] ').split(',') if part.strip()])
    return array.array('f', [float(value) for value in stored])


# ------------------------------------------------------------------ ghi

def upsert(records: Iterable[Dict[str, Any]]) -> int:
    """records: [{'id', 'values', 'metadata'}]. Ghi đè theo id nên nạp lại sách không nhân đôi."""
    rows: List[Dict[str, Any]] = []
    for record in records:
        metadata = record.get('metadata') or {}
        row: Dict[str, Any] = {'id': record['id'], 'embedding': _encode(record['values'])}
        for column in COLUMNS:
            value = metadata.get(column)
            if column in _INT_COLUMNS:
                try:
                    value = int(value)
                except (TypeError, ValueError):
                    value = None
            row[column] = value
        rows.append(row)
    if not rows:
        return 0

    columns = ('id',) + COLUMNS + ('embedding',)
    embedding_value = f'CAST(:embedding AS {_vector_type()})' if backend_name() == 'pgvector' else ':embedding'
    placeholders = ', '.join(embedding_value if column == 'embedding' else f':{column}' for column in columns)

    if is_postgres():
        updates = ', '.join(f'{column} = EXCLUDED.{column}' for column in columns if column != 'id')
        statement = (
            f'INSERT INTO {TABLE} ({", ".join(columns)}) VALUES ({placeholders}) '
            f'ON CONFLICT (id) DO UPDATE SET {updates}'
        )
    else:
        statement = f'INSERT OR REPLACE INTO {TABLE} ({", ".join(columns)}) VALUES ({placeholders})'

    with engine.begin() as conn:
        conn.execute(text(statement), rows)
    _invalidate_memory()
    return len(rows)


def delete_ids(ids: Sequence[str]) -> int:
    if not ids:
        return 0
    statement = text(f'DELETE FROM {TABLE} WHERE id IN :ids').bindparams(bindparam('ids', expanding=True))
    with engine.begin() as conn:
        for start in range(0, len(ids), 500):
            conn.execute(statement, {'ids': list(ids[start:start + 500])})
    _invalidate_memory()
    return len(ids)


def delete_source(source: str) -> int:
    with engine.begin() as conn:
        result = conn.execute(text(f'DELETE FROM {TABLE} WHERE source = :source'), {'source': source})
    _invalidate_memory()
    return int(result.rowcount or 0)


def count_source(source: str) -> int:
    """Kho đang giữ bao nhiêu chunk của đúng file PDF này."""
    try:
        with engine.connect() as conn:
            return int(conn.execute(
                text(f'SELECT COUNT(*) FROM {TABLE} WHERE source = :source'),
                {'source': source},
            ).scalar() or 0)
    except Exception:
        return 0


def count(subject: Optional[str] = None, grade: Optional[int] = None) -> int:
    clauses: List[str] = []
    params: Dict[str, Any] = {}
    if subject:
        clauses.append('subject = :subject')
        params['subject'] = subject
    if grade is not None:
        clauses.append('grade = :grade')
        params['grade'] = int(grade)
    where = f' WHERE {" AND ".join(clauses)}' if clauses else ''
    try:
        with engine.connect() as conn:
            return int(conn.execute(text(f'SELECT COUNT(*) FROM {TABLE}{where}'), params).scalar() or 0)
    except Exception:
        return 0


def stats() -> Dict[str, Any]:
    """Cho /api/health: kho có bao nhiêu vector và đang chạy bằng cách nào."""
    return {
        'backend': backend_name(),
        'dialect': engine.dialect.name,
        'vectors': count(),
        # 'exact' = quét chính xác, recall 100%. 'hnsw' = gần đúng, chỉ bật khi kho đã lớn.
        'vector_index': 'hnsw' if _hnsw_active else 'exact',
        'hnsw_min_rows': HNSW_MIN_ROWS,
    }


# ------------------------------------------------------------------ bộ lọc kiểu Pinecone -> SQL

_OPERATORS = {'$gte': '>=', '$lte': '<=', '$gt': '>', '$lt': '<', '$ne': '!='}


def _where_sql(query_filter: Optional[Dict[str, Any]]) -> Tuple[str, Dict[str, Any]]:
    """Dịch {'page': {'$gte': 5, '$lte': 9}} thành "page >= :f0 AND page <= :f1"."""
    if not query_filter:
        return '', {}
    clauses: List[str] = []
    params: Dict[str, Any] = {}
    for field, condition in query_filter.items():
        if field not in COLUMNS and field != 'id':
            continue
        if isinstance(condition, dict):
            for operator, value in condition.items():
                if operator == '$in':
                    keys = []
                    for item in (list(value) or ['']):
                        item_key = f'f{len(params)}'
                        params[item_key] = item
                        keys.append(f':{item_key}')
                    clauses.append(f'{field} IN ({", ".join(keys)})')
                    continue
                key = f'f{len(params)}'
                if operator in _OPERATORS:
                    params[key] = value
                    clauses.append(f'{field} {_OPERATORS[operator]} :{key}')
                elif operator == '$eq':
                    params[key] = value
                    clauses.append(f'{field} = :{key}')
        else:
            key = f'f{len(params)}'
            params[key] = condition
            clauses.append(f'{field} = :{key}')
    return ' AND '.join(clauses), params


def _matches_filter(row: Dict[str, Any], query_filter: Optional[Dict[str, Any]]) -> bool:
    """Bản dùng cho đường `memory`, hiểu đúng những toán tử mà _where_sql hiểu."""
    if not query_filter:
        return True
    for field, condition in query_filter.items():
        value = row.get(field)
        if not isinstance(condition, dict):
            if value != condition:
                return False
            continue
        for operator, expected in condition.items():
            if operator == '$in':
                if value not in list(expected):
                    return False
            elif operator == '$eq':
                if value != expected:
                    return False
            elif operator == '$ne':
                if value == expected:
                    return False
            elif operator in ('$gte', '$lte', '$gt', '$lt'):
                if value is None:
                    return False
                if operator == '$gte' and not value >= expected:
                    return False
                if operator == '$lte' and not value <= expected:
                    return False
                if operator == '$gt' and not value > expected:
                    return False
                if operator == '$lt' and not value < expected:
                    return False
    return True


# ------------------------------------------------------------------ đọc

def _row_to_match(row: Dict[str, Any], score: float) -> Dict[str, Any]:
    """Trả về đúng hình dạng match của Pinecone để retriever không phải đổi cách đọc."""
    return {
        'id': row.get('id'),
        'score': float(score),
        'metadata': {column: row.get(column) for column in COLUMNS},
    }


def _invalidate_memory() -> None:
    global _memory_rows
    with _lock:
        _memory_rows = None


def _load_memory() -> Tuple[List[Dict[str, Any]], Any, Any]:
    """Cả kho trong RAM: (hàng, ma trận vector float32, độ dài mỗi vector). Đọc một lần.

    Vector KHÔNG giữ bằng list float của Python: 4.765 vector 1536 chiều thì list tốn
    225 MB, còn float32 chỉ 28 MB - mà Render gói free chỉ có 512 MB cho cả tiến trình.
    """
    global _memory_rows
    if _memory_rows is not None:
        return _memory_rows
    with _lock:
        if _memory_rows is not None:
            return _memory_rows
        rows: List[Dict[str, Any]] = []
        vectors: List[array.array] = []
        with engine.connect() as conn:
            result = conn.execute(text(f'SELECT id, {", ".join(COLUMNS)}, embedding FROM {TABLE}'))
            for record in result.mappings():
                vector = _decode_f32(record['embedding'])
                if not len(vector) or not any(vector):
                    continue
                rows.append({key: record[key] for key in ('id',) + COLUMNS})
                vectors.append(vector)

        if _np is not None:
            matrix = _np.array(vectors, dtype=_np.float32) if vectors else _np.zeros((0, 0), dtype=_np.float32)
            norms = _np.linalg.norm(matrix, axis=1) if vectors else _np.zeros(0, dtype=_np.float32)
        else:
            matrix = vectors
            norms = [math.sqrt(sum(value * value for value in item)) for item in vectors]

        _memory_rows = (rows, matrix, norms)
        return _memory_rows


def _search_memory(vector: Sequence[float], top_k: int, query_filter: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows, matrix, norms = _load_memory()
    if not rows:
        return []
    query_norm = math.sqrt(sum(value * value for value in vector))
    if query_norm <= 0:
        return []

    # Lọc trước theo metadata, rồi mới xếp hạng - đúng thứ tự mà pgvector KHÔNG làm được
    # khi có index HNSW (xem HNSW_MIN_ROWS), nên đường này luôn trả đủ top_k hàng khớp lọc.
    keep = [index for index, row in enumerate(rows) if _matches_filter(row, query_filter)]
    if not keep:
        return []

    if _np is not None:
        # Một phép nhân ma trận cho cả kho mất ~2 ms, nhanh hơn vòng lặp Python ~180 lần.
        scores = (matrix @ _np.asarray(vector, dtype=_np.float32)) / (norms * query_norm)
        best = sorted(keep, key=lambda index: -scores[index])[:top_k]
        return [_row_to_match(rows[index], float(scores[index])) for index in best]

    scored = sorted(
        (
            (sum(map(operator.mul, vector, matrix[index])) / (norms[index] * query_norm), index)
            for index in keep
        ),
        key=lambda item: item[0],
        reverse=True,
    )
    return [_row_to_match(rows[index], score) for score, index in scored[:top_k]]


def _search_pgvector(vector: Sequence[float], top_k: int, query_filter: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    where, params = _where_sql(query_filter)
    params['embedding'] = _encode(vector)
    params['limit'] = int(top_k)
    statement = (
        f'SELECT id, {", ".join(COLUMNS)}, 1 - (embedding <=> CAST(:embedding AS {_vector_type()})) AS score '
        f'FROM {TABLE} '
        + (f'WHERE {where} ' if where else '')
        + f'ORDER BY embedding <=> CAST(:embedding AS {_vector_type()}) LIMIT :limit'
    )
    # SET LOCAL chỉ sống trong một transaction, nên khi cần nó phải mở transaction hẳn hoi.
    opener = engine.begin if _hnsw_active else engine.connect
    with opener() as conn:
        if _hnsw_active:
            # Bù phần recall mất đi vì pgvector lọc SAU khi đi index (xem HNSW_MIN_ROWS).
            conn.exec_driver_sql(f'SET LOCAL hnsw.ef_search = {HNSW_EF_SEARCH}')
            # Đi tiếp trong index cho tới khi ĐỦ số hàng khớp bộ lọc, thay vì trả về thiếu.
            # Chỉ có từ pgvector 0.8.0; bản cũ hơn báo lỗi thì thôi, đã có ef_search gánh.
            try:
                conn.exec_driver_sql("SET LOCAL hnsw.iterative_scan = 'relaxed_order'")
            except Exception:
                pass
        rows = conn.execute(text(statement), params).mappings().all()
    return [_row_to_match({key: row[key] for key in ('id',) + COLUMNS}, row['score']) for row in rows]


def search(vector: Sequence[float], top_k: int = 5, query_filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """top_k đoạn SGK gần nghĩa nhất, đo bằng cosine - đúng metric đã dùng trên Pinecone."""
    if not vector:
        return []
    if backend_name() == 'pgvector':
        return _search_pgvector(vector, top_k, query_filter)
    return _search_memory(vector, top_k, query_filter)


__all__ = [
    'EMBEDDING_DIMENSION',
    'TABLE',
    'backend_name',
    'count',
    'count_source',
    'delete_ids',
    'delete_source',
    'init_store',
    'search',
    'stats',
    'sync_vector_index',
    'upsert',
]
