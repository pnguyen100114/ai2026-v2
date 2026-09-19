"""Chụp lại ảnh sản phẩm cho hồ sơ, bằng cách điều khiển trình duyệt thật.

Vì sao không chụp tay: mỗi lần sửa giao diện là bộ ảnh trong hồ sơ lạc hậu, mà ảnh cũ thì
không ai nhìn ra là cũ. Chạy lại file này thì cả bộ ảnh khớp với bản đang chạy.

Chuẩn bị:
    1. Đặt VITE_API_BASE_URL trong .env.local trỏ vào backend đang chạy (máy hoặc bản deploy).
    2. npm run dev -- --host 127.0.0.1 --port 5173
    3. .venv\\Scripts\\python.exe bao-cao\\chup_anh.py

Ảnh ghi vào bao-cao/anh-san-pham/. Tài khoản demo được tạo mới mỗi lần chạy để ảnh luôn đi
đúng luồng của một học sinh lần đầu dùng sản phẩm.
"""
from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import TimeoutError as PWTimeout, sync_playwright

WEB = 'https://ai2026-v2.vercel.app/'
RA = Path(__file__).resolve().parent / 'anh-san-pham'
RA.mkdir(parents=True, exist_ok=True)

# Tài khoản demo riêng mỗi lần chạy: luồng khảo sát chỉ hiện với tài khoản mới.
DAU = datetime.now().strftime('%m%d%H%M')
EMAIL = f'minh.anh.demo+{DAU}@example.com'
MATKHAU = 'MimoDemo-2026'
TEN = 'Minh Anh'
LOP = 8

# Khổ ảnh: rộng 1440 cho đủ sidebar, cao 900 cho vừa một màn hình laptop.
KHO = {'width': 1440, 'height': 900}

# Bài dùng để minh họa. Cố ý chọn bài thuộc Toán 8 TẬP HAI: bản PDF Toán 8 tập một nhóm đang
# có là bản chia sẻ lại, in đè watermark "BlogTailieu.com" lên từng trang, nên ảnh "Xem trang"
# chụp từ tập một sẽ đầy watermark của bên thứ ba. 28 cuốn còn lại trong kho đều sạch.
BAI = '25. Phương trình bậc nhất một ẩn'
CAU_HOI = 'Phương trình bậc nhất một ẩn là gì ạ? Cho em một ví dụ với.'


def chup(trang, ten: str, cho: float = 0.6) -> None:
    time.sleep(cho)
    duong = RA / f'{ten}.png'
    trang.screenshot(path=str(duong))
    print(f'  → {duong.name}')


