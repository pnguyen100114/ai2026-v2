"""Accounts and persistence: email-only sign-in, chat/feedback/quiz logs.

DATABASE_URL picks the database:
- unset (local dev): SQLite file backend/local.db, created automatically;
- production: any Postgres URL (Supabase pooler, Neon...), e.g. postgresql://user:pass@host:5432/postgres
Tables are created on startup; nothing has to be run by hand.
"""
from __future__ import annotations

import copy
import hashlib
import hmac
import logging
import os
import re
import secrets
import threading
import time
import uuid
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import jwt
from dotenv import load_dotenv
from fastapi import Header, HTTPException
from sqlalchemy import (
    JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, MetaData, String, Table, Text,
    create_engine, delete, insert, inspect, or_, select, update,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BACKEND_DIR / '.env')
logger = logging.getLogger('gia_su_ai.db')

TOKEN_TTL = timedelta(days=180)
CHAT_RATE_PER_MINUTE = int(os.getenv('CHAT_RATE_PER_MINUTE', '10'))
CHAT_RATE_PER_DAY = int(os.getenv('CHAT_RATE_PER_DAY', '200'))
EMAIL_PATTERN = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
# Empty until the frontend picks a lesson from the student's own roadmap (subject + grade).
DEFAULT_LESSON = ''
DEFAULT_TOPIC = ''
# Every account used to start on this grade-8 math lesson regardless of grade/subject.
LEGACY_DEFAULT_TOPIC = 'Phép nhân đa thức'


def _database_url() -> str:
    url = os.getenv('DATABASE_URL', '').strip()
    if not url:
        return f"sqlite:///{(BACKEND_DIR / 'local.db').as_posix()}"
    # Render/Heroku style URLs → SQLAlchemy psycopg3 driver.
    return re.sub(r'^postgres(ql)?://', 'postgresql+psycopg://', url)


def _auth_secret() -> str:
    secret = os.getenv('AUTH_SECRET', '').strip()
    if secret:
        return secret
    if os.getenv('DATABASE_URL'):
        logger.warning('AUTH_SECRET is not set: every restart will sign all students out. Set it in production.')
    # Local dev: keep a stable random secret next to the SQLite file (gitignored).
    secret_file = BACKEND_DIR / '.auth_secret'
    if not secret_file.exists():
        secret_file.write_text(secrets.token_urlsafe(48), encoding='utf-8')
    return secret_file.read_text(encoding='utf-8').strip()


AUTH_SECRET = _auth_secret()
metadata = MetaData()


def _now() -> datetime:
    return datetime.now(timezone.utc)


utc_now = _now


users = Table(
    'users', metadata,
    Column('id', String(36), primary_key=True),
    Column('email', String(254), nullable=False, unique=True),
    # PBKDF2 hash; NULL only for accounts created before passwords existed (their first login sets it).
    Column('password_hash', String(255)),
    Column('name', String(80), nullable=False),
    Column('grade', Integer, nullable=False, default=8),
    Column('subject', String(40), nullable=False, default='Toán'),
    Column('current_lesson', String(200), nullable=False, default=DEFAULT_LESSON),
    Column('current_topic', String(200), nullable=False, default=DEFAULT_TOPIC),
    Column('learning_profile', JSON, nullable=False, default=dict),
    # Onboarding survey: subjects, favorite, goal, daily_minutes, target_grade.
    Column('onboarding', JSON, nullable=False, default=dict),
    Column('onboarded', Boolean, nullable=False, default=False),
    Column('created_at', DateTime(timezone=True), nullable=False, default=_now),
    Column('last_login_at', DateTime(timezone=True), nullable=False, default=_now),
)

