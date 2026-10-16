# Ghi chú cho Claude

## Chạy backend ở máy

- Bật hoặc khởi động lại backend **chỉ** bằng `scripts\restart-backend.ps1`, chạy nền (`run_in_background`):
  `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\restart-backend.ps1`.
  Script tắt mọi uvicorn đang giữ cổng 8000 rồi bật lại với `--reload`.
- Không gọi thẳng `uvicorn ... --port 8000`. Nếu một phiên khác đã bật backend thì lệnh mới lỗi
  `[Errno 10048]`, còn bản cũ vẫn chạy code trước khi sửa. Đã từng xảy ra.
- Sau khi sửa `backend/` mà không chắc backend đang chạy có `--reload`, chạy lại script trước khi kiểm tra
  bằng app hay bằng `curl http://127.0.0.1:8000/...`. `Chay AI Gia Su.bat` cũng gọi script này.
- Lỗi "khởi động backend" thất bại ở tác vụ nền thì đọc output, đừng coi bản đang trả lời ở cổng 8000 là bản mới.
