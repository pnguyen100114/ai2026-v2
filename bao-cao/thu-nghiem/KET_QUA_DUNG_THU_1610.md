# Buổi học sinh dùng thử sáng 16/10/2026: số liệu từ hệ thống

Số liệu dưới đây đọc từ database production ngày 17/10, chỉ lấy số tổng hợp, không ghi tên hay email.
Khung giờ: 16/10/2026, 8:30–11:30 giờ Việt Nam. Bỏ tài khoản kiểm thử (`@example.com`, có chữ `test`).

**Chưa có**: kết quả Google Form (Mimo có giải hộ không, em có tự làm tiếp được không, thang 1–5) và phiếu
quan sát `phieu_quan_sat.csv` (đang để trống). Hai phần này chỉ người tổ chức buổi thử có.

## Ai dùng, dùng bao lâu

| Chỉ số | Giá trị |
| --- | --- |
| Số bạn có đặt câu hỏi | 34 (hồ sơ đều ghi lớp 7) |
| Số câu hỏi | 368 |
| Câu hỏi mỗi bạn | trung vị 9 (ít nhất 1, nhiều nhất 42) |
| Thời gian từ câu đầu tới câu cuối của mỗi bạn | trung vị 17 phút (dài nhất 50 phút) |
| Số cuộc trò chuyện | 69 |
| Câu hỏi theo môn | Toán 192 · Tiếng Anh 107 · LSĐL 47 · Ngữ văn 13 · KHTN 8 (+1 câu Ngữ văn 9) |
| Câu gửi kèm ảnh đề | 0 |

## Mimo trả lời ra sao

| Chỉ số | Giá trị |
| --- | --- |
| Mô hình trả lời | `gemini-3.1-flash-lite`, cả 368 câu (không lần nào phải chuyển mô hình dự phòng) |
| Độ trễ | trung vị 3,1 giây · 90% câu dưới 3,8 giây |
| Câu trả lời có trích trang sách | **36/368** (chưa rõ lý do, xem mục cuối) |
| Mức hiểu bài Mimo ước lượng | đã hiểu 113 · hiểu sơ 92 · mất gốc 1 (còn lại không đánh giá: chào hỏi, chuyện ngoài lề) |
| Câu có chữ xin đáp án / giải hộ (đếm theo từ khóa) | 8 câu, của 4 bạn |
| Đánh giá 👍 / 👎 | 4 👍 · 0 👎 |
| Báo "Trang này không đúng?" | 0 (nút này mới có từ 17/10, sau buổi thử) |

## Luyện tập thích ứng

| Chỉ số | Giá trị |
| --- | --- |
| Lượt làm | 178, của 14 bạn |
| Làm đúng | 100/178 (56%) |
| Lượt có mở gợi ý | 5 |
| Độ khó các câu | mức 2: 74 · mức 3: 88 · mức 4: 16 |
| Tag lỗi gặp nhiều nhất | hiểu sai khái niệm 26 · nhầm ngữ pháp 14 · nguyên nhân – kết quả 13 · trình tự thời gian 7 · nhầm từ vựng 5 |

## Từ buổi thử tới sản phẩm

Trong buổi thử, vài bạn báo Mimo mở "lệch trang, không đúng bài" (Prompt Log 16/10, 16:37). Hôm sau nhóm thêm nút
**"Trang này không đúng?"** để học sinh báo trang sai ngay trên ảnh trang sách, lưu vào bảng `source_reports`
(commit 187973f), và dọn các đoạn bìa, mục lục khỏi kho vector.

## Vì sao chỉ 36/368 câu trả lời có trích trang

Đọc nội dung tin nhắn ngày 17/10 (người dùng cho phép), chỉ đọc, không chép tên ra đây.

**1. Phần lớn lượt chat không phải câu hỏi bài.** Câu hỏi trung vị chỉ 21 ký tự: "Đáp án là B ạ", "1. collects",
"ko", "Em làm xong rồi đây", "Kiểm tra nhanh em nhé", "Để em tính thử rồi báo Mimo". Đây là học sinh trả lời
hoặc nói chuyện tiếp với Mimo, không cần trang sách. Theo bộ lọc "câu hỏi học tập" của backend hiện tại, chỉ
**124/368** lượt là câu hỏi bài; trong đó **36 có trang (29%)**.

