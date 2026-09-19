# Kế hoạch quay video và nộp hồ sơ — Gia Sư AI Mimo

Ban tổ chức yêu cầu **hai video khác nhau**, không phải một:

| Mục | Giới hạn | Hình thức nộp | Trạng thái |
|---|---|---|---|
| Tài liệu dự án (PDF) | **tối đa 8 trang** | Tải tệp lên hệ thống | Đã cắt còn **đúng 8 trang**, cần xuất lại PDF |
| **Video thuyết trình** | **tối đa 5 phút** | Link Drive / YouTube đã mở quyền xem | Chưa quay |
| **Video demo sản phẩm** | **tối đa 3 phút** | Link Drive / YouTube đã mở quyền xem | Chưa quay |
| Lịch sử câu lệnh + ảnh minh chứng | không bắt buộc | Link thư mục Drive | Đã có sẵn `prompt-log/`, nên nộp |
| Kê khai AI / API / thư viện / mã nguồn mở | không bắt buộc | Link Drive | Nên nộp |
| Kho mã nguồn | không bắt buộc | URL repository | Đã có GitHub, nên nộp |

Hai video **không được cắt ra từ cùng một file**. Video thuyết trình là bài nói về dự án; video
demo là màn hình sản phẩm chạy thật. Nộp trùng nội dung là mất điểm cả hai.

Riêng bản chiếu tại hội trường vẫn giữ trên USB (mục 6), vì lúc trình bày trực tiếp không nên phụ
thuộc vào mạng để mở Drive.

---

## 0. Hồ sơ PDF — đã cắt xuống 8 trang

Yêu cầu của BTC là tối đa 8 trang. Bản cũ 11 trang; `bao-cao/make_report.py` đã được sửa và nay
xuất ra **đúng 8 trang** (đã kiểm bằng Word):

- Hai biểu đồ cột ghép chung một hình (bản rời vẫn xuất riêng để chiếu trong video).
- Hình minh họa thu từ 16cm xuống 14cm, ảnh sản phẩm dùng bản cắt gọn `_crop`.
- Giãn dòng 1,25 -> 1,15; khoảng cách đoạn và tiêu đề ép lại.

**Mỗi lần sửa hồ sơ phải chạy lại hai lệnh này, theo đúng thứ tự:**

    python bao-cao/make_report.py
    powershell -ExecutionPolicy Bypass -File bao-cao/xuat_pdf.ps1

Lệnh thứ hai xuất PDF **và in ra số trang**, báo rõ ngay nếu vượt 8. Phải **đóng file Word** trước
khi chạy, không thì script không ghi đè được file .docx.

> ⚠️ Đang vừa khít 8 trang. Thêm một đoạn văn hay một tấm ảnh là sang trang 9, nên chạy lại lệnh
> kiểm tra sau **mọi** lần sửa — nhất là khi thay link Drive thật và bổ sung ảnh học sinh dùng thử.

## 1. Video thuyết trình (tối đa 5 phút)

Đây là bài nói về dự án: vì sao làm, làm thế nào, kết quả ra sao. Có mặt người nói, không chỉ là
lồng tiếng trên slide — ban giám khảo muốn thấy đội thi.

**Mục tiêu độ dài: 4 phút 40 giây.** Đừng quay sát 5:00; hệ thống nộp bài làm tròn lên và một video
4:59 đôi khi hiện thành 5:01, bị loại vì quá thời lượng.

### Bố cục và ngân sách thời gian

| Phút | Phần | Nội dung |
|---|---|---|
| 0:00–0:25 | Chào và giới thiệu đội | Tên đội, tên thành viên, tên sản phẩm. Quay mặt người nói |
| 0:25–1:10 | **Vấn đề** | Học sinh THCS hỏi chatbot thì nhận được câu trả lời chung chung, nhiều khi sai, và không biết nó lấy từ đâu. Phụ huynh không kiểm chứng được |
| 1:10–1:55 | **Giải pháp** | Mimo chỉ trả lời dựa trên SGK đã số hóa, mỗi câu trả lời kèm tên sách và số trang, bấm vào là thấy đúng trang đó |
| 1:55–2:45 | **Cách làm** | Sơ đồ kiến trúc: PDF SGK → tách trang, nhúng vector → Pinecone → khi học sinh hỏi thì tìm trang liên quan rồi mới đưa cho Gemini trả lời. Nói rõ đây là RAG, không phải hỏi thẳng chatbot |
| 2:45–3:40 | **Kết quả thử nghiệm** | Dùng đúng số liệu thật trong hồ sơ: số cuộc trò chuyện, 3 môn Toán/KHTN/Ngữ văn, lớp 6–8, thời gian trả lời trung bình. Chiếu 3 biểu đồ trong `bao-cao/charts/` |
| 3:40–4:10 | **Quá trình làm** | Ảnh bản đầu tiên còn lỗi bên cạnh bản hiện tại. Phần này cho thấy đội tự làm thật, rất dễ ăn điểm |
| 4:10–4:40 | **Hạn chế và hướng phát triển** | Nói thẳng điểm còn yếu và dự định. Kết bằng một câu ngắn |

