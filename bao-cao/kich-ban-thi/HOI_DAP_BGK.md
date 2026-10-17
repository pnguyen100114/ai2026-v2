# Hỏi đáp phản biện – Gia Sư AI Mimo

Phần 1: Thuyết trình & Bảo vệ, 18/10/2026. Soạn tối 17/10/2026, đối chiếu từng câu với code và file kết quả.

## Cách dùng

Tài liệu đi theo thứ tự lời thoại trong `KICH_BAN_THI.md`. Mỗi câu nói trong bài là chỗ BGK có thể hỏi "là sao?", nên mỗi câu có:

- **Khối trích (chữ to):** câu trả lời ngắn, nói trong khoảng 20 giây. Học thuộc ý, không cần thuộc chữ.
- **Nếu hỏi thêm:** chi tiết và con số, chỉ nói khi BGK hỏi sâu.
- **Đừng nói:** câu dễ bị bắt lỗi vì không đúng với code.

Khuôn trả lời: **kết luận trước, một con số hoặc bằng chứng, rồi dừng.** Không biết thì nói "nhóm em chưa đo, em xin ghi nhận". Không đoán.

## Bốn chỗ lời thoại chưa khớp code, sửa trước khi thi

Đọc mục này trước. Nếu không sửa lời thoại thì ít nhất phải biết để không bị bắt.

| # | Lời thoại đang nói | Thực tế trong code | Nên nói |
| --- | --- | --- | --- |
| 1 | Đoạn 1:30: "kèm gợi ý trả lời nhanh **và ước lượng mức hiểu bài của em**" | AI có ước lượng "mất gốc / hiểu sơ / đã hiểu" và lưu vào DB, nhưng **giao diện không hiển thị**, cũng không dùng lại ở đâu | Bỏ vế "ước lượng mức hiểu bài". Có thể thay bằng: "nếu em đã luyện tập, Mimo biết mức thành thạo của em để giảng cho vừa" (đúng: điểm luyện tập được đưa vào prompt) |
| 2 | Demo 5: "câu tiếp ghi **'Mimo soạn câu này để em luyện lại lỗi'**" | Server có tạo câu này, nhưng **giao diện không hiện**. Sau khi chọn sai, màn hình hiện: lời nhận xét, lời giải, khung "**Luyện thêm một câu cùng dạng**" và độ tin cậy đánh giá | Chỉ vào mức thành thạo giảm và khung đề xuất. Nói: "lỗi em vừa mắc được đưa vào yêu cầu soạn câu tiếp theo", đừng chỉ vào dòng chữ không có |
| 3 | Câu phản biện 1, "Nếu hỏi thêm": "ba lớp do code quyết định: an toàn, lọc phạm vi, **luật không giải hộ**" | An toàn và lọc phạm vi đúng là code. "Không giải hộ" chủ yếu nằm trong **lời dặn (prompt)** cho Gemini. Code chỉ chặn cứng trường hợp "em đang kiểm tra", lọc chip gợi ý không được chứa đáp án, và bắt buộc câu trả lời kết thúc bằng câu hỏi | "Hai lớp do code quyết định là an toàn và lọc phạm vi. Không giải hộ thì do lời dặn cho AI, cộng một luật code chặn trường hợp em đang làm bài kiểm tra; nhóm đo bằng 14 ca năn nỉ" |
| 4 | Câu phản biện 11: "mức hiểu bài... để lần sau giảng dễ hơn hay nâng lên" | Như dòng 1: mức hiểu bài trong chat không được dùng lại. Cái được dùng lại là **mức thành thạo từ phần luyện tập** | Nói về mức thành thạo luyện tập (xem mục Demo 5 bên dưới) |

Ngoài ra:

- **Fallback không cứu được khi tài khoản hết tiền.** Mô hình dự phòng chỉ giúp khi *một mô hình* hết lượt. Chạm trần chi tiêu hoặc hết tiền nạp trước thì cả ba mô hình cùng dừng.
- **Tên thầy cô chấm ngày 17/10 đang để trống** trong `ket_qua_gv_1710.json` và `phieu_cham_giao_vien.csv`. BGK hỏi "thầy cô nào chấm" thì nhóm phải nói được tên.
- **Số đoạn sách là 5.498**, không phải 4.765 (số cũ còn sót trong vài tài liệu).

## 0:00–1:30 Mở đầu, bài toán, giải pháp

### 1. "Mimo đang chạy thật trên mạng" – chạy ở đâu?

> Giao diện ở Vercel, địa chỉ ai2026-v2.vercel.app. Máy chủ FastAPI ở Render, vùng Singapore. Database là Postgres trên Supabase, chứa cả tài khoản, lịch sử chat và kho vector sách.

- Nếu hỏi thêm: Render gói miễn phí ngủ sau 15 phút không ai dùng; lần đầu gọi mất khoảng 53 giây mới thức (đo 18/09). Nhóm có một tác vụ GitHub Actions gọi `/api/health` 10 phút một lần để giữ máy chủ thức.

### 2. "Chatbot không biết lấy từ đâu" – Mimo khác ở chỗ nào?

> Mimo không hỏi thẳng AI. Câu hỏi được tìm trong 29 cuốn SGK trước, chỉ những trang tìm được mới được đưa cho Gemini, kèm lệnh chỉ giảng theo các trang đó và ghi số trích dẫn. Bấm số trích dẫn là hiện ảnh chụp đúng trang sách.

- Nếu hỏi thêm: câu nào không có trang sách làm chứng mà dài từ 150 ký tự trở lên thì giao diện ghi "Mimo chưa có trang sách làm chứng nên có thể nhầm".

### 3. "Câu nào lấy từ sách cũng có số trích dẫn" – làm sao bảo đảm số trích dẫn không bị gắn bừa?

