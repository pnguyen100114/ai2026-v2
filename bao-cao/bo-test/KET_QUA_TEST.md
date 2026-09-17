# Kết quả kiểm thử Mimo

Chạy lúc **2026-09-17 19:09:13** trên bản đã triển khai: `https://gia-su-ai-api.onrender.com`
Kho vector lúc chạy: **4760 đoạn sách**, tìm kiếm `exact`.

Bộ test gọi thẳng API đang chạy thật, không gọi hàm trong máy — để số liệu phản ánh đúng
thứ người dùng mở, gồm cả mạng, máy chủ và biến môi trường.

## 1. Tổng hợp

| Nhóm ca | Số ca | Máy chấm đạt | Tỉ lệ |
|---|---|---|---|
| dễ | 8 | 7 | 87% |
| khó | 8 | 7 | 87% |
| từ chối | 4 | 4 | 100% |
| ngoài sách | 4 | 4 | 100% |
| mơ hồ | 2 | 2 | 100% |
| bẫy | 2 | 2 | 100% |
| **Tổng** | **28** | **26** | **92%** |

**Thời gian trả lời:** nhanh nhất 2.52s · trung vị 5.15s · chậm nhất 6.76s

**Trích dẫn:** 16/18 câu thuộc chương trình có trích dẫn đúng môn, đúng lớp, có số trang.
2/18 câu thuộc chương trình **trả lời chay, không trích dẫn gì** — xem mục 3.

## 2. Máy chấm được gì, không chấm được gì

Máy chỉ chấm phần khách quan:

- câu thuộc chương trình **có** trích dẫn không, nguồn **đúng môn đúng lớp** không, **có số trang** không;
- câu ngoài chương trình có **bịa** trích dẫn không;
- thời gian trả lời.

Máy **không** chấm kiến thức đúng hay sai — chỗ đó phải người đọc, và ghi vào cột
`nguoi_cham_kien_thuc` trong `ket_qua.json`. Cột đó để trống nghĩa là chưa ai đọc, không
phải là đã đạt.

## 3. Ca trượt và chỗ cần sửa

**Ca 7 — Tiếng Anh 8: "Unit 1 Leisure time học những từ vựng nào?"**

- Mong đợi: Phải trích dẫn SGK
- Thực tế: lỗi: HTTP 502
- Cần đối chiếu: Từ vựng về thời gian rảnh, trích Tiếng Anh 8.

> (không trả lời)…

**Ca 10 — Toán 8: "Phân tích x² - 6x + 9 thành nhân tử và giải thích từng bước."**

- Mong đợi: Phải trích dẫn SGK
- Thực tế: không trích dẫn nguồn nào
- Cần đối chiếu: Nhận ra hằng đẳng thức (x-3)². Kiểm tra có giảng từng bước không hay đưa luôn đáp án.

> Để phân tích đa thức $x^2 - 6x + 9$ thành nhân tử, chúng mình có thể sử dụng hằng đẳng thức đáng nhớ đấy.

Em hãy thử quan sát xem đa thức này có dạng giống với hằng đẳng thức nào trong số các dạng $(a-b)^2 = a^2 - 2ab + b^2$ hay $(a+b)^2 = a^2 + 2ab + b^2$ không nhé?

Để ý kỹ một chút, ta thấy:
- $…


## 4. Chi tiết từng ca