**2. Câu hỏi bài vẫn thiếu trang, vì buổi thử chạy trên code trước các bản sửa.** Buổi thử chạy lúc 9–11 giờ
ngày 16/10 trên commit f798a72. Các bản sửa sau buổi thử:

| Commit | Giờ | Sửa gì |
| --- | --- | --- |
| f06a357 | 16/10 22:32 | Danh mục bài học kèm số trang cho cả 20 môn/lớp; Mimo tìm trong trang của bài đang mở |
| b8c1ef1, 03e34da | 17/10 03:56, 04:49 | Bản scan đầy đủ cho 10 cuốn (trước đó thiếu trang) |
| 953d7c8 | 17/10 05:29 | "Giảng lại … cho em" được tính là câu hỏi học tập. Trước đó Mimo coi như lời chào, không trích trang: 36 lượt kiểu này trong buổi thử |
| 62e228d | 17/10 08:36 | Bài ở sách lớp khác thì giảng theo trang sách lớp đó |
| f2793f6 | 17/10 08:56 | Hướng dẫn bài tập theo cách làm trong sách thì luôn gắn trang; có dự phòng tất định khi mô hình quên |

**3. Chạy lại 25 câu hỏi bài thật của buổi thử trên bản deploy 17/10** (577ccef, cùng môn, lớp 7, cùng bài đang
mở, tài khoản bộ kiểm thử):

| Môn | Lúc buổi thử | Bản 17/10 |
| --- | --- | --- |
| Toán | 6/12 | **11/12** |
| Lịch sử và Địa lí | 4/5 | **5/5** |
| Ngữ văn | 0/2 | **2/2** |
| Tiếng Anh | 0/6 | **0/6** |
| **Tổng** | **10/25** | **18/25** |

Câu Toán còn thiếu là "Em chưa hiểu cách tìm số chia": hỏi riêng, không có lịch sử, nên Mimo hỏi lại phần
học. Trong buổi thử câu này có lịch sử chat đi kèm.

**4. Tiếng Anh: đã sửa chiều 17/10 (commit 52eacf6).** Ba chỗ chặn:

- Trang của bài đang mở bị lọc theo điểm khớp của tên bài với trang. "Getting Started" với trang hội thoại
  tiếng Anh (bản OCR) chỉ 0,58–0,61, dưới ngưỡng trích 0,65, nên Mimo không có số [n] nào để gắn.
- Bước dọn câu trả lời bỏ [n] khi câu giảng không trùng 2 cặp từ với trang. Câu tiếng Việt giảng bài
  tiếng Anh thì không bao giờ trùng.
- Unit nào cũng có tám mục cùng tên ("Skills 1", "A Closer Look 2"), nên Mimo trích nhầm Unit: hỏi
  "Unit 3 – Skills 1" thì ra trang "Unit 8 – Skills 1".

Dò 2 bài × 2 câu cho mỗi môn/lớp, với tên bài như giao diện hiện tại gửi ("Unit 3 – Skills 1"):

| | Bản deploy trước khi sửa | Bản sửa |
| --- | --- | --- |
| Tiếng Anh: câu có trang | 10/16 | **15/16** |
| Tiếng Anh: câu mà mọi trang trích đều đúng Unit | 0/10 | **15/15** |
| Toán, KHTN, Ngữ văn, Lịch sử và Địa lí: câu có trang đúng bài | 64/64 | 64/64 |

Ghi chú: các bạn dùng thử còn lưu tên bài kiểu cũ ("Bài 17: A Closer Look 2") trong tài khoản, do lộ trình cũ
sinh ra. Tên đó không tra được trong danh mục; mở lại Lộ trình học và chọn bài thì tên mới ("Unit 8 – A Closer
Look 2") được lưu.

## Còn thiếu

- Kết quả Google Form và phiếu quan sát.
