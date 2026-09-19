# Hướng dẫn cài đặt đầy đủ — Mimo, Gia sư AI THCS

Tài liệu này dành cho người mới dùng Windows. Làm theo đúng thứ tự để chạy được website và backend AI.

Muốn đưa sản phẩm lên mạng cho người khác dùng, xem [DEPLOY.md](DEPLOY.md).

## 1. Thành phần của dự án

| Thành phần | Nội dung |
|---|---|
| Frontend React + Vite | Đăng nhập, khảo sát đầu vào, trang chủ, lộ trình học, hỏi bài, luyện tập, Pomodoro, hồ sơ tiến độ |
| Backend FastAPI | Gọi Gemini, tìm kiếm SGK, quản lý tài khoản, luyện tập thích ứng, lọc tin nhắn nguy hiểm |
| Kho vector SGK | Bảng `sgk_chunks` nằm trong chính database của dự án — không dùng dịch vụ vector ngoài |
| Database | Postgres khi deploy; để trống `DATABASE_URL` khi chạy local thì tự dùng SQLite `backend/local.db` |

Dự án **cần khóa API Gemini** để chạy. Không có khóa thì giao diện vẫn mở được nhưng Mimo không trả lời.

## 2. Cấu hình máy tối thiểu

- Windows 10 hoặc Windows 11.
- Node.js LTS 20 trở lên.
- Python 3.12 hoặc 3.13 (PyMuPDF có sẵn bản cài cho hai phiên bản này).
- RAM tối thiểu 8GB.
- Trình duyệt Chrome hoặc Edge bản mới.
- Micro nếu muốn dùng nút hỏi bài bằng giọng nói.
- Khoảng 2GB dung lượng trống cho thư viện.

## 3. Cách nhanh nhất — chỉ cần nhấp đúp

