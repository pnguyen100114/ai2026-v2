# Kịch bản video thuyết trình — Mimo, Gia sư AI học theo sách giáo khoa

**Thời lượng đích: 4 phút 35 giây** (giới hạn 5 phút, chừa 25 giây an toàn).
**Tổng số chữ: khoảng 690** — đọc ở tốc độ 150 chữ/phút, là tốc độ nói rõ ràng, không vội.

Cách dùng: đọc to cả bài, bấm giờ. Nếu ra trên 4:50 thì nói chậm quá hoặc đang thêm chữ ngoài kịch
bản. Nếu dưới 4:10 thì đang đọc vội, ban giám khảo sẽ không kịp nghe số liệu.

Ký hiệu: **HÌNH** là thứ hiện trên màn hình, **LỜI** là câu phải nói. Chỗ có `//` là chỗ ngắt lấy hơi.

---

## Cảnh 1 — Mở đầu · 0:00 → 0:20 · 48 chữ

**HÌNH:** Mặt người nói, chính giữa khung. Góc dưới hiện tên đội và tên sản phẩm.

**LỜI:**

> Em chào thầy cô và ban giám khảo. // Em là [tên], đại diện nhóm **LD-14**, trường **THCS Tân An
> Hội**.
> // Hôm nay nhóm em xin trình bày dự án **Mimo — gia sư AI trả lời theo đúng sách giáo khoa**,
> dành cho học sinh trung học cơ sở.

> 💡 Nói chậm đoạn tên sản phẩm. Đây là câu duy nhất ban giám khảo chắc chắn nhớ.

---

## Cảnh 2 — Vấn đề · 0:20 → 1:05 · 112 chữ

**HÌNH:** Ảnh chụp một chatbot thường trả lời một bài Toán 8, không có nguồn. Khoanh đỏ chỗ không
có trích dẫn.

**LỜI:**

> Tụi em bắt đầu từ chính việc học của mình. // Khi bí một bài, tụi em hỏi các chatbot AI. Chúng
> trả lời rất nhanh, nhưng có ba vấn đề.
>
> **Một là không biết nó lấy từ đâu.** // Câu trả lời trôi chảy nhưng không có nguồn, đúng sai
> không kiểm chứng được.
>
> **Hai là lệch chương trình.** // Nó giải theo cách của sách nước ngoài, ký hiệu khác, phương pháp
> khác với sách giáo khoa lớp 8 tụi em đang học.
>
> **Ba là làm hộ chứ không dạy.** // Hỏi gì nó đưa ngay đáp án, chép xong là quên.
>
> Còn phụ huynh thì không có cách nào kiểm tra xem con mình vừa học đúng hay sai.

> 💡 Đoạn "một là — hai là — ba là" phải tách bạch, ngắt hẳn giữa các ý. Đây là đoạn dựng nên toàn
> bộ lý do dự án tồn tại.

---

## Cảnh 3 — Giải pháp · 1:05 → 1:50 · 105 chữ

**HÌNH:** Chuyển sang quay màn hình. Mimo trả lời một câu hỏi, cuộn xuống phần trích nguồn, bấm vào
ảnh thu nhỏ để phóng to đúng trang sách. Để hình chạy chậm, đừng lướt.

**LỜI:**

> Mimo giải quyết cả ba vấn đề đó bằng một nguyên tắc: // **chỉ trả lời dựa trên sách giáo khoa đã
> được số hóa.**
>
> Mỗi câu trả lời đều kèm tên sách và số trang. // Và như thầy cô đang thấy, bấm vào là hiện đúng
> trang sách đó — học sinh đối chiếu được ngay, phụ huynh cũng kiểm tra được.
>
> Mimo cũng không đưa đáp án luôn. // Nó giảng từng bước, hỏi lại để xem học sinh hiểu tới đâu, rồi
> mới ra bài luyện tập.
>
> Danh mục sách hiện có **29 đầu sách, 5 môn, từ lớp 6 đến lớp 9**.

> ✔️ Đã đối chiếu: sổ nạp sách `backend/rag/.ingest_manifest.json` ghi **29 cuốn, 4.765 đoạn** đã vào
> kho Pinecone — khớp đúng danh mục `books.py`. Nói con số 29 là an toàn, ban giám khảo có hỏi lại
> cũng chứng minh được.

---

## Cảnh 4 — Cách làm · 1:50 → 2:40 · 120 chữ

**HÌNH:** Slide sơ đồ kiến trúc trong `bao-cao/slides/`, hiện dần theo lời nói. Năm bản dựng sẵn,
cùng khổ 1920×1080 nên cắt qua lại không bị nhảy hình:

