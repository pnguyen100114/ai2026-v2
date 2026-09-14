# SETUP ĐẦY ĐỦ - AI GIA SƯ THCS     


Tài liệu này dành cho người mới sử dụng Windows. Làm theo đúng thứ tự để chạy website, API nhận diện tư thế và camera AI.

## 1. Thành phần của dự án

Website gồm:

- Frontend React/Vite: trang chủ, đăng nhập, khảo sát, roadmap, Pomodoro, trợ lý AI và tiến độ.
- Dashboard **Tư thế học tập**: mở camera để tự động nhận diện `good/bad` mỗi vài giây hoặc tải ảnh lên.
- Backend FastAPI: nhận ảnh và chạy model YOLO.
- Model YOLO đã huấn luyện: `sitting posture.v4-sitting_posture_4keypoint.yolov8\best.pt`.

Model chỉ nhận diện **tư thế ngồi**, không nhận diện bạo lực và không nhận diện khuôn mặt.

## 2. Cấu hình máy tối thiểu

- Windows 10 hoặc Windows 11.
- Node.js LTS 20 trở lên.
- Python 3.10 - 3.12, khuyến nghị Python 3.12.
- RAM tối thiểu 8GB.
- Trình duyệt Chrome hoặc Edge phiên bản mới.
- Camera nếu muốn dùng nhận diện trực tiếp.
- Khoảng 5GB dung lượng trống để cài thư viện AI.

## 3. Cách nhanh nhất cho người mới - chỉ cần nhấp đúp