1. Cài [Node.js LTS](https://nodejs.org/).
2. Cài [Python 3.12](https://www.python.org/downloads/). Khi cài nhớ chọn **Add python.exe to PATH**.
3. Cài [Git](https://git-scm.com/download/win).
4. Giải nén toàn bộ file ZIP vào một thư mục — không mở trực tiếp từ bên trong file ZIP.
5. Tạo file `backend\.env` (xem mục 4) rồi điền `GEMINI_API_KEY`.
6. Nhấp đúp **`Cai dat AI Gia Su.bat`**. File sẽ tự cài thư viện giao diện, tạo môi trường Python,
   cài thư viện backend, build, khởi động cả hai và mở trình duyệt.
7. Lần đầu có thể mất vài phút. Sau đó chỉ cần nhấp đúp **`Chay AI Gia Su.bat`**.
8. Không đóng hai cửa sổ **Backend** và **Frontend** đang chạy thu nhỏ.

Nếu Windows hiện cảnh báo SmartScreen, chọn **More info** → **Run anyway**.

## 4. Khóa API và file `.env`

1. Lấy khóa miễn phí tại <https://aistudio.google.com/apikey>.
2. Chép `backend\.env.example` thành `backend\.env`.
3. Mở `backend\.env` bằng Notepad, điền khóa vào dòng `GEMINI_API_KEY=`.

```powershell
Copy-Item backend\.env.example backend\.env
notepad backend\.env
```

Các biến còn lại đều có giá trị mặc định hợp lý, để trống cũng chạy được. Ý nghĩa từng biến được
ghi chú ngay trong `backend\.env.example`.

> ⚠️ `backend\.env` nằm trong `.gitignore`. **Tuyệt đối không commit file này lên GitHub.**

## 5. Cài và chạy thủ công

Nếu không dùng file `.bat`, mở PowerShell tại thư mục dự án:

```powershell
# --- frontend ---
npm install
npm run dev                  # → http://127.0.0.1:5173

# --- backend (mở cửa sổ PowerShell thứ hai) ---
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

Kiểm tra backend đã sống chưa:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/api/health | Select-Object -ExpandProperty Content
```

Frontend mặc định gọi `http://127.0.0.1:8000`. Đổi địa chỉ backend bằng biến `VITE_API_BASE_URL`
trong file `.env.local` ở thư mục gốc.

## 6. Luồng demo đầy đủ

1. Bấm **Tạo tài khoản mới**, nhập tên, email, mật khẩu và lớp.
2. Làm khảo sát: chọn môn học, mục tiêu và số phút học mỗi ngày.
3. Mở **Lộ trình** — danh sách bài dựng theo mục lục sách giáo khoa, mỗi bài có chương, tên bài, số trang.
4. Chọn một bài rồi mở **Hỏi bài**. Thử cả ba cách: gõ chữ, chụp ảnh đề bài, bấm micro nói.
5. Xem câu trả lời hiện dần từng chữ. Bấm số `[1]` để mở ảnh đúng trang sách được trích.
6. Bấm biểu tượng loa để nghe Mimo đọc bài giảng.
7. Bấm **Luyện tập** để làm trắc nghiệm — trả lời đúng liên tiếp thì câu sau khó hơn.
8. Mở **Pomodoro** để học tập trung, thời gian được cộng vào nhiệm vụ hằng ngày.
9. Mở **Hồ sơ** để xem XP, chuỗi ngày học và lịch sử hỏi đáp.

## 7. Nạp sách giáo khoa vào kho vector

Lộ trình học và phần hỏi bài có trích dẫn đều cần kho vector SGK. Đặt các file PDF vào `backend\data`.

> Nạp vào database nào là do `DATABASE_URL` lúc chạy lệnh quyết định. Để trống → nạp vào SQLite ở máy.
> Muốn nạp lên bản đã deploy thì đặt `DATABASE_URL` trỏ vào Postgres đó rồi chạy đúng lệnh dưới đây;
> vector đã nằm trong cache nên lần nạp thứ hai gần như không tốn quota.

**Bước 1 — khai báo sách.** Mỗi cuốn phải có một dòng `Book(...)` trong
[backend/rag/books.py](backend/rag/books.py): môn, lớp, tập, tên file PDF và độ lệch trang.
File này là nguồn sự thật duy nhất. Thiếu khai báo thì bìa, mục lục và trang quảng cáo cũng bị nạp theo.

**Bước 2 — kiểm tra PDF.** Nhiều bản SGK tải trên mạng là scan ảnh: người đọc được nhưng máy không
trích được chữ nào. Nạp loại này chỉ tốn quota và làm bẩn kết quả tìm kiếm.

```powershell
.venv\Scripts\python.exe -m backend.rag.check_pdf
```

Quyển nào báo `SCAN ẢNH` thì phải tìm bản PDF khác. Cách tự kiểm tra: mở PDF rồi thử bôi đen một dòng
chữ trong bài học — bôi được là dùng được.

**Bước 3 — nạp.** Chạy từ thư mục gốc dự án:

```powershell
.venv\Scripts\python.exe -m backend.rag.ingest                  # chỉ nạp quyển chưa có
.venv\Scripts\python.exe -m backend.rag.ingest "KHTN 6.pdf"     # nạp một quyển
.venv\Scripts\python.exe -m backend.rag.ingest --force          # nạp lại cả quyển đã có
```

Lệnh nạp theo từng quyển và ghi nhận vào `backend/rag/.ingest_manifest.json`, nên dừng giữa chừng
(hết quota, mất mạng, `Ctrl + C`) vẫn giữ nguyên các quyển đã xong. Lệnh cũng hỏi thẳng kho xem quyển
đó đã có chưa, nên nạp sang một database mới sẽ nạp lại đầy đủ chứ không bị manifest cũ làm bỏ qua.
Mọi vector tạo ra đều lưu vào `backend/rag/.embed_cache.sqlite3`, vì vậy chạy lại gần như không tốn quota.

Gói miễn phí Gemini giới hạn **100 text mỗi phút**, mà mỗi đoạn sách tính là một request — nên tốc độ
khoảng 100 đoạn mỗi phút. Bật billing thì tăng `EMBED_RPM` trong `.env`.

**Kiểm tra kết quả:**

```powershell
Invoke-WebRequest http://127.0.0.1:8000/api/health | Select-Object -ExpandProperty Content
```

Trường `rag.vectors` phải lớn hơn `0`. Trường `rag.backend` cho biết đang tìm kiếm bằng `pgvector` hay
`memory`. Nạp xong thì khởi động lại backend rồi tải lại trang lộ trình.

**Ảnh trang sách (chỉ cần khi deploy).** Thư mục PDF không đẩy lên GitHub được, nên bản deploy không có
gì để render nút "Xem trang". Chạy một lần ở máy có PDF để render sẵn rồi upload lên Supabase Storage:

```powershell
.venv\Scripts\python.exe backend\rag\render_pages.py
```

## 8. Kiểm tra dự án

```powershell
npm run lint
npm run build
.venv\Scripts\python.exe -m pytest        # 214 ca kiểm thử backend
```

Bộ kiểm thử chất lượng trả lời chạy qua **API đã deploy**, không gọi hàm trong máy — để số liệu phản
ánh đúng thứ người dùng mở, gồm cả mạng, máy chủ và biến môi trường:

```powershell
.venv\Scripts\python.exe bao-cao\bo-test\chay_test.py     # 28 ca
.venv\Scripts\python.exe bao-cao\bo-test\lam_bang.py      # → bao-cao/bo-test/KET_QUA_TEST.md
```

Muốn chạy bộ này với backend ở máy: thêm `--api http://127.0.0.1:8000`.

## 9. Xóa dữ liệu ở trình duyệt để đăng nhập lại

Nếu website tự động đăng nhập tài khoản cũ:

1. Mở website, nhấn `F12`.
2. Chọn tab **Application** (hoặc **Storage**).
3. Chọn **Local Storage** → địa chỉ website.
4. Xóa khóa `gia-su-ai-token` và các khóa bắt đầu bằng `aiTutor_`.
5. Tải lại trang bằng `Ctrl + R`.

Dữ liệu tài khoản, lịch sử chat và kết quả luyện tập nằm trong database của backend, không nằm ở trình
duyệt. Xóa localStorage chỉ là đăng xuất, không mất dữ liệu học.

## 10. Các lỗi thường gặp

### `node is not recognized` hoặc `npm is not recognized`

Cài Node.js LTS, đóng toàn bộ cửa sổ PowerShell rồi mở lại cửa sổ mới.

### `python is not recognized`

Cài Python 3.12 và chọn **Add python.exe to PATH**, hoặc gọi thẳng `.venv\Scripts\python.exe`.

### Mimo không trả lời, giao diện báo lỗi

- Kiểm tra `backend\.env` đã có `GEMINI_API_KEY` chưa.
- Mở <http://127.0.0.1:8000/api/health>, xem trường `rag.gemini_key` có phải `true` không.
- Hết lượt gói miễn phí thì backend tự chuyển sang model dự phòng; hết cả ba thì phải đợi sang ngày mới.

### Hỏi bài được nhưng không có số trích dẫn `[1]`

Kho vector chưa có sách. Mở `/api/health` xem `rag.vectors`; bằng `0` thì quay lại mục 7 để nạp sách.

### Không kết nối được backend

- Kiểm tra cửa sổ uvicorn còn đang chạy.
- Mở <http://127.0.0.1:8000/api/health>.
- Kiểm tra frontend đang gọi đúng `VITE_API_BASE_URL`.
- Chạy backend từ đúng thư mục gốc dự án.

### Micro không dùng được

Trình duyệt chỉ cho ghi âm khi trang mở bằng `https://` hoặc `localhost`. Mở bằng địa chỉ IP trong mạng
LAN sẽ không ghi âm được.

### Cổng 5173 hoặc 8000 đã được sử dụng

```powershell
npm run dev -- --port 5174
.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8001
```

Đổi cổng backend thì phải cập nhật `VITE_API_BASE_URL` trong `.env.local` rồi chạy lại frontend.

### Cài thư viện bị lỗi

```powershell
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt

Remove-Item -Recurse -Force node_modules
npm install
```

## 11. Cấu trúc thư mục chính

```
AI2026-v2/
├── src/                          # Frontend React
│   ├── App.tsx                   # Trang chủ, lộ trình, hỏi bài, điều hướng
│   ├── components/               # AuthPage, Onboarding, ProfilePage, PomodoroState…
│   ├── contexts/                 # AuthContext, PomodoroContext
│   ├── services/                 # chatRepository, storageService
│   └── lib/                      # api.ts (gọi backend), audio.ts (ghi âm)
├── backend/
│   ├── app.py                    # FastAPI: chat streaming, quiz, lộ trình, giọng đọc, health
│   ├── accounts.py               # Đăng ký, đăng nhập, hồ sơ, tiến độ, feedback
│   ├── db.py                     # Bảng dữ liệu và truy vấn (SQLAlchemy)
│   ├── learning.py               # Luyện tập thích ứng: độ khó, mức nắm bài
│   ├── safety.py                 # Lọc tin nhắn nguy hiểm, số tổng đài 111
│   ├── rag/
│   │   ├── books.py              # Danh mục sách + mục lục — nguồn sự thật
│   │   ├── ingest.py             # Nạp sách vào kho vector
│   │   ├── retriever.py          # Tìm đoạn sách gần nghĩa nhất
│   │   ├── vector_store.py       # Kho vector trong database dự án
│   │   └── render_pages.py       # Render ảnh trang SGK lên Supabase Storage
│   ├── tests/                    # 214 ca pytest
│   └── data/                     # PDF sách giáo khoa (không đẩy lên GitHub)
├── bao-cao/                      # Hồ sơ dự thi, biểu đồ, bộ kiểm thử chất lượng
├── prompt-log/                   # Lịch sử câu lệnh đã dùng với công cụ AI
├── Cai dat AI Gia Su.bat         # Cài đặt tự động
└── Chay AI Gia Su.bat            # Khởi động lại sản phẩm
```

## 12. Ghi chú bảo mật và phạm vi

- Đăng nhập bằng email + mật khẩu; mật khẩu được băm trước khi lưu. Backend chặn đoán mật khẩu theo
  từng email (5 lần/phút) lẫn theo IP.
- Khóa API Gemini chỉ nằm ở backend, không bao giờ gửi xuống trình duyệt.
- Mimo là sản phẩm học tập, **không thay thế thầy cô hay người lớn**. Khi học sinh nhắn về chuyện bị
  bắt nạt hoặc muốn tự làm hại mình, Mimo luôn khuyên nói với người lớn tin cậy và đưa số Tổng đài
  quốc gia bảo vệ trẻ em 111.
- Câu trả lời của AI không tất định: cùng một câu hỏi có lần kèm trích dẫn, có lần không. Kiến thức
  quan trọng vẫn nên đối chiếu lại với sách.