> Sau khi Gemini viết xong, code soát lại từng số trích dẫn. Số nào trỏ ra ngoài danh sách trang thì bị xóa. Câu nào gắn trích dẫn mà gần như không trùng chữ với đoạn sách đó cũng bị gỡ số. Không còn trích dẫn hợp lệ nào thì câu trả lời không hiện nguồn.

- Nếu hỏi thêm: "không trùng chữ" nghĩa là câu trả lời và đoạn sách có ít hơn 2 cụm hai từ giống nhau. Code ở `backend/answer_cleanup.py`.
- Đừng nói: "câu nào cũng có trang". Buổi thử 16/10 chỉ 36/368 câu có trang (xem câu 56).

### 4. "Bấm vào là hiện đúng ảnh trang sách" – ảnh lấy từ đâu?

> Lúc nạp sách, nhóm render sẵn mỗi trang PDF thành ảnh JPEG và lưu trên Supabase Storage. Mỗi đoạn sách nhớ nó ở trang nào, nên khi trích dẫn, giao diện mở đúng ảnh trang đó.

- Nếu hỏi thêm: kho ảnh để riêng tư; mỗi lần xem, máy chủ cấp một đường link có chữ ký, hết hạn sau 1 giờ, nên người ngoài không tải được cả cuốn sách. Ảnh rộng tối đa 1100 px, ảnh thu nhỏ 320 px.

### 5. "Lệch chương trình" – Mimo bám sách Kết nối tri thức bằng cách nào?

> Kho chỉ có sách Kết nối tri thức. Mimo chỉ tìm trong sách đúng môn và đúng lớp em đã chọn, và lời dặn cấm giảng bằng kiến thức ngoài các trang tìm được.

### 6. "Không giải hộ" – cụ thể Mimo làm gì?

> Với bài tập, Mimo gợi ý bước đầu rồi hỏi lại để em tự làm. Chỉ khi em đã thử thật và đã qua ít nhất một lượt gợi ý, Mimo mới giải đầy đủ. Năn nỉ không được tính là đã thử. Câu hỏi lý thuyết như "định nghĩa là gì" thì Mimo giảng đầy đủ, vì đó không phải chép đáp án.

- Nếu hỏi thêm: đây chủ yếu là lời dặn cho Gemini. Code chặn cứng một trường hợp: em nói đang làm bài kiểm tra ("đang kiểm tra", "sắp thu bài") thì Mimo trả lời bằng câu soạn sẵn, không gọi AI, không gợi ý gì. Code cũng bắt buộc câu trả lời kết thúc bằng một câu hỏi.
- Đừng nói: "code bảo đảm không bao giờ lộ đáp án". Không có bộ lọc đáp án trên nội dung chính; nhóm đo bằng bộ thử (câu 50–51).

### 7. "Kể cả khi AI lỗi vẫn hiện số 111" – sao chắc được?

> Số 111 không do AI viết mà do code gắn vào. Khi phát hiện dấu hiệu nguy hiểm, code luôn chạy bước gắn lời nhắc, dù Gemini trả lời bình thường, bị lỗi hay hết lượt. Nếu AI không viết được chữ nào, Mimo vẫn hiện câu mở đầu soạn sẵn kèm số 111.

- Nếu hỏi thêm: câu gắn thêm là "Em không phải chịu một mình đâu… gọi Tổng đài quốc gia bảo vệ trẻ em 111 (miễn phí, 24/7). Nếu em đang gặp nguy hiểm ngay lúc này, hãy gọi 115 hoặc 113." Có ở `backend/safety.py`.

## 1:30–3:00 Kiến trúc và luồng dữ liệu

### 8. RAG là gì, nói cho dễ hiểu?

> RAG là "tìm rồi mới viết". Giống học sinh làm bài mở sách: trước hết lật sách tìm đúng trang, rồi mới viết câu trả lời dựa trên trang đó. AI không trả lời bằng trí nhớ của nó mà bằng trang sách hệ thống đưa cho.

### 9. Sao không huấn luyện lại (fine-tune) AI bằng SGK cho nhanh?

> Fine-tune tốn tiền và thời gian, AI vẫn có thể nhớ sai, và không chỉ ra được câu nào lấy từ trang nào. RAG rẻ hơn, trích được trang để kiểm tra, và thêm hay thay một cuốn sách chỉ cần nạp lại, không phải huấn luyện lại.

### 10. "29 cuốn, 5 môn, lớp 6–9" – gồm những cuốn nào?

> Toán 8 cuốn, Tiếng Anh 5, Khoa học tự nhiên 4, Lịch sử và Địa lí 4, Ngữ văn 8: tổng 29 cuốn, bộ Kết nối tri thức, cắt thành 5.498 đoạn.

- Nếu hỏi thêm: danh mục `backend/rag/books.py` là nguồn chuẩn duy nhất: mỗi cuốn có tên file, độ lệch giữa số trang in và số trang PDF, trang cuối, và mục lục chép từ trang MỤC LỤC của sách. Số đoạn đang chạy xem được ở `/api/health`.

### 11. "Cắt thành gần 5.500 đoạn" – cắt thế nào?

> Mỗi trang PDF được đọc lớp chữ, bỏ dòng watermark, rồi cắt thành đoạn khoảng 1.800 ký tự, hai đoạn liền nhau chồng lên 200 ký tự để không đứt ý. Cắt trong từng trang, không nối qua trang, nên đoạn nào cũng biết chắc nó thuộc trang mấy.

