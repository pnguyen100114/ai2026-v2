"""Tổng hợp số liệu thử nghiệm với học sinh thật (bao-cao/KE_HOACH_THU_NGHIEM.md, Việc 2 và 3).

    python bao-cao/thu-nghiem/tong_hop.py khao-sat <phieu_khao_sat.csv>
        CSV tải từ Trang tính của Google Form do tao_google_form.gs tạo.
        → KET_QUA_KHAO_SAT.md

    python bao-cao/thu-nghiem/tong_hop.py truoc-sau <diem_truoc_sau.csv>
        CSV theo mẫu diem_truoc_sau_mau.csv: mỗi dòng một bạn, nhóm A (dùng Mimo) / B (không).
        → KET_QUA_TRUOC_SAU.md

Cả hai chỉ đếm và tính trung bình, không chấm hộ ai. Số liệu nhỏ (một buổi 10–15 bạn, một
lớp 30–40 bạn) nên báo cáo luôn kèm số bạn trả lời và khoảng tin cậy, không chỉ một con số.
"""
from __future__ import annotations

import csv
import random
import statistics
import sys
from datetime import datetime
from pathlib import Path

THU_MUC = Path(__file__).resolve().parent
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Tiêu đề câu hỏi y như trong tao_google_form.gs.
LOP = 'Em học lớp mấy?'
GIAI_HET = 'Có lúc nào Mimo giải hết bài cho em không?'
TU_LAM = 'Sau gợi ý của Mimo, em có tự làm tiếp được bước sau không?'
NAN_NI = 'Em có thử năn nỉ Mimo cho đáp án không?'
PHAN_UNG = 'Nếu có năn nỉ, Mimo phản ứng thế nào?'
TRANG_SACH = 'Em có bấm xem trang sách Mimo trích không?'
GIANG_SAI = 'Em có phát hiện chỗ nào Mimo giảng sai không? Chỗ nào?'
SO_VOI_AI = 'So với hỏi ChatGPT/Gemini, Mimo giúp em hiểu bài hơn hay kém hơn?'
DUNG_TIEP = 'Lần sau làm bài tập về nhà, em có muốn dùng Mimo không?'
VI_SAO = 'Vì sao em muốn hoặc không muốn dùng tiếp?'
KHO_CHIU = 'Điều em khó chịu nhất khi dùng Mimo là gì?'


def _doc_csv(duong_dan: Path) -> list[dict[str, str]]:
    with duong_dan.open(encoding='utf-8-sig', newline='') as f:
        return [{(k or '').strip(): (v or '').strip() for k, v in dong.items()} for dong in csv.DictReader(f)]


def _thang_diem(dong: list[dict[str, str]], cot: str) -> str:
    diem = [int(d[cot]) for d in dong if d.get(cot, '').isdigit()]
    if not diem:
        return 'chưa có ai trả lời'
    return f'**{statistics.mean(diem):.1f}/5** ({len(diem)} bạn; ' + ', '.join(
        f'{m} điểm: {diem.count(m)}' for m in range(1, 6) if diem.count(m)) + ')'


def _dem(dong: list[dict[str, str]], cot: str) -> str:
    gia_tri = [d[cot] for d in dong if d.get(cot)]
    return ' · '.join(f'{g}: **{gia_tri.count(g)}**' for g in dict.fromkeys(gia_tri)) or 'chưa có ai trả lời'


def _trich(dong: list[dict[str, str]], cot: str) -> list[str]:
    return [f'- {d[cot]}' for d in dong if d.get(cot)] or ['- (không có)']


def khao_sat(duong_dan: Path) -> None:
    dong = _doc_csv(duong_dan)
    thieu = [c for c in (GIAI_HET, TU_LAM, TRANG_SACH, DUNG_TIEP) if dong and c not in dong[0]]
    if thieu:
        raise SystemExit('CSV thiếu cột (đã đổi tiêu đề câu hỏi trong Form?): ' + '; '.join(thieu))
    n = len(dong)
    khong_bao_gio = sum(1 for d in dong if d.get(GIAI_HET) == 'Không bao giờ')
    khong_khop = sum(1 for d in dong if d.get(TRANG_SACH, '').endswith('không khớp'))
    md = [
        '# Kết quả khảo sát sau buổi dùng thử Mimo', '',
        f'Tổng hợp lúc {datetime.now():%d/%m/%Y %H:%M} từ `{duong_dan.name}`: **{n} bạn** trả lời '
        f'({_dem(dong, LOP)}).', '',
        '## Con số chính', '',
        f'- Mimo **không bao giờ giải hết bài**: **{khong_bao_gio}/{n}** bạn '
        f'({khong_bao_gio / n:.0%}). Chi tiết: {_dem(dong, GIAI_HET)}.' if n else '- Chưa có ai trả lời.',
        f'- Tự làm tiếp được sau gợi ý: {_thang_diem(dong, TU_LAM)}.',
        f'- Muốn dùng tiếp khi làm bài về nhà: {_thang_diem(dong, DUNG_TIEP)}.',
        f'- So với ChatGPT/Gemini: {_thang_diem(dong, SO_VOI_AI)}.',
        f'- Có thử năn nỉ xin đáp án: {_dem(dong, NAN_NI)}.',
        f'- Bấm xem trang sách: {_dem(dong, TRANG_SACH)}.',
        '',
        '## Phải xem kỹ', '',
        f'**{khong_khop} bạn** thấy trang sách không khớp lời Mimo giảng, và **'
        f'{n - khong_bao_gio} bạn** nói Mimo có lúc giải hết bài. Mỗi trường hợp cần đối chiếu ảnh '
        'chụp màn hình của người quan sát; ca nào là lỗi thật thì thêm vào `bao-cao/bo-test/cau_hoi.py`.', '',
        '### Chỗ các bạn thấy Mimo giảng sai', '', *_trich(dong, GIANG_SAI), '',
        '### Mimo phản ứng thế nào khi bị năn nỉ', '', *_trich(dong, PHAN_UNG), '',
        '### Vì sao muốn hoặc không muốn dùng tiếp', '', *_trich(dong, VI_SAO), '',
        '### Điều khó chịu nhất', '', *_trich(dong, KHO_CHIU), '',
        '---', '',
        '*Giới hạn: một buổi, các bạn biết mình đang được hỏi ý kiến về sản phẩm của bạn cùng lớp, '
        'nên điểm tự đánh giá có xu hướng cao. Câu trả lời mở và ca lỡ đưa đáp án đáng tin hơn điểm trung bình.*',
    ]
    ra = THU_MUC / 'KET_QUA_KHAO_SAT.md'
    ra.write_text('\n'.join(md) + '\n', encoding='utf-8')
    print(f'Đã ghi {ra} ({n} bạn).')


