"""Phiếu để thầy cô bộ môn chấm KIẾN THỨC của từng câu trả lời — phần máy không chấm được.

Máy chỉ biết Mimo có trích dẫn, có từ chối, có lộ đáp án hay không. Một câu giảng sai mà vẫn
gắn đúng trang sách thì máy cho đạt, và đó lại là lỗi nguy hiểm nhất vì học sinh khó tự phát
hiện. Nên mỗi câu trả lời cần một thầy cô đúng môn đánh dấu: đúng / có chỗ sai / sai.

Cách dùng:
    python bao-cao/bo-test/phieu_cham.py xuat
        → phieu_cham_giao_vien.csv (mở bằng Google Sheets hoặc Excel, Data → From Text/CSV),
          kèm phieu_theo_mon/phieu_<môn>.csv để gửi riêng từng thầy cô bộ môn
    python bao-cao/bo-test/phieu_cham.py nhap phieu_cham_giao_vien.csv
        (hoặc từng phiếu môn, mỗi môn một lần nhap) → ghi đánh giá vào ket_qua.json; chạy lại lam_bang.py để cập nhật KET_QUA_TEST.md

Phiếu gắn với đúng lần chạy trong ket_qua.json (cột "Lần chạy"): chạy lại chay_test.py là có
câu trả lời mới, phiếu cũ không nhập vào được nữa.
"""
from __future__ import annotations

import csv
import json
import re
import sys
import unicodedata
from pathlib import Path

THU_MUC = Path(__file__).resolve().parent
KET_QUA = THU_MUC / 'ket_qua.json'
PHIEU = THU_MUC / 'phieu_cham_giao_vien.csv'
THEO_MON = THU_MUC / 'phieu_theo_mon'

DANH_GIA = ('đúng', 'có chỗ sai', 'sai')
COT = ['STT', 'Lần chạy', 'Nhóm', 'Môn', 'Lớp', 'Hội thoại trước', 'Câu hỏi của em',
       'Câu trả lời của Mimo', 'Trang sách Mimo trích', 'Điều cần đối chiếu',
       'Đánh giá (đúng / có chỗ sai / sai)', 'Chỗ sai (nếu có)', 'Thầy cô chấm']


# Mimo viết công thức bằng LaTeX ("$x^2 + 2x + 1$"); app vẽ bằng KaTeX nên em thấy x² + 2x + 1,
# còn Excel thì hiện nguyên dấu $ và ^. Đổi về chữ thường giống plainMath() ở
# src/components/ChatMessageContent.tsx, để thầy cô đọc đúng thứ học sinh thấy.
_SO_MU = str.maketrans('0123456789+-()n', '⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁽⁾ⁿ')
_CHI_SO = str.maketrans('0123456789', '₀₁₂₃₄₅₆₇₈₉')
_DOAN_TOAN = re.compile(r'(\$\$[\s\S]*?\$\$|\$[^$\n]*\$)')
_NGOAC_TOAN = re.compile(r'\\\[([\s\S]+?)\\\]|\\\(([\s\S]+?)\\\)')
_nhom = lambda s: s if re.fullmatch(r'[\w^.,²³]+', s) else f'({s})'
_LATEX = [
    (r'\\begin\{cases\}([\s\S]*?)\\end\{cases\}', lambda m: 'hệ [ ' + m[1].strip().replace('\\\\', ' ; ') + ' ]'),
    (r'\\[dt]?frac\{([^{}]*)\}\{([^{}]*)\}', lambda m: f'{_nhom(m[1])}/{_nhom(m[2])}'),
    (r'\\sqrt\{([^{}]*)\}', lambda m: f'√{_nhom(m[1])}'),
    (r'\\(?:text|mathrm|mathbf|operatorname)\{([^{}]*)\}', lambda m: m[1]),
    (r'\\(?:widehat|hat|angle)\{([^{}]*)\}', lambda m: f'góc {m[1]}'),
    (r'\\overline\{([^{}]*)\}', lambda m: m[1]),
    (r'\^\{?\\circ\}?', '°'),
    (r'\^\{([^{}]*)\}', lambda m: m[1].translate(_SO_MU) if re.fullmatch(r'[\d+\-()n]+', m[1])
     else f'^{m[1]}' if len(m[1]) == 1 else f'^({m[1]})'),
    (r'\^(\d+)', lambda m: m[1].translate(_SO_MU)),
    (r'_\{?(\d+)\}?', lambda m: m[1].translate(_CHI_SO)),
]
_KY_HIEU = {
    'cdot': '·', 'times': '×', 'div': ':', 'pm': '±', 'le': '≤', 'leq': '≤', 'ge': '≥', 'geq': '≥',
    'ne': '≠', 'neq': '≠', 'approx': '≈', 'pi': 'π', 'infty': '∞', 'int': '∫', 'Rightarrow': '⇒',
    'Leftrightarrow': '⇔', 'rightarrow': '→', 'to': '→', 'in': '∈', 'notin': '∉', 'Omega': 'Ω',
    'Delta': 'Δ', 'alpha': 'α', 'beta': 'β', 'lambda': 'λ', 'triangle': 'Δ', 'perp': '⊥',
    'parallel': '//', 'ldots': '…', 'cdots': '…', 'dots': '…', 'lt': '<', 'gt': '>', '%': '%',
    'sin': 'sin', 'cos': 'cos', 'tan': 'tan', 'cot': 'cot', 'log': 'log', 'ln': 'ln',
}