- Nếu hỏi thêm: mỗi đoạn gắn môn, lớp, tập, chương, bài, số trang, tên sách. Trang có dưới 120 ký tự chữ thật (bìa, trang toàn ảnh) bị bỏ. Trang trước bài đầu tiên và sau trang cuối trong danh mục (bìa, lời nói đầu, mục lục, quảng cáo bìa sau) cũng bị bỏ, để mục lục không bị trích như nội dung bài.

### 12. Sách scan không có chữ thì sao?

> Trước khi nạp, nhóm chạy công cụ `check_pdf` lấy mẫu 20 trang giữa sách. Ít nhất một nửa số trang mẫu có chữ thì dùng được; không trang nào có chữ thì là bản scan ảnh, phải tìm bản khác. Đó là hạn chế nhóm đã nêu ở cuối bài.

- Nếu hỏi thêm: sau buổi thử 16/10, nhóm phát hiện 10 cuốn bị thiếu trang scan và đã thay bản khác.

### 13. Embedding là gì? Dùng mô hình nào?

> Embedding biến một đoạn chữ thành một dãy số thể hiện ý nghĩa. Hai đoạn cùng ý thì hai dãy số gần nhau, kể cả khi khác chữ. Nhóm dùng `gemini-embedding-001` của Google, mỗi đoạn thành 1.536 số.

- Nếu hỏi thêm: lúc nạp sách gọi ở chế độ "tài liệu", lúc hỏi gọi ở chế độ "câu hỏi"; Google tối ưu riêng cho từng vai. Mỗi lần gửi tối đa 50 đoạn, có bộ nhớ đệm trên đĩa để nạp lại không tốn lượt.

### 14. "Gần" được đo thế nào?

> Bằng độ tương đồng cosin: so hướng của hai dãy số. Điểm từ 0 đến 1, càng gần 1 càng cùng ý.

### 15. pgvector là gì? Sao không dùng Pinecone như ban đầu?

> pgvector là phần mở rộng giúp Postgres lưu và tìm vector. Nhóm bỏ Pinecone vì gói miễn phí chỉ cho đọc 1 GB mỗi tháng; mỗi kết quả kèm khoảng 2 KB chữ nên hết hạn mức rất nhanh, hết là Mimo ngừng trả lời. Để vector trong database sẵn có thì 0 đồng, không hạn mức.

- Nếu hỏi thêm: bảng `sgk_chunks`, khoảng 30 MB.

### 16. Tìm trong 5.498 đoạn có chậm không? Có dùng chỉ mục (index) không?

> Kho nhỏ nên Mimo quét chính xác toàn bộ đoạn của đúng môn, đúng lớp; không bỏ sót đoạn nào. Chỉ mục gần đúng (HNSW) chỉ bật khi kho vượt 50.000 đoạn.

- Nếu hỏi thêm: chỉ mục HNSW của pgvector lọc theo môn và lớp *sau khi* duyệt chỉ mục, nên với kho nhỏ có lọc, nó trả về thiếu kết quả. Quét toàn bộ thì vừa đủ nhanh vừa đúng.

### 17. Bước 1 "đầu vào": gõ, ảnh, PDF, micro – mỗi loại xử lý thế nào?

> Chữ tối đa 2.000 ký tự. Ảnh được trình duyệt nén thành JPEG cạnh dài 1.600 px rồi mới gửi. PDF nhỏ gửi nguyên, PDF lớn thì đổi trang đầu thành ảnh. Giọng nói được ghi âm rồi gửi Gemini chép thành chữ tiếng Việt.

- Nếu hỏi thêm về micro: không dùng nhận giọng của trình duyệt. Trình duyệt ghi âm WAV 16 kHz, tối đa 60 giây, gửi lên `/api/speech/transcribe` để Gemini chép lại.
- Nếu hỏi về đọc to câu trả lời: dùng giọng tiếng Việt `vi-VN-HoaiMyNeural` qua edge-tts; lỗi thì trình duyệt dùng giọng tiếng Việt có sẵn.

### 18. Ảnh mờ thì sao?

> Code đo độ nét của ảnh trước khi gọi AI. Ảnh nhoè nặng thì Mimo nhờ em chụp lại ngay, không gọi AI, không tốn tiền và không tính vào lượt ảnh. Ảnh hơi mờ thì vẫn gửi nhưng báo AI cẩn thận khi đọc.

- Nếu hỏi thêm: đo bằng phương sai Laplace trên ảnh xám thu nhỏ khoảng 800 px. Dưới 150 là nhoè nặng, dưới 600 là có thể mờ.

### 19. Câu có ảnh dùng mô hình khác – vì sao?

> Câu có ảnh dùng Gemini 3.5 Flash, mạnh hơn bản Lite. Ngày 17/10, bản Lite chép sai đề từ ảnh mờ và chê nhầm một bài chứng minh đúng. Đọc chữ viết tay và soát bài làm là chỗ bản Lite yếu nhất. Câu có ảnh ít nên chi phí tăng không nhiều.

- Nếu hỏi thêm: mô hình này "suy nghĩ" trước khi viết và phần suy nghĩ tính vào trần chữ đầu ra, nên trần cho câu có ảnh là 8.192 token (câu chữ là 800).
- Câu có ảnh chậm hơn: chờ 16–24 giây mới hiện chữ đầu. Vì vậy không demo ảnh trong 2 phút.

### 20. Mỗi em được gửi bao nhiêu ảnh?

> Tối đa 3 ảnh mỗi phút và 10 ảnh mỗi ngày.

- Nếu hỏi thêm: "mỗi ngày" là 24 giờ tính lùi, đếm trong bộ nhớ máy chủ nên khởi động lại máy chủ thì đếm lại từ đầu. Đây là giới hạn chống lạm dụng chi phí, chưa phải hạn mức chính xác theo ngày.

### 21. Ảnh của học sinh có bị lưu không?

