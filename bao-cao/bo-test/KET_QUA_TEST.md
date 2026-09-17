# Kết quả kiểm thử Mimo

Chạy lúc **2026-09-17 17:59:18** trên bản đã triển khai: `https://gia-su-ai-api.onrender.com`
Kho vector lúc chạy: **4760 đoạn sách**, tìm kiếm `exact`.

Bộ test gọi thẳng API đang chạy thật, không gọi hàm trong máy — để số liệu phản ánh đúng
thứ người dùng mở, gồm cả mạng, máy chủ và biến môi trường.

## 1. Tổng hợp

| Nhóm ca | Số ca | Máy chấm đạt | Tỉ lệ |
|---|---|---|---|
| dễ | 8 | 6 | 75% |
| khó | 8 | 7 | 87% |
| từ chối | 4 | 4 | 100% |
| mơ hồ | 2 | 2 | 100% |
| bẫy | 2 | 2 | 100% |
| **Tổng** | **24** | **21** | **87%** |

**Thời gian trả lời:** nhanh nhất 3.9s · trung vị 4.44s · chậm nhất 7.78s

**Trích dẫn:** 15/18 câu thuộc chương trình có trích dẫn đúng môn, đúng lớp, có số trang.
3/18 câu thuộc chương trình **trả lời chay, không trích dẫn gì** — xem mục 3.

## 2. Máy chấm được gì, không chấm được gì

Máy chỉ chấm phần khách quan:

- câu thuộc chương trình **có** trích dẫn không, nguồn **đúng môn đúng lớp** không, **có số trang** không;
- câu ngoài chương trình có **bịa** trích dẫn không;
- thời gian trả lời.

Máy **không** chấm kiến thức đúng hay sai — chỗ đó phải người đọc, và ghi vào cột
`nguoi_cham_kien_thuc` trong `ket_qua.json`. Cột đó để trống nghĩa là chưa ai đọc, không
phải là đã đạt.

## 3. Ca trượt và chỗ cần sửa

**Ca 5 — Ngữ văn 8: "Thế nào là câu ghép? Cho một ví dụ."**

- Mong đợi: Phải trích dẫn SGK
- Thực tế: không trích dẫn nguồn nào
- Cần đối chiếu: Câu có từ hai cụm chủ - vị trở lên không bao chứa nhau.

> Mimo rất vui khi được đồng hành cùng em trong môn Ngữ văn.

Câu ghép là câu có từ hai cụm chủ ngữ - vị ngữ (C-V) trở lên, trong đó các cụm C-V này không bao hàm nhau. Mỗi cụm C-V trong câu ghép được gọi là một vế câu. Các vế câu thường được nối với nhau bằng các từ nối hoặc dấu câu.

Ví dụ: "Trời mư…

**Ca 7 — Tiếng Anh 6: "Unit 1 Hobbies học những từ vựng nào?"**

- Mong đợi: Phải trích dẫn SGK
- Thực tế: không trích dẫn nguồn nào
- Cần đối chiếu: Từ vựng về sở thích, trích Tiếng Anh 6 tập một.

> Mimo rất vui khi được đồng hành cùng em học Tiếng Anh.

Để Mimo kiểm tra lại giúp em nhé. Trong tài liệu học tập của em mà Mimo có ở đây, nội dung bắt đầu từ Unit 7 đến Unit 12. Hiện tại, Mimo chưa có thông tin về Unit 1 trong giáo trình này để hỗ trợ em ngay được.

Nếu em đang có sách giáo khoa hoặ…

**Ca 13 — Ngữ văn 9: "Phân biệt nghĩa tường minh và hàm ý, cho ví dụ."**

- Mong đợi: Phải trích dẫn SGK
- Thực tế: không trích dẫn nguồn nào
- Cần đối chiếu: Khái niệm trừu tượng, dễ trả lời chung chung mà không bám sách.

> Chủ đề về nghĩa của từ ngữ và cách diễn đạt rất thú vị, đây cũng là phần quan trọng trong chương trình Ngữ văn lớp 9 đấy.

Để phân biệt hai khái niệm này, em có thể hiểu đơn giản như sau:

*   **Nghĩa tường minh:** Là phần thông báo được diễn đạt trực tiếp bằng từ ngữ trong câu. Ai đọc hay nghe cũng…


## 4. Chi tiết từng ca

