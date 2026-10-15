# Mimo — Gia sư AI học theo sách giáo khoa cho học sinh THCS

Mimo là gia sư AI cho học sinh lớp 6 đến lớp 9. Khác với chatbot thông thường, Mimo **trả lời dựa trên
đúng sách giáo khoa các em đang học**: mỗi câu lấy từ sách đều có số trích dẫn `[1]`, bấm vào là mở ra
ảnh đúng trang sách đó.

Ba nguyên tắc sản phẩm được xây quanh:

- **Không giải hộ.** Gặp bài tập, Mimo gợi ý bước đầu rồi hỏi lại để em tự làm tiếp.
- **Nói theo sách.** Thuật ngữ và cách giải bám bộ *Kết nối tri thức với cuộc sống*, chương trình GDPT 2018.
- **An toàn cho trẻ em.** Tin nhắn có dấu hiệu bị bắt nạt hoặc tự làm hại được xử lý riêng, luôn kèm số
  Tổng đài quốc gia bảo vệ trẻ em 111 — kể cả khi mô hình AI lỗi hoặc hết lượt.

## Sản phẩm làm được gì

| Chức năng | Mô tả |
|---|---|
| Hỏi bài | Gõ, chụp ảnh đề hoặc bấm micro nói. Câu trả lời hiện dần từng chữ (SSE), công thức toán render bằng KaTeX |
| Trích dẫn trang sách | Câu lấy từ SGK có số `[1]`, `[2]`; bấm vào mở ảnh đúng trang |
| Lộ trình học | Dựng theo mục lục sách (chương, bài, số trang). Môn/lớp chưa có mục lục thì AI tự soạn theo GDPT 2018 |
| Luyện tập thích ứng | Mimo tự soạn câu trắc nghiệm cho bài đang học; đúng liên tiếp thì khó lên, sai thì ôn lại |
| Nghe giảng | Đọc câu trả lời bằng giọng tiếng Việt (edge-tts, giọng HoaiMy) |
| Pomodoro | Hẹn giờ học tập trung, cộng vào nhiệm vụ hằng ngày |
| Hồ sơ & tiến độ | XP, chuỗi ngày học, lịch sử hỏi đáp, đánh giá 👍/👎 từng câu trả lời |

## Kiến trúc

```
React + Vite (Vercel)  ──►  FastAPI (Render)  ──►  Gemini  (giảng bài, đọc ảnh đề, soạn quiz)
                                   │                Gemini Embedding  (vector hoá)
                                   ├──►  Postgres + pgvector   tài khoản, chat, quiz, kho vector SGK
                                   └──►  Supabase Storage      ảnh trang SGK render sẵn
```

Kho vector nằm trong **chính database của dự án** (bảng `sgk_chunks`), không dùng dịch vụ vector ngoài —
xem [backend/rag/vector_store.py](backend/rag/vector_store.py).

Chạy local mà để trống `DATABASE_URL` thì backend tự dùng SQLite `backend/local.db`.

## Chạy dự án

**Cách đơn giản nhất (Windows):** nhấp đúp `Cai dat AI Gia Su.bat`. File tự cài thư viện, tạo môi trường
Python, khởi động backend và frontend, rồi mở trình duyệt. Lần sau chỉ cần `Chay AI Gia Su.bat`.

**Thủ công:**

```bash
npm install
npm run dev                  # frontend  → http://127.0.0.1:5173

python -m venv .venv
.venv\Scripts\activate
pip install -r backend\requirements.txt
cp backend\.env.example backend\.env      # rồi điền GEMINI_API_KEY
uvicorn backend.app:app --reload --port 8000    # backend → http://127.0.0.1:8000
```

Hướng dẫn từng bước cho người mới: [SETUP.md](SETUP.md). Đưa lên mạng: [DEPLOY.md](DEPLOY.md).

## Nạp sách giáo khoa vào kho

Sách PDF đặt trong `backend/data/` (thư mục này **không** được đẩy lên GitHub vì dung lượng lớn).
Mỗi cuốn phải được khai trong [backend/rag/books.py](backend/rag/books.py) trước — file đó là nguồn sự
thật duy nhất về môn, lớp, độ lệch trang và mục lục.

```bash
python backend\rag\check_pdf.py            # kiểm tra PDF có lớp chữ chưa (bản scan ảnh sẽ không nạp được)
python backend\rag\ingest.py               # nạp sách chưa nạp vào kho vector
python backend\rag\render_pages.py         # render ảnh trang lên Supabase Storage (chỉ cần khi deploy)
```

## Kiểm tra

```bash
npm run lint
npm run build
.venv\Scripts\python.exe -m pytest      # 214 ca kiểm thử backend
```

Ngoài pytest còn có bộ kiểm thử chất lượng trả lời, chạy qua **API đã deploy** chứ không gọi hàm trong máy:

```bash
python bao-cao\bo-test\chay_test.py     # 28 ca: dễ, khó, ngoài sách, phải từ chối, mơ hồ, bẫy
python bao-cao\bo-test\lam_bang.py      # → bao-cao/bo-test/KET_QUA_TEST.md
```

## Bảo mật

- Đăng nhập bằng email + mật khẩu, backend cấp token JWT. Mật khẩu được băm, chặn đoán mật khẩu theo
  từng email lẫn theo IP.
- **Không** đặt API key ở frontend. Mọi lệnh gọi Gemini đi qua backend.
- File `backend/.env` và `backend/local.db` nằm trong `.gitignore`, tuyệt đối không commit.

## Hồ sơ dự án

Hồ sơ dự thi, biểu đồ, ảnh minh chứng và kịch bản video nằm trong [bao-cao/](bao-cao/).
Lịch sử câu lệnh đã dùng với công cụ AI nằm trong [prompt-log/](prompt-log/).