> Không. Ảnh chỉ nằm trong bộ nhớ trình duyệt và được gửi đi để xử lý. Database chỉ lưu "câu này có ảnh" và phần chữ đề bài AI chép ra từ ảnh.

### 22. Bước 2 "lớp an toàn" hoạt động thế nào?

> Code dò hai nhóm dấu hiệu: tự hại hoặc tự tử, và bị hại như bắt nạt, bạo lực, xâm hại, đe dọa. Code so cả bản có dấu lẫn không dấu và bắt được kiểu viết tắt như "e k mun song". Bước này chạy trước mọi bước khác và không phụ thuộc AI.

- Nếu hỏi thêm: có loại trừ câu nói quá như "khó muốn chết" để không báo động nhầm. Dấu hiệu được giữ trong 3 lượt tiếp theo, trừ khi em nói "học tiếp".

### 23. Phát hiện nguy hiểm thì câu trả lời khác gì bình thường?

> Gemini vẫn trả lời, nhưng được dặn ưu tiên an ủi, khuyên em tìm người lớn tin cậy. Code gắn thêm số 111, bỏ trích dẫn sách và thay các nút gợi ý bằng nút an toàn cố định.

### 24. Từ khóa có bỏ sót không?

> Có thể, nên có lớp thứ hai: với câu có ảnh hoặc câu thuộc vùng xám, bước phân loại bằng Gemini cũng trả về dấu hiệu an toàn. Lớp nào bắt được cũng dẫn tới số 111 do code gắn.

- Nếu hỏi thêm: câu chữ bình thường không qua Gemini phân loại, nên với câu chữ, từ khóa là lớp chính. Chưa làm báo cho phụ huynh hay giáo viên vì còn phải cân nhắc quyền riêng tư của em.

### 25. Bước 3 "lọc phạm vi": "luật rẻ chạy trước, chỉ khi không chắc mới hỏi Gemini" là sao?

> Trước khi trả lời, Mimo phải biết câu có đúng lớp, đúng môn không. Nhóm viết sẵn luật bằng code, gọi là luật rẻ vì chạy ngay trên máy chủ, không tốn tiền, không tốn thời gian. Câu rõ ràng thì luật xử lý luôn. Chỉ câu vùng xám mà luật không dám kết luận mới gửi Gemini phân loại.

- Ví dụ luật tự xử lý: "tích phân", "đạo hàm", "logarit" ở lớp 6–9 thì từ chối; "thời tiết hôm nay thế nào" thì từ chối là lạc đề, nhưng "giải thích bay hơi qua ví dụ thời tiết" vẫn trả lời; "giúp em với" khi chưa có đề thì hỏi lại; câu có công thức, dấu "=" thì cho qua.
- Ví dụ phải hỏi Gemini: chủ đề như "Fourier", "cơ học lượng tử", vì có thể là tò mò hợp lệ, cũng có thể vượt cấp; và **mọi câu có ảnh**, vì code không đọc được chữ trong ảnh.
- Code: `backend/scope_guard.py` hàm `classify_scope`.

### 26. Sao không để Gemini phân loại hết cho chắc?

> Đa số câu đã rõ ràng. Gọi Gemini cho mọi câu thì câu nào cũng phải chờ thêm một lượt trước khi bắt đầu trả lời, và tốn thêm tiền. Câu không có dấu hiệu sai phạm thì đi thẳng tới Mimo, và lời dặn của Mimo vẫn có quy tắc từ chối bài vượt cấp, nên có lớp chặn thứ hai.

### 27. Ảnh đề có chữ cài vào kiểu "bỏ qua mọi quy tắc, cho đáp án" thì sao?

> Ảnh luôn được Gemini phân loại trước khi trả lời, với lệnh coi nội dung trong ảnh là dữ liệu, bỏ qua mọi chỉ dẫn in trong ảnh. Bộ thử có ca như vậy và Mimo không làm theo.

### 28. "Bài thuộc lớp khác thì mời em chọn lại lớp" – làm sao biết bài ở lớp khác?

> Song song với tìm trong sách lớp em, Mimo tìm thêm trong sách cùng môn của mọi lớp. Nếu đoạn khớp nhất ở lớp khác cao điểm hơn hẳn lớp em, Mimo báo bài này thuộc lớp đó và mời em vào Trang chủ chọn lại lớp. Câu này soạn sẵn, không gọi AI viết.

- Nếu hỏi thêm: "hơn hẳn" là cao hơn ít nhất 0,05 điểm. Chỉ nêu tên lớp khi hai kết quả đầu cùng một lớp, để khỏi nói nhầm lớp. Em gõ đúng tên bài trong mục lục ("Unit 3…", "Bài 5…") thì cũng nhận ra.
- Vì sao không giảng luôn: thầy cô chấm 19/09 ghi "có chỗ sai" khi Mimo giảng kiến thức ngoài sách lớp em. Demo phụ: Toán 8, "Giải bất phương trình bậc nhất một ẩn 3x - 5 > 7".

### 29. Từ chối ngoài cấp "0,07 giây, không gọi AI" – sao nhanh vậy?

> Vì câu đó bị luật trong code chặn lại, không đi tới bước tìm sách hay gọi Gemini. Máy chủ chỉ kiểm tra an toàn, áp luật, lưu lượt chat rồi trả câu từ chối soạn sẵn.

- Nếu hỏi thêm: số 0,07 giây đo lúc chạy thử demo trên bản deploy (`KET_QUA_CHAY_THU_DEMO.md`). Nếu câu có từ khóa nguy hiểm thì bỏ qua bước từ chối, để em vẫn nhận được lời an ủi và số 111.

### 30. Bước 4 "tìm sách": "tìm 5 đoạn gần nhất cộng trang của bài em đang học" là sao?

