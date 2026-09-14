# Tài khoản, lưu dữ liệu & đưa Gia Sư AI lên mạng

## Cách hoạt động

- Học sinh **chỉ cần nhập email** (lần đầu thêm tên và lớp), không có mật khẩu. Sau khi tạo tài khoản sẽ làm khảo sát 3 bước (môn học, mục tiêu, lộ trình).
- Backend FastAPI tự quản lý tài khoản và cấp token đăng nhập, lưu trong trình duyệt 180 ngày.
- Mọi dữ liệu nằm trong database của backend:

| Bảng | Nội dung |
|---|---|
| `users` | Email, tên, lớp, môn, kết quả khảo sát (`onboarding`), tiến độ luyện tập |
| `chat_sessions` / `messages` | Toàn bộ câu hỏi (`prompt`), câu trả lời, nguồn SGK, model, thời gian phản hồi |
| `feedback` | 👍/👎 và góp ý cho từng câu trả lời |
| `quiz_attempts` | Lịch sử làm bài luyện tập |

Bảng được **tạo tự động** khi backend khởi động, không cần chạy SQL bằng tay.

> ⚠️ Không có mật khẩu nên ai biết email của một học sinh cũng có thể đăng nhập bằng email đó. Cách này phù hợp cho dự án học tập hoặc demo; không nên lưu thông tin nhạy cảm.

## Chạy local

Không cần cấu hình gì thêm. Nếu `DATABASE_URL` để trống, backend tự tạo file SQLite `backend/local.db` (không bị đẩy lên GitHub). Cứ chạy như cũ bằng `Chay AI Gia Su.bat`, hoặc chạy backend port 8000 và `npm run dev`.

Xem dữ liệu local: mở `backend/local.db` bằng [DB Browser for SQLite](https://sqlitebrowser.org/) (miễn phí).

## Deploy (miễn phí)

```
GitHub repo ──► Vercel   (frontend React)   VITE_API_BASE_URL
            └─► Render   (backend FastAPI)  GEMINI_*, PINECONE_*, DATABASE_URL, AUTH_SECRET, ALLOWED_ORIGINS
                              │
                        Postgres miễn phí (Supabase hoặc Neon)
```

> Không dùng SQLite trên Render: ổ đĩa gói free bị xóa mỗi lần deploy hoặc restart, mất hết dữ liệu. GitHub Pages cũng không chạy được backend Python.

### 1. Tạo database Postgres (chọn một)

**Supabase** (500MB; project bị tạm dừng nếu 7 ngày không có truy cập, bấm Restore là chạy lại):
1. https://supabase.com → **New project**, đặt mật khẩu database, Region Singapore.
2. Bấm **Connect** → tab **Connection string** → chọn **Session pooler** → copy chuỗi `postgresql://...`, thay `[YOUR-PASSWORD]` bằng mật khẩu. Không dùng "Direct connection" vì Render không kết nối được địa chỉ IPv6.

**Neon** (0.5GB, không bị tạm dừng lâu): https://neon.tech → tạo project → copy **Connection string**.

### 2. Backend lên Render

1. https://render.com → **New → Web Service** → chọn repo GitHub.
2. Build command: `pip install -r backend/requirements.txt`
   Start command: `uvicorn backend.app:app --host 0.0.0.0 --port $PORT --no-proxy-headers`
   (`--no-proxy-headers`: IP thật của học sinh do backend tự đọc theo `TRUSTED_PROXY_HOPS`, không để uvicorn tin header giả)
3. **Environment**: nhập các biến trong [backend/.env.example](backend/.env.example):
   - `DATABASE_URL`: chuỗi ở bước 1
   - `AUTH_SECRET`: chuỗi ngẫu nhiên dài, tạo bằng `python -c "import secrets; print(secrets.token_urlsafe(48))"`
   - `ALLOWED_ORIGINS=https://<ten-app>.vercel.app`
   - `TRUSTED_PROXY_HOPS=1` (Render có 1 proxy phía trước; để giới hạn đăng nhập tính đúng IP thật của học sinh)
   - `GEMINI_API_KEY`, `PINECONE_*` như file `.env` local
4. Mở `https://<ten-backend>.onrender.com/api/health` và kiểm tra thấy `"status": "ok"`.

Gói free của Render "ngủ" sau 15 phút không có truy cập, nên lần mở đầu tiên mất khoảng 30–50 giây. Thư mục `backend/data/` (PDF SGK) không có trên GitHub nên nút **Xem trang** sách không chạy trên server; chat vẫn bình thường.

### 3. Frontend lên Vercel

1. https://vercel.com → **Add New → Project** → chọn repo (Vercel tự nhận Vite).
2. Environment Variables: `VITE_API_BASE_URL=https://<ten-backend>.onrender.com`
3. Deploy.

## Xem feedback trên Postgres

Supabase → **SQL Editor** (hoặc Neon → SQL Editor):

```sql
-- Tỉ lệ thích / không thích
select rating, count(*) from feedback group by rating;

-- Các câu trả lời bị chê kèm câu hỏi
select f.created_at, u.name, u.grade, f.comment,
       (select q.prompt from messages q
         where q.session_id = a.session_id and q.role = 'user' and q.created_at <= a.created_at
         order by q.created_at desc limit 1) as question,
       a.content as answer
from feedback f
join messages a on a.id = f.message_id
join users u on u.id = f.user_id
where f.rating = 'down'
order by f.created_at desc limit 50;
```

## Bảo mật cần nhớ

- Không commit `.env`, `backend/.env`, `backend/local.db`, `backend/.auth_secret` (đã có trong `.gitignore`). Nếu lỡ đẩy API key lên GitHub, **tạo key mới ngay**.
- Mỗi học sinh bị giới hạn `CHAT_RATE_PER_MINUTE` / `CHAT_RATE_PER_DAY` câu hỏi; mỗi địa chỉ IP tối đa 10 lần đăng nhập mỗi phút.
- Học sinh chỉ xem, sửa, xóa được lịch sử và feedback của chính mình.
- Người dùng là học sinh THCS: nên ghi rõ việc lưu nội dung hội thoại để cải thiện chất lượng.
