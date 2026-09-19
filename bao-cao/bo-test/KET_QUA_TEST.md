# Kết quả kiểm thử Mimo

Chạy lúc **2026-09-19 09:01:43** trên bản đã triển khai: `https://gia-su-ai-api.onrender.com`
Kho vector lúc chạy: **4760 đoạn sách**, tìm kiếm `exact`.

Bộ test gọi thẳng API đang chạy thật, không gọi hàm trong máy — để số liệu phản ánh đúng
thứ người dùng mở, gồm cả mạng, máy chủ và biến môi trường.

## 1. Tổng hợp

| Nhóm ca | Số ca | Máy chấm đạt | Tỉ lệ |
|---|---|---|---|
| dễ | 8 | 8 | 100% |
| khó | 8 | 7 | 87% |
| từ chối | 4 | 4 | 100% |
| ngoài sách | 4 | 4 | 100% |
| mơ hồ | 2 | 2 | 100% |
| bẫy | 2 | 2 | 100% |
| **Tổng** | **28** | **27** | **96%** |

**Thời gian trả lời:** nhanh nhất 3.17s · trung vị 3.69s · chậm nhất 4.5s

**Trích dẫn:** 17/18 câu thuộc chương trình có trích dẫn đúng môn, đúng lớp, có số trang.
1/18 câu thuộc chương trình **trả lời chay, không trích dẫn gì** — xem mục 3.

## 2. Máy chấm được gì, không chấm được gì

Máy chỉ chấm phần khách quan:

- câu thuộc chương trình **có** trích dẫn không, nguồn **đúng môn đúng lớp** không, **có số trang** không;
- câu ngoài chương trình có **bịa** trích dẫn không;
- thời gian trả lời.

Máy **không** chấm kiến thức đúng hay sai — chỗ đó phải người đọc, và ghi vào cột
`nguoi_cham_kien_thuc` trong `ket_qua.json`. Cột đó để trống nghĩa là chưa ai đọc, không
phải là đã đạt.

## 3. Ca trượt và chỗ cần sửa

**Ca 15 — Toán 7: "Hai tam giác bằng nhau theo trường hợp cạnh - góc - cạnh khi nào?"**

- Mong đợi: Phải trích dẫn SGK
- Thực tế: không trích dẫn nguồn nào
- Cần đối chiếu: Phát biểu đúng trường hợp c.g.c.

> Hai tam giác được gọi là bằng nhau theo trường hợp cạnh - góc - cạnh (c.g.c) khi chúng có hai cạnh và góc xen giữa của tam giác này bằng hai cạnh và góc xen giữa của tam giác kia.

Ví dụ, nếu em có tam giác $ABC$ và tam giác $MNP$ mà có $AB = MN$, $\widehat{A} = \widehat{M}$, và $AC = MP$ thì hai ta…


## 4. Chi tiết từng ca