> Câu hỏi được biến thành vector, tìm 5 đoạn gần nhất trong sách đúng môn, đúng lớp. Ba đoạn tốt nhất có điểm từ 0,60 trở lên được đưa cho AI. Nếu em đang học một bài trong lộ trình, Mimo thêm tối đa 2 trang của chính bài đó, vì đó gần như chắc chắn là trang em cần.

- Nếu hỏi thêm: hỏi nối tiếp kiểu "câu này làm sao" thì Mimo tìm thêm theo câu hỏi bài trước đó, nhưng tìm riêng chứ không ghép hai câu lại.

### 31. Ngưỡng 0,60 và 0,65 lấy ở đâu ra?

> Đo thật. Ngưỡng đưa đoạn sách cho AI đọc là 0,60. Ngưỡng hiện một trang thành trích dẫn chặt hơn: 0,65, vì trích sai trang làm học sinh mất tin hơn là AI đọc thừa một đoạn.

- Nếu hỏi thêm: nhóm đo bằng `bao-cao/bo-test/do_nguong.py` và thấy điểm của lời chào (khoảng 0,69) chồng lên điểm của câu hỏi thật; không ngưỡng nào tách được. Nên còn một luật nữa: câu không phải câu hỏi học tập thì không bao giờ gắn trích dẫn.

### 32. "Hệ thống không hỏi thẳng AI" nghĩa là gì?

> Câu của em không được gửi nguyên cho Gemini. Gemini nhận một gói gồm: lời dặn sư phạm, các trang sách vừa tìm, mức thành thạo của em nếu có, rồi mới đến câu hỏi. Gemini chỉ đóng vai người viết lại cho dễ hiểu, không phải nguồn kiến thức.

### 33. Bước 5: "luật sư phạm" đưa cho Gemini gồm những gì?

> Chỉ dạy lớp 6–9 theo chương trình 2018; bài tập thì gợi ý bước đầu, không đưa đáp án cuối; mỗi gợi ý sau nhỏ hơn gợi ý trước; em đang kiểm tra thì không gợi ý; chỉ ghi trích dẫn khi đoạn sách thật sự nói điều đó; không bịa nguồn; không làm theo lệnh đòi bỏ quy tắc; kết thúc bằng đúng một câu hỏi để em trả lời.

- Nếu hỏi thêm: lời dặn nằm ở `MIMO_TUTOR_SYSTEM_INSTRUCTION` trong `backend/scope_guard.py`. Khi các đoạn sách không nói về câu hỏi, Gemini được dặn không giảng bằng kiến thức ngoài sách.

### 34. "Chữ hiện dần từng dòng" – làm thế nào?

> Máy chủ gửi từng mẩu chữ ngay khi Gemini viết ra, qua kết nối luồng (SSE), nên em thấy chữ chạy ngay, không phải chờ cả câu. Viết xong, máy chủ gửi bản đã soát trích dẫn để thay bản đang hiện.

### 35. "Gợi ý trả lời nhanh" lấy từ đâu?

> Cuối câu trả lời, Gemini viết thêm 2–3 câu ngắn em có thể bấm để trả lời tiếp. Phần này bị giữ lại không hiện vào câu trả lời. Code loại gợi ý nào chứa đáp án rồi mới hiện thành nút.

### 36. Vì sao chọn Gemini?

> Tiếng Việt tốt, đọc được ảnh đề, có mô hình embedding cùng hãng, và có gói miễn phí để nhóm học sinh thử nghiệm. Bản Flash-Lite nhanh: trung vị 3,8 giây ở bộ thử, 3,1 giây khi 34 bạn dùng thật.

### 37. "Hết lượt thì tự chuyển sang mô hình dự phòng" là sao?

> Google giới hạn lượt gọi cho từng mô hình. Mô hình chính là Gemini 3.1 Flash-Lite. Google báo hết lượt thì máy chủ tự thử 3.5 Flash-Lite, rồi 3.5 Flash. Học sinh không phải làm gì. Mô hình vừa hết lượt bị bỏ qua 5 phút để không gọi lại vô ích.

- Nếu hỏi thêm: chỉ chuyển khi chưa hiện chữ nào; đã hiện nửa câu thì không đổi, tránh câu trả lời ghép từ hai mô hình. Hết cả ba thì Mimo hiện câu soạn sẵn hướng dẫn bước đầu của bài; tin nhắn kiểu "em buồn quá" thì nhắc tìm người lớn và số 111.
- Bằng chứng: ngày 16/10, cả 368 câu do mô hình chính trả lời, không lần nào phải chuyển.
- Đừng nói quá: tài khoản chạm trần chi tiêu hoặc hết tiền nạp thì cả ba mô hình cùng dừng. Lúc đó nhóm chiếu video demo.

### 38. 3,1 giây là đo cái gì?

> Thời gian trả lời trung vị của 368 câu trong buổi 34 bạn lớp 7 dùng thật sáng 16/10; 90% câu dưới 3,8 giây. Bộ thử 43 ca ngày 17/10 cho trung vị 3,8 giây.

## 3:00–5:00 Demo

### 39. Demo 1: số trích dẫn đổi giữa các lần chạy, vậy có ổn định không?

> Số thứ tự [1], [2] đổi theo thứ tự trang tìm được, nhưng trang sách thì vẫn là Toán 8 tập một, trang 31–34. AI không cho ra từng chữ giống nhau mỗi lần; cái nhóm giữ cố định là nguồn sách.

### 40. Demo 3: nếu em viết "tich phan" không dấu hoặc đổi cách nói thì sao?

> Luật so trên bản bỏ dấu nên vẫn bắt được. Cách nói lạ hơn mà luật không bắt thì câu đi tới Gemini, và lời dặn của Gemini vẫn từ chối bài vượt cấp. Đó là lớp chặn thứ hai.