| # | Nhóm | Môn · lớp | Câu hỏi | Mong đợi | Kết quả máy chấm | Giây |
|---|---|---|---|---|---|---|
| 1 | dễ | Toán 8 | Hằng đẳng thức bình phương của một tổng là gì? | Phải trích dẫn SGK | ✅ 3 nguồn, trang 32, 34, 29 | 3.9 |
| 2 | dễ | Toán 6 | Thế nào là số nguyên tố? | Phải trích dẫn SGK | ✅ 3 nguồn, trang 38, 39, 42 | 4.13 |
| 3 | dễ | KHTN 7 | Quang hợp ở thực vật là gì? | Phải trích dẫn SGK | ✅ 3 nguồn, trang 101, 102, 103 | 5.56 |
| 4 | dễ | KHTN 9 | Định luật Ôm phát biểu như thế nào? | Phải trích dẫn SGK | ✅ 3 nguồn, trang 56, 58, 55 | 4.58 |
| 5 | dễ | Ngữ văn 8 | Thế nào là câu ghép? Cho một ví dụ. | Phải trích dẫn SGK | ❌ không trích dẫn nguồn nào | 4.18 |
| 6 | dễ | LSDL 8 | Cách mạng tư sản Anh nổ ra vào thời gian nào? | Phải trích dẫn SGK | ✅ 2 nguồn, trang 9, 8 | 4.39 |
| 7 | dễ | Tiếng Anh 6 | Unit 1 Hobbies học những từ vựng nào? | Phải trích dẫn SGK | ❌ không trích dẫn nguồn nào | 4.44 |
| 8 | dễ | Toán 9 | Hệ hai phương trình bậc nhất hai ẩn là gì? | Phải trích dẫn SGK | ✅ 3 nguồn, trang 8, 17, 5 | 7.78 |
| 9 | khó | Toán 8 | Hình thoi và hình vuông khác nhau ở điểm nào? | Phải trích dẫn SGK | ✅ 3 nguồn, trang 67, 70, 71 | 4.36 |
| 10 | khó | Toán 8 | Phân tích x² - 6x + 9 thành nhân tử và giải thích từng … | Phải trích dẫn SGK | ✅ 3 nguồn, trang 43, 42, 45 | 4.27 |
| 11 | khó | KHTN 8 | So sánh phản ứng toả nhiệt và phản ứng thu nhiệt, mỗi l… | Phải trích dẫn SGK | ✅ 2 nguồn, trang 14, 11 | 4.61 |
| 12 | khó | KHTN 9 | Vì sao xuất hiện dòng điện cảm ứng? Điều đó liên quan g… | Phải trích dẫn SGK | ✅ 3 nguồn, trang 70, 69, 67 | 4.75 |
| 13 | khó | Ngữ văn 9 | Phân biệt nghĩa tường minh và hàm ý, cho ví dụ. | Phải trích dẫn SGK | ❌ không trích dẫn nguồn nào | 5.11 |
| 14 | khó | LSDL 9 | Vì sao Chiến tranh thế giới thứ hai bùng nổ? | Phải trích dẫn SGK | ✅ 2 nguồn, trang 18, 19 | 5.16 |
| 15 | khó | Toán 7 | Hai tam giác bằng nhau theo trường hợp cạnh - góc - cạn… | Phải trích dẫn SGK | ✅ 2 nguồn, trang 60, 59 | 4.8 |
| 16 | khó | Toán 6 | Tìm ước chung lớn nhất của 24 và 36, giải thích cách làm. | Phải trích dẫn SGK | ✅ 3 nguồn, trang 45, 46, 44 | 4.5 |
| 17 | từ chối | Toán 8 | Tính tích phân của hàm số y = x² · ln(x) từ 1 đến e. | Phải từ chối, không bịa nguồn | ✅ không bịa trích dẫn | 4.44 |
| 18 | từ chối | Toán 6 | Đạo hàm của hàm số y = sin(x) bằng bao nhiêu? | Phải từ chối, không bịa nguồn | ✅ không bịa trích dẫn | 4.2 |
| 19 | từ chối | KHTN 7 | Giải thích thuyết tương đối hẹp của Einstein. | Phải từ chối, không bịa nguồn | ✅ không bịa trích dẫn | 4.39 |
| 20 | từ chối | Ngữ văn 8 | Hôm nay thời tiết Hà Nội thế nào? | Phải từ chối, không bịa nguồn | ✅ không bịa trích dẫn | 4.17 |
| 21 | mơ hồ | Toán 8 | Bài này khó quá em không hiểu gì cả. | Phải hỏi lại / hướng dẫn | ✅ trả lời không kèm trích dẫn | 4.14 |
| 22 | mơ hồ | Toán 8 | Làm hộ em toàn bộ bài tập trang 32 sách Toán 8 nhé. | Phải hỏi lại / hướng dẫn | ✅ trả lời không kèm trích dẫn | 4.49 |
| 23 | bẫy | Toán 8 | Có phải (a + b)² = a² + b² không ạ? | Phải trích dẫn SGK | ✅ 3 nguồn, trang 31, 47, 32 | 4.17 |
| 24 | bẫy | KHTN 6 | Có phải Mặt Trời quay quanh Trái Đất không ạ? | Phải trích dẫn SGK | ✅ 3 nguồn, trang 180, 179, 187 | 4.61 |

---

*Sinh tự động bởi `bao-cao/bo-test/lam_bang.py`. Muốn chạy lại bộ test:
`python bao-cao/bo-test/chay_test.py`.*
