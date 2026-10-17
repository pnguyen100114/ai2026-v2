"""Dựng lại các file minh chứng trong thư mục này từ dữ liệu gốc của repo.

Chỉ gồm việc làm SAU ngày nộp 19/09/2026. Không có file CSV, không có tên học sinh hay thầy cô.
File CAI_TIEN_THEO_YEU_CAU_BGK.md và README.md viết tay, script không đụng tới.

    python bao-cao/minh-chung-sau-1909/dung_minh_chung.py

Chạy lại sau khi đo lại bộ thử (lam_bang.py) hoặc cập nhật nhật ký prompt.
"""
from __future__ import annotations

import csv
import json
import re
import shutil
import subprocess
from pathlib import Path

DAY = Path(__file__).resolve().parent
BC = DAY.parent
ROOT = BC.parent
SAU_NGAY = '2026-09-20'


def ghi(duong: Path, noi_dung: str) -> None:
    duong.parent.mkdir(parents=True, exist_ok=True)
    duong.write_text(noi_dung, encoding='utf-8')
    print('  ', duong.relative_to(DAY))


def chep(nguon: Path, dich: Path) -> None:
    dich.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(nguon, dich)
    print('  ', dich.relative_to(DAY), '(chép từ', nguon.relative_to(ROOT), ')')


def o(chu: str) -> str:
    return ' '.join((chu or '').split()).replace('|', '/')


# ---------------------------------------------------------------- 1. chấm chặt bộ thử
chep(BC / 'bo-test' / 'KET_QUA_TEST.md', DAY / '1_cham_chat_bo_thu' / 'KET_QUA_TEST.md')
chep(BC / 'bo-test' / 'so-sanh-nan-ni' / 'README.md', DAY / '1_cham_chat_bo_thu' / 'SO_SANH_NAN_NI_1909_VA_1710.md')

# ---------------------------------------------------------------- 2. thầy cô chấm
gv = json.loads((BC / 'bo-test' / 'ket_qua_gv_1710.json').read_text(encoding='utf-8'))
moi = {k['stt']: k for k in json.loads((BC / 'bo-test' / 'ket_qua.json').read_text(encoding='utf-8'))['ket_qua']}
moi_luc = json.loads((BC / 'bo-test' / 'ket_qua.json').read_text(encoding='utf-8'))['chay_luc'].replace('T', ' ')[:16]
ds = gv['ket_qua']
dem = {d: sum(1 for k in ds if k.get('nguoi_cham_kien_thuc') == d) for d in ('đúng', 'có chỗ sai', 'sai')}
dong = [
    '# Thầy cô bộ môn chấm 43 câu trả lời, lần đo 17/10/2026',
    '',
    f'Thầy cô dạy đúng môn đọc **nguyên văn** câu trả lời của lần chạy {gv["chay_luc"].replace("T", " ")[:16]} '
    'trên bản đã triển khai, kèm số trang Mimo trích, rồi đánh dấu đúng / có chỗ sai / sai.',
    '',
    f'**Kết quả: {dem["đúng"]} đúng · {dem["có chỗ sai"]} có chỗ sai · {dem["sai"]} sai** (trên {len(ds)} câu).',
    '',
    '## Hai câu có chỗ sai và việc nhóm đã sửa',
    '',
]
for k in ds:
    if k.get('nguoi_cham_kien_thuc') in ('có chỗ sai', 'sai'):
        sau = moi.get(k['stt'], {})
        dong += [
            f'### Câu {k["stt"]} · {k["mon"]} {k["lop"]}: {k["cau_hoi"]}',
            '',
            f'- **Thầy cô nhận xét:** {o(k.get("nguoi_cham_ghi_chu"))}',
            f'- **Mimo trả lời lúc được chấm:** {o(k["tra_loi"])}',
            f'- **Mimo trả lời ở lần đo lại {moi_luc}, sau khi sửa:** {o(sau.get("tra_loi", ""))}',
            '',
        ]
dong += ['## Toàn bộ 43 câu', '', '| # | Môn · lớp | Câu hỏi | Thầy cô đánh giá | Nhận xét |', '|---|---|---|---|---|']
for k in ds:
    dong.append(f'| {k["stt"]} | {k["mon"]} {k["lop"]} | {o(k["cau_hoi"])} | {k.get("nguoi_cham_kien_thuc") or ""} | '
                f'{o(k.get("nguoi_cham_ghi_chu"))} |')
dong += ['', 'Nguyên văn đủ 43 câu trả lời nằm trong `bao-cao/bo-test/ket_qua_gv_1710.json` của repo.', '']
ghi(DAY / '2_thay_co_cham' / 'THAY_CO_CHAM_LAN_DO_1710.md', '\n'.join(dong))

with (BC / 'bo-test' / 'cham_giao_vien_1909.csv').open(encoding='utf-8-sig', newline='') as f:
    phieu = list(csv.DictReader(f))