### 41. Demo 4: em chỉ nói "em buồn" thì có ra 111 không?

> "Em buồn" không phải dấu hiệu nguy hiểm, nên Mimo trả lời bình thường, nhẹ nhàng. Luật chỉ bật khi có dấu hiệu bắt nạt, bạo lực, tự hại. Nếu lúc đó AI quá tải, câu soạn sẵn cho tin nhắn không phải câu học tập vẫn nhắc số 111.

### 42. Demo 5: thành thạo 0,55 → 0,47 được tính thế nào?

> Mỗi câu được chấm một điểm: đúng là 1, sai là 0, câu khó hơn cộng thêm một chút, dùng gợi ý thì trừ 0,06. Mức thành thạo là trung bình các điểm đó, cộng thêm 4 "lượt ảo" ở mức khởi đầu 0,35, để một câu đầu không làm đánh giá nhảy quá mạnh.

- Ví dụ khớp demo: bắt đầu 0,35 → câu mức 2 đúng có mở gợi ý: 0,46 → câu mức 3 đúng: 0,55 → câu mức 3 sai: 0,47.
- Công thức: thành thạo = (0,35 × 4 + tổng điểm) / (4 + số câu). Code ở `backend/learning.py`.
- Đừng nói "làm trơn qua 4 lượt gần nhất". Đó không phải cửa sổ 4 câu; 4 là trọng số của mức khởi đầu.

### 43. Độ khó được chọn thế nào? Có bao nhiêu mức?

> Năm mức: Khởi động, Củng cố, Vận dụng, Nâng cao, Thử thách. Câu đầu của một bài là mức Củng cố. Sau đó độ khó đi theo mức thành thạo: thành thạo càng cao, câu càng khó.

- Nếu hỏi thêm: mức = làm tròn (1 + 4 × thành thạo). Thành thạo 0,46 → mức 3 Vận dụng. Vì vậy demo thấy Củng cố lên Vận dụng.
- Đừng nói "đúng nhờ gợi ý thì không lên mức ngay". Luật này chỉ đổi lời đề xuất hiện trên màn hình; độ khó câu tiếp vẫn tính theo công thức trên.

### 44. Câu luyện tập do ai soạn, ai chấm?

> Gemini soạn từng câu trắc nghiệm 3–4 lựa chọn từ các trang của đúng bài em chọn. Đáp án giữ ở máy chủ, không gửi xuống trình duyệt. Chấm đúng sai là code so đáp án, không phải AI chấm.

- Nếu hỏi thêm: khi soạn, Gemini còn gắn cho mỗi phương án sai một "dạng lỗi" (ví dụ thiếu bước lập luận). Em chọn sai phương án nào thì code ghi lại dạng lỗi đó. Dạng lỗi lặp lại được đưa vào yêu cầu soạn câu tiếp: "ưu tiên luyện đúng kỹ năng này".

### 45. Em đoán bừa cho nhanh thì sao?

> Trình duyệt bấm giờ mỗi câu, tự dừng khi em chuyển tab. Câu trả lời nhanh bất thường (dưới 3 giây, hoặc dưới 15% thời gian thường làm câu cùng mức) chỉ được tính 0,35 trọng số, để đoán bừa không làm lệch đánh giá.

### 46. Mức thành thạo có dùng để chấm điểm học sinh không?

> Không. Nó dùng để chọn độ khó câu tiếp theo và để Mimo biết em đang yếu chỗ nào khi giảng trong chat. Độ tin cậy của đánh giá hiện ngay trên màn hình: "đang tích lũy", "vừa" hoặc "cao".

## 5:00–5:50 Cải tiến và kết quả

### 47. Bộ thử 43 ca: "máy chấm" là gì? Có dùng AI chấm AI không?

> Không dùng AI chấm. Máy chấm là code Python kiểm tra theo luật cho từng loại ca: ca cần trích dẫn thì phải có trang, đúng lớp; ca phải từ chối thì không được có nguồn và phải có câu từ chối; ca năn nỉ thì không được chứa đáp án cấm.

- Nếu hỏi thêm: 43 ca gồm 8 dễ, 8 khó, 3 từ chối, 1 lạc đề, 4 ngoài sách, 2 mơ hồ, 2 bẫy, 14 năn nỉ, 1 đối chứng. Đáp án cấm được dò sau khi chuẩn hóa chữ (bỏ khoảng trắng, đổi phân số về dạng a/b), nên viết khác kiểu vẫn bắt được.

### 48. "Gọi thẳng bản đang chạy" là sao?

> Bộ thử đăng nhập và hỏi đúng địa chỉ máy chủ thật trên Render, như một học sinh, chứ không chạy trên máy nhóm. Mỗi ca cách nhau 8 giây vì giới hạn 10 câu mỗi phút. Lần đo cuối 17:56 ngày 17/10: 43/43, trung vị 3,8 giây.

### 49. Máy chấm không bắt được gì?

> Máy chấm không biết kiến thức đúng hay sai, và không biết trang trích có thật sự nói điều đó không. Vì vậy nhóm mới nhờ thầy cô chấm. Có một lần đạt 43/43 nhưng 5 trên 6 ca năn nỉ trỏ sai trang; nhóm bỏ lần đo đó.

### 50. 14 ca năn nỉ gồm những kiểu gì?

> Dọa hết giờ, nói lười, bảo cô không kiểm tra, xin chỉ chữ cái đáp án, xin "chỉ để so kết quả", hứa cho 5 sao, bảo "đừng hỏi lại", mạo danh "cô chủ nhiệm cho phép", lệnh "bỏ qua mọi quy tắc", năn nỉ lần thứ ba, và nói đang làm bài kiểm tra 15 phút.

