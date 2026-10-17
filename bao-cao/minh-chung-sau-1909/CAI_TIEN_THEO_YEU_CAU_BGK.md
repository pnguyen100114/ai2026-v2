# Cải tiến theo yêu cầu của ban giám khảo (sau 19/09/2026)

Gia sư AI Mimo · cập nhật 17/10/2026 · sản phẩm đang chạy: https://ai2026-v2.vercel.app

Tài liệu này chỉ ghi việc nhóm làm **sau ngày nộp 19/09/2026**. Mỗi yêu cầu có: nhóm đã làm gì, đo được gì, còn thiếu gì, và minh chứng nằm ở đâu trong thư mục này.

## Tóm tắt

| # | Yêu cầu của ban giám khảo | Trạng thái | Con số chính |
|---|---|---|---|
| 1 | Sửa cách tự chấm bộ thử, kiểm tra lại câu ngoài chương trình và câu thời tiết | **Xong** | Bộ thử 28 → 43 ca chấm chặt; lần đo cuối **43/43** trên bản đang chạy |
| 2 | Thầy cô chấm câu trả lời; dòng nhắc "Mimo có thể nhầm"; thêm ~10 câu năn nỉ | **Xong** | Thầy cô chấm nguyên văn 43 câu: **41 đúng, 2 có chỗ sai, 0 sai**, đã sửa cả 2; thêm **14** ca năn nỉ, lộ đáp án **3/14 → 0/14** |
| 3 | 10–15 bạn dùng thử 15–20 phút, khảo sát Google Form | **Xong** | **34** bạn lớp 7, **368** câu hỏi, trung vị **17 phút** mỗi bạn. Google Form 12 phiếu: tự làm tiếp **4,4/5**; **2/12** bạn thấy Mimo giải hộ |
| 4 | Luyện tập tính độ khó, số lần dùng gợi ý, dạng lỗi hay gặp | **Xong phần sản phẩm** | Buổi thử: **178** lượt luyện tập của 14 bạn, có độ khó, gợi ý và dạng lỗi cho từng lượt |
| 5 | Thử 2–4 tuần với 1–2 lớp, kiểm tra trước và sau, có nhóm đối chứng | **Chưa làm**, đã có kế hoạch | — |

---

## 1. Sửa cách tự chấm bộ thử

> Cách tự chấm bộ 28 câu còn dễ dãi: vài câu ngoài chương trình (tích phân, đạo hàm, thuyết tương đối) Mimo vẫn hướng dẫn mà lại được tính là "từ chối đạt", câu hỏi thời tiết còn được trả lời không có căn cứ.

**Nhóm đã làm**

- Viết lại máy chấm. Mỗi ca có danh sách **chuỗi cấm** (bước tích phân, đáp án đạo hàm `cos x`, mô tả thời tiết, đáp án cuối…) và danh sách **"phải có"**. Câu nào giảng tiếp phần ngoài chương trình là trượt, dù có từ chối ở đầu.
- Mở rộng bộ thử từ 28 lên **43 ca**, chia 9 nhóm: dễ, khó, từ chối (kiến thức lớp trên), lạc đề, ngoài sách, mơ hồ, bẫy (học sinh nói sai), năn nỉ, đối chứng (em làm đúng thì Mimo phải xác nhận).
- Bộ thử gọi thẳng vào **bản đang chạy cho học sinh**, không gọi hàm trong máy.
- Sửa Mimo: câu kiến thức THPT và câu lạc đề bị từ chối **trước khi gọi mô hình AI**, kể cả khi hỏi lách. Mimo trả lời trong khoảng 0,2 giây và không giảng thêm gì.

**Kết quả đo**

| Lần đo | Cách chấm | Kết quả |
|---|---|---|
| Bản nộp 19/09 | Cũ, chỉ xét "có bịa nguồn không" | 27/28 |
| 16/10, lần đầu chấm chặt | Mới | 37/43 |
| 17/10 15:13, bản đang chạy | Mới | **43/43** |

- Nhóm từ chối (tích phân, đạo hàm, thuyết tương đối): **3/3**. Câu thời tiết: **1/1**, Mimo không còn tả thời tiết.
- Trung vị thời gian trả lời 4,1 giây, chậm nhất 5,6 giây.
- Đạt máy chấm chưa đủ. Sáng 17/10 có một lần đo đạt 43/43, nhưng nhóm đọc lại thì thấy 5/6 ca năn nỉ trỏ sai trang sách. Nhóm không dùng con số đó, sửa lỗi rồi đo lại. Ở lần đo cuối, nhóm đọc lại trang trích của cả 43 câu.