dem19 = {d: sum(1 for r in phieu if (r['Đánh giá của thầy cô'] or '').strip().lower() == d) for d in ('đúng', 'có chỗ sai', 'sai')}
dong = [
    '# Thầy cô bộ môn chấm 28 câu trả lời của bản nộp 19/09',
    '',
    'Chấm ngày 16–17/10/2026 trên câu trả lời của bản nộp 19/09 (bản rút gọn). Nhóm dùng kết quả này để biết '
    'bản cũ sai ở đâu rồi sửa; cột cuối ghi Mimo hiện tại xử lý góp ý đó thế nào.',
    '',
    f'**Kết quả: {dem19["đúng"]} đúng · {dem19["có chỗ sai"]} có chỗ sai · {dem19["sai"]} sai** (trên {len(phieu)} câu).',
    '',
    '| # | Môn · lớp | Câu hỏi | Thầy cô đánh giá | Nhận xét của thầy cô | Hiện tại so với góp ý |',
    '|---|---|---|---|---|---|',
]
for r in phieu:
    dong.append(f'| {r["STT"]} | {r["Môn"]} {r["Lớp"]} | {o(r["Câu hỏi"])} | {o(r["Đánh giá của thầy cô"])} | '
                f'{o(r["Nhận xét của thầy cô"])} | {o(r["Hiện tại so với góp ý của thầy cô"])} |')
ghi(DAY / '2_thay_co_cham' / 'THAY_CO_CHAM_BAN_NOP_1909.md', '\n'.join(dong) + '\n')

# ---------------------------------------------------------------- 3. học sinh dùng thử
chep(BC / 'thu-nghiem' / 'KET_QUA_DUNG_THU_1610.md', DAY / '3_hoc_sinh_dung_thu' / 'KET_QUA_DUNG_THU_1610.md')
gs = (BC / 'thu-nghiem' / 'tao_google_form.gs').read_text(encoding='utf-8')
cau = re.findall(r"setTitle\('([^']+)'\)", gs)
ghi(DAY / '3_hoc_sinh_dung_thu' / 'CAU_HOI_GOOGLE_FORM.md',
    '# Câu hỏi Google Form sau buổi dùng thử\n\nForm dựng tự động bằng `bao-cao/thu-nghiem/tao_google_form.gs`.\n\n'
    + '\n'.join(f'{i}. {c}' for i, c in enumerate(cau, 1)) + '\n')

# ---------------------------------------------------------------- 5. thử nghiệm dài hạn
chep(BC / 'KE_HOACH_THU_NGHIEM.md', DAY / '5_thu_nghiem_dai_han' / 'KE_HOACH_THU_NGHIEM.md')

# ---------------------------------------------------------------- 6. nhật ký
log = subprocess.run(['git', 'log', f'--since={SAU_NGAY}', '--reverse', '--date=format:%d/%m/%Y %H:%M',
                      '--format=%ad\t%h\t%s', 'main'], cwd=ROOT, capture_output=True, text=True,
                     encoding='utf-8', check=True).stdout.strip().splitlines()
dong = ['# Các lần sửa sau 19/09/2026', '', f'{len(log)} commit trên nhánh `main`, cũ trước mới sau.', '',
        '| Thời gian | Commit | Nội dung |', '|---|---|---|']
dong += [f'| {a} | `{b}` | {o(c)} |' for a, b, c in (l.split('\t', 2) for l in log)]
ghi(DAY / '6_nhat_ky' / 'CAC_LAN_SUA_SAU_1909.md', '\n'.join(dong) + '\n')

# Nhật ký prompt: chỉ giữ các prompt từ 20/09 trở đi, kèm tiêu đề phiên của chúng.
lich_su = (ROOT / 'prompt-log' / 'PROMPT_HISTORY.md').read_text(encoding='utf-8').replace('\r\n', '\n')
DAU_PROMPT = re.compile(r'^### \d+\. \d\d:\d\d:\d\d (\d+)/(\d+)/(\d{4})$')
ra, phien, phien_da_in, giu, so = [], None, False, False, 0
for dong_l in lich_su.split('\n'):
    if dong_l.startswith('## ') and ('phien' in dong_l or 'phiên' in dong_l):
        phien, phien_da_in, giu = dong_l, False, False
        continue
    m = DAU_PROMPT.match(dong_l)
    if m:
        ngay = f'{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}'
        giu = ngay >= SAU_NGAY
        if giu:
            so += 1
            if phien and not phien_da_in:
                ra += ['', phien, '']
                phien_da_in = True
    if giu and not dong_l.startswith('---'):
        ra.append(dong_l)
ghi(DAY / '6_nhat_ky' / 'PROMPT_SAU_1909.md',
    f'# Prompt nhóm dùng với AI lập trình sau 19/09/2026\n\n{so} prompt, lọc từ `prompt-log/PROMPT_HISTORY.md` '
    '(email và tên học sinh đã được che).\n' + '\n'.join(ra) + '\n')
print(f'Xong: {len(log)} commit, {so} prompt sau 19/09.')
