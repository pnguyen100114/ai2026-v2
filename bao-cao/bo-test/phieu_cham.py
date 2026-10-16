"""Phiếu để thầy cô bộ môn chấm KIẾN THỨC của từng câu trả lời — phần máy không chấm được.

Máy chỉ biết Mimo có trích dẫn, có từ chối, có lộ đáp án hay không. Một câu giảng sai mà vẫn
gắn đúng trang sách thì máy cho đạt, và đó lại là lỗi nguy hiểm nhất vì học sinh khó tự phát
hiện. Nên mỗi câu trả lời cần một thầy cô đúng môn đánh dấu: đúng / có chỗ sai / sai.

Cách dùng:
    python bao-cao/bo-test/phieu_cham.py xuat
        → phieu_cham_giao_vien.csv (mở bằng Google Sheets hoặc Excel, Data → From Text/CSV)
    python bao-cao/bo-test/phieu_cham.py nhap phieu_cham_giao_vien.csv
        → ghi đánh giá vào ket_qua.json; chạy lại lam_bang.py để cập nhật KET_QUA_TEST.md

Phiếu gắn với đúng lần chạy trong ket_qua.json (cột "Lần chạy"): chạy lại chay_test.py là có
câu trả lời mới, phiếu cũ không nhập vào được nữa.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

THU_MUC = Path(__file__).resolve().parent
KET_QUA = THU_MUC / 'ket_qua.json'
PHIEU = THU_MUC / 'phieu_cham_giao_vien.csv'

DANH_GIA = ('đúng', 'có chỗ sai', 'sai')
COT = ['STT', 'Lần chạy', 'Nhóm', 'Môn', 'Lớp', 'Hội thoại trước', 'Câu hỏi của em',
       'Câu trả lời của Mimo', 'Trang sách Mimo trích', 'Điều cần đối chiếu',
       'Đánh giá (đúng / có chỗ sai / sai)', 'Chỗ sai (nếu có)', 'Thầy cô chấm']


def _doc() -> dict:
    if not KET_QUA.exists():
        raise SystemExit('Chưa có ket_qua.json. Chạy chay_test.py trước.')
    return json.loads(KET_QUA.read_text(encoding='utf-8'))


def xuat() -> None:
    data = _doc()
    # utf-8-sig: Excel cần BOM mới đọc đúng chữ có dấu.
    with PHIEU.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(COT)
        for k in data['ket_qua']:
            lich_su = '\n'.join(f"{'Em' if l['vai'] == 'user' else 'Mimo'}: {l['noi_dung']}"
                                for l in k.get('lich_su') or [])
            trang = '; '.join(f"{n.get('sach') or 'SGK'} tr.{n.get('trang')}" for n in k.get('nguon') or [])
            w.writerow([k['stt'], data['chay_luc'], k['nhom'], k['mon'], k['lop'], lich_su,
                        k['cau_hoi'], k['tra_loi'], trang or '(không trích)', k['ghi_chu_cham'],
                        k.get('nguoi_cham_kien_thuc') or '', k.get('nguoi_cham_ghi_chu') or '',
                        k.get('nguoi_cham_ten') or ''])
    print(f'Đã ghi {PHIEU} ({len(data["ket_qua"])} câu).')
    print('Gửi thầy cô đúng môn; cột Đánh giá chỉ nhận: ' + ' / '.join(DANH_GIA))


def nhap(duong_dan: Path) -> None:
    data = _doc()
    theo_stt = {k['stt']: k for k in data['ket_qua']}
    loi, da_cham = [], 0
    with duong_dan.open(encoding='utf-8-sig', newline='') as f:
        for dong in csv.DictReader(f):
            stt = int(dong['STT'])
            if dong['Lần chạy'] != data['chay_luc']:
                raise SystemExit(f'Phiếu của lần chạy {dong["Lần chạy"]}, còn ket_qua.json là lần '
                                 f'{data["chay_luc"]}. Câu trả lời đã khác, phải xuất phiếu mới.')
            danh_gia = (dong[COT[10]] or '').strip().lower()
            if not danh_gia:
                continue
            if danh_gia not in DANH_GIA:
                loi.append(f'câu {stt}: "{danh_gia}" không phải một trong {DANH_GIA}')
                continue
            if danh_gia != 'đúng' and not (dong[COT[11]] or '').strip():
                loi.append(f'câu {stt}: chấm "{danh_gia}" nhưng chưa ghi chỗ sai')
            k = theo_stt[stt]
            k['nguoi_cham_kien_thuc'] = danh_gia
            k['nguoi_cham_ghi_chu'] = (dong[COT[11]] or '').strip() or None
            k['nguoi_cham_ten'] = (dong[COT[12]] or '').strip() or None
            da_cham += 1
    if loi:
        raise SystemExit('Phiếu chưa nhập được:\n  ' + '\n  '.join(loi))
    KET_QUA.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Đã nhập {da_cham}/{len(theo_stt)} câu vào {KET_QUA}. Chạy lam_bang.py để cập nhật bảng.')


if __name__ == '__main__':
    if len(sys.argv) >= 2 and sys.argv[1] == 'xuat':
        xuat()
    elif len(sys.argv) >= 3 and sys.argv[1] == 'nhap':
        nhap(Path(sys.argv[2]))
    else:
        raise SystemExit(__doc__)
