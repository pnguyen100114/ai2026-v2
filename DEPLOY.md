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
                              ├── Postgres miễn phí (Supabase hoặc Neon)
                              └── Supabase Storage (ảnh trang SGK render sẵn)
```

> Không dùng SQLite trên Render: ổ đĩa gói free bị xóa mỗi lần deploy hoặc restart, mất hết dữ liệu. GitHub Pages cũng không chạy được backend Python.

### 1. Tạo database Postgres (chọn một)

**Supabase** (500MB; project bị tạm dừng nếu 7 ngày không có truy cập, bấm Restore là chạy lại):
1. https://supabase.com → **New project**, đặt mật khẩu database, Region Singapore.
2. Bấm **Connect** → tab **Connection string** → chọn **Session pooler** → copy chuỗi `postgresql://...`, thay `[YOUR-PASSWORD]` bằng mật khẩu. Không dùng "Direct connection" vì Render không kết nối được địa chỉ IPv6.

**Neon** (0.5GB, không bị tạm dừng lâu): https://neon.tech → tạo project → copy **Connection string**.

### 2. Backend lên Render

Repo đã có sẵn [render.yaml](render.yaml) nên **không phải gõ tay tên biến nào** — gõ sai một ký tự trong tên biến là lỗi rất khó tìm: backend vẫn chạy, chỉ im lặng cư xử sai.

1. https://render.com → **New → Blueprint** (không phải "Web Service") → chọn repo GitHub.
2. Render đọc `render.yaml` và tự điền: build/start command, health check `/api/health`, vùng Singapore, gói Free,
   `TRUSTED_PROXY_HOPS=1`, `ALLOWED_ORIGINS=*`, `PAGE_BUCKET=sgk-pages`, và **tự sinh `AUTH_SECRET`**.
3. Render hỏi 6 giá trị, năm trong số đó copy thẳng từ `backend/.env` ở máy:

   | Render hỏi | Lấy ở đâu |
   |---|---|
   | `DATABASE_URL` | chuỗi Session pooler ở bước 1 |
   | `SUPABASE_URL` · `SUPABASE_SERVICE_KEY` | `backend/.env` (xem bước 3 bên dưới) |
   | `GEMINI_API_KEY` | `backend/.env` |
   | `PINECONE_API_KEY` · `PINECONE_INDEX` | `backend/.env` |

4. Mở `https://<ten-backend>.onrender.com/api/health`, phải thấy `"status": "ok"` và `"vectors"` lớn hơn 0.

`render.yaml` cố ý **không** khai `PINECONE_NAMESPACE`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSION`: mặc định trong code đã khớp với lúc nạp sách, khai thêm rồi điền số khác là hỏng toàn bộ tìm kiếm SGK. `BOOK_PAGE_OFFSETS` cũng không khai: độ lệch trang của từng quyển nằm trong [backend/rag/books.py](backend/rag/books.py) và ghi đè biến môi trường khi nạp sách, nên sửa trên Render không có tác dụng — muốn chỉnh thì sửa `books.py` rồi nạp lại.

Gói free của Render "ngủ" sau 15 phút không có truy cập, nên lần mở đầu tiên mất khoảng 30–50 giây. Build lỗi vì Python thì sửa `PYTHON_VERSION` trong `render.yaml` thành một phiên bản Render liệt kê rồi push lại.

### 3. Ảnh trang SGK lên Supabase Storage

Thư mục `backend/data/` nặng 2,1 GB nên không lên GitHub được → server không có PDF để render nút **Xem trang**. Cách giải quyết: **render sẵn 3.609 trang thành JPEG ở máy của bạn**, upload lên Supabase Storage, server chỉ việc ký link.

1. Vẫn ở project Supabase bước 1 → **Project Settings → API**, copy:
   - **Project URL** → `SUPABASE_URL`
   - **service_role** key → `SUPABASE_SERVICE_KEY` (key này qua mặt được mọi quyền, **chỉ để ở backend**, không bao giờ đưa vào frontend hay commit lên GitHub)
2. Thêm 2 giá trị đó vào `backend/.env` **ở máy local**, rồi chạy một lần:
   ```bash
   python backend/rag/render_pages.py --dry-run   # xem trước dung lượng, chưa upload gì
   python backend/rag/render_pages.py             # render + upload thật
   ```
   Script tự tạo bucket `sgk-pages` ở chế độ **private**. Mạng đứt giữa chừng thì chạy lại — nó chỉ upload phần còn thiếu. Nạp thêm sách mới thì chạy lại, chỉ cuốn mới được upload.
3. Nhập cùng 2 biến `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` vào **Environment của Render**, rồi deploy lại.

Backend tự chọn nguồn ảnh: có `SUPABASE_URL` thì trả về link Supabase (hết hạn sau 1 giờ), không có thì render thẳng từ PDF như cũ. **Nên chạy local vẫn hoạt động bình thường mà không cần cấu hình gì.**

> Bucket để private và link luôn có chữ ký hết hạn, nên không ai tải trộm được cả bộ SGK — giữ đúng cơ chế chống scrape mà backend đang dùng.

**Dung lượng & hạn mức (gói Supabase free: 1 GB lưu trữ, 5 GB băng thông/tháng)**

Cả bộ 29 cuốn = 3.609 trang → 7.218 ảnh (mỗi trang một ảnh đầy đủ + một thumbnail):

| `PAGE_RENDER_SCALE` | Dung lượng | Chỗ trống còn lại |
|---|---|---|
| `1.2` — nét nhất | ~802 MB | 20% — hơi sát |
| **`1.0` — mặc định** | **633 MB** (số đo thật) | 37% |
| `0.8` — tiết kiệm | ~422 MB | 58% |

Muốn rộng chỗ hơn thì đặt `PAGE_RENDER_SCALE=0.8` trước khi chạy script. Về băng thông thì rất thoải mái: một lớp 40 học sinh hỏi 20 câu/tháng chỉ tốn khoảng **70 MB**, tức ~1,4% hạn mức 5 GB.

> Dung lượng database Postgres (500 MB) được Supabase tính riêng, không ăn vào 1 GB storage này.

### 4. Frontend lên Vercel

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
- `SUPABASE_SERVICE_KEY` mạnh hơn mọi key khác trong dự án (đọc/ghi được toàn bộ database lẫn storage, bỏ qua mọi giới hạn). Chỉ đặt trong `backend/.env` và Environment của Render; đừng nhầm sang biến `VITE_*` — mọi biến `VITE_*` đều bị nhúng thẳng vào file JavaScript mà học sinh tải về.
- Mỗi học sinh bị giới hạn `CHAT_RATE_PER_MINUTE` / `CHAT_RATE_PER_DAY` câu hỏi; mỗi địa chỉ IP tối đa 10 lần đăng nhập mỗi phút.
- Học sinh chỉ xem, sửa, xóa được lịch sử và feedback của chính mình.
- Người dùng là học sinh THCS: nên ghi rõ việc lưu nội dung hội thoại để cải thiện chất lượng.