### Cách quay

- Người nói ngồi hoặc đứng trước nền gọn, ánh sáng từ phía trước mặt (đừng ngồi quay lưng ra cửa sổ).
- Quay ngang, 1080p. Nếu quay bằng điện thoại thì kẹp cố định, **tuyệt đối không cầm tay**.
- Mic: tai nghe có mic hoặc điện thoại thứ hai đặt gần miệng ghi âm riêng, rồi ghép tiếng khi dựng.
  Tiếng thu từ xa bằng mic camera nghe rất vang.
- Slide chiếu xen kẽ: mặt người nói ở các đoạn chào/vấn đề/kết, slide toàn màn hình ở các đoạn
  kiến trúc và số liệu.
- Chia nhau nói nếu đội có nhiều thành viên — ban giám khảo thích thấy cả đội tham gia.

---

## 2. Video demo sản phẩm (tối đa 3 phút)

Chỉ có màn hình sản phẩm chạy thật, không có mặt người, không có slide giới thiệu dài dòng.

**Mục tiêu độ dài: 2 phút 50 giây.**

### Danh sách phân cảnh

Lời thoại chi tiết cho từng cảnh nằm ở `bao-cao/KICH_BAN_VIDEO_DEMO.md`.

| # | Cảnh | Thao tác | Thời lượng |
|---|---|---|---|
| 1 | Nhan đề | Slide 1 dòng: tên sản phẩm và câu "Trả lời theo đúng trang SGK" | 4 giây |
| 2 | Đăng nhập | Nhập email, khảo sát 3 bước (môn – mục tiêu – lộ trình), tua nhanh 2× | 16 giây |
| 3 | Lộ trình học | Lộ trình Toán 8 theo SGK, mỗi bài hiện tên sách và số trang. Bấm một bài để mở chat | 18 giây |
| 4 | **Hỏi Mimo — cảnh đinh** | Gõ một bài Toán 8, ra lời giải từng bước, cuộn xuống phần trích nguồn, **bấm ảnh thu nhỏ để phóng to đúng trang sách** | **50 giây** |
| 5 | Hỏi bằng ảnh | Tải ảnh chụp đề bài, Mimo đọc đề và giải | 22 giây |
| 6 | Giọng nói | Bấm nghe Mimo đọc đáp án | 12 giây |
| 7 | Luyện tập | Nhận câu hỏi, xin gợi ý, trả lời, được chấm ngay | 24 giây |
| 8 | Pomodoro và hồ sơ | Đặt 25 phút rồi chạy; mở hồ sơ xem tiến độ; bấm 👍 một câu trả lời | 18 giây |
| 9 | Kết | Slide kiến trúc: React (Vercel) → FastAPI (Render) → Pinecone + Gemini → PDF SGK | 6 giây |
| | **Tổng** | | **2:50** |

**Cảnh 4 là cảnh quyết định giải.** Nó là thứ phân biệt sản phẩm với một con chatbot bất kỳ. Zoom
vào phần trích nguồn, để chuột dừng đủ lâu cho người xem đọc kịp số trang.

Quay **rời từng cảnh** rồi mới ghép: hỏng một cảnh chỉ quay lại cảnh đó. Việc này quan trọng vì mỗi
lần quay lại là tốn thêm một lượt Gemini và một lượt đọc Pinecone.

### Bản mẫu quay bằng máy, để canh nhịp trước khi tự quay

`bao-cao/quay_video.py` lái trình duyệt đi đúng chín cảnh trên và ghi lại thành video. Đây **không
phải bản nộp** — nó là bản mẫu để xem trước một cảnh dài bao nhiêu, dừng ở đâu, cuộn tới đâu, rồi
mới ngồi quay lại bằng OBS cho đúng nhịp đó.

    .venv\Scripts\python.exe bao-cao\quay_video.py          # in ra danh sách chín cảnh
    .venv\Scripts\python.exe bao-cao\quay_video.py 4        # quay riêng cảnh 4
    .venv\Scripts\python.exe bao-cao\quay_video.py 3 4 7    # quay vài cảnh
    .venv\Scripts\python.exe bao-cao\quay_video.py tat-ca   # quay cả chín cảnh

