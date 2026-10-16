"""Đọc ket_qua.json rồi dựng KET_QUA_TEST.md + biểu đồ cho hồ sơ.

Tách khỏi chay_test.py để sửa lại bảng không phải chạy lại cả bộ test (mỗi lần chạy tốn
38 lượt Gemini và khoảng 8 phút).
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

THU_MUC = Path(__file__).resolve().parent
NGUON = THU_MUC / 'ket_qua.json'

if not NGUON.exists():
    raise SystemExit('Chưa có ket_qua.json. Chạy chay_test.py trước.')

data = json.loads(NGUON.read_text(encoding='utf-8'))
ket_qua = data['ket_qua']

NHAN = {
    'trich_dan': 'Phải trích dẫn SGK',
    'tu_choi': 'Phải từ chối, không giảng phần ngoài cấp',
    'lac_de': 'Phải từ chối, không bịa thông tin',
    'khong_co_trong_sach': 'Phải nói rõ sách không có bài này',
    'hoi_lai': 'Phải hỏi lại, không giải hộ',
    'nan_ni': 'Năn nỉ vẫn không lộ đáp án',
    'xac_nhan': 'Em làm đúng thì phải xác nhận',
}


def phan_giao_vien() -> str:
    """Thầy cô bộ môn chấm kiến thức, nhập qua phieu_cham.py. Chưa chấm thì nói thẳng là chưa."""
    da_cham = [k for k in ket_qua if k.get('nguoi_cham_kien_thuc')]
    if not da_cham:
        return ('**Chưa có thầy cô nào chấm lần chạy này.** Xuất phiếu bằng '
                '`python bao-cao/bo-test/phieu_cham.py xuat`, gửi thầy cô đúng môn, rồi nhập lại bằng '
                '`phieu_cham.py nhap <file>`.')
    dem = Counter(k['nguoi_cham_kien_thuc'] for k in da_cham)
    dong = [f'Đã chấm **{len(da_cham)}/{len(ket_qua)}** câu: '
            f'**{dem["đúng"]}** đúng · **{dem["có chỗ sai"]}** có chỗ sai · **{dem["sai"]}** sai.', '']
    sai = [k for k in da_cham if k['nguoi_cham_kien_thuc'] != 'đúng']
    if sai:
        dong += ['| # | Môn · lớp | Câu hỏi | Đánh giá | Chỗ sai | Người chấm |', '|---|---|---|---|---|---|']
        for k in sai:
            dong.append(f'| {k["stt"]} | {k["mon"]} {k["lop"]} | {k["cau_hoi"][:50]} | '
                        f'{k["nguoi_cham_kien_thuc"]} | {(k.get("nguoi_cham_ghi_chu") or "").replace("|", "/")} | '
                        f'{k.get("nguoi_cham_ten") or ""} |')
    # Câu giảng sai mà vẫn có trang sách: máy cho đạt, học sinh tin vì thấy trang sách.
    sai_co_nguon = [k for k in sai if k['so_nguon'] > 0]
    if sai_co_nguon:
        dong += ['', f'**{len(sai_co_nguon)} câu có chỗ sai dù có trang sách đi kèm** '
                 f'(ca {", ".join(str(k["stt"]) for k in sai_co_nguon)}) — loại lỗi máy chấm không phát hiện được.']
    return '\n'.join(dong)


def bang_tong_hop() -> str:
    dong = ['| Nhóm ca | Số ca | Máy chấm đạt | Tỉ lệ |', '|---|---|---|---|']
    for nhom in dict.fromkeys(k['nhom'] for k in ket_qua):
        trong = [k for k in ket_qua if k['nhom'] == nhom]
        dat = sum(1 for k in trong if k['dat_may_cham'])
        dong.append(f'| {nhom} | {len(trong)} | {dat} | {dat * 100 // len(trong)}% |')
    dat = sum(1 for k in ket_qua if k['dat_may_cham'])
    dong.append(f'| **Tổng** | **{len(ket_qua)}** | **{dat}** | **{dat * 100 // len(ket_qua)}%** |')
    return '\n'.join(dong)


def bang_chi_tiet() -> str:
    dong = ['| # | Nhóm | Môn · lớp | Câu hỏi | Mong đợi | Kết quả máy chấm | Giây |',
            '|---|---|---|---|---|---|---|']
    for k in ket_qua:
        cau = k['cau_hoi'].replace('|', '\\|')
        cau = cau if len(cau) <= 58 else cau[:55] + '…'
        dong.append(f'| {k["stt"]} | {k["nhom"]} | {k["mon"]} {k["lop"]} | {cau} | '
                    f'{NHAN.get(k["mong_doi"], k["mong_doi"])} | '
                    f'{"✅ " if k["dat_may_cham"] else "❌ "}{k["ly_do"]} | {k["giay"]} |')
    return '\n'.join(dong)


def phan_truot() -> str:
    truot = [k for k in ket_qua if not k['dat_may_cham']]
    if not truot:
        return ('Không ca nào trượt phần máy chấm. Phần kiến thức đúng/sai vẫn cần thầy cô '
                'xác nhận — xem mục 3.')
    khoi = []
    for k in truot:
        khoi.append(
            f'**Ca {k["stt"]} — {k["mon"]} {k["lop"]}: "{k["cau_hoi"]}"**\n\n'
            f'- Mong đợi: {NHAN.get(k["mong_doi"], k["mong_doi"])}\n'
            f'- Thực tế: {k["ly_do"]}\n'
            f'- Cần đối chiếu: {k["ghi_chu_cham"]}\n\n'
            f'> {(k["tra_loi"] or "(không trả lời)")[:300]}…\n')
    return '\n'.join(khoi)


giay = sorted(k['giay'] for k in ket_qua)
co_nguon = [k for k in ket_qua if k['so_nguon'] > 0]
can_nguon = [k for k in ket_qua if k['mong_doi'] == 'trich_dan']
dat_nguon = [k for k in can_nguon if k['dat_may_cham']]
# Câu thuộc chương trình mà trả lời không kèm nguồn nào: đây là lỗi nặng nhất của sản
# phẩm này, vì lời hứa cốt lõi là chỉ dạy theo sách. Phải đếm từ dữ liệu, không viết cứng.
chay_sai = [k for k in can_nguon if k['so_nguon'] == 0]
kho = data.get('kho_vector', {})

md = f'''# Kết quả kiểm thử Mimo

Chạy lúc **{data["chay_luc"].replace("T", " ")}** trên bản đã triển khai: `{data["api"]}`
Kho vector lúc chạy: **{kho.get("vectors", "?")} đoạn sách**, tìm kiếm `{kho.get("vector_index", "?")}`.

Bộ test gọi thẳng API đang chạy thật, không gọi hàm trong máy — để số liệu phản ánh đúng
thứ người dùng mở, gồm cả mạng, máy chủ và biến môi trường.

## 1. Tổng hợp

{bang_tong_hop()}

**Thời gian trả lời:** nhanh nhất {giay[0]}s · trung vị {giay[len(giay) // 2]}s · chậm nhất {giay[-1]}s

**Trích dẫn:** {len(dat_nguon)}/{len(can_nguon)} câu thuộc chương trình có trích dẫn đúng môn, đúng lớp, có số trang.
{len(chay_sai)}/{len(can_nguon)} câu thuộc chương trình **trả lời chay, không trích dẫn gì** — xem mục 4.

## 2. Máy chấm được gì, không chấm được gì

Máy chỉ chấm phần khách quan:

- câu thuộc chương trình **có** trích dẫn không, nguồn **đúng môn đúng lớp** không, **có số trang** không;
- câu ngoài cấp / lạc đề có **từ chối thật** không: phải nói rõ lý do, không bịa nguồn, và không
  được chứa nội dung bị cấm của ca đó (bước tích phân, đáp án $\\cos x$, mô tả thời tiết…);
- câu mơ hồ / nhờ làm hộ có **hỏi lại** em không, có lời giải không;
- câu năn nỉ (hội thoại nhiều lượt) có **lộ đáp án cuối** không, có hỏi em làm bước tiếp không;
- thời gian trả lời.

Danh sách chuỗi cấm của từng ca nằm trong `cau_hoi.py`. Bản chấm ngày 19/09 chỉ xét "có bịa nguồn
không", nên các câu vẫn giảng tích phân, đưa đáp án đạo hàm hay tả thời tiết đều bị tính là đạt;
bản này sửa lại cách chấm đó.

Máy **không** chấm kiến thức đúng hay sai — xem mục 3.

## 3. Thầy cô bộ môn chấm kiến thức

{phan_giao_vien()}

## 4. Ca trượt và chỗ cần sửa

{phan_truot()}

## 5. Chi tiết từng ca

{bang_chi_tiet()}

---

*Sinh tự động bởi `bao-cao/bo-test/lam_bang.py`. Muốn chạy lại bộ test:
`python bao-cao/bo-test/chay_test.py`.*
'''

(THU_MUC / 'KET_QUA_TEST.md').write_text(md, encoding='utf-8')
print(f'Đã ghi {THU_MUC / "KET_QUA_TEST.md"}')
print(f'  {len(ket_qua)} ca · máy chấm đạt {sum(1 for k in ket_qua if k["dat_may_cham"])}')
print('  Nhóm:', dict(Counter(k['nhom'] for k in ket_qua)))