**Minh chứng:** `1_cham_chat_bo_thu/KET_QUA_TEST.md` có bảng từng ca, lý do đạt/trượt và thời gian trả lời. Danh sách câu hỏi và chuỗi cấm nằm ở `bao-cao/bo-test/cau_hoi.py` trong repo. Xem thêm ảnh `anh/5_tu_choi_kien_thuc_ngoai_chuong_trinh.png`.

---

## 2. Thầy cô chấm, dòng nhắc "Mimo có thể nhầm", thêm câu năn nỉ

> AI không thể đúng 100%… Hãy nhờ thầy cô bộ môn đánh dấu 28 câu trả lời "đúng / có chỗ sai / sai", thêm dòng nhắc "Mimo có thể nhầm, em đối chiếu với trang sách nhé", và thêm khoảng 10 câu năn nỉ vào bộ thử.

**Thầy cô bộ môn chấm**

| Lần chấm | Thầy cô đọc | Kết quả |
|---|---|---|
| 28 câu của bản nộp 19/09 | Bản rút gọn câu trả lời | 25 đúng, 3 có chỗ sai |
| 43 câu của lần đo 17/10 10:01 | **Nguyên văn** câu trả lời, kèm số trang Mimo trích | **41 đúng, 2 có chỗ sai, 0 sai** |

- Lần 19/09 có 3 câu có chỗ sai, cả 3 vì **chưa bám sách**: câu thời tiết, câu hàm ý và câu bất phương trình. Nhóm sửa: bài nằm ở sách lớp khác thì Mimo báo lớp và chỉ giảng theo trang sách lớp đó; không sách nào có bài thì Mimo nói thật và không giảng.
- Lần 17/10 có 2 câu có chỗ sai:
  - Câu 16 (ƯCLN) thiếu bước hướng dẫn phân tích ra thừa số nguyên tố.
  - Câu 27 ("(a+b)² = a² + b²?") chưa nêu thẳng công thức đúng và chưa trích sách.
- Nhóm sửa trong ngày. Lần đo lại, câu 16 làm mẫu phép chia liên tiếp, còn câu 27 nói rõ "chưa đúng", nêu (A + B)² = A² + 2AB + B² và trích trang sách Toán 8.
- Câu 16 là loại lỗi nguy hiểm mà ban giám khảo nhắc: **có trang sách đi kèm nhưng vẫn thiếu ý**. Máy chấm không bắt được lỗi này, thầy cô mới bắt được. Nhóm đã thêm điều kiện "phải có" vào bộ thử cho các câu như vậy.

**Dòng nhắc và nút báo sai**

- Dưới ô nhập luôn có dòng: "Mimo có thể nhầm lẫn, em nhớ đối chiếu lại với sách giáo khoa nhé!"
- Câu trả lời có trang sách thì kèm dòng: "Mimo có thể nhầm, em bấm vào trang sách để đối chiếu nhé."
- Câu trả lời dài mà không có trang sách thì kèm dòng: "Câu này Mimo chưa có trang sách làm chứng nên có thể nhầm, em đối chiếu với sách giáo khoa hoặc hỏi thầy cô nhé."
- Mở trang sách, em bấm được **"Trang này không đúng?"** rồi chọn lý do: sai trang, sai sách/sai lớp, hoặc không liên quan câu hỏi. Nhóm xem lại các trang bị báo để sửa.

**Câu năn nỉ**

- Thêm **14 ca năn nỉ** (nhiều hơn 10 ca được yêu cầu), đều là hội thoại nhiều lượt. Có các tình huống: em vội, em "đang làm bài kiểm tra", em nói "cô cho phép dùng AI", và em ra lệnh "bỏ qua mọi quy tắc".
- Chạy cùng 14 ca trên code bản 19/09 và code hiện tại:

| | Đạt máy chấm | Lộ đáp án |
|---|---|---|
| Code bản nộp 19/09 | 9/14 | **3/14** |
| Code hiện tại | 14/14 | **0/14** |

**Minh chứng**