Gọi trống thì nó không quay gì cả, chỉ in danh sách. Mỗi cảnh ra một tệp `.webm` riêng trong
`bao-cao/video-tho/`, kèm dòng báo cảnh đó **dài bao nhiêu giây so với kịch bản** — đó chính là số
cần biết trước khi tự quay.

Vài điều phải nhớ khi dùng:

- [ ] **Trỏ `VITE_API_BASE_URL` sang bản deploy trên Render** (`https://gia-su-ai-api.onrender.com`),
      để quay đúng bản mà ban giám khảo sẽ mở. Số liệu đợt thử nghiệm trong hồ sơ đã khóa cứng theo
      ngày 13–14/9 nên tài khoản demo sinh ra hôm nay không làm lệch con số nộp — cứ quay thoải mái.
      Script tự kiểm tra và dừng lại nếu backend không trả lời.
- [ ] **Mỗi lần chạy vẫn tốn quota thật** — đúng như cảnh báo ở mục 3.2. Chạy `tat-ca` là một loạt
      lượt Gemini và lượt đọc Pinecone. Quay thử từng cảnh một, đừng chạy cả bộ cho vui.
- [ ] Thêm `--nhanh` khi chỉ muốn kiểm tra script còn bám đúng giao diện hay không: nó rút hết các
      quãng dừng, ra đoạn quay vô dụng nhưng chạy nhanh.
- [ ] **Cảnh 6 không dùng được bản mẫu**: video Playwright không có tiếng, mà cảnh 6 chính là cảnh
      nghe Mimo đọc. Cảnh đó bắt buộc tự quay có thu tiếng.
- [ ] Chuột trong bản mẫu là chấm tròn vẽ thêm, không phải con trỏ thật. Lúc tự quay nhớ bật hiệu
      ứng làm nổi con trỏ như mục 3.3.
- [ ] Cảnh 5 cần ảnh đề bài đặt sẵn ở `bao-cao/anh-de-bai.png`.

Phiên demo (tài khoản, lộ trình, câu hỏi đầu tiên) được dựng một lần rồi lưu vào
`video-tho/phien.json` để quay lại cảnh khác khỏi chờ từ đầu. Backend dựng lại DB thì thêm
`--phien-moi`. Thư mục này không lên kho — cả `bao-cao/` vốn đã nằm trong `.gitignore` — và cũng
đừng gỡ ra: tệp video hàng chục MB, mà `phien.json` còn giữ phiên đăng nhập của tài khoản demo.

---

## 3. Chuẩn bị trước khi bấm ghi

### 3.1 Nội dung, phần quan trọng nhất

- [ ] Chọn **5–6 câu hỏi cố định** dùng trong video demo, viết ra giấy.
- [ ] Chạy thử từng câu **trước ngày quay**: trả lời đúng, trích đúng tên sách, đúng số trang, ảnh
      trang sách mở lên đúng nội dung. Câu nào trích sai trang thì thay câu khác, đừng quay xong
      mới phát hiện.
- [ ] Ảnh đề bài cho cảnh 5: chụp sẵn, chữ rõ, đã thử ra kết quả tốt.
- [ ] Tài khoản demo có sẵn dữ liệu đẹp: vài bài đã hoàn thành, chuỗi ngày học trên 3, biểu đồ thời
      gian có cột. Đừng để dashboard trống trơn trên video.

### 3.2 Hạn mức miễn phí, đọc kỹ phần này

- [ ] **Gemini**: quay vào buổi sáng ngay sau khi quota reset, đừng quay cuối ngày. Có key trả phí
      thì để dành dùng đúng ngày quay.
- [ ] **Pinecone**: gói free tính theo **lượt đọc**, không phải lượt ghi. Mỗi câu hỏi trong video là
      một lần đọc, nên chuẩn bị kỹ để quay một lần ăn ngay.
- [ ] **Render**: mở `https://<backend>/api/health` trước khi quay 2 phút để đánh thức, rồi mới ghi.

### 3.3 Máy quay (chính là laptop)

