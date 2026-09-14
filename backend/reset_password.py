"""Reset a student's password when they forget it (there is no email sending yet).

Usage, from the project folder:
    .venv\\Scripts\\python.exe -m backend.reset_password hocsinh@example.com MatKhauMoi123

Uses the same DATABASE_URL as the backend (backend/.env), so it works for local SQLite and production Postgres.
"""
from __future__ import annotations

import sys

from backend import db


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    email, password = argv[1], argv[2]
    if len(password) < db.PASSWORD_MIN_LENGTH:
        print(f'Mật khẩu cần ít nhất {db.PASSWORD_MIN_LENGTH} ký tự.')
        return 1
    db.init_db()
    user = db.find_user_by_email(db.normalize_email(email))
    if user is None:
        print(f'Không có tài khoản nào dùng email {email}.')
        return 1
    db.set_password(user['id'], password)
    print(f'Đã đặt lại mật khẩu cho {user["name"]} ({user["email"]}). Nhắc em đổi sang mật khẩu riêng khi có tính năng đổi mật khẩu.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
