"""Đo ngưỡng CHAT_SOURCE_MIN_SCORE: điểm nào tách được câu hỏi thật khỏi lời chào.

Vì sao cần: nếu ngưỡng quá thấp thì một câu "Em cảm ơn ạ" cũng được gắn một trang SGK —
tức sản phẩm bịa nguồn, đúng thứ nó hứa không làm. Nếu quá cao thì câu hỏi thật trả lời
chay, mất luôn lời hứa "chỉ dạy theo sách".

Chạy lại mỗi khi thêm sách vào kho, vì phân bố điểm đổi theo kho:
    python bao-cao/bo-test/do_nguong.py

Script gọi thẳng retriever trong máy (không qua API) vì chỉ cần điểm tương đồng, và như vậy
mỗi lần chạy chỉ tốn 1 lượt embedding cho mỗi câu, không tốn lượt sinh văn bản.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))

from rag import retriever  # noqa: E402

THU_MUC = Path(__file__).resolve().parent

# Lời chào, cảm ơn, tán gẫu, lạc đề — KHÔNG được gắn trích dẫn SGK.
NHIEU = [
    ('Chào cô Mimo ạ', 'Toán', 8),
    ('Em cảm ơn nhiều ạ', 'Ngữ văn', 8),
    ('Ok em hiểu rồi', 'KHTN', 7),
    ('Mimo ơi', 'Toán', 6),
    ('Hôm nay em mệt quá', 'Toán', 8),
    ('Bạn tên gì?', 'Ngữ văn', 9),
    ('Mai em đi chơi', 'LSDL', 8),
    ('Haha vui quá', 'Toán', 9),
    ('Chào Mimo!', 'Toán', 8),
    ('Hôm nay thời tiết Hà Nội thế nào?', 'Ngữ văn', 8),
]

# Câu hỏi thật, bài có thật trong sách — BẮT BUỘC có trích dẫn.
THAT = [
    ('Biện pháp tu từ chơi chữ là gì?', 'Ngữ văn', 9),
    ('Từ ngữ địa phương là gì?', 'Ngữ văn', 8),
    ('Từ tượng hình và từ tượng thanh khác nhau thế nào?', 'Ngữ văn', 8),
    ('Có mấy kiểu câu ghép? Cho ví dụ.', 'Ngữ văn', 9),
    ('Định luật Ôm phát biểu thế nào?', 'KHTN', 9),
    ('Quang hợp ở thực vật là gì?', 'KHTN', 7),
    ('Thế nào là số nguyên tố?', 'Toán', 6),
    ('Hình thoi khác hình vuông ở đâu?', 'Toán', 8),
    ('Cách mạng tư sản Anh nổ ra khi nào?', 'LSDL', 8),
    ('Chữ Nôm ra đời thế nào?', 'Ngữ văn', 9),
    ('Hằng đẳng thức bình phương của một tổng là gì?', 'Toán', 8),
    ('Biệt ngữ xã hội là gì?', 'Ngữ văn', 8),
]


def diem(items: list[tuple[str, str, int]]) -> list[tuple[float, str]]:
    ra = []
    for cau, mon, lop in items:
        ket = retriever.search_knowledge(cau, subject=mon, grade=lop, top_k=1)
        ra.append((ket[0]['score'] if ket else 0.0, cau))
    return sorted(ra, reverse=True)


def main() -> None:
    nhieu, that = diem(NHIEU), diem(THAT)

    print('NHIỄU (chào hỏi, lạc đề) — không được trích dẫn:')
    for s, q in nhieu:
        print(f'   {s:.3f}  {q}')
    print('\nCÂU HỎI THẬT (bài có trong sách) — bắt buộc trích dẫn:')
    for s, q in that:
        print(f'   {s:.3f}  {q}')

    dinh_nhieu, day_that = nhieu[0][0], that[-1][0]
    print(f'\nĐỉnh nhiễu     : {dinh_nhieu:.3f}  ({nhieu[0][1]})')
    print(f'Đáy câu thật   : {day_that:.3f}  ({that[-1][1]})')

    if day_that <= dinh_nhieu:
        print('\n⚠ HAI NHÓM CHỒNG NHAU — không có ngưỡng nào tách sạch được.')
        print('  Chọn ngưỡng là chấp nhận đánh đổi: cao thì mất trích dẫn thật, thấp thì bịa nguồn.')
        de_xuat = round(day_that - 0.005, 3)
        print(f'  Ưu tiên không bịa nguồn thì lấy {de_xuat:.3f}, và ghi rõ số câu thật bị mất.')
    else:
        de_xuat = round((dinh_nhieu + day_that) / 2, 2)
        print(f'Khoảng tách    : {day_that - dinh_nhieu:+.3f}')
        print(f'\n→ Đề xuất CHAT_SOURCE_MIN_SCORE = {de_xuat}')
        if day_that - dinh_nhieu < 0.03:
            print('  (khoảng tách hẹp — thêm sách mới là phải đo lại, đừng coi là con số chắc chắn)')

    (THU_MUC / 'nguong.json').write_text(json.dumps({
        'dinh_nhieu': dinh_nhieu, 'day_cau_that': day_that, 'de_xuat': de_xuat,
        'nhieu': [{'diem': s, 'cau': q} for s, q in nhieu],
        'cau_that': [{'diem': s, 'cau': q} for s, q in that],
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\nĐã ghi {THU_MUC / "nguong.json"}')


if __name__ == '__main__':
    main()