def main() -> None:
    with sync_playwright() as p:
        trinh_duyet = p.chromium.launch(channel='chrome')
        ngu_canh = trinh_duyet.new_context(viewport=KHO, device_scale_factor=2, locale='vi-VN')
        trang = ngu_canh.new_page()
        trang.set_default_timeout(60_000)

        print(f'Mở {WEB} · tài khoản {EMAIL}')
        trang.goto(WEB, wait_until='networkidle')

        # ---------------------------------------------------------------- 1. màn hình chào
        trang.wait_for_selector('text=Không gian học tập')
        chup(trang, 'sp_1_dangnhap')

        # ---------------------------------------------------------------- 2. tạo tài khoản
        trang.click('button:has-text("Tạo tài khoản mới")')
        trang.wait_for_selector('h2:has-text("Tạo tài khoản")')
        trang.fill('input[placeholder="Ví dụ: Minh Anh"]', TEN)
        trang.fill('input[type="email"]', EMAIL)
        trang.fill('input[placeholder="Ít nhất 6 ký tự"]', MATKHAU)
        # Ô "Nhập lại mật khẩu" không có placeholder, lấy theo nhãn.
        trang.fill('label:has-text("Nhập lại mật khẩu") input', MATKHAU)
        trang.select_option('label:has-text("Lớp hiện tại") select', str(LOP))
        chup(trang, 'sp_2_taotaikhoan')
        trang.click('button[type="submit"]')

        # ---------------------------------------------------------------- 3. khảo sát
        trang.wait_for_selector('h1:has-text("em muốn học môn nào")')
        trang.click('button:has-text("Toán")')
        chup(trang, 'sp_3_khaosat')
        trang.click('button:has-text("Tiếp tục")')

        trang.wait_for_selector('h1:has-text("Mục tiêu của em")')
        trang.click('button:has-text("45 phút")')
        trang.click('button:has-text("Tiếp tục")')

        trang.wait_for_selector('h1:has-text("Thiết lập lộ trình")')
        trang.click('button:has-text("Tạo lộ trình cho mình")')

        # ---------------------------------------------------------------- 4. trang chủ
        # Xong khảo sát thì sản phẩm đưa thẳng vào trang Hỏi Mimo, nên phải bấm về Trang chủ.
        trang.wait_for_selector('nav >> text=Trang chủ', timeout=90_000)
        trang.wait_for_load_state('networkidle')
        trang.click('nav >> text=Trang chủ')
        trang.wait_for_load_state('networkidle')
        chup(trang, 'sp_4_trangchu', cho=2.0)

        # ---------------------------------------------------------------- 5. lộ trình học
        trang.click('text=Lộ trình học')
        trang.wait_for_load_state('networkidle')
        chup(trang, 'sp_5_lotrinh', cho=2.0)

        # Chọn một bài để phần hỏi bài và luyện tập có ngữ cảnh đúng bài đó.
        # Mỗi bài là một .lesson-row, tên bài nằm trong <strong>, nút chọn bài nằm cuối hàng.
        # Bấm thẳng nút của ĐÚNG hàng đó, thay vì dò theo chuỗi chữ trên cả trang: tên bài
        # còn xuất hiện ở chỗ khác, dò nhầm là cả bộ ảnh nói về một bài không phải bài đang hỏi.
        hang = trang.locator(f'.lesson-row:has(strong:text-is("{BAI}"))')
        try:
            hang.scroll_into_view_if_needed(timeout=15_000)
            hang.locator('button').last.click()
            trang.wait_for_load_state('networkidle')
            time.sleep(1.2)
        except PWTimeout:
            print(f'  (không tìm thấy bài "{BAI}", bỏ qua bước chọn bài)')

        # ---------------------------------------------------------------- 6. hỏi bài
        trang.click('text=Hỏi Mimo')
        trang.wait_for_load_state('networkidle')
        time.sleep(1.0)

        o_nhap = trang.locator('textarea').first
        o_nhap.fill(CAU_HOI)
        chup(trang, 'sp_6_hoibai_dang_go', cho=0.4)
        o_nhap.press('Enter')

        # Chờ Mimo trả lời xong: nút trích dẫn [1] xuất hiện là dấu hiệu chắc chắn nhất.
        print('  đang chờ Mimo trả lời...')
        try:
            # .cite-ref là nút số [1] do ChatMessageContent dựng; .source-thumbs là dải ảnh trang.
            trang.wait_for_selector('.cite-ref, .source-thumbs', timeout=90_000)
        except PWTimeout:
            print('  (không thấy số trích dẫn, vẫn chụp lại những gì có)')
        time.sleep(5.0)
        # Chờ nốt ảnh nhỏ của trang được trích, để ảnh chụp không còn ô xám đang tải.
        try:
            trang.wait_for_function(
                "() => [...document.querySelectorAll('.source-thumbs img')]"
                ".every(a => a.complete && a.naturalWidth > 0)", timeout=60_000)
        except PWTimeout:
            print('  (ảnh nhỏ của trang sách chưa tải xong)')
        chup(trang, 'sp_6_hoibai', cho=1.2)

        # ---------------------------------------------------------------- 7. trang sách
        # Nút [n] bị disabled khi nguồn không có ảnh trang, nên chỉ bấm nút còn bấm được.
        so_trich_dan = trang.locator('.cite-ref:not([disabled])').first
        if not so_trich_dan.count():
            so_trich_dan = trang.locator('.source-thumbs button, .source-thumbs img').first
        if so_trich_dan.count():
            try:
                so_trich_dan.click(timeout=10_000)
                trang.wait_for_selector('.source-modal', timeout=20_000)
                # networkidle chưa đủ: ảnh trang đi qua một cú chuyển hướng sang Supabase, nên
                # phải chờ đúng thẻ <img> báo đã tải xong, không thì chụp phải khung xám.
                trang.wait_for_function(
                    "() => { const a = document.querySelector('.source-modal img');"
                    " return a && a.complete && a.naturalWidth > 0 }", timeout=60_000)
                chup(trang, 'sp_7_trangsach', cho=1.5)
                # Modal không đóng bằng Escape; phải bấm nút X, nếu không nó chắn mọi cú bấm sau.
                trang.click('button[aria-label="Đóng xem trang"]')
                trang.wait_for_selector('.source-modal', state='detached', timeout=15_000)
                time.sleep(0.5)
            except PWTimeout:
                print('  (không mở được ảnh trang sách)')
        else:
            print('  (không có nguồn nào bấm xem trang được)')

        # ---------------------------------------------------------------- 8. luyện tập
        for nhan in ('Bắt đầu luyện tập', 'Làm bài luyện tập', 'Luyện tập'):
            nut = trang.locator(f'button:has-text("{nhan}")')
            if nut.count():
                nut.first.click()
                print('  đang chờ Mimo soạn câu luyện tập...')
                time.sleep(14.0)
                trang.wait_for_load_state('networkidle')
                # Khối luyện tập nằm dưới khung chat, phải kéo vào giữa màn hình mới chụp đủ.
                khoi = trang.locator('text=Luyện tập vừa sức em').first
                if khoi.count():
                    khoi.scroll_into_view_if_needed()
                    trang.mouse.wheel(0, 260)
                chup(trang, 'sp_8_luyentap', cho=1.5)
                break
        else:
            print('  (không tìm thấy nút luyện tập)')

        # ---------------------------------------------------------------- 9. pomodoro
        trang.click('text=Pomodoro')
        trang.wait_for_load_state('networkidle')
        chup(trang, 'sp_9_pomodoro', cho=1.5)

        # ---------------------------------------------------------------- 10. hồ sơ
        trang.click('nav >> text=Hồ sơ')
        trang.wait_for_load_state('networkidle')
        chup(trang, 'sp_10_hoso', cho=1.5)

        ngu_canh.close()
        trinh_duyet.close()

    print(f'\nXong. Ảnh nằm trong {RA}')


if __name__ == '__main__':
    try:
        main()
    except Exception as loi:  # noqa: BLE001
        print(f'\nLỖI: {type(loi).__name__}: {loi}', file=sys.stderr)
        raise