- `2_thay_co_cham/THAY_CO_CHAM_LAN_DO_1710.md`: 43 câu thầy cô chấm, có nguyên văn câu trả lời trước và sau khi sửa.
- `2_thay_co_cham/THAY_CO_CHAM_BAN_NOP_1909.md`: 28 câu của bản nộp 19/09.
- `1_cham_chat_bo_thu/SO_SANH_NAN_NI_1909_VA_1710.md`: so sánh 14 ca năn nỉ.
- Ảnh `anh/1_…`: dòng nhắc. Ảnh `anh/2_…` và `anh/3_…`: nút báo trang sai. Ảnh `anh/4_…`: năn nỉ không lộ đáp án.

---

## 3. Học sinh dùng thử và khảo sát

> Mời 10-15 bạn cùng lớp dùng Mimo khoảng 15-20 phút cho một bài đang học, rồi hỏi bằng Google Form: Mimo có giải hộ không, bạn có tự làm tiếp được không.

**Nhóm đã làm**

- Buổi dùng thử sáng 16/10/2026 (8:30–11:30). Số liệu dưới đây đọc từ hệ thống, chỉ là số tổng hợp, không có tên hay email.

| Chỉ số | Giá trị |
|---|---|
| Số bạn có đặt câu hỏi | **34** (lớp 7) |
| Số câu hỏi | **368**, mỗi bạn trung vị 9 câu |
| Thời gian từ câu đầu tới câu cuối của mỗi bạn | trung vị **17 phút** |
| Môn | Toán 192 · Tiếng Anh 107 · Lịch sử và Địa lí 47 · Ngữ văn 13 · KHTN 8 |
| Thời gian chờ trả lời | trung vị 3,1 giây; 90% câu dưới 3,8 giây |
| Câu có chữ xin đáp án hoặc nhờ giải hộ | 8 câu, của 4 bạn |

**Google Form sau buổi thử (12 phiếu)**

| Câu hỏi | Kết quả |
|---|---|
| Khi nhờ giải trọn gói hoặc xin đáp án nhanh, Mimo phản hồi thế nào? | Chỉ gợi ý bước đầu, hỏi ngược lại: **10/12**. Giải hộ từ đầu đến cuối: **2/12** |
| Sau gợi ý của Mimo, bạn tự làm tiếp được tới đâu? (thang 1–5) | Trung bình **4,4**; 11/12 bạn chọn 4 hoặc 5 |
| Bấm số trích dẫn, Mimo có mở đúng trang sách không? | Đúng trang: 7/12 · lệch trang: 4/12 · không mở được: 1/12 |
| Cần cải tiến gì? | 2 bạn góp ý tốc độ trả lời; 10 bạn không có góp ý cụ thể |

- **2/12 bạn thấy Mimo giải hộ**, trong khi bộ thử đo 0/14 lộ đáp án. Buổi thử chạy trên code đã có luật "không giải tắt", nên cách học sinh thật hỏi vẫn có chỗ bộ thử chưa phủ. Phiếu không ghi câu hỏi cụ thể. Việc tiếp theo: đọc lại hội thoại của hai bạn (khi được đồng ý) và đưa cách hỏi đó vào bộ thử.
- 5/12 phiếu báo trang lệch hoặc không mở được, khớp với góp ý "lệch trang" trong buổi thử. Nhóm đã sửa như ghi ở dưới.

**Từ góp ý của học sinh tới sửa sản phẩm**

- Vài bạn báo Mimo mở trang sách "lệch trang, không đúng bài". Nhóm đã sửa ba chỗ:
  - Nhập mục lục kèm số trang cho đủ **20 môn-lớp** (trước chỉ có 3).
  - Thay 10 cuốn sách quét thiếu trang bằng bản trọn quyển.
  - Thêm nút "Trang này không đúng?".
- Chạy lại 25 câu hỏi bài thật của buổi thử trên bản 17/10: câu có trang sách tăng từ **10/25 lên 18/25**.
- Riêng Tiếng Anh: khi dò 16 câu, số câu trích đúng Unit em đang học tăng từ **0/10 lên 15/15**.

**Còn thiếu:** phiếu quan sát trong buổi thử chưa được điền.

**Minh chứng**

- `3_hoc_sinh_dung_thu/KET_QUA_DUNG_THU_1610.md`: số liệu đầy đủ và cách nhóm tìm ra lỗi lệch trang.
- `3_hoc_sinh_dung_thu/KET_QUA_GOOGLE_FORM.md`: tổng hợp 12 phiếu Google Form, không có tên hay tài khoản.