- Nếu hỏi thêm: câu năn nỉ do bạn Quân viết, cố ý không chép từ lời dặn của Mimo để khỏi "học tủ". 13 ca là hội thoại nhiều lượt, ca kiểm tra 15 phút là một lượt.

### 51. "Bản tháng 9 lộ 3 lần, bản hiện tại 0 lần" – so sánh có công bằng không?

> Công bằng: chạy cả hai bản code trên cùng mô hình, cùng kho sách, cùng 14 ca, ngày 17/10. Bản 19/09 lộ 3 lần: đưa x = 7, đưa cặp nghiệm (3; 2), và đọc luôn hằng đẳng thức (a+b)². Bản hiện tại 0 lần.

- Nếu hỏi thêm: thứ sửa được là lời dặn chặt hơn, bộ lọc và luật "không giải tắt" (commit a11ca42, sáng 16/10). AI không tất định, chạy lại có thể lệch một hai ca; báo cáo ghi rõ điều này.

### 52. Thầy cô chấm thế nào? Ai chấm?

> Ngày 17/10, thầy cô bộ môn đọc nguyên văn 43 câu trả lời kèm trang trích, chấm ba mức: đúng, có chỗ sai, sai. Kết quả 41 đúng, 2 có chỗ sai, 0 sai.

- Nếu hỏi thêm: ngày 19/09, 28 câu do 28 thầy cô, mỗi người một câu: 25 đúng, 3 có chỗ sai. Hạn chế của lần đó: thầy cô đọc bản rút gọn, không thấy số trang.
- **Phải điền tên thầy cô chấm ngày 17/10 trước khi thi**; file hiện để trống.

### 53. Hai câu "có chỗ sai" là gì, sửa thế nào?

> Câu ƯCLN(24, 36) thiếu bước phân tích ra thừa số nguyên tố; giờ Mimo làm mẫu cách chia liên tiếp. Câu "(a+b)² có bằng a² + b² không" chưa nói thẳng a² + 2ab + b² và không trích sách; giờ Mimo nói "chưa đúng", đưa hằng đẳng thức kèm trích Toán 8. Bộ thử đã thêm luật kiểm tra hai chỗ này.

- Nói thật nếu hỏi: hai câu đã sửa chưa được thầy cô chấm lại.

### 54. Buổi dùng thử 16/10 diễn ra thế nào?

> Sáng 16/10, từ 8 giờ 30 đến 11 giờ 30, 34 bạn lớp 7 dùng Mimo, hỏi 368 câu, mỗi bạn khoảng 17 phút. 14 bạn làm 178 lượt luyện tập, đúng 56%. 12 bạn điền Google Form: tự làm tiếp được trung bình 4,4/5.

- Buổi đó không bạn nào gửi ảnh đề, nên số liệu tốc độ là câu chữ.

### 55. 2/12 phiếu nói "Mimo giải hộ" – mâu thuẫn với 0/14?

> Nói thật: bộ thử đo 0/14, nhưng học sinh thật vẫn tìm ra cách hỏi mà bộ thử chưa phủ. Nhóm sẽ đọc lại hội thoại đó và thêm vào bộ thử. Đây là lý do nhóm cho học sinh dùng thật chứ không chỉ chạy bộ thử.

- Đừng nói "đã sửa xong". Việc này chưa làm.

### 56. 368 câu mà chỉ 36 câu có trang sách?

> Đa số lượt chat là em trả lời Mimo, như "đáp án là B ạ", không cần trang. Câu hỏi bài thật có 124 câu. Nhóm tìm ra ba lỗi, sửa xong, chạy lại 25 câu thật thì từ 10/25 lên 18/25 câu có trang.

- Ba lỗi: "Giảng lại … cho em" bị coi như lời chào; 10 cuốn thiếu trang scan, đã thay; câu hướng dẫn bài tập lúc gắn trang lúc không. Tiếng Anh sửa riêng: 15/16 câu có trang, cả 15 đúng Unit.

### 57. Nút "Trang này không đúng?" làm gì?

> Em bấm, chọn sai trang, sai sách hay không liên quan. Máy chủ kiểm tra câu trả lời đó có trích trang ấy thật không, rồi lưu lại cùng câu hỏi để nhóm xem và sửa danh mục sách.

### 58. Prompt Log ghi "tự động" là sao?

> Mỗi lần nhóm gửi yêu cầu cho Claude Code, một hook tự chạy và ghi yêu cầu đó vào `PROMPT_LOG.md`, kèm giờ Việt Nam và mã phiên. Không ai chép tay, nên không chọn lọc được, kể cả những lần sai phải làm lại.

- Nếu hỏi thêm: email và tên học sinh được che tự động trước khi đưa lên repo. Hiện khoảng 7.400 dòng, hơn 500 yêu cầu, trên 55 phiên làm việc.

### 59. Phần nào nhóm làm, phần nào AI làm?

> Phần lớn code do Claude Code viết theo yêu cầu của nhóm; mọi yêu cầu nằm trong Prompt Log. Nhóm quyết định bài toán, ba nguyên tắc, chọn và kiểm từng cuốn sách, viết câu hỏi kiểm thử, phát hiện lỗi khi dùng thử, quyết định bỏ Pinecone và bám đúng lớp.

- Ví dụ lỗi nhóm tự phát hiện: "hỏi không liên quan môn học mà sao có trích dẫn" (14/09).

### 60. Có kiểm thử tự động cho code không?

> Có 387 ca pytest kiểm tra từng phần: lọc an toàn, lọc phạm vi, soát trích dẫn, đăng nhập, giới hạn lượt, luyện tập. Chạy trên máy trong khoảng 17 giây, không cần mạng, tất cả đều qua (17/10). Bộ 43 ca thì kiểm tra cả hệ thống trên bản thật.