1. Cài [Node.js LTS](https://nodejs.org/).
2. Cài [Python 3.12](https://www.python.org/downloads/). Khi cài nhớ chọn **Add Python to PATH**.
3. Giải nén toàn bộ file ZIP vào một thư mục, không mở ứng dụng trực tiếp bên trong file ZIP.
4. Mở thư mục project và nhấp đúp file **`Cai dat AI Gia Su.bat`**.
5. File sẽ tự động cài frontend, tạo môi trường Python, cài backend, build project, khởi động API, khởi động website và mở trình duyệt.
6. Lần đầu có thể mất vài phút vì phải tải thư viện AI.
7. Sau lần cài đầu tiên, chỉ cần nhấp đúp **`Chay AI Gia Su.bat`**. File này cũng tự gọi bộ cài nếu thiếu thư viện.
8. Không đóng hai cửa sổ Backend và Frontend được mở ở chế độ thu nhỏ trong lúc sử dụng.

Nếu Windows hiện cảnh báo SmartScreen, chọn **More info** → **Run anyway** khi bạn tin cậy file dự án.

## 4. Cài frontend lần đầu

Mở PowerShell trong thư mục dự án:

```powershell
cd "C:\Users\HP\Desktop\Sáng tạo AI"
npm install
```

Nếu `npm` không được nhận diện, hãy đóng PowerShell, mở cửa sổ mới rồi thử lại.

## 5. Chạy website

```powershell
cd "C:\Users\HP\Desktop\Sáng tạo AI"
npm run dev
```

Mở địa chỉ:

<http://127.0.0.1:5173>

Người mới không cần chạy các lệnh trên; chỉ cần nhấp đúp **`Chay AI Gia Su.bat`**. Để dừng frontend, đóng cửa sổ Frontend hoặc nhấn `Ctrl + C`.

## 6. Cài và chạy backend nhận diện tư thế

### 6.1. Tạo môi trường Python

Thông thường không cần chạy thủ công: `Cai dat AI Gia Su.bat` tự tạo môi trường `.venv` ngay trong thư mục dự án. Nếu cần chạy bằng lệnh:

Chạy một lần:

```powershell
cd "C:\Users\HP\Desktop\Sáng tạo AI"
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

Nếu lệnh `py` không có, dùng đường dẫn Python đã cài:

```powershell
python -m venv .venv
```

### 6.2. Khởi động API

Mở PowerShell mới:

```powershell
cd "C:\Users\HP\Desktop\Sáng tạo AI"
.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

Giữ cửa sổ này mở trong lúc sử dụng camera.

Kiểm tra API bằng cách mở:

<http://127.0.0.1:8000/api/health>

Kết quả đúng có dạng:

```json
{"ok": true, "model": "...best.pt"}
```

Frontend gọi API tại:

```text
http://127.0.0.1:8000/predict
```

Nếu muốn đổi địa chỉ API, tạo file `.env.local` trong thư mục dự án:

```env
VITE_POSTURE_API_URL=http://127.0.0.1:8000
```

Sau khi đổi biến môi trường, cần khởi động lại `npm run dev`.

## 7. Sử dụng camera tự động

1. Khởi động frontend và backend.
2. Đăng ký hoặc đăng nhập.
3. Mở **Tư thế học tập** trong menu.
4. Nhấn **Bật camera & nhận diện**.
5. Cho phép quyền Camera trên trình duyệt.
6. Đặt camera ngang tầm mắt, đủ sáng và ngồi cách camera vừa phải.
7. AI tự gửi khung hình khoảng mỗi 4 giây, không cần nhấn nút chụp.
8. Xem kết quả `good/bad`, độ tin cậy và lời khuyên ở bên phải.
9. Nhấn **Tắt camera** khi dùng xong.

Ảnh gửi tới backend chỉ dùng cho lần nhận diện. Ứng dụng không lưu video camera.

### Nếu trình duyệt không cho phép camera

- Dùng `http://127.0.0.1:5173`, không dùng đường dẫn file `file://`.
- Nhấn biểu tượng khóa bên trái thanh địa chỉ và bật Camera.
- Kiểm tra Windows Settings → Privacy & security → Camera.
- Đóng ứng dụng khác đang chiếm camera.
- Thử Chrome hoặc Edge mới nhất.

## 8. Luồng demo đầy đủ

1. Chọn **Đăng ký tài khoản**.
2. Nhập họ tên, email/tài khoản, mật khẩu và lớp.
3. Chọn môn học, mục tiêu và số phút học mỗi ngày.
4. Chọn lộ trình đúng lớp hoặc vượt cấp.
5. Làm bài kiểm tra đầu vào nếu chọn vượt cấp.
6. Mở roadmap để học theo chương; chương sau chỉ mở khi hoàn thành chương trước.
7. Dùng Pomodoro: thời gian học và nghỉ tự động chuyển theo timestamp.
8. Mở Trợ lý AI để hỏi bài.
9. Mở Tư thế học tập để bật camera nhận diện tự động.
10. Mở Tiến độ để xem XP, chuỗi học, phiên Pomodoro và lịch sử.

### Nạp dữ liệu curriculum vào Pinecone

Roadmap và AI Tutor cần vector dữ liệu trong Pinecone. Sau khi đặt các PDF SGK vào thư mục `backend/data`, chạy từ thư mục gốc dự án:

```powershell
.venv\Scripts\python.exe -m backend.rag.ingest
```

Tên file PDF cần chứa môn và lớp, ví dụ `toan8_tap1.pdf`, để hệ thống tự nhận diện metadata. Kiểm tra kết quả bằng:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/api/health | Select-Object -ExpandProperty Content
```

Trường `rag.vectors` phải lớn hơn `0`. Sau khi nạp xong, khởi động lại backend rồi tải lại trang roadmap.

Dữ liệu demo được lưu trong `localStorage` của trình duyệt, chưa dùng cơ sở dữ liệu thật.

## 9. Kiểm tra dự án

```powershell
cd "C:\Users\HP\Desktop\Sáng tạo AI"
npm run lint
npm run build
```

Xem bản production:

```powershell
npm run preview
```

## 10. Huấn luyện lại model

Model hiện tại đã có sẵn tại:

```text
sitting posture.v4-sitting_posture_4keypoint.yolov8\best.pt
```

Dataset gồm 573 ảnh train, 55 ảnh validation và 27 ảnh test.

Để huấn luyện lại bằng cấu hình demo:

1. Đảm bảo đã cài môi trường `.venv` bằng file `Cai dat AI Gia Su.bat`.
2. Nhấp đúp **`Huấn luyện model tư thế.bat`**.
3. Chờ script hoàn tất.
4. Weights mới sẽ được chép vào thư mục model và backend dùng ở lần khởi động tiếp theo.

Hoặc chạy:

```powershell
cd "C:\Users\HP\Desktop\Sáng tạo AI"
.venv\Scripts\python.exe backend\train_model.py
```

Huấn luyện trên CPU có thể mất nhiều thời gian. Không xóa `best.pt` nếu chưa có weights mới.

## 11. Xóa dữ liệu demo để đăng ký lại

Nếu website tự động đăng nhập tài khoản cũ:

1. Mở website.
2. Nhấn `F12`.
3. Chọn **Application** hoặc **Storage**.
4. Chọn **Local Storage** → địa chỉ website.
5. Xóa các khóa bắt đầu bằng `ai-tutor-`.
6. Tải lại trang bằng `Ctrl + R`.

## 12. Các lỗi thường gặp

### `node is not recognized` hoặc `npm is not recognized`

Cài Node.js LTS, đóng toàn bộ PowerShell rồi mở lại cửa sổ mới.

### `python is not recognized`

Cài Python 3.12 và chọn **Add Python to PATH**, hoặc dùng trực tiếp:

```powershell
.venv\Scripts\python.exe
```

### Không kết nối được backend

- Kiểm tra cửa sổ uvicorn còn đang chạy.
- Mở <http://127.0.0.1:8000/api/health>.
- Kiểm tra frontend đang gọi đúng `VITE_POSTURE_API_URL`.
- Khởi động backend từ đúng thư mục dự án.

### Cổng 5173 hoặc 8000 đã được sử dụng

Frontend:

```powershell
npm run dev -- --port 5174
```

Backend:

```powershell
.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8001
```

Nếu đổi cổng backend, cập nhật `.env.local` rồi chạy lại frontend.

### Cài thư viện bị lỗi

Đóng server và thử:

```powershell
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

Với frontend:

```powershell
Remove-Item -Recurse -Force node_modules
npm install
```

## 13. Cấu trúc thư mục chính

```text
Sáng tạo AI/
├── src/
│   ├── App.tsx                  # Giao diện và logic ứng dụng
│   ├── App.css                  # Giao diện responsive
│   └── index.css                # CSS nền
├── backend/
│   ├── app.py                   # API FastAPI /health và /predict
│   ├── train_model.py           # Script huấn luyện YOLO
│   └── requirements.txt         # Thư viện Python
├── sitting posture...yolov8/
│   ├── best.pt                  # Model đang sử dụng
│   └── train.yaml               # Cấu hình dataset
├── Chay AI Gia Su.bat           # Mở frontend nhanh
├── Huấn luyện model tư thế.bat  # Huấn luyện lại model
├── package.json                 # Lệnh và thư viện frontend
├── README.md                    # Tổng quan dự án
└── SETUP.md                     # Tài liệu cài đặt này
```

## 14. Ghi chú bảo mật và phạm vi demo

- Tài khoản chỉ lưu local trên máy, mật khẩu chưa phù hợp cho production.
- AI trợ lý hiện là mock service.
- Model tư thế là bản demo huấn luyện nhanh trên CPU, độ chính xác thực tế phụ thuộc ánh sáng, góc camera và dữ liệu.
- Không dùng kết quả model cho mục đích y tế hoặc đánh giá kỷ luật học sinh.
