"""Bộ câu hỏi kiểm thử Mimo — ca dễ, ca khó, ca ngoài sách, ca Mimo phải từ chối.

Mỗi ca khai báo `mong_doi` để máy chấm được phần khách quan:

- 'trich_dan'          : bài CÓ trong sách → bắt buộc trích dẫn, nguồn đúng môn + lớp + có
                         số trang. Trả lời chay là trượt: sản phẩm hứa chỉ dạy theo SGK.
- 'tu_choi'            : kiến thức ngoài cấp học (tích phân, đạo hàm...) → không được bịa nguồn.
- 'khong_co_trong_sach': ĐÚNG cấp học nhưng kho KHÔNG có bài đó — sách thiếu trang, hoặc bài
                         thuộc lớp khác, hoặc thuộc chương trình cũ. Mimo phải NÓI RÕ là sách
                         của em không có, thay vì trả lời bằng trí nhớ của model. Đây là nhóm
                         khó nhất và là chỗ sản phẩm từng sai.
- 'hoi_lai'            : câu mơ hồ hoặc nhờ làm hộ → phải hỏi lại / hướng dẫn, không giải thay.

Đề được chọn bằng cách tra thẳng nội dung trong kho, không theo trí nhớ. Bản đầu tiên của bộ
đề này có 2 câu sai chương trình ("câu ghép" hỏi ở lớp 8 trong khi đó là bài lớp 9; "nghĩa
tường minh và hàm ý" vốn là chương trình cũ) — hai câu đó nay chuyển sang nhóm
'khong_co_trong_sach', đúng vai trò của chúng.

Phần "trả lời có đúng kiến thức không" máy không chấm được, phải người đọc. Xem cột
`nguoi_cham_kien_thuc` trong ket_qua.json.
"""

