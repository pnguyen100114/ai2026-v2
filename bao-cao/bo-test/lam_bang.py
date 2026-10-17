"""Đọc ket_qua.json rồi dựng KET_QUA_TEST.md + biểu đồ cho hồ sơ.

Tách khỏi chay_test.py để sửa lại bảng không phải chạy lại cả bộ test (mỗi lần chạy tốn
38 lượt Gemini và khoảng 8 phút).
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

THU_MUC = Path(__file__).resolve().parent
NGUON = THU_MUC / 'ket_qua.json'
# Thầy cô chấm lần chạy 19/09 (ket_qua_1909.json) trên bản rút gọn, trước khi có phieu_cham.py.
CHAM_1909 = THU_MUC / 'cham_giao_vien_1909.csv'
# Lần đo 17/10 10:01 đã được thầy cô chấm (phieu_cham_giao_vien.csv). Đo lại thì ket_qua.json đổi
# câu trả lời, nên phiếu chấm gắn với bản lưu riêng này.
DA_CHAM = THU_MUC / 'ket_qua_gv_1710.json'

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


def lan_da_cham() -> tuple[dict, list]:
    """Lần chạy hiện tại nếu đã chấm, không thì lần đã chấm gần nhất (ket_qua_gv_1710.json)."""
    if any(k.get('nguoi_cham_kien_thuc') for k in ket_qua) or not DA_CHAM.exists():
        return data, ket_qua
    gv = json.loads(DA_CHAM.read_text(encoding='utf-8'))
    return gv, gv['ket_qua']


def phan_giao_vien() -> str:
    """Thầy cô bộ môn chấm kiến thức, nhập qua phieu_cham.py. Chưa chấm thì nói thẳng là chưa."""
    lan, ds = lan_da_cham()
    da_cham = [k for k in ds if k.get('nguoi_cham_kien_thuc')]
    if not da_cham:
        return ('**Chưa có thầy cô nào chấm lần chạy này.** Xuất phiếu bằng '
                '`python bao-cao/bo-test/phieu_cham.py xuat`, gửi thầy cô đúng môn, rồi nhập lại bằng '
                '`phieu_cham.py nhap <file>`.')
    dem = Counter(k['nguoi_cham_kien_thuc'] for k in da_cham)
    dong = [] if lan is data else [
        f'Thầy cô chấm nguyên văn câu trả lời của lần chạy **{lan["chay_luc"].replace("T", " ")}** '
        f'(`ket_qua_gv_1710.json`, phiếu `phieu_cham_giao_vien.csv`). Lần chạy ở mục 1 đo lại sau khi sửa '
        'theo góp ý, câu chữ khác nên chưa chấm lại.', '']
    dong += [f'Đã chấm **{len(da_cham)}/{len(ds)}** câu: '
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


def phan_giao_vien_1909() -> str:
    """Phiếu thầy cô chấm lần chạy 19/09. Câu trả lời đó khác lần chạy hiện tại, nên để riêng."""
    if not CHAM_1909.exists():
        return ''
    with CHAM_1909.open(encoding='utf-8-sig', newline='') as f:
        dong = list(csv.DictReader(f))
    dem = Counter((d['Đánh giá của thầy cô'] or '').strip().lower() or 'chưa chấm' for d in dong)
    can_xem = [d for d in dong if d['Ghi chú của nhóm khi đối chiếu câu trả lời thật']]
    md = [f'### Lần chạy 19/09 ({len(dong)} ca, bản trước các bản sửa)', '',
          f'Thầy cô bộ môn chấm **{len(dong) - dem["chưa chấm"]}/{len(dong)}** câu: '
          f'**{dem["đúng"]}** đúng · **{dem["có chỗ sai"]}** có chỗ sai · **{dem["sai"]}** sai'
          + (f' · **{dem["chưa chấm"]}** để trống' if dem['chưa chấm'] else '') + '.', '',
          'Cách chấm lần này còn ba giới hạn:', '',
          '- Thầy cô đọc **bản rút gọn** câu trả lời, không phải nguyên văn. Nguyên văn nằm trong '
          '`ket_qua_1909.json`.',
          '- Phiếu không kèm số trang Mimo trích, nên chưa kiểm được loại lỗi "giảng sai mà vẫn có trang sách".',
          f'- Mỗi thầy cô chấm một câu ({len({d["Thầy cô chấm"] for d in dong})} thầy cô, tên ghi trong phiếu), '
          'nên chưa có câu nào được hai người cùng chấm để đối chiếu.', '',
          'Khi đối chiếu lại với câu trả lời thật, nhóm ghi chú những câu sau:', '',
          '| # | Môn · lớp | Câu hỏi | Thầy cô | Ghi chú của nhóm |', '|---|---|---|---|---|']
    for d in can_xem:
        md.append(f'| {d["STT"]} | {d["Môn"]} {d["Lớp"]} | {d["Câu hỏi"].replace("|", "/")} | '
                  f'{d["Đánh giá của thầy cô"] or "(trống)"} | '
                  f'{d["Ghi chú của nhóm khi đối chiếu câu trả lời thật"].replace("|", "/")} |')
    md += ['', 'Ở các câu 17, 18 và 19, thầy cô chấm đúng vì kiến thức không sai. Tuy vậy Mimo vẫn giảng '
           'phần ngoài cấp, nên nếu chấm theo cách chấm từ 16/10 thì các câu trả lời này là trượt (xem mục 2). '
           'Ở lần chạy hiện tại, Mimo đã từ chối và đạt cả ba câu.', '',
           'Ba câu thầy cô chấm "có chỗ sai" (20, 22, 24) không phải vì kiến thức sai. Thầy cô muốn Mimo '
           'bám sát sách giáo khoa: không nói chuyện thời tiết, và không giảng bằng kiến thức ngoài sách phần '
           'sách lớp em không có. Câu thời tiết đã được sửa (bản hiện tại từ chối). Câu 22 và 24 ngược với cách '
           'nhóm chọn từ 17/09 ("sách không có bài thì vẫn dạy, nhưng báo cho em biết"); từ 17/10 nhóm đổi theo '
           'góp ý: bài nằm ở sách lớp khác thì Mimo chỉ giảng theo trang sách lớp đó, có trích dẫn; không sách '
           'nào có thì không giảng.', '',
           'Toàn bộ nhận xét của thầy cô: `cham_giao_vien_1909.csv`.']
    return '\n'.join(md)


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

### Lần đo 17/10

{phan_giao_vien()}

{phan_giao_vien_1909()}

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