- [ ] Màn hình để **1920×1080**, tỉ lệ 16:9.
- [ ] Trình duyệt mở **cửa sổ mới sạch**: không tiện ích mở rộng, không thanh bookmark, không tab lạ.
- [ ] Zoom trang **110–125%**, chữ nhỏ chiếu lên tường là không đọc được.
- [ ] Bật **Focus assist**, thoát Zalo, Messenger, Outlook. Một thông báo nhảy lên giữa cảnh là hỏng
      cả cảnh quay.
- [ ] Bật hiệu ứng làm nổi con trỏ chuột.
- [ ] Cắm sạc, tắt chế độ tiết kiệm pin, nếu không khung hình sẽ giật.

### 3.4 Phần mềm ghi

- **OBS Studio** (miễn phí): Display Capture, 1920×1080, **30 fps**, bitrate 10–12 Mbps.
- Ghi ra **MKV** rồi *Remux to MP4* sau. Máy treo giữa chừng thì file MKV vẫn xem được, file MP4
  mất trắng.
- Tiếng mic ghi **ra track riêng** để lúc dựng còn tách được lời ra khỏi hình.

---

## 4. Lời thuyết minh cho video demo

Quay hình **im lặng trước**, thu lời sau. Vừa thao tác vừa nói sẽ vấp, mà mỗi lần vấp là tốn thêm
một lượt Gemini để quay lại.

- Viết kịch bản lời trước, đọc thử và canh giờ cho khớp từng cảnh.
- Thu bằng tai nghe có mic, phòng kín, tắt quạt và điều hòa.
- **Có phụ đề cháy cứng vào hình**, cỡ chữ lớn, nền mờ phía dưới. Ban giám khảo có thể xem video
  trên máy không loa.
- Xuất thêm một bản **không lời, chỉ có phụ đề** để dùng khi trình bày trực tiếp ở hội trường
  (mục 6).

---

## 5. Nộp bài — phần dễ mất điểm oan nhất

### Kiểm tra thời lượng trước khi tải lên

Mở file bằng VLC hoặc xem thuộc tính, ghi lại con số chính xác. Video thuyết trình phải dưới 5:00,
video demo phải dưới 3:00. Quá **một giây** cũng có thể bị loại.

### Mở quyền xem đúng cách

**Nếu dùng Google Drive:**
1. Chuột phải vào file → Chia sẻ → đổi "Hạn chế" thành **"Bất kỳ ai có đường liên kết"**.
2. Vai trò để **"Người xem"**.
3. Sao chép liên kết, dán vào **cửa sổ ẩn danh** (Ctrl+Shift+N) để thử. Nếu nó hỏi đăng nhập hoặc
   hiện "Bạn cần quyền truy cập" thì chưa mở đúng.
4. Đừng dùng tài khoản Google của trường — nhiều tài khoản trường bị chặn chia sẻ ra ngoài tổ chức,
   và lỗi này chỉ lộ ra khi thử bằng cửa sổ ẩn danh.

**Nếu dùng YouTube:** để chế độ **"Không công khai" (Unlisted)**, không phải "Riêng tư" (Private).
Riêng tư thì ban giám khảo không xem được. Tắt luôn phần bình luận cho gọn.

### Đặt tên file rõ ràng

```
[Tên đội] - Mimo - Video thuyet trinh.mp4
[Tên đội] - Mimo - Video demo san pham.mp4
[Tên đội] - Mimo - Ho so du an.pdf
```

### Thư mục minh chứng (không bắt buộc nhưng nên nộp)

Đội đã có sẵn `prompt-log/PROMPT_LOG.md` và `PROMPT_HISTORY.md` (hơn 2.000 dòng lịch sử làm việc
với AI). Đây là minh chứng rất mạnh cho việc đội tự làm và dùng AI minh bạch.

Tạo một thư mục Drive `Minh chung/` gồm:
- `Lich_su_cau_lenh.pdf` — xuất từ hai file trong `prompt-log/`
- `Anh_minh_chung/` — ảnh trong `bao-cao/hinh-minh-hoa/` và `bao-cao/charts/`
- `Ke_khai_cong_cu.pdf` — bảng liệt kê: Gemini API, Pinecone, FastAPI, React, YOLOv8, SGK Kết nối
  tri thức, và các thư viện mã nguồn mở đã dùng. Ghi rõ cái nào miễn phí, cái nào có giấy phép gì
- Link GitHub repository

Mở quyền cả thư mục theo đúng cách ở trên, rồi dán link vào ô "Lịch sử câu lệnh và hình ảnh minh chứng".