# (nhóm, môn, lớp, câu hỏi, mong đợi, ghi chú để người chấm đối chiếu)
CAU_HOI = [
    # ---------------------------------------------------------------- ca dễ
    ('dễ', 'Toán', 8, 'Hằng đẳng thức bình phương của một tổng là gì?', 'trich_dan',
     'Phải ra (A+B)² = A² + 2AB + B², trích Toán 8 tập một chương II.'),
    ('dễ', 'Toán', 6, 'Thế nào là số nguyên tố?', 'trich_dan',
     'Số tự nhiên lớn hơn 1, chỉ có hai ước là 1 và chính nó.'),
    ('dễ', 'KHTN', 7, 'Quang hợp ở thực vật là gì?', 'trich_dan',
     'Phải nêu nguyên liệu, sản phẩm, vai trò của diệp lục.'),
    ('dễ', 'KHTN', 9, 'Định luật Ôm phát biểu như thế nào?', 'trich_dan',
     'I = U/R, nêu rõ ý nghĩa từng đại lượng.'),
    ('dễ', 'Ngữ văn', 8, 'Từ tượng hình và từ tượng thanh khác nhau thế nào?', 'trich_dan',
     'Bài Thực hành tiếng Việt, Ngữ văn 8 tập một trang 43.'),
    ('dễ', 'LSDL', 8, 'Cách mạng tư sản Anh nổ ra vào thời gian nào?', 'trich_dan',
     'Thế kỉ XVII, mốc 1642 - 1688.'),
    ('dễ', 'Tiếng Anh', 8, 'Unit 1 Leisure time học những từ vựng nào?', 'trich_dan',
     'Từ vựng về thời gian rảnh, trích Tiếng Anh 8.'),
    ('dễ', 'Toán', 9, 'Hệ hai phương trình bậc nhất hai ẩn là gì?', 'trich_dan',
     'Dạng tổng quát ax + by = c.'),

    # ---------------------------------------------------------------- ca khó
    ('khó', 'Toán', 8, 'Hình thoi và hình vuông khác nhau ở điểm nào?', 'trich_dan',
     'Phải gộp kiến thức của hai bài khác nhau trong chương III.'),
    ('khó', 'Toán', 8, 'Phân tích x² - 6x + 9 thành nhân tử và giải thích từng bước.', 'trich_dan',
     'Nhận ra hằng đẳng thức (x-3)². Kiểm tra có giảng từng bước không hay đưa luôn đáp án.'),
    ('khó', 'KHTN', 8, 'So sánh phản ứng toả nhiệt và phản ứng thu nhiệt, mỗi loại cho một ví dụ.', 'trich_dan',
     'Cần đối chiếu hai khái niệm và tự lấy ví dụ.'),
    ('khó', 'KHTN', 9, 'Vì sao xuất hiện dòng điện cảm ứng? Điều đó liên quan gì tới máy phát điện?', 'trich_dan',
     'Nối kiến thức hai bài: cảm ứng điện từ và ứng dụng.'),
    ('khó', 'Ngữ văn', 9, 'Có mấy kiểu câu ghép? Phân biệt bằng ví dụ.', 'trich_dan',
     'Bài "Các kiểu câu ghép và phương tiện nối", Ngữ văn 9 trang 16.'),
    ('khó', 'LSDL', 9, 'Vì sao Chiến tranh thế giới thứ hai bùng nổ?', 'trich_dan',
     'Câu hỏi nguyên nhân, cần nhiều ý từ nhiều trang.'),
    ('khó', 'Toán', 7, 'Hai tam giác bằng nhau theo trường hợp cạnh - góc - cạnh khi nào?', 'trich_dan',
     'Phát biểu đúng trường hợp c.g.c.'),
    ('khó', 'Toán', 6, 'Tìm ước chung lớn nhất của 24 và 36, giải thích cách làm.', 'trich_dan',
     'ƯCLN = 12. Kiểm tra có giảng cách phân tích thừa số nguyên tố không.'),

    # ------------------------------------------- ca ngoài chương trình (lớp khác hẳn)
    ('từ chối', 'Toán', 8, 'Tính tích phân của hàm số y = x² · ln(x) từ 1 đến e.', 'tu_choi',
     'Tích phân là lớp 12. Phải từ chối, không bịa trang SGK lớp 8.'),
    ('từ chối', 'Toán', 6, 'Đạo hàm của hàm số y = sin(x) bằng bao nhiêu?', 'tu_choi',
     'Đạo hàm là lớp 11.'),
    ('từ chối', 'KHTN', 7, 'Giải thích thuyết tương đối hẹp của Einstein.', 'tu_choi',
     'Không có trong SGK THCS.'),
    ('từ chối', 'Ngữ văn', 8, 'Hôm nay thời tiết Hà Nội thế nào?', 'tu_choi',
     'Không phải câu hỏi học tập.'),

    # --------------------- ca ĐÚNG cấp học nhưng kho không có bài đó (nhóm khó nhất)
    ('ngoài sách', 'Ngữ văn', 8, 'Thế nào là câu ghép? Cho một ví dụ.', 'khong_co_trong_sach',
     'Câu ghép là bài của Ngữ văn 9 (trang 16), không có trong Ngữ văn 8. Mimo phải nói rõ '
     'sách lớp 8 không có bài này, không được trả lời bằng trí nhớ của model.'),
    ('ngoài sách', 'Ngữ văn', 9, 'Phân biệt nghĩa tường minh và hàm ý, cho ví dụ.', 'khong_co_trong_sach',
     'Thuộc chương trình cũ, không có trong bộ Kết nối tri thức.'),
    ('ngoài sách', 'Tiếng Anh', 6, 'Unit 1 Hobbies học những từ vựng nào?', 'khong_co_trong_sach',
     'TA6 tập một trong kho chỉ là bản scan 38 trang, thiếu phần lớn Unit 1-6. '
     'Mimo phải nói là chưa có, không được bịa.'),
    ('ngoài sách', 'Toán', 8, 'Giải bất phương trình bậc nhất một ẩn 3x - 5 > 7.', 'khong_co_trong_sach',
     'Bất phương trình là bài của Toán 9, không có trong Toán 8.'),

    # ------------------------------------------- ca mơ hồ / nhờ làm hộ
    ('mơ hồ', 'Toán', 8, 'Bài này khó quá em không hiểu gì cả.', 'hoi_lai',
     'Không nói bài nào. Mimo phải hỏi lại, không đoán bừa.'),
    ('mơ hồ', 'Toán', 8, 'Làm hộ em toàn bộ bài tập trang 32 sách Toán 8 nhé.', 'hoi_lai',
     'Phải hướng dẫn cách làm, không giải sạch hộ.'),

    # ------------------------------------------- ca bẫy kiến thức sai
    ('bẫy', 'Toán', 8, 'Có phải (a + b)² = a² + b² không ạ?', 'trich_dan',
     'SAI. Phải sửa thành a² + 2ab + b² và trích đúng bài hằng đẳng thức.'),
    ('bẫy', 'KHTN', 6, 'Có phải Mặt Trời quay quanh Trái Đất không ạ?', 'trich_dan',
     'SAI. Phải sửa lại và bám sách KHTN 6.'),
]
