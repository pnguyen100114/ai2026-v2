"""Chạy bộ câu hỏi kiểm thử qua API thật rồi ghi lại số liệu cho hồ sơ.

Vì sao gọi API đã deploy chứ không gọi thẳng hàm trong máy: hồ sơ nói sản phẩm chạy được,
nên số liệu phải đo trên đúng thứ ban giám khảo sẽ mở. Gọi hàm trong máy thì bỏ qua Render,
CORS, mạng và cả biến môi trường - đúng ba chỗ đã hỏng trong quá trình làm.

Cách dùng:
    python bao-cao/bo-test/chay_test.py                 # chạy cả bộ
    python bao-cao/bo-test/chay_test.py --nhom dễ       # chỉ một nhóm
    python bao-cao/bo-test/chay_test.py --api http://localhost:8000

Tài khoản: đặt MIMO_TEST_EMAIL / MIMO_TEST_PASSWORD trong môi trường, hoặc truyền --email
--password. Script tự đăng ký nếu email chưa có tài khoản.

Kết quả ghi ra ket_qua.json (máy đọc) và KET_QUA_TEST.md (người đọc, dán thẳng vào hồ sơ).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cau_hoi import CAU_HOI  # noqa: E402

THU_MUC = Path(__file__).resolve().parent

# Backend giới hạn 10 câu/phút mỗi học sinh. Giãn 8 giây để không bị chặn giữa chừng, vì
# một lần bị 429 là cả bộ test phải chạy lại.
GIAN_CACH = float(os.getenv('TEST_DELAY', '8'))


def dang_nhap(client: httpx.Client, api: str, email: str, password: str) -> str:
    """Trả về token. Chưa có tài khoản thì đăng ký."""
    for mode in ('login', 'register'):
        body = {'email': email, 'password': password, 'mode': mode}
        if mode == 'register':
            body |= {'name': 'Bộ kiểm thử', 'grade': 8}
        r = client.post(f'{api}/api/auth/email', json=body, timeout=120)
        if r.status_code == 200:
            return r.json()['token']
        # 404 = chưa có tài khoản (thử đăng ký); 409 = đã có (thử đăng nhập lại)
        if r.status_code not in (404, 409):
            raise SystemExit(f'Đăng nhập thất bại: {r.status_code} {r.text[:300]}')
    raise SystemExit('Không đăng nhập được mà cũng không đăng ký được.')


def hoi(client: httpx.Client, api: str, token: str, mon: str, lop: int, cau: str) -> dict:
    """Gửi một câu hỏi, đọc luồng SSE, trả về nội dung + nguồn + thời gian."""
    payload = {'message': cau, 'student': {'name': 'Bộ kiểm thử', 'grade': lop, 'subject': mon}}
    bat_dau = time.perf_counter()
    noi_dung, nguon, loi = '', [], None

    with client.stream('POST', f'{api}/api/chat/stream', json=payload, timeout=240,
                       headers={'Authorization': f'Bearer {token}'}) as r:
        if r.status_code != 200:
            r.read()
            return {'loi': f'HTTP {r.status_code}', 'giay': round(time.perf_counter() - bat_dau, 2),
                    'noi_dung': '', 'nguon': []}
        for dong in r.iter_lines():
            if not dong.startswith('data: '):
                continue
            try:
                su_kien = json.loads(dong[6:])
            except json.JSONDecodeError:
                continue
            loai = su_kien.get('type')
            if loai == 'chunk':
                noi_dung += su_kien.get('text', '')
            elif loai == 'done':
                noi_dung = su_kien.get('content') or noi_dung
                nguon = su_kien.get('sources') or []
            elif loai == 'error':
                loi = su_kien.get('message')

    return {'noi_dung': noi_dung, 'nguon': nguon, 'loi': loi,
            'giay': round(time.perf_counter() - bat_dau, 2)}


def cham(mong_doi: str, mon: str, lop: int, ket: dict) -> tuple[bool, str]:
    """Chấm phần máy chấm được. Đúng/sai về KIẾN THỨC thì phải người đọc, không chấm ở đây."""
    if ket.get('loi'):
        return False, f"lỗi: {ket['loi']}"
    if not (ket.get('noi_dung') or '').strip():
        return False, 'không trả lời'

    nguon = ket.get('nguon') or []

    if mong_doi == 'trich_dan':
        if not nguon:
            return False, 'không trích dẫn nguồn nào'
        lech = [n for n in nguon if str(n.get('grade') or lop) != str(lop)]
        if lech:
            return False, f'trích nguồn sai lớp ({len(lech)}/{len(nguon)} nguồn)'
        thieu_trang = [n for n in nguon if not n.get('page')]
        if thieu_trang:
            return False, f'{len(thieu_trang)} nguồn không có số trang'
        return True, f'{len(nguon)} nguồn, trang {", ".join(str(n.get("page")) for n in nguon[:3])}'

    if mong_doi == 'tu_choi':
        if nguon:
            return False, f'bịa {len(nguon)} trích dẫn cho kiến thức ngoài sách'
        return True, 'không bịa trích dẫn'

    if mong_doi == 'khong_co_trong_sach':
        if nguon:
            return False, f'bịa {len(nguon)} trích dẫn cho bài không có trong sách'
        # Không bịa nguồn mới là một nửa. Nửa còn lại: Mimo VẪN dạy (không từ chối, vì kiến
        # thức vừa sức lớp em) nhưng phải BÁO cho em biết phần này không có trong sách -
        # giao diện không hiện gì khi thiếu nguồn, nên câu báo đó là tín hiệu duy nhất em có.
        #
        # Dò từ khoá thì không chắc chắn: một câu báo diễn đạt kiểu khác sẽ bị chấm nhầm là
        # trượt. Nên ca nào cũng phải người đọc xác nhận lại, xem cột nguoi_cham_kien_thuc.
        loi = (ket.get('noi_dung') or '').lower()
        dau_hieu = ('không có trong', 'chưa có', 'không nằm trong', 'không thuộc',
                    'không tìm thấy', 'sách của em', 'chương trình lớp', 'thuộc chương trình',
                    'mimo có', 'mimo đang có', 'tài liệu', 'sách mimo', 'lớp 9', 'lớp 10',
                    'lớp 11', 'lớp 12', 'chương trình cũ')
        if any(d in loi for d in dau_hieu):
            return True, 'có báo sách không có bài này'
        return False, 'dạy như thể sách có bài này, không báo gì'

    if mong_doi == 'hoi_lai':
        if nguon:
            return True, f'có hướng dẫn kèm {len(nguon)} nguồn'
        return True, 'trả lời không kèm trích dẫn'

    return False, f'không hiểu mong đợi "{mong_doi}"'


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--api', default=os.getenv('MIMO_API', 'https://gia-su-ai-api.onrender.com'))
    p.add_argument('--email', default=os.getenv('MIMO_TEST_EMAIL', 'bo-kiem-thu@example.com'))
    p.add_argument('--password', default=os.getenv('MIMO_TEST_PASSWORD', 'KiemThu-2026-Mimo'))
    p.add_argument('--nhom', default=None, help='chỉ chạy một nhóm: dễ / khó / từ chối / mơ hồ / bẫy')
    args = p.parse_args()

    cases = [c for c in CAU_HOI if args.nhom is None or c[0] == args.nhom]
    if not cases:
        raise SystemExit(f'Không có ca nào thuộc nhóm "{args.nhom}".')

    print(f'API      : {args.api}')
    print(f'Số ca    : {len(cases)}')
    print(f'Giãn cách: {GIAN_CACH}s (backend giới hạn 10 câu/phút)')
    print(f'Dự kiến  : ~{len(cases) * (GIAN_CACH + 5) / 60:.0f} phút\n')

    with httpx.Client() as client:
        suc_khoe = client.get(f'{args.api}/api/health', timeout=120).json()
        print('Kho vector:', json.dumps(suc_khoe.get('rag', {}), ensure_ascii=False), '\n')

        token = dang_nhap(client, args.api, args.email, args.password)

        ket_qua = []
        for i, (nhom, mon, lop, cau, mong_doi, ghi_chu) in enumerate(cases, 1):
            print(f'[{i:>2}/{len(cases)}] {nhom:8} {mon} {lop}: {cau[:52]}...', flush=True)
            ket = hoi(client, args.api, token, mon, lop, cau)
            dat, ly_do = cham(mong_doi, mon, lop, ket)
            print(f'         {"ĐẠT  " if dat else "TRƯỢT"} {ly_do} · {ket["giay"]}s')

            ket_qua.append({
                'stt': i, 'nhom': nhom, 'mon': mon, 'lop': lop, 'cau_hoi': cau,
                'mong_doi': mong_doi, 'ghi_chu_cham': ghi_chu,
                'dat_may_cham': dat, 'ly_do': ly_do, 'giay': ket['giay'],
                'so_nguon': len(ket.get('nguon') or []),
                'nguon': [{'sach': n.get('source'), 'trang': n.get('page'),
                           'bai': n.get('lesson_title')} for n in (ket.get('nguon') or [])],
                'tra_loi': ket.get('noi_dung', ''),
                # Người đọc điền: kiến thức có đúng không. Máy không chấm được phần này.
                'nguoi_cham_kien_thuc': None,
            })
            if i < len(cases):
                time.sleep(GIAN_CACH)

    (THU_MUC / 'ket_qua.json').write_text(
        json.dumps({'chay_luc': datetime.now().isoformat(timespec='seconds'),
                    'api': args.api, 'kho_vector': suc_khoe.get('rag', {}),
                    'ket_qua': ket_qua}, ensure_ascii=False, indent=2), encoding='utf-8')

    dat = sum(1 for k in ket_qua if k['dat_may_cham'])
    print(f'\n{"="*60}\nMáy chấm: {dat}/{len(ket_qua)} ĐẠT')
    for nhom in dict.fromkeys(k['nhom'] for k in ket_qua):
        trong = [k for k in ket_qua if k['nhom'] == nhom]
        print(f'   {nhom:8} {sum(1 for k in trong if k["dat_may_cham"])}/{len(trong)}')
    giay = sorted(k['giay'] for k in ket_qua)
    print(f'Thời gian trả lời: trung vị {giay[len(giay)//2]:.1f}s, chậm nhất {giay[-1]:.1f}s')
    print(f'\nĐã ghi {THU_MUC / "ket_qua.json"}')
    print('Chạy tiep: python bao-cao/bo-test/lam_bang.py  → KET_QUA_TEST.md')


if __name__ == '__main__':
    main()