---

## 6. Bản dự phòng cho buổi trình bày trực tiếp

Link Drive là để nộp bài. Lúc đứng trước ban giám khảo thì **không mở Drive** — mạng hội trường hay
chết, Render hay ngủ, Gemini hay hết lượt.

Chép ra USB (format **exFAT**), file MP4 mã hóa **H.264 + AAC** (không dùng H.265/HEVC vì nhiều máy
Windows thiếu codec, mở ra chỉ thấy màn hình đen):

```
USB/
├── 00_DOC_TRUOC.txt          ← 5 dòng: mở file nào, mở bằng gì
├── 01_Demo_3phut.mp4         ← bản chính để chiếu
├── 02_Demo_3phut_KHONG_LOI.mp4  ← để tự thuyết minh đè lên nếu loa hỏng
├── 03_Thuyet_trinh_5phut.mp4
├── 04_Demo_90giay.mp4        ← cắt từ bản 3 phút, dùng khi bị giục
├── Slide/           Ho_so_du_an.pdf + slide trình bày
├── Anh_man_hinh/    10–12 ảnh PNG  ← phao cuối cùng nếu video cũng không chạy
└── VLC_Portable/    vlc.exe, chạy thẳng không cần cài
```

Sao lưu: **2 USB** (một cầm tay, một trong cặp), thêm một bản trên laptop ngoài Desktop và một bản
trong điện thoại.

### Thang xử lý tại hội trường

Quyết định trong 10 giây, không loay hoay trước ban giám khảo:

1. **Có mạng, Render đã thức, Gemini còn lượt** → demo trực tiếp, để video mở sẵn ở tab bên cạnh.
2. **Mạng hội trường chết** → phát 4G điện thoại cho laptop, demo tiếp.
3. **Gemini hết lượt hoặc backend lỗi** → mở video từ USB.
4. **Máy hội trường không mở được video** → mở thư mục ảnh màn hình, thuyết minh theo ảnh.

Câu chuyển cảnh nên tập trước: *"Để tiết kiệm thời gian của hội đồng, em xin chiếu phần demo đã
được ghi lại đầy đủ."* Chủ động, không có vẻ đang chữa cháy.

---

## 7. Lịch làm việc

| Mốc | Việc | Thời gian |
|---|---|---|
| D-7 | **Cắt hồ sơ PDF từ 11 xuống 8 trang**, xuất lại từ bản `.docx` mới nhất | 3 giờ |
| D-6 | Chốt 5–6 câu hỏi cho video demo, chạy thử, thay câu nào trích sai trang | 2 giờ |
| D-5 | Tạo tài khoản demo và nuôi dữ liệu đẹp; viết kịch bản lời cho cả hai video | 3 giờ |
| D-4 sáng | **Quay hình demo** lúc quota Gemini còn mới. Quay rời từng cảnh, mỗi cảnh 2 lần | 3 giờ |
| D-4 chiều | Thu lời cho video demo | 1 giờ |
| D-3 | Làm slide và **quay video thuyết trình** | 4 giờ |
| D-2 | Dựng cả hai video, làm phụ đề, xuất file, **kiểm tra thời lượng** | 4 giờ |
| D-1 | Tải lên Drive, mở quyền, **thử link bằng cửa sổ ẩn danh**, nộp hồ sơ | 2 giờ |
| D-1 | Chuẩn bị thư mục minh chứng và link GitHub, nộp các mục không bắt buộc | 1 giờ |
| D-1 | Chép USB, thử mở trên một máy khác đã rút mạng | 1 giờ |
| D-0 | Đến sớm, cắm thử USB vào máy hội trường, kiểm tra tỉ lệ hình và âm lượng | 30 phút |

---

## 8. Kiểm tra lần cuối trước khi bấm nộp

- [ ] Hồ sơ PDF **đúng 8 trang hoặc ít hơn**, và là bản xuất từ `.docx` mới nhất
- [ ] Video thuyết trình **dưới 5:00**, video demo **dưới 3:00**
- [ ] Hai video **khác nội dung nhau**, không phải hai bản cắt của cùng một file
- [ ] Cả hai link mở được trong **cửa sổ ẩn danh**, không hỏi đăng nhập
- [ ] YouTube để **Unlisted**, không phải Private
- [ ] Trong video không lộ email thật, API key, hay tên file cá nhân trên thanh tiêu đề
- [ ] USB đã thử trên máy khác, đã rút mạng, bằng trình phát mặc định
