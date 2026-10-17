"""Chốt các con số hồ sơ cần mà nguồn của chúng không lên được GitHub, ghi vào so_lieu_goc.json.

    đợt thử nghiệm   backend/local.db                    dữ liệu người dùng thật, không đưa lên kho
    kho sách         backend/rag/.ingest_manifest.json   sổ nạp sách riêng của máy đã nạp Pinecone
    sách lỗi         backend/data/*.pdf                  2,5 GB, quá nặng cho GitHub

Chỉ chạy được ở máy có đủ ba nguồn trên. Máy khác không cần chạy: make_report.py và
illustrations.py đọc so_lieu_goc.json đã có sẵn trong kho. File chỉ chứa số đếm, không có
tên, email hay câu hỏi của ai.

Chạy lại sau khi nạp thêm sách hoặc thay bản scan, rồi commit so_lieu_goc.json:

    .venv\\Scripts\\python.exe bao-cao\\chot_so_lieu.py
"""
import json
import re
import sqlite3
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
RA = ROOT / 'bao-cao' / 'so_lieu_goc.json'

# ---------------------------------------------------------------- đợt thử nghiệm (backend/local.db)
# local.db là DB chạy thật: mỗi lần mở app ở máy lại đẻ thêm tài khoản và câu hỏi. Khóa cứng
# theo ngày, không thì số liệu nộp bị thổi lên mà không ai biết.
TRIAL_FROM, TRIAL_TO = '2026-09-13', '2026-09-14'
IN_TRIAL = f"substr({{}}.created_at, 1, 10) between '{TRIAL_FROM}' and '{TRIAL_TO}'"

db = sqlite3.connect(ROOT / 'backend' / 'local.db')
q = lambda s: db.execute(s).fetchall()
thu_nghiem = {
    'tu_ngay': TRIAL_FROM,
    'den_ngay': TRIAL_TO,
    'tai_khoan': q(f'select count(*) from users where {IN_TRIAL.format("users")}')[0][0],
    'phien': q(f'select count(*) from chat_sessions where {IN_TRIAL.format("chat_sessions")}')[0][0],
    'cau_hoi': q(f"select count(*) from messages where role='user' and {IN_TRIAL.format('messages')}")[0][0],
    'cau_kem_anh': q(f"select count(*) from messages where role='user' and has_image=1 and {IN_TRIAL.format('messages')}")[0][0],
    'phien_theo_mon': q(f'select subject, grade, count(*) from chat_sessions where {IN_TRIAL.format("chat_sessions")} group by subject, grade order by count(*)'),
    'muc_hieu': dict(q(f"select coalesce(understanding,'none'), count(*) from messages where role='assistant' and {IN_TRIAL.format('messages')} group by 1")),
    'luot_luyen_tap': q(f'select count(*) from quiz_attempts where {IN_TRIAL.format("quiz_attempts")}')[0][0],
    'lo_trinh_ai': q(f'select count(*) from ai_roadmaps where {IN_TRIAL.format("ai_roadmaps")}')[0][0],
}

# ---------------------------------------------------------------- kho sách (sổ nạp sách)
_manifest = json.loads((ROOT / 'backend' / 'rag' / '.ingest_manifest.json').read_text(encoding='utf-8'))
kho_sach = {
    'so_cuon': len(_manifest),
    'so_doan': sum(book['chunks'] for book in _manifest.values()),
    'nap_xong': max(book['ingested_at'] for book in _manifest.values())[:10],
}

# ---------------------------------------------------------------- chất lượng sách trong kho
# Bản quét thiếu: đếm thẳng số trang PDF. Sách in mỏng nhất trong bộ cũng trên 100 trang,
# nên dưới 80 trang chắc chắn là bản scan dở dang.
sach_ngan = []
# Bản chia sẻ lại: lớp chữ của từng trang mang watermark của trang web phát tán. Watermark đó
# còn IN ĐÈ lên ảnh trang, nên học sinh bấm "Xem trang" là thấy. Đếm thẳng thay vì gõ tay.
_WATERMARK = re.compile(r'blogtailieu|tailieu\.com|sách chia sẻ', re.IGNORECASE)
sach_watermark = []
for _f in sorted((ROOT / 'backend' / 'data').glob('*.pdf')):
    with pymupdf.open(_f) as _d:
        if _d.page_count < 80:
            sach_ngan.append((_f.stem, _d.page_count))
        _mau = range(10, min(_d.page_count, 40))
        if _mau and all(_WATERMARK.search(_d[_i].get_text() or '') for _i in _mau):
            sach_watermark.append(_f.stem)
sach_ngan.sort(key=lambda x: x[1])

so_lieu = {
    'thu_nghiem': thu_nghiem,
    'kho_sach': kho_sach,
    'sach_loi': {'quet_thieu': sach_ngan, 'watermark': sach_watermark},
}
RA.write_text(json.dumps(so_lieu, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('Đã ghi', RA)
print(f"  đợt thử    {thu_nghiem['tai_khoan']} tài khoản · {thu_nghiem['phien']} phiên · {thu_nghiem['cau_hoi']} câu")
print(f"  kho sách   {kho_sach['so_cuon']} cuốn · {kho_sach['so_doan']} đoạn · nạp xong {kho_sach['nap_xong']}")
print(f'  sách lỗi   {len(sach_ngan)} bản quét thiếu · {len(sach_watermark)} bản có watermark')