def _khoang_tin_cay(a: list[float], b: list[float], lan: int = 10000) -> tuple[float, float]:
    """Khoảng tin cậy 95% của chênh lệch trung bình (A − B), lấy mẫu lại có hoàn lại.

    Không giả định điểm phân phối chuẩn - với 15–20 bạn mỗi nhóm thì giả định đó khó kiểm.
    """
    ngau_nhien = random.Random(2026)  # cố định để chạy lại ra cùng số
    chenh = sorted(
        statistics.mean(ngau_nhien.choices(a, k=len(a))) - statistics.mean(ngau_nhien.choices(b, k=len(b)))
        for _ in range(lan))
    return chenh[int(lan * 0.025)], chenh[int(lan * 0.975) - 1]


def truoc_sau(duong_dan: Path) -> None:
    dong = _doc_csv(duong_dan)
    tang: dict[str, list[float]] = {'A': [], 'B': []}
    bo_qua = 0
    for d in dong:
        try:
            tang[d['nhom'].upper()].append(float(d['diem_sau'].replace(',', '.')) - float(d['diem_truoc'].replace(',', '.')))
        except (KeyError, ValueError):
            bo_qua += 1  # thiếu một trong hai bài kiểm tra: không tính được mức tăng
    a, b = tang['A'], tang['B']
    if len(a) < 2 or len(b) < 2:
        raise SystemExit(f'Mỗi nhóm cần ít nhất 2 bạn có đủ điểm trước và sau (A: {len(a)}, B: {len(b)}).')
    thap, cao = _khoang_tin_cay(a, b)
    chenh = statistics.mean(a) - statistics.mean(b)
    ket_luan = (
        'Khoảng tin cậy nằm hẳn trên 0: nhóm dùng Mimo tăng điểm nhiều hơn, ở mức mẫu nhỏ này.' if thap > 0 else
        'Khoảng tin cậy nằm hẳn dưới 0: nhóm dùng Mimo tăng điểm ít hơn. Cần xem lại cách dùng.' if cao < 0 else
        'Khoảng tin cậy chứa 0: chưa đủ bằng chứng nói hai nhóm khác nhau. Không được viết là "Mimo giúp tăng điểm".')
    md = [
        '# So sánh mức tăng điểm: nhóm dùng Mimo và nhóm không dùng', '',
        f'Tổng hợp lúc {datetime.now():%d/%m/%Y %H:%M} từ `{duong_dan.name}`.'
        + (f' Bỏ qua {bo_qua} dòng thiếu điểm trước hoặc sau.' if bo_qua else ''), '',
        '| Nhóm | Số bạn | Mức tăng trung bình (sau − trước) | Độ lệch chuẩn |',
        '|---|---|---|---|',
        f'| A — dùng Mimo | {len(a)} | {statistics.mean(a):+.2f} | {statistics.stdev(a):.2f} |',
        f'| B — học bình thường | {len(b)} | {statistics.mean(b):+.2f} | {statistics.stdev(b):.2f} |', '',
        f'Chênh lệch A − B: **{chenh:+.2f} điểm**, khoảng tin cậy 95%: **[{thap:+.2f}; {cao:+.2f}]**.', '',
        ket_luan, '',
        '---', '',
        '*Giới hạn: mẫu nhỏ, thời gian ngắn, nhóm A có thể cố gắng hơn vì biết mình đang được thử '
        '(hiệu ứng Hawthorne). Đây là dấu hiệu ban đầu, chưa phải bằng chứng chắc chắn.*',
    ]
    ra = THU_MUC / 'KET_QUA_TRUOC_SAU.md'
    ra.write_text('\n'.join(md) + '\n', encoding='utf-8')
    print(f'Đã ghi {ra}: A {len(a)} bạn, B {len(b)} bạn, chênh {chenh:+.2f} [{thap:+.2f}; {cao:+.2f}].')


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == 'khao-sat':
        khao_sat(Path(sys.argv[2]))
    elif len(sys.argv) == 3 and sys.argv[1] == 'truoc-sau':
        truoc_sau(Path(sys.argv[2]))
    else:
        raise SystemExit(__doc__)