| Ảnh | Cắt vào lúc nói |
|---|---|
| `so_do_kien_truc_b1.png` | "phương pháp RAG — tìm kiếm rồi mới sinh câu trả lời" |
| `so_do_kien_truc_b2.png` | "sách PDF được tách ra từng trang… lưu vào Pinecone" |
| `so_do_kien_truc_b3.png` | "nó đi tìm những trang sách liên quan nhất trước" |
| `so_do_kien_truc_b4.png` | "rồi mới đưa đúng những trang đó cho mô hình Gemini" — lúc này mũi tên gạch chéo **KHÔNG hỏi thẳng AI** hiện ra |
| `so_do_kien_truc_b5.png` | "React, FastAPI, toàn bộ chạy trên hạ tầng miễn phí" |

Sinh lại bằng `python bao-cao/slides.py` nếu sửa số liệu trên slide.

**LỜI:**

> Về kỹ thuật, nhóm em dùng phương pháp **RAG — tìm kiếm rồi mới sinh câu trả lời**.
>
> Trước tiên, sách giáo khoa bản PDF được tách ra từng trang, chuyển thành vector, lưu vào cơ sở dữ
> liệu Pinecone. //
>
> Khi học sinh đặt câu hỏi, hệ thống **không hỏi thẳng AI**. // Nó đi tìm những trang sách liên quan
> nhất trước, rồi mới đưa đúng những trang đó cho mô hình Gemini, kèm yêu cầu: chỉ được giảng dựa
> trên phần sách này, và phải ghi rõ trang.
>
> Đó là lý do câu trả lời bám chương trình và luôn có nguồn. //
>
> Giao diện viết bằng React, máy chủ dùng FastAPI, toàn bộ chạy trên hạ tầng miễn phí.

> 💡 Câu "**không hỏi thẳng AI**" là câu quan trọng nhất của cảnh này. Nhấn mạnh nó — đây là chỗ
> phân biệt sản phẩm với một con chatbot bọc giao diện.

---

## Cảnh 5 — Kết quả thử nghiệm · 2:40 → 3:30 · 118 chữ

**HÌNH:** Lần lượt 3 biểu đồ trong `bao-cao/charts/`, mỗi biểu đồ hiện toàn màn hình khoảng 15 giây:
`bieu_do1_phien_theo_mon.png` → `bieu_do2_thoi_gian_phan_hoi.png` → `bieu_do3_muc_hieu_bai.png`.

> Dùng ba file rời này, **đừng dùng** `bieu_do1_mon_va_muc_hieu.png` — đó là bản ghép hai biểu đồ
> cho hồ sơ PDF, chiếu lên màn hình sẽ nhỏ và khó đọc.

**LỜI:**

> Nhóm em đã cho Mimo chạy thử thật. //
>
> **17 cuộc trò chuyện, 53 câu hỏi**, trên ba môn Toán, Khoa học tự nhiên và Ngữ văn, từ lớp 6 đến
> lớp 8. //
>
> Về tốc độ: một nửa số câu được trả lời **trong vòng 4,8 giây**, và 90% số câu dưới 11 giây. //
>
> Mimo còn tự đánh giá mức hiểu bài của học sinh sau mỗi câu trả lời — mất gốc, hiểu sơ, hay đã
> hiểu — để lần sau giảng dễ hơn hoặc nâng dần lên. //
>
> Ngoài gõ chữ, học sinh còn **chụp ảnh đề bài** gửi lên, và **nghe Mimo đọc** lời giải.

> 💡 Đọc số liệu chậm hơn phần còn lại. Số nói nhanh là số không ai nhớ.
> Ba con số này phải **khớp tuyệt đối với hồ sơ PDF**. Sửa hồ sơ thì sửa cả kịch bản.

---

## Cảnh 6 — Quá trình làm · 3:30 → 4:05 · 88 chữ