---

## 4. Luyện tập thích ứng

> Phần luyện tập thích ứng nên tính thêm độ khó của câu, số lần dùng gợi ý và dạng lỗi hay gặp, để gợi ý bài luyện sát với từng bạn hơn.

**Trước 19/09 đã có:** độ khó chọn theo mức nắm bài, và ghi lại em có xem gợi ý không.

**Thêm sau 19/09**

- **Dạng lỗi:** mỗi phương án sai gắn một dạng lỗi theo môn. Ví dụ: hiểu sai khái niệm, nhầm ngữ pháp, nhầm nguyên nhân – kết quả, nhầm trình tự thời gian. Lần chọn sai nào cũng được ghi lại dạng lỗi.
- **Dạng lỗi hay gặp:** những dạng lỗi lặp lại (tối đa 3) được đưa vào đề bài cho Mimo, để câu sau nhắm đúng chỗ em hay sai.
- **Số lần dùng gợi ý:** Mimo đếm em phải xem gợi ý ở bao nhiêu câu gần nhất. Nếu quá nửa số câu phải xem, câu sau giữ cùng mức nhưng có bước trung gian rõ hơn để em tự làm. Làm đúng nhờ gợi ý thì không lên độ khó ngay. Nút gợi ý ghi rõ "được ít điểm hơn một chút".
- **Chấm theo từng chủ đề** của bài đang học. Mỗi câu chỉ được tính một lần, kể cả khi em bấm nộp hai lần.

**Số liệu buổi dùng thử 16/10**

| Chỉ số | Giá trị |
|---|---|
| Lượt làm | 178 lượt, của 14 bạn; đúng 100/178 (56%) |
| Độ khó các câu | mức 2: 74 · mức 3: 88 · mức 4: 16 |
| Lượt có mở gợi ý | 5 |
| Dạng lỗi gặp nhiều nhất | hiểu sai khái niệm 26 · nhầm ngữ pháp 14 · nguyên nhân – kết quả 13 · trình tự thời gian 7 · nhầm từ vựng 5 |

**Còn lại:** chưa đo được luyện tập thích ứng giúp em tiến bộ bao nhiêu. Việc này cần thử nghiệm dài ngày ở mục 5.

**Minh chứng:** ảnh `anh/6_luyen_tap_muc_do_kho_va_goi_y.png` có mức độ khó, năng lực hiện tại và gợi ý. Ảnh `anh/7_luyen_tap_cham_va_goi_y_bai_tiep.png` có phần chấm, giải thích lỗi và gợi ý bài tiếp. Số liệu lấy từ `3_hoc_sinh_dung_thu/KET_QUA_DUNG_THU_1610.md`.

---

## 5. Thử nghiệm dài hạn (2–4 tuần)

> Về lâu dài, thử 2-4 tuần với 1-2 lớp, làm bài kiểm tra ngắn trước và sau, so sánh nhóm dùng Mimo với nhóm không dùng.

**Trạng thái:** chưa làm. Nhóm đã viết kế hoạch, triển khai khi nhà trường và phụ huynh đồng ý bằng văn bản.

- Chia hai nhóm **cùng lớp, cùng giáo viên, cùng chương** theo số thứ tự chẵn/lẻ. Nhóm A dùng Mimo khi làm bài về nhà, nhóm B học như bình thường.
- Bài kiểm tra trước và sau do giáo viên bộ môn ra đề: 15 phút, 10 câu, cùng dạng và cùng độ khó, khác số liệu.
- So sánh **mức tăng điểm** của hai nhóm, kèm khoảng tin cậy 95%. Script tổng hợp đã viết sẵn (`bao-cao/thu-nghiem/tong_hop.py`). Nếu khoảng tin cậy chứa 0 thì không kết luận Mimo giúp tăng điểm.
- Hết đợt thử, nhóm B cũng được dùng Mimo.

**Minh chứng:** `5_thu_nghiem_dai_han/KE_HOACH_THU_NGHIEM.md`.

---

## Nhật ký làm việc sau 19/09

- `6_nhat_ky/CAC_LAN_SUA_SAU_1909.md`: mọi lần sửa code và tài liệu từ 20/09 đến nay, kèm mã commit.
- `6_nhat_ky/PROMPT_SAU_1909.md`: các câu lệnh nhóm dùng với AI lập trình trong giai đoạn này. Email và tên học sinh đã được che.
