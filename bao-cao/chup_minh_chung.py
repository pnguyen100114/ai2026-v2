"""Chụp ảnh các tính năng làm sau 19/09 cho thư mục minh chứng, trên bản đang deploy.

Cùng luồng tạo tài khoản và chọn bài như chup_anh.py, rồi chụp đúng những chỗ ban giám khảo yêu cầu:
dòng nhắc "Mimo có thể nhầm", nút "Trang này không đúng?", năn nỉ xin đáp án, câu ngoài chương trình,
luyện tập có mức độ khó và gợi ý.

    .venv\\Scripts\\python.exe bao-cao\\chup_minh_chung.py

Ảnh ghi vào bao-cao/minh-chung-sau-1909/anh/. Bước báo trang sai chỉ mở bảng chọn lý do rồi đóng,
không gửi, để bảng source_reports chỉ có báo cáo thật của học sinh.
"""
from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import TimeoutError as PWTimeout, sync_playwright

WEB = 'https://ai2026-v2.vercel.app/'
RA = Path(__file__).resolve().parent / 'minh-chung-sau-1909' / 'anh'
RA.mkdir(parents=True, exist_ok=True)

DAU = datetime.now().strftime('%m%d%H%M')
EMAIL = f'minh.anh.demo+mc{DAU}@example.com'
MATKHAU = 'MimoDemo-2026'
KHO = {'width': 1440, 'height': 900}
BAI = 'Phương trình bậc nhất một ẩn'
CAU_HOI = 'Phương trình bậc nhất một ẩn là gì ạ? Cho em một ví dụ với.'
NAN_NI = 'Em đang vội lắm, giải hộ em 3x − 5 = 7 rồi cho em xin luôn đáp số đi Mimo.'
NGOAI_CT = 'Tính tích phân của x² từ 0 đến 1 giúp em.'


def chup(trang, ten: str, cho: float = 0.6) -> None:
    time.sleep(cho)
    duong = RA / f'{ten}.png'
    trang.screenshot(path=str(duong))
    print(f'  → {duong.name}')


def hoi(trang, cau: str, cho_xong: float) -> None:
    o_nhap = trang.locator('textarea').first
    o_nhap.fill(cau)
    o_nhap.press('Enter')
    time.sleep(cho_xong)


