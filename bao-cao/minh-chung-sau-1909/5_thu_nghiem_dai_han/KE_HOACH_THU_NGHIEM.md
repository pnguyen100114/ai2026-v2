# Kế hoạch thử nghiệm Mimo với học sinh thật

Ban giám khảo góp ý: bộ 28 câu tự chấm chưa cho biết Mimo có thật sự giúp học sinh tự học
hay không. Tài liệu này gồm ba việc, xếp theo thứ tự làm được sớm nhất.

---

## Việc 1 — Thầy cô bộ môn chấm kiến thức (1 tuần)

Máy chỉ chấm được Mimo có trích dẫn, có từ chối, có lộ đáp án không. Một câu giảng sai mà
vẫn gắn đúng trang sách thì máy cho đạt, trong khi học sinh lại tin vì thấy có trang sách.

1. `python bao-cao/bo-test/phieu_cham.py xuat` → `phieu_cham_giao_vien.csv`, kèm mỗi môn một
   phiếu riêng trong `bo-test/phieu_theo_mon/` (Toán 24 câu, KHTN 9, Ngữ văn 5, Tiếng Anh 3, LSĐL 2).
2. Gửi mỗi thầy cô phiếu đúng môn mình dạy.
3. Thầy cô điền cột **Đánh giá**: `đúng` / `có chỗ sai` / `sai`. Nếu không phải `đúng` thì ghi rõ chỗ sai.
4. `python bao-cao/bo-test/phieu_cham.py nhap <file>` (mỗi phiếu môn nhập một lần) rồi `python bao-cao/bo-test/lam_bang.py`.

Báo cáo đếm riêng những câu **có chỗ sai dù có trang sách đi kèm**, vì đây là loại lỗi nguy
hiểm nhất.

**Đã làm (16–17/10):** 28 thầy cô, mỗi người một câu, đã chấm 28 câu của lần chạy 19/09 trên bản
rút gọn. Kết quả cuối: 25 đúng, 3 có chỗ sai (20, 22, 24), xem
`bo-test/cham_giao_vien_1909.csv`. Ba câu có chỗ sai đều vì thầy cô muốn Mimo bám sát sách:
câu 20 bịa thời tiết (bản hiện tại đã từ chối), câu 22 và 24 giảng bài sách lớp em không có bằng
kiến thức ngoài sách (từ 17/10 Mimo không giảng bài của lớp khác, chỉ báo bài ở lớp nào và mời
em chọn lại lớp). **Cần hỏi lại thầy cô**
chỗ sai cụ thể ở câu 24. Đối chiếu với nguyên văn thì bản rút gọn lệch ở các câu
21–24. Phiếu nguyên văn của lần chạy
16/10 đã xuất sẵn ở `bo-test/phieu_cham_giao_vien.csv`, **chờ gửi thầy cô**. Nhắc thầy cô điền
cột "Thầy cô chấm" (tên, môn, trường). Lưu ý: chạy lại `chay_test.py` thì phiếu này không nhập
được nữa, nên chấm xong mới chạy lại.

---

## Việc 2 — 10–15 bạn cùng lớp dùng thử 15–20 phút (1 buổi)

**Chuẩn bị**
- Chọn **một bài đang học trên lớp** (ví dụ Toán 8 — Hằng đẳng thức đáng nhớ) để ai cũng có bài tập thật.
- Mỗi bạn một tài khoản; xin phép giáo viên chủ nhiệm và báo phụ huynh.
- Nhóm **không** hướng dẫn cách hỏi, chỉ giao: *"Em dùng Mimo để làm 2–3 bài tập trong SGK trang …"*.

**Công cụ đã chuẩn bị** (`bao-cao/thu-nghiem/`)
- `tao_google_form.gs`: dán vào script.google.com rồi bấm Chạy là có sẵn Google Form 9 câu dưới đây.
- `phieu_quan_sat.csv`: phiếu cho người quan sát, mỗi dòng một bạn.
- `tong_hop.py khao-sat <csv tải từ Form>` → `KET_QUA_KHAO_SAT.md` với các con số ở mục Báo cáo lại.