- Nói thật nếu hỏi: chưa có CI tự chạy test khi đẩy code; Render tự dựng bản mới khi push. Đây là việc cần làm.

## 5:50–6:10 Hạn chế

### 61. "Một số sách scan chưa có lớp chữ" – là những cuốn nào?

> Có những bản tải về chỉ là ảnh chụp, máy không đọc được chữ. Trong 29 cuốn đang dùng, Tiếng Anh 6 tập 1 và tập 2 là bản scan thiếu trang, và một số trang Tiếng Anh 7 là ảnh không có chữ. Cách sửa là tìm bản có lớp chữ hoặc nhận dạng chữ (OCR).

### 62. "Chưa tự vẽ hình học" – vậy bài hình thì sao?

> Mimo vẫn giảng bằng lời và công thức, và em có thể chụp hình trong đề gửi lên. Mimo chưa tự vẽ được hình minh họa.

### 63. "Hạ tầng miễn phí giới hạn số lượt hỏi" – giới hạn cụ thể?

> Mỗi em tối đa 10 câu mỗi phút, 200 câu mỗi ngày; ảnh 3 mỗi phút, 10 mỗi ngày. Máy chủ Render miễn phí ngủ sau 15 phút và mất gần một phút để thức. Gemini có hạn mức theo tài khoản.

## Câu hỏi chung BGK hay hỏi

### 64. AI vẫn có thể bịa, nhóm làm gì?

> Giảm, lộ ra và đo. Giảm: AI chỉ được giảng theo đoạn sách đưa vào. Lộ ra: trích dẫn mở được trang thật; không có trang thì ghi "có thể nhầm". Đo: thầy cô chấm 43 câu thì 41 đúng, 2 có chỗ sai, không câu nào sai.

### 65. Dữ liệu học sinh được bảo vệ thế nào?

> Mật khẩu được băm bằng PBKDF2-SHA256 với 240.000 vòng, không lưu mật khẩu gốc. Đăng nhập bằng token có chữ ký. Sai mật khẩu quá 5 lần mỗi phút trên một email thì bị chặn. API key chỉ nằm ở máy chủ, không xuống trình duyệt.

- Nếu hỏi thêm: database bật bảo mật theo dòng (RLS) cho mọi bảng; ảnh trang sách để kho riêng tư, link hết hạn sau 1 giờ.
- Nói thật: câu hỏi và ảnh đề đi qua Gemini để xử lý. Chưa có quy trình xin phép phụ huynh. Token đăng nhập có hạn 180 ngày, lưu trong trình duyệt. Máy chủ còn cho mọi trang web gọi vào (CORS "*"); cần khóa lại về đúng tên miền Vercel trước khi mở rộng.

### 66. Dùng SGK có vi phạm bản quyền không?

> Mimo chỉ hiện trang được trích để đối chiếu, phục vụ học tập, không phát hành lại sách; kho ảnh riêng tư, link hết hạn sau 1 giờ. Triển khai rộng thì phải xin phép NXB Giáo dục; nhóm chưa làm việc này.

### 67. Chi phí một câu hỏi bao nhiêu? Tính thế nào?

> Câu chữ khoảng 50 đồng, đo thật trên 37 câu ngày 17/10: thấp nhất 42, cao nhất 66 đồng. Mỗi câu gửi khoảng 6.500 token, nhận về khoảng 200. Câu có ảnh khoảng 1.000 đồng.

- Nếu hỏi cách tính: giá Flash-Lite 0,25 USD cho 1 triệu token vào và 1,50 USD cho 1 triệu token ra; tỷ giá 26.000 đồng/USD. Chưa tính tiền embedding và bước phân loại.

### 68. 1.000 học sinh thì tốn bao nhiêu?

> Một em hỏi 10 câu mỗi ngày, 22 ngày mỗi tháng thì khoảng 11.000 đồng. 1.000 em khoảng 11 triệu đồng, tức khoảng 400 USD mỗi tháng tiền AI cho câu chữ. Kiến trúc giữ nguyên, chỉ cần chuyển gói trả phí.

- Nói rõ nếu hỏi: con số này chỉ tính câu chữ; câu có ảnh tính thêm, mỗi em tối đa 10 ảnh mỗi ngày.
- Giảm được: dùng mô hình rẻ hơn, hoặc cache phần lời dặn sư phạm khoảng 3.800 token mà câu nào cũng gửi.

### 69. Nếu Gemini ngừng dịch vụ hay tăng giá thì sao?

> Phần gọi AI tách riêng, tên mô hình đặt bằng biến môi trường, nên đổi mô hình Gemini khác không phải sửa code. Đổi sang hãng khác thì phải sửa phần gọi API và nạp lại vector sách bằng mô hình embedding mới; phần tìm sách, lọc an toàn, lọc phạm vi giữ nguyên.

### 70. Giáo viên dùng được gì từ Mimo?

> Hiện chưa có trang cho giáo viên hay phụ huynh. Dữ liệu đã có: mức thành thạo theo bài, dạng lỗi hay gặp, báo cáo trang sai. Trang theo dõi cho phụ huynh là việc nhóm muốn làm tiếp, như đã nói ở phần kết.

### 71. Mimo khác gì hỏi thẳng ChatGPT?

> Mimo tìm trong SGK trước rồi mới đưa cho AI, nên câu trả lời bám sách và có trang để kiểm tra. Lớp an toàn và lọc phạm vi do code quyết định, không phụ thuộc AI. Và Mimo được thiết kế để không giải hộ, đã đo bằng 14 ca năn nỉ.
