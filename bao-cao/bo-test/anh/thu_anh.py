"""Gửi 3 ảnh vở thật tới backend, in đề Mimo chép ra (image_text), câu trả lời và thời gian chờ.

Bộ 43 ca trong cau_hoi.py không có ca ảnh nào, nên phần đọc ảnh đo riêng ở đây. Mong đợi của
từng ảnh ghi trong README.md cùng thư mục; máy không chấm, người đọc đối chiếu.

Cách dùng:
    python bao-cao/bo-test/anh/thu_anh.py                          # backend ở máy, mỗi ảnh 1 lần
    python bao-cao/bo-test/anh/thu_anh.py --api https://gia-su-ai-api.onrender.com --lan 2

Dùng tài khoản thử riêng (mặc định bo-kiem-thu-4) để không đụng giới hạn 10 câu/phút của bộ 43 ca.
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
import time
from pathlib import Path

import httpx

THU_MUC = Path(__file__).resolve().parent
ANH = ['anh1_nhoe.jpg', 'anh2_nghieng_bai_sai.jpg', 'anh3_ro_bai_dung.jpg']
CAU = 'Em làm bài này đúng chưa ạ?'


def main() -> None:
    sys.stdout.reconfigure(encoding='utf-8')
    p = argparse.ArgumentParser()
    p.add_argument('--api', default='http://127.0.0.1:8000')
    p.add_argument('--lan', type=int, default=1)
    p.add_argument('--email', default='bo-kiem-thu-4@example.com')
    p.add_argument('--password', default='KiemThu-2026-Mimo')
    args = p.parse_args()

    with httpx.Client(timeout=180) as c:
        for mode in ('login', 'register'):
            body = {'email': args.email, 'password': args.password, 'mode': mode}
            if mode == 'register':
                body |= {'name': 'Bộ kiểm thử ảnh', 'grade': 6}
            r = c.post(f'{args.api}/api/auth/email', json=body)
            if r.status_code == 200:
                token = r.json()['token']
                break
        else:
            raise SystemExit(f'Không đăng nhập được: {r.status_code} {r.text[:200]}')

        for lan in range(args.lan):
            for ten in ANH:
                data = base64.b64encode((THU_MUC / ten).read_bytes()).decode()
                body = {'message': CAU, 'image_data': f'data:image/jpeg;base64,{data}', 'image_mime_type': 'image/jpeg',
                        'student': {'name': 'Bộ kiểm thử', 'grade': 6, 'subject': 'Toán'}}
                bat_dau, chu_dau, done = time.perf_counter(), None, {}
                with c.stream('POST', f'{args.api}/api/chat/stream', json=body,
                              headers={'Authorization': f'Bearer {token}'}) as r:
                    for line in r.iter_lines():
                        if not line.startswith('data: '):
                            continue
                        ev = json.loads(line[6:])
                        if ev.get('type') == 'chunk' and chu_dau is None:
                            chu_dau = time.perf_counter() - bat_dau
                        elif ev.get('type') in ('done', 'error'):
                            done = ev
                xong = time.perf_counter() - bat_dau
                print(f'===== {ten} (lần {lan + 1}) · chữ đầu {chu_dau or xong:.1f}s · xong {xong:.1f}s')
                print('ĐỀ MIMO CHÉP:', (done.get('image_text') or '(không có)').replace('\n', ' | '))
                print('TRẢ LỜI:', (done.get('content') or done.get('message') or '').replace('\n', ' '))
                time.sleep(8)


if __name__ == '__main__':
    main()