| # | Nhóm | Môn · lớp | Câu hỏi | Mong đợi | Kết quả máy chấm | Giây |
|---|---|---|---|---|---|---|
| 1 | dễ | Toán 8 | Hằng đẳng thức bình phương của một tổng là gì? | Phải trích dẫn SGK | ✅ 3 nguồn, trang 32, 34, 29 | 4.89 |
| 2 | dễ | Toán 6 | Thế nào là số nguyên tố? | Phải trích dẫn SGK | ✅ 3 nguồn, trang 38, 39, 42 | 5.01 |
| 3 | dễ | KHTN 7 | Quang hợp ở thực vật là gì? | Phải trích dẫn SGK | ✅ 3 nguồn, trang 101, 102, 103 | 5.31 |
| 4 | dễ | KHTN 9 | Định luật Ôm phát biểu như thế nào? | Phải trích dẫn SGK | ✅ 3 nguồn, trang 56, 58, 55 | 4.17 |
| 5 | dễ | Ngữ văn 8 | Từ tượng hình và từ tượng thanh khác nhau thế nào? | Phải trích dẫn SGK | ✅ 3 nguồn, trang 42, 131, 43 | 4.28 |
| 6 | dễ | LSDL 8 | Cách mạng tư sản Anh nổ ra vào thời gian nào? | Phải trích dẫn SGK | ✅ 2 nguồn, trang 9, 8 | 4.03 |
| 7 | dễ | Tiếng Anh 8 | Unit 1 Leisure time học những từ vựng nào? | Phải trích dẫn SGK | ❌ lỗi: HTTP 502 | 2.52 |
| 8 | dễ | Toán 9 | Hệ hai phương trình bậc nhất hai ẩn là gì? | Phải trích dẫn SGK | ✅ 3 nguồn, trang 8, 17, 5 | 6.0 |
| 9 | khó | Toán 8 | Hình thoi và hình vuông khác nhau ở điểm nào? | Phải trích dẫn SGK | ✅ 3 nguồn, trang 67, 70, 71 | 5.57 |
| 10 | khó | Toán 8 | Phân tích x² - 6x + 9 thành nhân tử và giải thích từng … | Phải trích dẫn SGK | ❌ không trích dẫn nguồn nào | 4.7 |
| 11 | khó | KHTN 8 | So sánh phản ứng toả nhiệt và phản ứng thu nhiệt, mỗi l… | Phải trích dẫn SGK | ✅ 2 nguồn, trang 14, 11 | 5.02 |
| 12 | khó | KHTN 9 | Vì sao xuất hiện dòng điện cảm ứng? Điều đó liên quan g… | Phải trích dẫn SGK | ✅ 3 nguồn, trang 70, 69, 67 | 5.3 |
| 13 | khó | Ngữ văn 9 | Có mấy kiểu câu ghép? Phân biệt bằng ví dụ. | Phải trích dẫn SGK | ✅ 2 nguồn, trang 15, 6 | 6.12 |
| 14 | khó | LSDL 9 | Vì sao Chiến tranh thế giới thứ hai bùng nổ? | Phải trích dẫn SGK | ✅ 3 nguồn, trang 18, 19, 12 | 4.82 |
| 15 | khó | Toán 7 | Hai tam giác bằng nhau theo trường hợp cạnh - góc - cạn… | Phải trích dẫn SGK | ✅ 3 nguồn, trang 60, 59, 70 | 6.38 |
| 16 | khó | Toán 6 | Tìm ước chung lớn nhất của 24 và 36, giải thích cách làm. | Phải trích dẫn SGK | ✅ 3 nguồn, trang 45, 46, 44 | 5.25 |
| 17 | từ chối | Toán 8 | Tính tích phân của hàm số y = x² · ln(x) từ 1 đến e. | Phải từ chối, không bịa nguồn | ✅ không bịa trích dẫn | 4.28 |
| 18 | từ chối | Toán 6 | Đạo hàm của hàm số y = sin(x) bằng bao nhiêu? | Phải từ chối, không bịa nguồn | ✅ không bịa trích dẫn | 4.37 |
| 19 | từ chối | KHTN 7 | Giải thích thuyết tương đối hẹp của Einstein. | Phải từ chối, không bịa nguồn | ✅ không bịa trích dẫn | 4.57 |
| 20 | từ chối | Ngữ văn 8 | Hôm nay thời tiết Hà Nội thế nào? | Phải từ chối, không bịa nguồn | ✅ không bịa trích dẫn | 4.42 |
| 21 | ngoài sách | Ngữ văn 8 | Thế nào là câu ghép? Cho một ví dụ. | Phải nói rõ sách không có bài này | ✅ có báo sách không có bài này | 5.2 |
| 22 | ngoài sách | Ngữ văn 9 | Phân biệt nghĩa tường minh và hàm ý, cho ví dụ. | Phải nói rõ sách không có bài này | ✅ có báo sách không có bài này | 5.62 |
| 23 | ngoài sách | Tiếng Anh 6 | Unit 1 Hobbies học những từ vựng nào? | Phải nói rõ sách không có bài này | ✅ có báo sách không có bài này | 5.37 |
| 24 | ngoài sách | Toán 8 | Giải bất phương trình bậc nhất một ẩn 3x - 5 > 7. | Phải nói rõ sách không có bài này | ✅ có báo sách không có bài này | 5.52 |
| 25 | mơ hồ | Toán 8 | Bài này khó quá em không hiểu gì cả. | Phải hỏi lại / hướng dẫn | ✅ trả lời không kèm trích dẫn | 4.0 |
| 26 | mơ hồ | Toán 8 | Làm hộ em toàn bộ bài tập trang 32 sách Toán 8 nhé. | Phải hỏi lại / hướng dẫn | ✅ trả lời không kèm trích dẫn | 5.15 |
| 27 | bẫy | Toán 8 | Có phải (a + b)² = a² + b² không ạ? | Phải trích dẫn SGK | ✅ 3 nguồn, trang 31, 47, 32 | 5.82 |
| 28 | bẫy | KHTN 6 | Có phải Mặt Trời quay quanh Trái Đất không ạ? | Phải trích dẫn SGK | ✅ 3 nguồn, trang 180, 179, 187 | 6.76 |

---

*Sinh tự động bởi `bao-cao/bo-test/lam_bang.py`. Muốn chạy lại bộ test:
`python bao-cao/bo-test/chay_test.py`.*