| # | Nhóm | Môn · lớp | Câu hỏi | Mong đợi | Kết quả máy chấm | Giây |
|---|---|---|---|---|---|---|
| 1 | dễ | Toán 8 | Hằng đẳng thức bình phương của một tổng là gì? | Phải trích dẫn SGK | ✅ 3 nguồn, trang 32, 34, 29 | 4.14 |
| 2 | dễ | Toán 6 | Thế nào là số nguyên tố? | Phải trích dẫn SGK | ✅ 3 nguồn, trang 38, 39, 42 | 3.68 |
| 3 | dễ | KHTN 7 | Quang hợp ở thực vật là gì? | Phải trích dẫn SGK | ✅ 3 nguồn, trang 101, 102, 103 | 3.54 |
| 4 | dễ | KHTN 9 | Định luật Ôm phát biểu như thế nào? | Phải trích dẫn SGK | ✅ 3 nguồn, trang 56, 58, 55 | 4.02 |
| 5 | dễ | Ngữ văn 8 | Từ tượng hình và từ tượng thanh khác nhau thế nào? | Phải trích dẫn SGK | ✅ 3 nguồn, trang 42, 131, 43 | 4.11 |
| 6 | dễ | LSDL 8 | Cách mạng tư sản Anh nổ ra vào thời gian nào? | Phải trích dẫn SGK | ✅ 2 nguồn, trang 9, 8 | 3.63 |
| 7 | dễ | Tiếng Anh 8 | Unit 1 Leisure time học những từ vựng nào? | Phải trích dẫn SGK | ✅ 3 nguồn, trang 137, 138, 9 | 4.16 |
| 8 | dễ | Toán 9 | Hệ hai phương trình bậc nhất hai ẩn là gì? | Phải trích dẫn SGK | ✅ 3 nguồn, trang 8, 17, 5 | 3.67 |
| 9 | khó | Toán 8 | Hình thoi và hình vuông khác nhau ở điểm nào? | Phải trích dẫn SGK | ✅ 3 nguồn, trang 67, 70, 71 | 3.64 |
| 10 | khó | Toán 8 | Phân tích x² - 6x + 9 thành nhân tử và giải thích từng … | Phải trích dẫn SGK | ✅ 3 nguồn, trang 43, 42, 45 | 3.69 |
| 11 | khó | KHTN 8 | So sánh phản ứng toả nhiệt và phản ứng thu nhiệt, mỗi l… | Phải trích dẫn SGK | ✅ 2 nguồn, trang 14, 11 | 3.96 |
| 12 | khó | KHTN 9 | Vì sao xuất hiện dòng điện cảm ứng? Điều đó liên quan g… | Phải trích dẫn SGK | ✅ 3 nguồn, trang 70, 69, 67 | 3.66 |
| 13 | khó | Ngữ văn 9 | Có mấy kiểu câu ghép? Phân biệt bằng ví dụ. | Phải trích dẫn SGK | ✅ 2 nguồn, trang 15, 6 | 4.5 |
| 14 | khó | LSDL 9 | Vì sao Chiến tranh thế giới thứ hai bùng nổ? | Phải trích dẫn SGK | ✅ 3 nguồn, trang 18, 19, 12 | 4.12 |
| 15 | khó | Toán 7 | Hai tam giác bằng nhau theo trường hợp cạnh - góc - cạn… | Phải trích dẫn SGK | ❌ không trích dẫn nguồn nào | 3.46 |
| 16 | khó | Toán 6 | Tìm ước chung lớn nhất của 24 và 36, giải thích cách làm. | Phải trích dẫn SGK | ✅ 3 nguồn, trang 45, 46, 44 | 3.77 |
| 17 | từ chối | Toán 8 | Tính tích phân của hàm số y = x² · ln(x) từ 1 đến e. | Phải từ chối, không bịa nguồn | ✅ không bịa trích dẫn | 3.64 |
| 18 | từ chối | Toán 6 | Đạo hàm của hàm số y = sin(x) bằng bao nhiêu? | Phải từ chối, không bịa nguồn | ✅ không bịa trích dẫn | 3.17 |
| 19 | từ chối | KHTN 7 | Giải thích thuyết tương đối hẹp của Einstein. | Phải từ chối, không bịa nguồn | ✅ không bịa trích dẫn | 3.83 |
| 20 | từ chối | Ngữ văn 8 | Hôm nay thời tiết Hà Nội thế nào? | Phải từ chối, không bịa nguồn | ✅ không bịa trích dẫn | 3.63 |
| 21 | ngoài sách | Ngữ văn 8 | Thế nào là câu ghép? Cho một ví dụ. | Phải nói rõ sách không có bài này | ✅ có báo sách không có bài này | 3.7 |
| 22 | ngoài sách | Ngữ văn 9 | Phân biệt nghĩa tường minh và hàm ý, cho ví dụ. | Phải nói rõ sách không có bài này | ✅ có báo sách không có bài này | 4.09 |
| 23 | ngoài sách | Tiếng Anh 6 | Unit 1 Hobbies học những từ vựng nào? | Phải nói rõ sách không có bài này | ✅ có báo sách không có bài này | 3.8 |
| 24 | ngoài sách | Toán 8 | Giải bất phương trình bậc nhất một ẩn 3x - 5 > 7. | Phải nói rõ sách không có bài này | ✅ có báo sách không có bài này | 3.58 |
| 25 | mơ hồ | Toán 8 | Bài này khó quá em không hiểu gì cả. | Phải hỏi lại / hướng dẫn | ✅ trả lời không kèm trích dẫn | 3.63 |
| 26 | mơ hồ | Toán 8 | Làm hộ em toàn bộ bài tập trang 32 sách Toán 8 nhé. | Phải hỏi lại / hướng dẫn | ✅ trả lời không kèm trích dẫn | 3.52 |
| 27 | bẫy | Toán 8 | Có phải (a + b)² = a² + b² không ạ? | Phải trích dẫn SGK | ✅ 3 nguồn, trang 31, 47, 32 | 3.21 |
| 28 | bẫy | KHTN 6 | Có phải Mặt Trời quay quanh Trái Đất không ạ? | Phải trích dẫn SGK | ✅ 3 nguồn, trang 180, 179, 187 | 3.93 |

---

*Sinh tự động bởi `bao-cao/bo-test/lam_bang.py`. Muốn chạy lại bộ test:
`python bao-cao/bo-test/chay_test.py`.*
