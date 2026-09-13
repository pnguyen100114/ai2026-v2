# Học cùng AI · Gia sư THCS

Website demo gia sư AI dành cho học sinh THCS, tập trung vào hành trình học Toán lớp 8.

## Tính năng

- Trang chủ với lộ trình, thống kê và nhiệm vụ hằng ngày.
- Roadmap Toán 8 theo tài liệu `SGK Toán 8, Tập một-mau.pdf`, gồm trạng thái bài học và modal chi tiết.
- Pomodoro có thể tùy chỉnh thời lượng, chạy/tạm dừng/đặt lại và lưu mục tiêu phiên.
- Trợ lý AI Mimo với mock chat hướng dẫn giải bài theo từng bước.
- Dashboard tiến độ với XP, chuỗi học, biểu đồ thời gian, điểm số và huy hiệu.
- Responsive sidebar/bottom-friendly layout cho màn hình nhỏ.
- Dashboard Tư thế học tập: mở camera hoặc tải ảnh, gửi tới API YOLO và lưu lịch sử good/bad.

## Chạy dự án

**Cách đơn giản nhất:** nhấp đúp file `Cai dat AI Gia Su.bat`. File sẽ tự động cài thư viện, tạo môi trường Python, khởi động backend nhận diện tư thế, khởi động frontend và mở trình duyệt.

Sau lần đầu, có thể nhấp đúp `Chay AI Gia Su.bat` để khởi động lại.

Xem thông tin đầy đủ tại [SETUP.md](./SETUP.md).

```bash
npm install
npm run dev
```

Mở URL được Vite hiển thị (mặc định là `http://localhost:5173`).

## Kiểm tra

```bash
npm run lint
npm run build
```

Dữ liệu hiện là mock để demo. Có thể thay `getMockAnswer` trong `src/App.tsx` bằng API AI thật khi có backend.

## Chỉnh dữ liệu roadmap

Danh sách bài Toán 8 nằm trong `src/data/math8.ts`. Mỗi bài có `title`, `chapter`, `duration`, `status` và `accent`. Workspace hiện không có file PDF SGK đính kèm, vì vậy hãy thay danh sách này bằng mục lục đã xác minh từ PDF trước khi dùng làm dữ liệu học thuật chính thức.

Tiến độ bài học và lịch sử chat được lưu ở `localStorage` với các khóa `mimo-completed` và `mimo-chat`. Xóa hai khóa này trong DevTools để reset dữ liệu demo.

## Kết nối AI API

Trong `TutorPage`, thay hàm `send` mock bằng `fetch('/api/chat', { method: 'POST', ... })`, sau đó đưa phản hồi API vào `setChat`. Không đặt API key ở frontend; proxy request qua backend để giữ bí mật thông tin xác thực.

## Deploy

Chạy `npm run build`, sau đó deploy thư mục `dist` lên Vercel, Netlify hoặc static hosting bất kỳ. Nếu dùng AI API hoặc nhận diện tư thế, cần deploy backend riêng và cấu hình biến môi trường tương ứng.

## Nhận diện tư thế

Model đã được huấn luyện từ 573 ảnh train, 55 ảnh validation và 27 ảnh test. Weights hiện tại nằm tại `sitting posture.v4-sitting_posture_4keypoint.yolov8\best.pt`, gồm 2 class `Bad` và `Good`.

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r backend\requirements.txt
uvicorn backend.app:app --reload --port 8000
```

Frontend gọi `http://127.0.0.1:8000/predict`. Có thể đổi URL bằng biến `VITE_POSTURE_API_URL`.

Để huấn luyện lại model bằng cấu hình demo nhanh, chạy file `Huấn luyện model tư thế.bat`. Model gốc `yolov8n-pose.pt` sẽ được tải tự động bởi Ultralytics nếu máy có Internet.
