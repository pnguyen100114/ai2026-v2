# Ba ảnh vở thật để thử phần đọc ảnh

Ảnh một bạn học sinh chụp vở bằng điện thoại ngày 17/10/2026, đã được bạn đồng ý cho đưa vào kho.
Mỗi ảnh đã thu về cạnh dài 1.600 px, JPEG chất lượng 85, giống hệt cách app gửi ảnh lên.
Câu hỏi kèm ảnh: "Em làm bài này đúng chưa ạ?", học sinh lớp 6, môn Toán.

| Ảnh | Độ nét đo được | Nội dung | Mimo phải |
|---|---|---|---|
| `anh1_nhoe.jpg` | 231 | Rung tay, gần như không đọc được | Không đoán đề; đánh dấu [không đọc rõ] và nhờ em chụp lại hoặc gõ lại đề |
| `anh2_nghieng_bai_sai.jpg` | 3.311 | HP5: chứng minh A = 1/2 + 2/2² + … + 100/2¹⁰⁰ < 2. Bài làm có lỗi: ghi 5/32 < 1/8 (sai, vì 1/8 = 4/32) và thay 3/8 bằng 1/4 trong tổng | Chép đúng đề, chỉ ra bước sai, gợi ý cách khác (2A − A), không giải hộ |
| `anh3_ro_bai_dung.jpg` | 1.807 | HP3: A = 1/11 + … + 1/70, chứng minh 4/3 < A < 5/2. Bài làm đúng | Chép đúng đề, xác nhận bài đúng, nếu có thì chỉ góp ý trình bày |

Độ nét là phương sai của bộ lọc Laplacian trên ảnh xám thu về cạnh dài ~800 px (`_do_net_anh` trong
`backend/app.py`). Dưới 150 Mimo trả lời cố định, không gọi mô hình; từ 150 đến 600 prompt báo ảnh có
thể mờ. Ảnh 3 làm mờ nhân tạo xuống còn ~290 vẫn đọc rõ, nên ngưỡng trả lời cố định đặt thấp hơn mức đó.

## Kết quả đo

| Lần đo | Ảnh 1 nhoè | Ảnh 2 bài sai | Ảnh 3 bài đúng |
|---|---|---|---|
| Bản deploy 17/10 sáng (Flash-Lite) | Đoán ra đề khác, từ chối là "ngoài chương trình" | Từ chối là "THPT, dãy số và giới hạn" | Chép đúng đề nhưng từ chối |
| Sau luật bám sách cho bài nâng cao (vẫn Flash-Lite) | Vẫn đoán ra đề khác | Không phát hiện lỗi 5/32 < 1/8 | Một lần chê nhầm phần A < 5/2 |
| 633b135 (ảnh dùng 3.5 Flash + đo độ nét), 2 lần | Đánh dấu [không đọc rõ], nhờ chụp lại | Chỉ đúng lỗi 5/32 > 4/32 = 1/8, gợi ý 2A − A | Xác nhận đúng, góp ý trình bày |
| Sau khi sửa đọc JSON + chép đề song song, 2 lần | Như trên; đề lưu kèm [không đọc rõ] | Như trên, đề lưu đủ | Như trên, đề lưu đủ |

Đề chép từ ảnh (`image_text`, để lượt sau Mimo còn nhớ đề) trước khi sửa mất 3/6 lần: dòng JSON cuối hỏng
vì LaTeX một dấu `\` (`\dots`, `\cdot`), hoặc câu trả lời hết trần token trước dòng đó. Sau khi sửa 6/6 lần
có đề. Hỏi tiếp không kèm ảnh ("nhóm từ 1/41 đến 1/70 có bao nhiêu số hạng?"), Mimo trả lời đúng bài trong ảnh.

Thời gian chờ ở máy với 3.5 Flash: chữ đầu tiên sau 12–25 giây (câu không có ảnh ~3,5 giây).

Chạy lại: `python bao-cao/bo-test/anh/thu_anh.py --api <địa chỉ> --lan 2`.