chat_sessions = Table(
    'chat_sessions', metadata,
    Column('id', String(64), primary_key=True),
    Column('user_id', String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
    Column('title', String(120), nullable=False),
    Column('subject', String(40), nullable=False),
    Column('grade', String(20), nullable=False),
    # Roadmap lesson label ("Bài 1: Đơn thức") the chat belongs to; empty for chats started before lessons were tracked.
    Column('lesson', String(200)),
    Column('created_at', DateTime(timezone=True), nullable=False, default=_now),
    Column('updated_at', DateTime(timezone=True), nullable=False, default=_now),
)

messages = Table(
    'messages', metadata,
    Column('id', String(64), primary_key=True),
    Column('session_id', String(64), ForeignKey('chat_sessions.id', ondelete='CASCADE'), nullable=False, index=True),
    Column('user_id', String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
    Column('role', String(10), nullable=False),
    Column('content', Text, nullable=False),
    Column('prompt', Text),
    Column('has_image', Boolean, nullable=False, default=False),
    # The problem copied out of the attached photo: the photo itself is not stored.
    Column('image_text', Text),
    Column('sources', JSON, nullable=False, default=list),
    Column('quick_replies', JSON, nullable=False, default=list),
    Column('understanding', String(20)),
    Column('model', String(80)),
    Column('latency_ms', Integer),
    Column('created_at', DateTime(timezone=True), nullable=False, default=_now),
)

feedback = Table(
    'feedback', metadata,
    Column('message_id', String(64), ForeignKey('messages.id', ondelete='CASCADE'), primary_key=True),
    Column('user_id', String(36), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('rating', String(4), nullable=False),
    Column('comment', Text),
    Column('created_at', DateTime(timezone=True), nullable=False, default=_now),
    Column('updated_at', DateTime(timezone=True), nullable=False, default=_now),
)

quiz_attempts = Table(
    'quiz_attempts', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('user_id', String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
    Column('question_id', String(80), nullable=False),
    Column('answer', Text, nullable=False),
    Column('is_correct', Boolean, nullable=False),
    Column('hints_used', Integer, nullable=False, default=0),
    Column('mastery', Float),
    Column('created_at', DateTime(timezone=True), nullable=False, default=_now),
)

# AI-generated practice questions; kept server-side so the answer never reaches the browser.
quiz_questions = Table(
    'quiz_questions', metadata,
    Column('id', String(36), primary_key=True),
    Column('user_id', String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
    Column('concept_id', String(200), nullable=False),
    Column('payload', JSON, nullable=False),
    Column('created_at', DateTime(timezone=True), nullable=False, default=_now),
)

# Gemini-outlined roadmaps for subjects/grades without textbooks in RAG; shared by all students.
ai_roadmaps = Table(
    'ai_roadmaps', metadata,
    Column('id', String(80), primary_key=True),  # "<subject>|<grade>"
    Column('payload', JSON, nullable=False),
    Column('created_at', DateTime(timezone=True), nullable=False, default=_now),
)


def _create_engine() -> Engine:
    url = _database_url()
    if url.startswith('sqlite'):
        return create_engine(url, connect_args={'check_same_thread': False})
    # Một tin nhắn giờ dùng tới hai kết nối cùng lúc (xem _io_pool trong app.py), nên pool
    # cũ 5+5 sẽ thành chỗ nghẽn ngay khi có vài em hỏi cùng lúc: kết nối không phải tài
    # nguyên đắt, còn chờ pool thì cộng thẳng vào thời gian em ngồi nhìn màn hình trống.
    return create_engine(url, pool_pre_ping=True, pool_size=10, max_overflow=20)


engine = _create_engine()


def init_db() -> None:
    metadata.create_all(engine)
    # create_all never alters existing tables: add columns introduced after the first deploy.
    if 'lesson' not in {column['name'] for column in inspect(engine).get_columns('chat_sessions')}:
        with engine.begin() as conn:
            conn.exec_driver_sql('ALTER TABLE chat_sessions ADD COLUMN lesson VARCHAR(200)')
    if 'password_hash' not in {column['name'] for column in inspect(engine).get_columns('users')}:
        with engine.begin() as conn:
            conn.exec_driver_sql('ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)')
    if 'image_text' not in {column['name'] for column in inspect(engine).get_columns('messages')}:
        with engine.begin() as conn:
            conn.exec_driver_sql('ALTER TABLE messages ADD COLUMN image_text TEXT')
    with engine.begin() as conn:
        # Idempotent cleanup: clear the old hardcoded lesson for students who are not in grade-8 math.
        conn.execute(update(users).where(
            users.c.current_topic == LEGACY_DEFAULT_TOPIC,
            or_(users.c.grade != 8, users.c.subject != 'Toán'),
        ).values(current_lesson='', current_topic=''))
    _user_cache.clear()
    if engine.dialect.name == 'postgresql':
        # On Supabase, tables in "public" are reachable through its REST API with the anon key.
        # RLS without policies blocks that path; the backend connects as the table owner and is unaffected.
        with engine.begin() as conn:
            for table in metadata.sorted_tables:
                conn.exec_driver_sql(f'ALTER TABLE public.{table.name} ENABLE ROW LEVEL SECURITY')


# ---------------------------------------------------------------- auth

def normalize_email(email: str) -> str:
    value = (email or '').strip().lower()
    if len(value) > 254 or not EMAIL_PATTERN.match(value):
        raise HTTPException(status_code=400, detail='Email chưa đúng định dạng, em kiểm tra lại nhé.')
    return value


PASSWORD_MIN_LENGTH = 6
PASSWORD_ITERATIONS = 240_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, PASSWORD_ITERATIONS)
    return f'pbkdf2_sha256${PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}'


def verify_password(password: str, stored: str | None) -> bool:
    try:
        algorithm, iterations, salt, digest = (stored or '').split('$')
        if algorithm != 'pbkdf2_sha256':
            return False
        candidate = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt), int(iterations))
    except ValueError:
        return False
    return hmac.compare_digest(candidate.hex(), digest)


def get_password_hash(user_id: str) -> str | None:
    with engine.connect() as conn:
        return conn.execute(select(users.c.password_hash).where(users.c.id == user_id)).scalar()


def set_password(user_id: str, password: str) -> None:
    with engine.begin() as conn:
        conn.execute(update(users).where(users.c.id == user_id).values(password_hash=hash_password(password)))
    forget_user(user_id)


SOURCE_URL_TTL = timedelta(days=7)


def _source_signature(source: str, page: int, expires: int) -> str:
    message = f'{source}|{page}|{expires}'.encode('utf-8')
    return hmac.new(AUTH_SECRET.encode('utf-8'), message, hashlib.sha256).hexdigest()[:32]


def signed_source_url(source: str | None, page: Any) -> str | None:
    """Textbook page previews are loaded by <img>, which cannot send the Bearer token, so the URL carries a signature."""
    try:
        page_number = int(page)
    except (TypeError, ValueError):
        return None
    if not source or page_number < 1:
        return None
    expires = int((_now() + SOURCE_URL_TTL).timestamp())
    return f'/api/sources/page?source={quote(str(source))}&page={page_number}&exp={expires}&sig={_source_signature(str(source), page_number, expires)}'


def verify_source_signature(source: str, page: int, expires: int | None, signature: str | None) -> bool:
    if not expires or not signature or expires < _now().timestamp():
        return False
    return hmac.compare_digest(_source_signature(source, page, expires), signature)


def issue_token(user_id: str) -> str:
    return jwt.encode({'sub': user_id, 'exp': _now() + TOKEN_TTL}, AUTH_SECRET, algorithm='HS256')


def current_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    """FastAPI dependency: the signed-in student, or 401."""
    token = authorization[7:].strip() if authorization and authorization.lower().startswith('bearer ') else ''
    try:
        user_id = jwt.decode(token, AUTH_SECRET, algorithms=['HS256'])['sub'] if token else None
    except jwt.PyJWTError:
        user_id = None
    user = get_user(user_id) if user_id else None
    if user is None:
        raise HTTPException(status_code=401, detail='Em cần đăng nhập để dùng Mimo nhé.')
    return user


_rate_lock = threading.Lock()
_rate_windows: dict[str, deque[float]] = {}


def check_rate(key: str, per_minute: int, per_day: int, *, record: bool = True, detail: str | None = None) -> None:
    """In-memory sliding window per key (per process) — protects the Gemini quota.

    record=False only checks the window; pair it with record_rate() to count just some events (e.g. wrong passwords).
    """
    now = time.time()
    with _rate_lock:
        window = _rate_windows.setdefault(key, deque())
        while window and window[0] < now - 86400:
            window.popleft()
        if sum(1 for stamp in window if stamp >= now - 60) >= per_minute:
            raise HTTPException(status_code=429, detail=detail or 'Em thao tác nhanh quá, nghỉ tay một phút rồi thử lại nhé!')
        if len(window) >= per_day:
            raise HTTPException(status_code=429, detail=detail or 'Hôm nay em đã hỏi rất nhiều rồi, mai mình học tiếp nhé!')
        if record:
            window.append(now)


def record_rate(key: str) -> None:
    with _rate_lock:
        _rate_windows.setdefault(key, deque()).append(time.time())


def check_chat_rate(user: dict[str, Any]) -> None:
    check_rate(f"chat:{user['id']}", CHAT_RATE_PER_MINUTE, CHAT_RATE_PER_DAY)


# ---------------------------------------------------------------- users

def public_user(row: Any) -> dict[str, Any]:
    data = dict(row._mapping)
    return {
        'id': data['id'],
        'email': data['email'],
        'name': data['name'],
        'grade': data['grade'],
        'subject': data['subject'],
        'currentLesson': data['current_lesson'],
        'currentTopic': data['current_topic'],
        'learningProfile': data['learning_profile'] or {},
        'onboarding': data['onboarding'] or {},
        'onboarded': bool(data['onboarded']),
    }


# Mỗi request đều đi qua current_user -> get_user, tức là một vòng đi-về tới database trước
# khi bất cứ việc gì bắt đầu. Đo trên bản đã triển khai: ~0,58s, nằm thẳng trên đường học sinh
# chờ chữ đầu tiên. Hàng users gần như không đổi giữa hai tin nhắn, nên giữ lại trong bộ nhớ.
#
# An toàn vì mọi chỗ ghi vào bảng users trong file này đều gọi forget_user() ngay sau đó, nên
# hồ sơ mới có hiệu lực lập tức. TTL chỉ là lưới đỡ cho những đường ghi không đi qua đây (lệnh
# reset_password chạy ở tiến trình khác, hoặc sau này chạy nhiều instance).
#
# 10 phút chứ không phải vài chục giây: học sinh ngồi nghĩ giữa hai câu hỏi thường lâu hơn thế,
# TTL ngắn thì gần như tin nhắn nào cũng trượt và cache thành vô nghĩa. Dài cũng không rủi ro
# vì bản nhớ chỉ chứa hồ sơ công khai (xem public_user - không có mật khẩu), còn đăng nhập đi
# qua find_user_by_email vốn không dùng cache nên đổi mật khẩu vẫn có hiệu lực ngay.
USER_CACHE_TTL = float(os.getenv('USER_CACHE_TTL', '600'))
USER_CACHE_SIZE = 2000
_user_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_user_cache_lock = threading.Lock()


def forget_user(user_id: str | None) -> None:
    """Bỏ bản nhớ của một học sinh. Gọi sau MỌI lệnh ghi vào bảng users."""
    if user_id:
        with _user_cache_lock:
            _user_cache.pop(user_id, None)


def get_user(user_id: str) -> dict[str, Any] | None:
    now = time.monotonic()
    with _user_cache_lock:
        cached = _user_cache.get(user_id)
    if cached is not None and (now - cached[0]) < USER_CACHE_TTL:
        # Trả bản sao: người gọi sửa dict trả về thì không được làm hỏng bản nhớ.
        return copy.deepcopy(cached[1])
    with engine.connect() as conn:
        row = conn.execute(select(users).where(users.c.id == user_id)).first()
    if row is None:
        forget_user(user_id)
        return None
    user = public_user(row)
    with _user_cache_lock:
        if len(_user_cache) >= USER_CACHE_SIZE:
            _user_cache.pop(next(iter(_user_cache)))
        _user_cache[user_id] = (now, copy.deepcopy(user))
    return user


def find_user_by_email(email: str) -> dict[str, Any] | None:
    with engine.connect() as conn:
        row = conn.execute(select(users).where(users.c.email == email)).first()
    return public_user(row) if row else None


def create_user(email: str, name: str, grade: int, password: str) -> dict[str, Any]:
    user_id = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(insert(users).values(id=user_id, email=email, password_hash=hash_password(password), name=name, grade=grade, subject='Toán', current_lesson=DEFAULT_LESSON, current_topic=DEFAULT_TOPIC, learning_profile={}, onboarding={}, onboarded=False))
    return get_user(user_id)  # type: ignore[return-value]


def touch_login(user_id: str) -> None:
    with engine.begin() as conn:
        conn.execute(update(users).where(users.c.id == user_id).values(last_login_at=_now()))
    forget_user(user_id)


PROFILE_FIELDS = {'name': 'name', 'grade': 'grade', 'subject': 'subject', 'currentLesson': 'current_lesson', 'currentTopic': 'current_topic', 'onboarding': 'onboarding', 'onboarded': 'onboarded'}


def update_user(user_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    values = {column: patch[key] for key, column in PROFILE_FIELDS.items() if key in patch and patch[key] is not None}
    if ('grade' in values or 'subject' in values) and 'current_lesson' not in values:
        # A lesson belongs to one grade/subject roadmap; drop it when either changes (e.g. onboarding).
        current = get_user(user_id)
        if current and (values.get('grade', current['grade']) != current['grade'] or values.get('subject', current['subject']) != current['subject']):
            values.update(current_lesson='', current_topic='')
    if values:
        with engine.begin() as conn:
            conn.execute(update(users).where(users.c.id == user_id).values(**values))
        forget_user(user_id)
    return get_user(user_id)  # type: ignore[return-value]


# ---------------------------------------------------------------- chat history

def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).isoformat()


def load_history(user_id: str, session_limit: int = 50) -> dict[str, Any]:
    with engine.connect() as conn:
        session_rows = conn.execute(select(chat_sessions).where(chat_sessions.c.user_id == user_id).order_by(chat_sessions.c.updated_at.desc()).limit(session_limit)).all()
        ids = [row.id for row in session_rows]
        message_rows = conn.execute(select(messages).where(messages.c.session_id.in_(ids)).order_by(messages.c.created_at)).all() if ids else []
        ratings = {row.message_id: row.rating for row in conn.execute(select(feedback.c.message_id, feedback.c.rating).where(feedback.c.user_id == user_id)).all()}
    return {
        'sessions': [{'id': row.id, 'title': row.title, 'subject': row.subject, 'grade': row.grade, 'lesson': row.lesson or '', 'createdAt': _iso(row.created_at), 'updatedAt': _iso(row.updated_at)} for row in session_rows],
        'messages': [{
            'id': row.id, 'sessionId': row.session_id, 'role': row.role, 'content': row.content, 'prompt': row.prompt, 'imageText': row.image_text,
            'sources': [_resign_source(source) for source in row.sources or []], 'quickReplies': row.quick_replies or [], 'understanding': row.understanding,
            'createdAt': _iso(row.created_at), 'feedback': ratings.get(row.id),
        } for row in message_rows],
    }


def _resign_source(source: Any) -> Any:
    """Stored preview links expire; hand out a fresh signature every time history is loaded."""
    if not isinstance(source, dict) or not source.get('preview_url'):
        return source
    return {**source, 'preview_url': signed_source_url(source.get('source'), source.get('pdf_page') or source.get('page'))}


def rename_session(user_id: str, session_id: str, title: str) -> None:
    with engine.begin() as conn:
        conn.execute(update(chat_sessions).where(chat_sessions.c.id == session_id, chat_sessions.c.user_id == user_id).values(title=title[:120]))


def delete_session(user_id: str, session_id: str) -> None:
    with engine.begin() as conn:
        # Explicit child deletes: SQLite does not enforce ON DELETE CASCADE by default.
        message_ids = select(messages.c.id).where(messages.c.session_id == session_id, messages.c.user_id == user_id)
        conn.execute(delete(feedback).where(feedback.c.message_id.in_(message_ids)))
        conn.execute(delete(messages).where(messages.c.session_id == session_id, messages.c.user_id == user_id))
        conn.execute(delete(chat_sessions).where(chat_sessions.c.id == session_id, chat_sessions.c.user_id == user_id))


def save_feedback(user_id: str, message_id: str, rating: str, comment: str | None) -> bool:
    with engine.begin() as conn:
        owned = conn.execute(select(messages.c.id).where(messages.c.id == message_id, messages.c.user_id == user_id, messages.c.role == 'assistant')).first()
        if not owned:
            return False
        exists = conn.execute(select(feedback.c.message_id).where(feedback.c.message_id == message_id, feedback.c.user_id == user_id)).first()
        values = {'rating': rating, 'updated_at': _now()}
        if comment is not None:
            values['comment'] = comment.strip()[:1000] or None
        if exists:
            conn.execute(update(feedback).where(feedback.c.message_id == message_id, feedback.c.user_id == user_id).values(**values))
        else:
            conn.execute(insert(feedback).values(message_id=message_id, user_id=user_id, **values))
    return True


def save_chat_turn(
    user: dict[str, Any],
    *,
    session: dict[str, Any] | None,
    user_message: dict[str, Any],
    assistant_message: dict[str, Any],
    replaces_message_id: str | None = None,
) -> None:
    """Persist one question/answer pair. Never raises: a DB outage must not break the chat."""
    if not session or not session.get('id'):
        return
    user_id = user['id']
    session_id = str(session['id'])[:64]
    try:
        with engine.begin() as conn:
            owner = conn.execute(select(chat_sessions.c.user_id).where(chat_sessions.c.id == session_id)).scalar()
            if owner and owner != user_id:
                logger.warning('User %s tried to write into session %s owned by someone else', user_id, session_id)
                return
            if owner is None:
                conn.execute(insert(chat_sessions).values(
                    id=session_id, user_id=user_id,
                    title=(session.get('title') or 'Cuộc trò chuyện mới')[:120],
                    subject=(session.get('subject') or 'Toán')[:40],
                    grade=(session.get('grade') or 'Lớp 8')[:20],
                    lesson=(session.get('lesson') or '')[:200] or None,
                    created_at=user_message['created_at'], updated_at=assistant_message['created_at'],
                ))
            else:
                conn.execute(update(chat_sessions).where(chat_sessions.c.id == session_id).values(updated_at=assistant_message['created_at']))

            if replaces_message_id:
                # "Thử lại": drop the old question and everything after it before storing the new answer.
                old_at = conn.execute(select(messages.c.created_at).where(messages.c.id == replaces_message_id, messages.c.user_id == user_id)).scalar()
                if old_at is not None:
                    stale = select(messages.c.id).where(messages.c.session_id == session_id, messages.c.created_at >= old_at)
                    conn.execute(delete(feedback).where(feedback.c.message_id.in_(stale)))
                    conn.execute(delete(messages).where(messages.c.session_id == session_id, messages.c.created_at >= old_at))

            # Plain insert: a colliding id fails instead of overwriting another student's message.
            conn.execute(insert(messages).values(**user_message, session_id=session_id, user_id=user_id, role='user'))
            conn.execute(insert(messages).values(**assistant_message, session_id=session_id, user_id=user_id, role='assistant'))
    except Exception:
        logger.exception('Failed to persist chat turn')


def lesson_history(user_id: str, subject: str, lesson: str, exclude_session_id: str | None = None, limit: int = 6) -> list[dict[str, str]]:
    """The student's latest messages about this lesson in their other chats, oldest first."""
    if not lesson:
        return []
    try:
        with engine.connect() as conn:
            query = (
                select(messages.c.role, messages.c.content)
                .join(chat_sessions, chat_sessions.c.id == messages.c.session_id)
                .where(chat_sessions.c.user_id == user_id, chat_sessions.c.subject == subject, chat_sessions.c.lesson == lesson)
            )
            if exclude_session_id:
                query = query.where(chat_sessions.c.id != exclude_session_id)
            rows = conn.execute(query.order_by(messages.c.created_at.desc()).limit(limit)).all()
    except Exception:
        logger.exception('Failed to load lesson history')
        return []
    return [{'role': row.role, 'content': row.content} for row in reversed(rows)]


STUDY_TIMEZONE = timezone(timedelta(hours=7))  # students are in Vietnam
MASTERED = 0.7


def _local_day(value: datetime) -> Any:
    return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).astimezone(STUDY_TIMEZONE).date()


def learning_progress(user: dict[str, Any], subject: str, grade: int, concept_prefix: str) -> dict[str, Any]:
    """Real study stats: streak of active days, today's activity, lessons studied and mastery per lesson topic."""
    user_id = user['id']
    since = _now() - timedelta(days=400)
    with engine.connect() as conn:
        asked = conn.execute(select(messages.c.created_at).where(messages.c.user_id == user_id, messages.c.role == 'user', messages.c.created_at >= since)).scalars().all()
        answered = conn.execute(select(quiz_attempts.c.created_at, quiz_attempts.c.is_correct).where(quiz_attempts.c.user_id == user_id, quiz_attempts.c.created_at >= since)).all()
        studied = conn.execute(
            select(chat_sessions.c.lesson).distinct()
            .join(messages, messages.c.session_id == chat_sessions.c.id)
            .where(chat_sessions.c.user_id == user_id, chat_sessions.c.subject == subject, chat_sessions.c.grade == f'Lớp {grade}',
                   chat_sessions.c.lesson.is_not(None), chat_sessions.c.lesson != '', messages.c.role == 'user')
        ).scalars().all()
    today = _now().astimezone(STUDY_TIMEZONE).date()
    active_days = {_local_day(stamp) for stamp in asked} | {_local_day(row.created_at) for row in answered}
    # A streak is still alive until the end of today even if the student has not studied yet today.
    day = today if today in active_days else today - timedelta(days=1)
    streak = 0
    while day in active_days:
        streak += 1
        day -= timedelta(days=1)
    concepts = {
        str(state.get('concept') or concept_id): {'mastery': float(state.get('mastery') or 0), 'attempts': int(state.get('attempts') or 0)}
        for concept_id, state in ((user.get('learningProfile') or {}).get('concepts') or {}).items()
        if concept_id.startswith(concept_prefix) and isinstance(state, dict)
    }
    return {
        'streak': streak,
        'activeToday': today in active_days,
        'today': {
            'questions': sum(1 for stamp in asked if _local_day(stamp) == today),
            'quizzes': sum(1 for row in answered if _local_day(row.created_at) == today),
            'quizCorrect': sum(1 for row in answered if _local_day(row.created_at) == today and row.is_correct),
        },
        'studiedLessons': sorted(studied),
        'concepts': concepts,
        'masteredThreshold': MASTERED,
    }


def save_generated_question(user: dict[str, Any], question: dict[str, Any]) -> str:
    question_id = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(insert(quiz_questions).values(id=question_id, user_id=user['id'], concept_id=question['concept_id'], payload=question))
    return question_id


def get_generated_question(user_id: str, question_id: str) -> dict[str, Any] | None:
    with engine.connect() as conn:
        payload = conn.execute(select(quiz_questions.c.payload).where(quiz_questions.c.id == question_id, quiz_questions.c.user_id == user_id)).scalar()
    return payload


def has_quiz_attempt(user_id: str, question_id: str) -> bool:
    with engine.connect() as conn:
        return conn.execute(select(quiz_attempts.c.id).where(quiz_attempts.c.user_id == user_id, quiz_attempts.c.question_id == question_id)).first() is not None


def recent_question_texts(user_id: str, concept_id: str, limit: int = 5) -> list[str]:
    """Recent questions on this concept, so Gemini does not repeat itself."""
    try:
        with engine.connect() as conn:
            rows = conn.execute(select(quiz_questions.c.payload).where(quiz_questions.c.user_id == user_id, quiz_questions.c.concept_id == concept_id).order_by(quiz_questions.c.created_at.desc()).limit(limit)).scalars().all()
    except Exception:
        logger.exception('Failed to load recent quiz questions')
        return []
    return [str(row.get('question') or '') for row in rows if row]


def _roadmap_key(subject: str, grade: int) -> str:
    return f'{subject.strip().lower()}|{grade}'[:80]


def get_ai_roadmap(subject: str, grade: int) -> dict[str, Any] | None:
    with engine.connect() as conn:
        return conn.execute(select(ai_roadmaps.c.payload).where(ai_roadmaps.c.id == _roadmap_key(subject, grade))).scalar()


def save_ai_roadmap(subject: str, grade: int, roadmap: dict[str, Any]) -> dict[str, Any]:
    """Store once; if another request stored one first, keep that so every student sees the same lessons."""
    try:
        with engine.begin() as conn:
            conn.execute(insert(ai_roadmaps).values(id=_roadmap_key(subject, grade), payload=roadmap))
    except IntegrityError:
        return get_ai_roadmap(subject, grade) or roadmap
    return roadmap


def save_quiz_attempt(user: dict[str, Any], attempt: dict[str, Any], learning_profile: dict[str, Any] | None) -> None:
    try:
        with engine.begin() as conn:
            conn.execute(insert(quiz_attempts).values(**attempt, user_id=user['id']))
            if learning_profile is not None:
                conn.execute(update(users).where(users.c.id == user['id']).values(learning_profile=learning_profile))
        # Mức nắm bài vừa đổi: tin nhắn tiếp theo phải dạy theo số mới, không theo số cũ.
        forget_user(user['id'])
    except Exception:
        logger.exception('Failed to persist quiz attempt')