**HÌNH:** Chia đôi màn hình. Bên trái là ảnh bản đầu tiên còn lỗi (Hình 7–9 trong hồ sơ: báo "Không
tìm thấy dữ liệu", công thức hiện ký hiệu thô). Bên phải là giao diện hiện tại.

**LỜI:**

> Bản đầu tiên của tụi em không chạy được như bây giờ. //
>
> Lúc mới làm, Mimo không đọc được kho sách, hỏi gì cũng báo "không tìm thấy dữ liệu". // Nạp được
> sách rồi thì công thức toán hiện ra toàn ký hiệu thô, phần trích nguồn dính vào câu trả lời, đọc
> rất khó.
>
> Nhóm em đã sửa qua nhiều vòng: số hóa lại sách, chỉnh cách hiển thị công thức, tách riêng phần
> nguồn, và làm thêm ảnh trang sách như thầy cô vừa thấy. //
>
> Toàn bộ quá trình này nhóm em có lưu lại đầy đủ trong hồ sơ.

> 💡 Đừng giấu bản lỗi. Ban giám khảo chấm cả quá trình, và ảnh "trước – sau" là bằng chứng mạnh
> nhất cho việc đội tự làm.

---

## Cảnh 7 — Hạn chế và hướng phát triển · 4:05 → 4:35 · 82 chữ

**HÌNH:** Quay lại mặt người nói. Cuối cảnh cắt sang `bao-cao/slides/slide_ket.png` — tên sản phẩm,
khẩu hiệu "Học đúng sách, hiểu đúng bài.", tên đội và tên trường. Để slide chạy hết câu cảm ơn rồi
mới tắt, đừng cắt ngay.

**LỜI:**

> Mimo vẫn còn những chỗ chưa tốt. //
>
> Một số sách giáo khoa bản scan chưa có lớp chữ nên chưa số hóa được. // Với bài hình học, Mimo
> giảng được lời giải nhưng chưa tự vẽ hình. // Và hệ thống đang chạy trên hạ tầng miễn phí nên
> giới hạn số lượt hỏi mỗi ngày. //
>
> Sắp tới nhóm em muốn số hóa nốt các môn còn lại, thêm phần vẽ hình, và làm trang cho phụ huynh
> theo dõi việc học của con. //
>
> Nhóm em xin hết. Em cảm ơn thầy cô đã lắng nghe.

> 💡 Nói thẳng hạn chế là điểm cộng, không phải điểm trừ. Đội nào cũng có hạn chế; đội biết hạn chế
> của mình là đội hiểu sản phẩm của mình.

---

## Bảng tổng hợp thời lượng

| Cảnh | Nội dung | Từ | Đến | Dài | Số chữ |
|---|---|---|---|---|---|
| 1 | Mở đầu | 0:00 | 0:20 | 20 giây | 48 |
| 2 | Vấn đề | 0:20 | 1:05 | 45 giây | 112 |
| 3 | Giải pháp | 1:05 | 1:50 | 45 giây | 105 |
| 4 | Cách làm | 1:50 | 2:40 | 50 giây | 120 |
| 5 | Kết quả thử nghiệm | 2:40 | 3:30 | 50 giây | 118 |
| 6 | Quá trình làm | 3:30 | 4:05 | 35 giây | 88 |
| 7 | Hạn chế và kết | 4:05 | 4:35 | 30 giây | 82 |
| | **Tổng** | | | **4:35** | **673** |

---

## Nếu phải co lại hoặc kéo dài

**Lỡ dài quá 5 phút** — cắt theo thứ tự này, cắt tới đâu đủ tới đó:
1. Cảnh 6 rút còn 20 giây: bỏ đoạn kể chi tiết lỗi, chỉ nói "bản đầu chưa đọc được kho sách, nhóm
   em đã sửa qua nhiều vòng".
2. Cảnh 2 bỏ ý thứ ba (làm hộ chứ không dạy), giữ hai ý đầu.
3. Cảnh 5 bỏ câu về chụp ảnh và nghe đọc — hai tính năng đó đã có trong video demo rồi.

**Còn dư thời gian** — thêm vào cảnh 3, không thêm vào cảnh khác: cho chạy thêm một câu hỏi nữa và
nói "đây là môn Khoa học tự nhiên lớp 6, cùng một cách trả lời, cũng có trang sách kèm theo".
Chứng minh sản phẩm không phải chỉ chạy được đúng một môn là điểm cộng lớn.

---

## Chia vai nếu đội có nhiều người

Ban giám khảo thích thấy cả đội tham gia. Cách chia tự nhiên nhất:

| Người | Cảnh | Lý do |
|---|---|---|
| Người 1 | 1, 2, 7 | Mở và đóng nên cùng một người, video mới liền mạch |
| Người 2 | 3, 4 | Phần giải pháp và kỹ thuật, để người nắm code nhất nói |
| Người 3 | 5, 6 | Phần số liệu và quá trình làm |

Mỗi lần chuyển người thì chuyển cảnh luôn (từ mặt người sang màn hình rồi quay lại), để chỗ ghép
không bị giật.

---

## Trước khi quay

- [ ] Đọc to cả kịch bản, bấm giờ, ra trong khoảng **4:10 – 4:50**
- [ ] Ba con số ở cảnh 5 **khớp với hồ sơ PDF**
- [x] Đã kiểm tra lại số đầu sách nói ở cảnh 3 — 29 cuốn, khớp sổ nạp sách
- [ ] Đã điền **tên thành viên** vào cảnh 1 (tên đội và tên trường đã điền sẵn)
- [x] Slide sơ đồ kiến trúc (cảnh 4) — đã có 5 bản dựng trong `bao-cao/slides/`
- [x] Slide kết (cảnh 7) — `bao-cao/slides/slide_ket.png`
- [ ] Ba biểu đồ trong `bao-cao/charts/` đã xuất ở kích thước đủ lớn để đọc trên màn hình