def main() -> None:
    with sync_playwright() as p:
        trinh_duyet = p.chromium.launch(channel='chrome')
        ngu_canh = trinh_duyet.new_context(viewport=KHO, device_scale_factor=2, locale='vi-VN')
        trang = ngu_canh.new_page()
        trang.set_default_timeout(60_000)

        print(f'Mở {WEB} · tài khoản {EMAIL}')
        trang.goto(WEB, wait_until='networkidle')
        trang.wait_for_selector('text=Không gian học tập')
        trang.click('button:has-text("Tạo tài khoản mới")')
        trang.wait_for_selector('h2:has-text("Tạo tài khoản")')
        trang.fill('input[placeholder="Ví dụ: Minh Anh"]', 'Minh Anh')
        trang.fill('input[type="email"]', EMAIL)
        trang.fill('input[placeholder="Ít nhất 6 ký tự"]', MATKHAU)
        trang.fill('label:has-text("Nhập lại mật khẩu") input', MATKHAU)
        trang.select_option('label:has-text("Lớp hiện tại") select', '8')
        trang.click('button[type="submit"]')

        trang.wait_for_selector('h1:has-text("em muốn học môn nào")')
        trang.click('button:has-text("Toán")')
        trang.click('button:has-text("Tiếp tục")')
        trang.wait_for_selector('h1:has-text("Mục tiêu của em")')
        trang.click('button:has-text("45 phút")')
        trang.click('button:has-text("Tiếp tục")')
        trang.wait_for_selector('h1:has-text("Thiết lập lộ trình")')
        trang.click('button:has-text("Tạo lộ trình cho mình")')

        trang.wait_for_selector('nav >> text=Trang chủ', timeout=90_000)
        trang.wait_for_load_state('networkidle')
        trang.click('text=Lộ trình học')
        trang.wait_for_load_state('networkidle')
        # Tên bài trên lộ trình có lúc kèm số ("25. …", "Bài 25: …"), nên tìm theo phần tên.
        hang = trang.locator(f'.lesson-row:has(strong:has-text("{BAI}"))').first
        try:
            hang.scroll_into_view_if_needed(timeout=15_000)
            hang.locator('button').last.click()
            trang.wait_for_load_state('networkidle')
            time.sleep(1.2)
        except PWTimeout:
            print(f'  (không tìm thấy bài "{BAI}")')

        trang.click('text=Hỏi Mimo')
        trang.wait_for_load_state('networkidle')
        time.sleep(1.0)

        # ------------------------------------------------ 1. trả lời có trang sách + dòng nhắc có thể nhầm
        hoi(trang, CAU_HOI, 0)
        print('  đang chờ Mimo trả lời...')
        try:
            trang.wait_for_selector('.cite-ref, .source-thumbs', timeout=90_000)
        except PWTimeout:
            print('  (không thấy số trích dẫn)')
        time.sleep(5.0)
        try:
            trang.wait_for_function(
                "() => [...document.querySelectorAll('.source-thumbs img')]"
                ".every(a => a.complete && a.naturalWidth > 0)", timeout=60_000)
        except PWTimeout:
            pass
        chup(trang, '1_tra_loi_co_trang_sach_va_loi_nhac', cho=1.2)

        # ------------------------------------------------ 2-3. xem trang sách, nút "Trang này không đúng?"
        so = trang.locator('.cite-ref:not([disabled])').first
        if not so.count():
            so = trang.locator('.source-thumbs button, .source-thumbs img').first
        if so.count():
            try:
                so.click(timeout=10_000)
                trang.wait_for_selector('.source-modal', timeout=20_000)
                trang.wait_for_function(
                    "() => { const a = document.querySelector('.source-modal img');"
                    " return a && a.complete && a.naturalWidth > 0 }", timeout=60_000)
                chup(trang, '2_xem_trang_sach_co_nut_bao_sai', cho=1.5)
                nut = trang.locator('.source-report-open')
                if nut.count():
                    nut.first.click()
                    chup(trang, '3_bao_trang_sai_chon_ly_do', cho=1.0)
                trang.click('button[aria-label="Đóng xem trang"]')
                trang.wait_for_selector('.source-modal', state='detached', timeout=15_000)
                time.sleep(0.5)
            except PWTimeout:
                print('  (không mở được ảnh trang sách)')

        # ------------------------------------------------ 4. năn nỉ xin đáp án
        hoi(trang, NAN_NI, 14.0)
        chup(trang, '4_nan_ni_khong_lo_dap_an', cho=1.0)

        # ------------------------------------------------ 5. câu ngoài chương trình
        hoi(trang, NGOAI_CT, 6.0)
        chup(trang, '5_tu_choi_kien_thuc_ngoai_chuong_trinh', cho=1.0)

        # ------------------------------------------------ 6-7. luyện tập: mức độ khó, gợi ý, chấm
        nut = trang.locator('button:has-text("Bắt đầu luyện tập")')
        if nut.count():
            nut.first.click()
            print('  đang chờ Mimo soạn câu luyện tập...')
            try:
                trang.wait_for_selector('.quiz-card', timeout=90_000)
            except PWTimeout:
                print('  (không thấy câu luyện tập)')
            trang.locator('.adaptive-quiz-panel').scroll_into_view_if_needed()
            goi_y = trang.locator('.quiz-hint-btn')
            if goi_y.count():
                goi_y.first.click()
            chup(trang, '6_luyen_tap_muc_do_kho_va_goi_y', cho=1.0)
            trang.locator('.quiz-options button').first.click()
            trang.click('.quiz-submit')
            try:
                trang.wait_for_selector('.quiz-feedback', timeout=60_000)
                trang.locator('.quiz-feedback').scroll_into_view_if_needed()
            except PWTimeout:
                print('  (chưa thấy kết quả chấm)')
            chup(trang, '7_luyen_tap_cham_va_goi_y_bai_tiep', cho=1.5)
        else:
            print('  (không tìm thấy nút luyện tập)')

        ngu_canh.close()
        trinh_duyet.close()
    print(f'\nXong. Ảnh nằm trong {RA}')


if __name__ == '__main__':
    try:
        main()
    except Exception as loi:  # noqa: BLE001
        print(f'\nLỖI: {type(loi).__name__}: {loi}', file=sys.stderr)
        raise
