# Minh chứng cải tiến sau 19/09/2026

Thư mục này chỉ gồm việc nhóm làm **sau ngày nộp 19/09/2026**. Phần trước đó đã có trong hồ sơ đã nộp.

**Đọc trước:** [`CAI_TIEN_THEO_YEU_CAU_BGK.md`](CAI_TIEN_THEO_YEU_CAU_BGK.md). File này ghi 5 yêu cầu của ban giám khảo, nhóm đã làm gì, tới đâu và minh chứng nằm ở file nào.

| Thư mục | Nội dung | Yêu cầu |
|---|---|---|
| `1_cham_chat_bo_thu/` | Kết quả 43 ca chấm chặt trên bản đang chạy; so sánh 14 ca năn nỉ giữa code 19/09 và code hiện tại | 1, 2 |
| `2_thay_co_cham/` | Thầy cô bộ môn chấm 43 câu lần đo 17/10 và 28 câu của bản nộp 19/09 | 2 |
| `3_hoc_sinh_dung_thu/` | Buổi 34 học sinh dùng thử ngày 16/10; kết quả 12 phiếu Google Form | 3, 4 |
| `5_thu_nghiem_dai_han/` | Kế hoạch thử 2–4 tuần, có nhóm đối chứng | 5 |
| `6_nhat_ky/` | Các lần sửa (commit) và câu lệnh dùng với AI lập trình sau 19/09 | tất cả |
| `anh/` | Ảnh chụp bản đang chạy ngày 17/10 | 1, 2, 4 |

**Ảnh trong `anh/`**

1. `1_tra_loi_co_trang_sach_va_loi_nhac.png`: câu trả lời có trang sách, kèm dòng nhắc "Mimo có thể nhầm".
2. `2_xem_trang_sach_co_nut_bao_sai.png`: em bấm xem trang sách Mimo trích.
3. `3_bao_trang_sai_chon_ly_do.png`: nút "Trang này không đúng?" và các lý do để chọn.
4. `4_nan_ni_khong_lo_dap_an.png`: em năn nỉ xin đáp số, Mimo chỉ gợi ý bước đầu.
5. `5_tu_choi_kien_thuc_ngoai_chuong_trinh.png`: câu tích phân bị từ chối.
6. `6_luyen_tap_muc_do_kho_va_goi_y.png`: câu luyện tập có mức độ khó, năng lực hiện tại và gợi ý.
7. `7_luyen_tap_cham_va_goi_y_bai_tiep.png`: chấm, giải thích lỗi, gợi ý bài tiếp.

Thư mục không chứa file CSV, tên học sinh hay tên thầy cô. Các file trong `1_`, `2_`, `3_`, `5_`, `6_` được dựng lại từ dữ liệu gốc bằng `python bao-cao/minh-chung-sau-1909/dung_minh_chung.py`. Ảnh được chụp lại bằng `python bao-cao/chup_minh_chung.py`.
