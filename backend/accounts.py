"""HTTP routes for email-only accounts, profile/onboarding, chat history and feedback."""
from __future__ import annotations

import os
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator

try:
    from backend import db
    from backend.learning import concept_prefix
except ImportError:  # pragma: no cover
    import db
    from learning import concept_prefix

router = APIRouter(prefix='/api')
# Number of reverse proxies in front of the app that append to X-Forwarded-For (Render: 1). 0 = ignore the header,
# otherwise anyone could send a fake X-Forwarded-For per request and dodge the sign-in rate limit.
TRUSTED_PROXY_HOPS = int(os.getenv('TRUSTED_PROXY_HOPS', '0'))


def client_ip(request: Request) -> str:
    forwarded = [part.strip() for part in request.headers.get('x-forwarded-for', '').split(',') if part.strip()]
    if TRUSTED_PROXY_HOPS > 0 and forwarded:
        # Trusted proxies append the address they saw, so the real client is that many entries from the right.
        return forwarded[-min(TRUSTED_PROXY_HOPS, len(forwarded))]
    return request.client.host if request.client else 'unknown'


class EmailSignIn(BaseModel):
    email: str
    password: str = Field(default='', max_length=128)
    mode: Literal['login', 'register'] = 'login'
    name: str | None = Field(default=None, max_length=80)
    grade: int | None = Field(default=None, ge=6, le=9)


class ProfilePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)

    grade: int | None = Field(default=None, ge=6, le=9)
    subject: str | None = Field(default=None, max_length=40)
    currentLesson: str | None = Field(default=None, max_length=200)
    currentTopic: str | None = Field(default=None, max_length=200)
    onboarding: dict[str, Any] | None = None
    onboarded: bool | None = None

    @field_validator('name')
    @classmethod
    def name_not_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError('Tên không được để trống.')
        return value.strip() if value is not None else value


class PasswordChange(BaseModel):
    currentPassword: str = Field(..., max_length=128)
    newPassword: str = Field(..., max_length=128)


class SessionPatch(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)


class FeedbackIn(BaseModel):
    message_id: str = Field(..., min_length=1, max_length=64)
    rating: Literal['up', 'down']
    comment: str | None = Field(default=None, max_length=1000)


@router.post('/auth/email')
def sign_in_with_email(body: EmailSignIn, request: Request) -> dict[str, Any]:
    # A whole class often shares one school IP, so this only stops floods; password guessing is limited per email below.
    db.check_rate(f'auth:{client_ip(request)}', per_minute=30, per_day=1000)
    email = db.normalize_email(body.email)
    # Wrong passwords are also limited per email, so guessing one student's password from many addresses stays slow.
    failures_key = f'auth-fail:{email}'
    db.check_rate(failures_key, per_minute=5, per_day=30, record=False,
                  detail='Em nhập sai mật khẩu nhiều lần quá, đợi một lát rồi thử lại nhé.')
    password = body.password
    user = db.find_user_by_email(email)
    if user is None:
        if body.mode == 'login':
            raise HTTPException(status_code=404, detail='Email này chưa có tài khoản. Em bấm "Tạo tài khoản mới" nhé.')
        name = (body.name or '').strip()
        if not name:
            raise HTTPException(status_code=400, detail='Em nhập tên của mình nhé.')
        _check_new_password(password)
        user = db.create_user(email, name, body.grade or 8, password)
        return {'token': db.issue_token(user['id']), 'user': user}

    if body.mode == 'register':
        raise HTTPException(status_code=409, detail='Email này đã có tài khoản rồi. Em bấm "Đăng nhập" nhé.')
    stored_hash = db.get_password_hash(user['id'])
    if stored_hash is None:
        # Account from before passwords existed: the first login with a password claims it.
        _check_new_password(password)
        db.set_password(user['id'], password)
    elif not db.verify_password(password, stored_hash):
        db.record_rate(failures_key)
        raise HTTPException(status_code=401, detail='Email hoặc mật khẩu chưa đúng, em kiểm tra lại nhé.')
    db.touch_login(user['id'])
    return {'token': db.issue_token(user['id']), 'user': user}


def _check_new_password(password: str) -> None:
    if len(password) < db.PASSWORD_MIN_LENGTH:
        raise HTTPException(status_code=400, detail=f'Mật khẩu cần ít nhất {db.PASSWORD_MIN_LENGTH} ký tự nhé.')


@router.get('/me')
def read_me(user: dict[str, Any] = Depends(db.current_user)) -> dict[str, Any]:
    return {'user': user}


@router.patch('/me')
def update_me(body: ProfilePatch, user: dict[str, Any] = Depends(db.current_user)) -> dict[str, Any]:
    return {'user': db.update_user(user['id'], body.model_dump(exclude_none=True))}


@router.post('/me/password')
def change_password(body: PasswordChange, user: dict[str, Any] = Depends(db.current_user)) -> dict[str, bool]:
    # Shares the sign-in failure window, so a stolen session can't be used to guess the password faster.
    failures_key = f"auth-fail:{user['email']}"
    db.check_rate(failures_key, per_minute=5, per_day=30, record=False,
                  detail='Em nhập sai mật khẩu nhiều lần quá, đợi một lát rồi thử lại nhé.')
    stored_hash = db.get_password_hash(user['id'])
    if stored_hash is not None and not db.verify_password(body.currentPassword, stored_hash):
        db.record_rate(failures_key)
        raise HTTPException(status_code=400, detail='Mật khẩu hiện tại chưa đúng, em kiểm tra lại nhé.')
    _check_new_password(body.newPassword)
    if body.newPassword == body.currentPassword:
        raise HTTPException(status_code=400, detail='Mật khẩu mới cần khác mật khẩu hiện tại nhé.')
    db.set_password(user['id'], body.newPassword)
    return {'success': True}


@router.get('/progress')
def read_progress(subject: str = Query(..., min_length=1, max_length=40), grade: int = Query(..., ge=6, le=9),
                  user: dict[str, Any] = Depends(db.current_user)) -> dict[str, Any]:
    return db.learning_progress(user, subject, grade, concept_prefix(subject, grade))


@router.get('/history')
def read_history(user: dict[str, Any] = Depends(db.current_user)) -> dict[str, Any]:
    return db.load_history(user['id'])


@router.patch('/sessions/{session_id}')
def rename_session(session_id: str, body: SessionPatch, user: dict[str, Any] = Depends(db.current_user)) -> dict[str, bool]:
    db.rename_session(user['id'], session_id, body.title.strip())
    return {'success': True}


@router.delete('/sessions/{session_id}')
def delete_session(session_id: str, user: dict[str, Any] = Depends(db.current_user)) -> dict[str, bool]:
    db.delete_session(user['id'], session_id)
    return {'success': True}


@router.post('/feedback')
def give_feedback(body: FeedbackIn, user: dict[str, Any] = Depends(db.current_user)) -> dict[str, bool]:
    if not db.save_feedback(user['id'], body.message_id, body.rating, body.comment):
        raise HTTPException(status_code=404, detail='Không tìm thấy câu trả lời để đánh giá.')
    return {'success': True}