**Trong buổi** — một thành viên ghi lại vào `phieu_quan_sat.csv` (không nhắc bài):
- bạn có xin đáp án không, xin mấy lần;
- Mimo có lỡ đưa đáp án không (chụp màn hình lại);
- bạn có bấm vào trang sách không.

**Google Form ngay sau buổi** (5 phút, không ghi tên)

| # | Câu hỏi | Kiểu trả lời |
|---|---|---|
| 1 | Em học lớp mấy, đã làm bài nào với Mimo? | Ngắn |
| 2 | Có lúc nào Mimo **giải hết bài** cho em không? | Không bao giờ / 1 lần / Nhiều lần |
| 3 | Sau gợi ý của Mimo, em có **tự làm tiếp** được bước sau không? | Thang 1–5 (1 = không làm được, 5 = tự làm hết) |
| 4 | Em có thử năn nỉ xin đáp án không? Mimo phản ứng thế nào? | Có/Không + đoạn ngắn |
| 5 | Em có bấm xem trang sách Mimo trích không? Có thấy khớp với lời Mimo giảng không? | Không bấm / Bấm, khớp / Bấm, thấy chỗ không khớp |
| 6 | Em có phát hiện chỗ nào Mimo giảng **sai** không? Chỗ nào? | Đoạn ngắn |
| 7 | So với hỏi ChatGPT/Gemini, Mimo giúp em hiểu bài hơn hay kém hơn? | Thang 1–5 |
| 8 | Lần sau làm bài tập về nhà, em có muốn dùng Mimo không? Vì sao? | Thang 1–5 + đoạn ngắn |
| 9 | Điều em **khó chịu nhất** khi dùng Mimo là gì? | Đoạn ngắn |

**Báo cáo lại:** tỉ lệ bạn trả lời "Không bao giờ" ở câu 2, điểm trung bình câu 3, và mọi ảnh
chụp Mimo lỡ đưa đáp án. Những ca lỡ đưa đáp án thì đưa vào bộ thử, nhóm `năn nỉ` trong
`bo-test/cau_hoi.py`.

---

## Việc 3 — Thử 2–4 tuần với 1–2 lớp, kiểm tra trước và sau (dài hạn)

**Thiết kế**
- Hai nhóm **cùng lớp, cùng giáo viên, cùng chương**: nhóm A dùng Mimo khi làm bài về nhà,
  nhóm B học như bình thường. Chia nhóm theo danh sách lớp xen kẽ (số thứ tự chẵn/lẻ), không
  để các bạn tự chọn, vì bạn tự chọn thường là bạn vốn chăm hơn.
- **Bài kiểm tra trước**: 15 phút, 10 câu về chương sắp học. Giáo viên bộ môn ra đề, không phải nhóm.
- **Bài kiểm tra sau**: cùng dạng, cùng độ khó, khác số liệu, làm sau 2–4 tuần.

**So sánh** — nhập điểm theo mẫu `thu-nghiem/diem_truoc_sau_mau.csv` rồi chạy
`python bao-cao/thu-nghiem/tong_hop.py truoc-sau <file>` → `KET_QUA_TRUOC_SAU.md` (mức tăng từng
nhóm và khoảng tin cậy 95% của chênh lệch; khoảng chứa 0 thì không được kết luận Mimo giúp tăng điểm).
- Mức tăng điểm (sau − trước) của nhóm A so với nhóm B, không so điểm sau một cách đơn lẻ.
- Với nhóm A, lấy thêm số liệu Mimo đã ghi: số lượt hỏi, số câu luyện tập, số lần xem gợi ý.

**Nói rõ giới hạn khi báo cáo:** mẫu nhỏ (khoảng 30–40 bạn), thời gian ngắn, nhóm A có thể
cố gắng hơn vì biết mình đang được thử (hiệu ứng Hawthorne). Kết quả là dấu hiệu ban đầu,
chưa phải bằng chứng chắc chắn.

**Đạo đức:** xin phép nhà trường và phụ huynh bằng văn bản. Hết đợt thử thì cho nhóm B dùng
Mimo. Không đưa điểm từng bạn vào báo cáo.