def _chu_toan(text: str) -> str:
    for _ in range(3):  # phân số lồng nhau mở từ trong ra ngoài
        for mau, thay in _LATEX:
            text = re.sub(mau, thay, text)
    text = re.sub(r'\\([a-zA-Z]+|%)', lambda m: _KY_HIEU.get(m[1], ''), text)
    text = re.sub(r'\\[,;:! ]', ' ', text)
    return re.sub(r' {2,}', ' ', text.replace('{', '').replace('}', ''))


def chu_thuong(content: str) -> str:
    content = _NGOAC_TOAN.sub(lambda m: f'$${m[1].strip()}$$' if m[1] is not None else f'${m[2].strip()}$', content or '')
    phan = _DOAN_TOAN.split(content)
    # Ngoài $...$ chỉ đổi số mũ, vì Gemini có lúc quên dấu $ ("x^2 - 4").
    return ''.join(_chu_toan(p.strip('$').strip()) if i % 2 else re.sub(r'\^(\d+)', lambda m: m[1].translate(_SO_MU), p)
                   for i, p in enumerate(phan))


def _doc() -> dict:
    if not KET_QUA.exists():
        raise SystemExit('Chưa có ket_qua.json. Chạy chay_test.py trước.')
    return json.loads(KET_QUA.read_text(encoding='utf-8'))


def _ghi_phieu(duong_dan: Path, dong: list[list]) -> None:
    # utf-8-sig: Excel cần BOM mới đọc đúng chữ có dấu.
    with duong_dan.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(COT)
        w.writerows(dong)


def xuat() -> None:
    data = _doc()
    theo_mon: dict[str, list[list]] = {}
    for k in data['ket_qua']:
        lich_su = '\n'.join(f"{'Em' if l['vai'] == 'user' else 'Mimo'}: {chu_thuong(l['noi_dung'])}"
                            for l in k.get('lich_su') or [])
        trang = '; '.join(f"{n.get('sach') or 'SGK'} tr.{n.get('trang')}" for n in k.get('nguon') or [])
        theo_mon.setdefault(k['mon'], []).append([
            k['stt'], data['chay_luc'], k['nhom'], k['mon'], k['lop'], lich_su,
            chu_thuong(k['cau_hoi']), chu_thuong(k['tra_loi']), trang or '(không trích)',
            chu_thuong(k['ghi_chu_cham']),
            k.get('nguoi_cham_kien_thuc') or '', k.get('nguoi_cham_ghi_chu') or '',
            k.get('nguoi_cham_ten') or ''])
    _ghi_phieu(PHIEU, sorted((d for ds in theo_mon.values() for d in ds), key=lambda d: d[0]))
    print(f'Đã ghi {PHIEU} ({len(data["ket_qua"])} câu).')
    # Mỗi thầy cô chỉ nhận đúng các câu của môn mình; nhap đọc được từng phiếu môn riêng lẻ.
    THEO_MON.mkdir(exist_ok=True)
    for cu in THEO_MON.glob('phieu_*.csv'):
        cu.unlink()
    for mon, dong in theo_mon.items():
        ten = THEO_MON / f"phieu_{re.sub(r'[^0-9A-Za-z]+', '_', _khong_dau(mon)).strip('_')}.csv"
        _ghi_phieu(ten, dong)
        print(f'   {mon:10} {len(dong):>2} câu → {ten.relative_to(THU_MUC)}')
    print('Gửi thầy cô đúng môn; cột Đánh giá chỉ nhận: ' + ' / '.join(DANH_GIA))


def _khong_dau(text: str) -> str:
    text = text.replace('đ', 'd').replace('Đ', 'D')
    return unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode()


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
