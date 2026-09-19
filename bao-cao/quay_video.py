"""Quay sẵn từng cảnh của video demo, để lấy mẫu trước khi tự quay lại.

File này KHÔNG tự chạy theo gì cả: gọi tay, và phải nói rõ quay cảnh nào. Gọi trống thì nó chỉ
in ra danh sách cảnh rồi thoát, không mở trình duyệt, không ghi đè gì.

Mục đích là làm bản nháp cho từng cảnh trong bao-cao/KICH_BAN_VIDEO_DEMO.md: máy đi đúng đường
đi, đúng nhịp, đúng chỗ dừng, để xem lại mà biết cảnh đó dài bao nhiêu và dừng ở đâu. Bản nộp
thì tự quay lại bằng OBS hoặc Win+Alt+R, có chuột thật và có tiếng.

    .venv\\Scripts\\python.exe bao-cao\\quay_video.py              # xem danh sách cảnh
    .venv\\Scripts\\python.exe bao-cao\\quay_video.py 4            # quay riêng cảnh 4
    .venv\\Scripts\\python.exe bao-cao\\quay_video.py 3 4 7        # quay vài cảnh
    .venv\\Scripts\\python.exe bao-cao\\quay_video.py tat-ca       # quay cả chín cảnh

Tuỳ chọn:
    --phien-moi   tạo tài khoản demo mới thay vì dùng lại phiên đã lưu
    --nhanh       rút ngắn mọi quãng dừng, dùng khi chỉ muốn thử xem có kẹt selector không

Chuẩn bị giống hệt chup_anh.py: đặt VITE_API_BASE_URL trong .env.local, rồi
    npm run dev -- --host 127.0.0.1 --port 5173

HAI ĐIỀU PHẢI BIẾT TRƯỚC KHI DÙNG BẢN QUAY NÀY:

1. Video Playwright KHÔNG CÓ TIẾNG. Cảnh 6 là cảnh nghe Mimo đọc, nên bản quay ở đây chỉ cho
   thấy nút loa đổi trạng thái, không nghe được gì. Cảnh 6 bắt buộc phải tự quay có thu tiếng.
2. Chuột trong video là chuột vẽ thêm bằng JS, không phải con trỏ thật của Windows. Playwright
   bấm thẳng vào phần tử chứ không di chuột của hệ điều hành, nên nếu không vẽ thì màn hình tự
   nhảy, người xem không hiểu ai đang bấm. Chấm tròn này chạy tới đúng chỗ sắp bấm rồi mới bấm.
"""
from __future__ import annotations

import json
import shutil
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from playwright.sync_api import Locator, Page, TimeoutError as PWTimeout, sync_playwright

# Console Windows mặc định cp1252, in tiếng Việt có dấu là văng UnicodeEncodeError giữa chừng.
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

WEB = 'http://127.0.0.1:5173'
GOC = Path(__file__).resolve().parent
RA = GOC / 'video-tho'
PHIEN = RA / 'phien.json'

# 16:9 đúng chuẩn, quay 1:1 không co kéo nên chữ nét. Muốn 1080p thì đổi cả hai số ở đây lên
# 1920x1080; Playwright quay đúng bằng khổ khung nhìn, device_scale_factor không ăn vào video.
KHO = {'width': 1280, 'height': 720}

MATKHAU = 'MimoDemo-2026'
TEN = 'Minh Anh'
LOP = 8

# Cùng một bài với chup_anh.py, và cùng một lý do: Toán 8 tập một mà nhóm đang có là bản in đè
# watermark của bên thứ ba, quay vào là dính watermark suốt cảnh 4.
BAI = '25. Phương trình bậc nhất một ẩn'
CAU_HOI = 'Phương trình bậc nhất một ẩn là gì ạ? Cho em một ví dụ với.'

# Cảnh 5 cần một ảnh đề bài chụp sẵn. Không có thì cảnh đó báo thiếu rồi bỏ qua, chứ không quay
# ra một đoạn rỗng để lúc dựng mới phát hiện.
ANH_DE_BAI = GOC / 'anh-de-bai.png'

NHANH = False

# Mốc giây 0 của cảnh, do bat_dau() đặt. Đo từ lúc mở ngữ cảnh thì con số báo ra gồm cả đoạn dẫn
# đường còn bị bìa che — mà con số đó chính là thứ cả file này sinh ra để trả lời.
MOC_CANH: float | None = None


def cho(giay: float) -> None:
    """Dừng cho người xem kịp nhìn. Chỉ dùng cho quãng dừng có chủ ý, không dùng để chờ mạng."""
    time.sleep(giay * (0.3 if NHANH else 1.0))


# --------------------------------------------------------------------------- con trỏ vẽ thêm
# Cài bằng add_init_script để sống sót qua mọi lần chuyển trang: SPA không tải lại trang, nhưng
# lần goto đầu tiên thì có, mà cảnh nào cũng mở đầu bằng một lần goto.
CON_TRO = r"""
(() => {
  const dungTro = () => {
    let o = document.getElementById('mimo-tro');
    if (o) return o;
    if (!document.body) return null;
    o = document.createElement('div');
    o.id = 'mimo-tro';
    o.style.cssText = [
      'position:fixed', 'left:0', 'top:0', 'width:20px', 'height:20px',
      'margin:-10px 0 0 -10px', 'border-radius:50%',
      'background:rgba(15,23,42,.45)', 'border:2px solid #fff',
      'box-shadow:0 2px 12px rgba(0,0,0,.5)', 'z-index:2147483646',
      'pointer-events:none', 'transform:translate(-200px,-200px)',
      'transition:transform .45s cubic-bezier(.22,.61,.36,1)'
    ].join(';');
    document.body.appendChild(o);
    return o;
  };
  window.__tro = (x, y, ms) => {
    const o = dungTro();
    if (!o) return;
    o.style.transitionDuration = (ms / 1000) + 's';
    o.style.transform = 'translate(' + x + 'px,' + y + 'px)';
  };
  window.__nhay = () => {
    const o = dungTro();
    if (!o) return;
    const s = document.createElement('div');
    s.style.cssText = [
      'position:fixed', 'left:0', 'top:0', 'width:20px', 'height:20px',
      'margin:-10px 0 0 -10px', 'border-radius:50%', 'border:2px solid #f59e0b',
      'z-index:2147483645', 'pointer-events:none', 'opacity:.9',
      'transform:' + o.style.transform,
      'transition:opacity .5s ease-out,box-shadow .5s ease-out'
    ].join(';');
    document.body.appendChild(s);
    requestAnimationFrame(() => {
      s.style.opacity = '0';
      s.style.boxShadow = '0 0 0 18px rgba(245,158,11,0)';
    });
    setTimeout(() => s.remove(), 600);
  };
  // Tấm bìa che đoạn dẫn đường đầu mỗi cảnh: mở app, chờ mạng, cuộn về đúng chỗ. Không che thì
  // mỗi đoạn quay mở đầu bằng vài giây lộn xộn, lúc dựng lại phải ngồi cắt tay từng cái.
  window.__bia = (dong, phu) => {
    let b = document.getElementById('mimo-bia');
    if (!b) {
      b = document.createElement('div');
      b.id = 'mimo-bia';
      b.style.cssText = [
        'position:fixed', 'inset:0', 'z-index:2147483647', 'display:flex',
        'flex-direction:column', 'align-items:center', 'justify-content:center',
        'gap:10px', 'background:#0f172a', 'color:#f8fafc', 'opacity:1',
        'transition:opacity .45s ease', 'pointer-events:none',
        'font-family:system-ui,Segoe UI,sans-serif'
      ].join(';');
      document.body.appendChild(b);
    }
    b.style.opacity = '1';
    b.innerHTML = '';
    const a = document.createElement('div');
    a.textContent = dong;
    a.style.cssText = 'font-size:15px;letter-spacing:.22em;text-transform:uppercase;color:#94a3b8';
    const c = document.createElement('div');
    c.textContent = phu;
    c.style.cssText = 'font-size:30px;font-weight:600';
    b.append(a, c);
  };
  window.__mo_bia = () => {
    const b = document.getElementById('mimo-bia');
    if (b) b.style.opacity = '0';
  };
})()
"""


def khong_dau(chu: str) -> str:
    """Bỏ dấu để đặt tên tệp. Premiere, CapCut và cả trình tải lên đều còn vấp tên tệp có dấu."""
    tach = unicodedata.normalize('NFD', chu.replace('đ', 'd').replace('Đ', 'D'))
    goi = ''.join(k for k in tach if unicodedata.category(k) != 'Mn').lower()
    return ''.join(k if k.isalnum() else '_' for k in goi).strip('_')


def bat_dau(trang: Page) -> None:
    """Hạ tấm bìa xuống. Gọi khi màn hình đã vào đúng tư thế — đây là giây 0 của cảnh."""
    global MOC_CANH
    trang.evaluate('() => window.__mo_bia && window.__mo_bia()')
    cho(0.6)
    MOC_CANH = time.time()


def tro_toi(trang: Page, dich: Locator, ms: int = 450) -> bool:
    """Đưa cả chấm tròn lẫn chuột thật tới giữa phần tử.

    Phải di chuột thật nữa, không chỉ vẽ: những chỗ chỉ hiện khi rê chuột (nút ẩn trên bong bóng
    trả lời, dòng chữ nhỏ dưới mỗi bài) mà chỉ vẽ chấm tròn thì quay ra không thấy gì.
    """
    try:
        dich.scroll_into_view_if_needed(timeout=10_000)
    except PWTimeout:
        return False
    hop = dich.bounding_box()
    if not hop:
        return False
    x = hop['x'] + hop['width'] / 2
    y = hop['y'] + hop['height'] / 2
    trang.evaluate('([x, y, ms]) => window.__tro(x, y, ms)', [x, y, ms])
    trang.mouse.move(x, y)
    time.sleep(ms / 1000 + 0.15)
    return True


def bam(trang: Page, dich: Locator, nghi: float = 0.5) -> bool:
    if not tro_toi(trang, dich):
        return False
    trang.evaluate('() => window.__nhay()')
    time.sleep(0.15)
    dich.click()
    cho(nghi)
    return True


def bam_chu(trang: Page, chu: str, nghi: float = 0.5) -> bool:
    return bam(trang, trang.locator(f'text={chu}').first, nghi)


def go(trang: Page, o: Locator, chu: str, cham: int = 55) -> None:
    """Gõ từng ký tự. fill() điền xong trong một khung hình, quay ra không ai thấy là đang gõ."""
    tro_toi(trang, o)
    trang.evaluate('() => window.__nhay()')
    o.click()
    o.press_sequentially(chu, delay=8 if NHANH else cham)


def cuon(trang: Page, tong: int, buoc: int = 28, nghi: float = 0.14) -> None:
    """Cuộn thành nhiều nhịp nhỏ. Một cú wheel lớn nhảy phựt một cái, nhìn như lỗi."""
    huong = 1 if tong > 0 else -1
    da = 0
    while abs(da) < abs(tong):
        trang.mouse.wheel(0, buoc * huong)
        da += buoc * huong
        time.sleep(nghi if not NHANH else 0.01)


def vao_muc(trang: Page, ten: str) -> None:
    bam(trang, trang.locator(f'nav >> text={ten}').first, nghi=0.3)
    trang.wait_for_load_state('networkidle')


def cho_tra_loi(trang: Page, han: int = 90_000) -> None:
    """Chờ Mimo trả lời xong: số trích dẫn [1] hiện ra là dấu hiệu chắc nhất."""
    try:
        trang.wait_for_selector('.cite-ref, .source-thumbs', timeout=han)
    except PWTimeout:
        print('  (không thấy số trích dẫn — vẫn quay tiếp phần nhìn thấy được)')
    # Chờ nốt ảnh nhỏ của trang sách tải xong, để trong video không còn ô xám đang tải.
    try:
        trang.wait_for_function(
            "() => [...document.querySelectorAll('.source-thumbs img')]"
            ".every(a => a.complete && a.naturalWidth > 0)", timeout=60_000)
    except PWTimeout:
        pass


# --------------------------------------------------------------------------- danh sách cảnh
@dataclass
class Canh:
    so: int
    ten: str
    giay: int
    chay: Callable[[Page], None]
    can_phien: bool
    can_web: bool


DS: list[Canh] = []


def canh(so: int, ten: str, giay: int, can_phien: bool = True, can_web: bool = True):
    def boc(f):
        DS.append(Canh(so, ten, giay, f, can_phien, can_web))
        return f
    return boc


SLIDE = """
<!doctype html><meta charset="utf-8">
<style>
 html,body{margin:0;height:100%%}
 body{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px;
      background:#0f172a;color:#f8fafc;font-family:system-ui,'Segoe UI',sans-serif;text-align:center}
 .to{font-size:%(co)spx;font-weight:600;max-width:78%%;line-height:1.35}
 .nho{font-size:19px;color:#94a3b8;max-width:70%%;line-height:1.6}
 .vach{width:56px;height:3px;background:#f59e0b;border-radius:2px}
</style>
<div class="to">%(to)s</div><div class="vach"></div><div class="nho">%(nho)s</div>
"""


@canh(1, 'Nhan đề', 4, can_phien=False, can_web=False)
def canh_1(trang: Page) -> None:
    trang.set_content(SLIDE % {
        'co': 40,
        'to': 'Mimo — Gia sư AI trả lời theo đúng trang sách giáo khoa',
        'nho': 'Sau đây là sản phẩm chạy thật.',
    })
    cho(4)


@canh(2, 'Đăng nhập và khảo sát', 16, can_phien=False)
def canh_2(trang: Page) -> None:
    # Cảnh này bắt buộc dùng tài khoản mới tinh: ba bước khảo sát chỉ hiện với người lần đầu vào.
    email = f'minh.anh.demo+{datetime.now():%m%d%H%M%S}@example.com'
    print(f'  tài khoản cho cảnh này: {email}')
    trang.goto(WEB, wait_until='networkidle')
    trang.wait_for_selector('text=Không gian học tập')
    bat_dau(trang)

    bam_chu(trang, 'Tạo tài khoản mới')
    trang.wait_for_selector('h2:has-text("Tạo tài khoản")')
    go(trang, trang.locator('input[placeholder="Ví dụ: Minh Anh"]'), TEN, cham=40)
    go(trang, trang.locator('input[type="email"]'), email, cham=22)
    go(trang, trang.locator('input[placeholder="Ít nhất 6 ký tự"]'), MATKHAU, cham=30)
    go(trang, trang.locator('label:has-text("Nhập lại mật khẩu") input'), MATKHAU, cham=30)
    trang.select_option('label:has-text("Lớp hiện tại") select', str(LOP))
    cho(0.8)
    bam(trang, trang.locator('button[type="submit"]'))

    trang.wait_for_selector('h1:has-text("em muốn học môn nào")')
    cho(1.0)
    bam_chu(trang, 'Toán')
    bam_chu(trang, 'Tiếp tục')

    trang.wait_for_selector('h1:has-text("Mục tiêu của em")')
    cho(1.0)
    bam_chu(trang, '45 phút')
    bam_chu(trang, 'Tiếp tục')

    trang.wait_for_selector('h1:has-text("Thiết lập lộ trình")')
    cho(1.0)
    bam_chu(trang, 'Tạo lộ trình cho mình')
    print('  đang chờ Mimo dựng lộ trình — đoạn này lúc dựng nhớ tua nhanh 2x...')
    trang.wait_for_selector('nav >> text=Trang chủ', timeout=150_000)
    trang.wait_for_load_state('networkidle')
    cho(2.5)


@canh(3, 'Lộ trình học', 18)
def canh_3(trang: Page) -> None:
    vao_muc(trang, 'Lộ trình học')
    bat_dau(trang)

    cuon(trang, 700)
    cho(1.5)

    # Chỗ phải cho người xem nhìn thấy: dòng chữ nhỏ ghi tên sách và số trang dưới mỗi bài.
    hang = trang.locator(f'.lesson-row:has(strong:text-is("{BAI}"))')
    if not hang.count():
        print(f'  (không thấy bài "{BAI}" trong lộ trình — lấy tạm bài đầu tiên)')
        hang = trang.locator('.lesson-row').first
    tro_toi(trang, hang.locator('small').first, ms=800)
    cho(3.5)
    bam(trang, hang.locator('button').last, nghi=0.4)

    trang.wait_for_load_state('networkidle')
    cho(3.0)


@canh(4, 'Hỏi Mimo', 50)
def canh_4(trang: Page) -> None:
    vao_muc(trang, 'Hỏi Mimo')
    # Mở cuộc trò chuyện mới để cảnh quan trọng nhất bắt đầu trên khung sạch, không vướng lịch sử.
    # Phải dùng .new-chat-btn trong cột trái: nút có aria-label cùng tên là nút icon của bản hẹp,
    # ở khổ quay này nó nằm trong DOM nhưng CSS ẩn đi, bấm vào là treo cho tới hết hạn chờ.
    moi = trang.locator('button.new-chat-btn')
    if moi.count() and moi.first.is_visible():
        bam(trang, moi.first, nghi=0.3)
        trang.wait_for_load_state('networkidle')
    cho(0.8)
    bat_dau(trang)

    # 4a — gõ câu hỏi, cho thấy từng chữ.
    go(trang, trang.locator('textarea').first, CAU_HOI, cham=75)
    cho(1.2)
    trang.locator('textarea').first.press('Enter')

    # 4b — câu trả lời chạy ra.
    print('  đang chờ Mimo trả lời...')
    cho_tra_loi(trang)
    cho(10.0)

    # 4c — cuộn xuống chỗ trích nguồn rồi phóng nhẹ vào đó.
    nguon = trang.locator('.source-thumbs').first
    if nguon.count():
        nguon.scroll_into_view_if_needed()
        cho(1.5)
        trang.evaluate("""() => {
          const o = document.querySelector('.source-thumbs');
          if (!o) return;
          o.style.transition = 'transform .8s ease';
          o.style.transformOrigin = 'center';
          o.style.transform = 'scale(1.22)';
        }""")
        cho(6.0)
        trang.evaluate("""() => {
          const o = document.querySelector('.source-thumbs');
          if (o) o.style.transform = 'scale(1)';
        }""")
        cho(1.2)

    # 4d — mở trang sách thật, giữ nguyên 6 giây, không động vào.
    so = trang.locator('.cite-ref:not([disabled])').first
    if not so.count():
        so = trang.locator('.source-thumbs button, .source-thumbs img').first
    if not so.count():
        print('  (câu trả lời này không có nguồn bấm xem được — quay lại cảnh 4 với câu khác)')
        cho(1.0)
        return
    try:
        bam(trang, so, nghi=0.2)
        trang.wait_for_selector('.source-modal', timeout=20_000)
        # networkidle chưa đủ: ảnh trang đi qua một cú chuyển hướng sang Supabase, phải chờ đúng
        # thẻ <img> báo đã tải xong, không thì quay phải khung xám.
        trang.wait_for_function(
            "() => { const a = document.querySelector('.source-modal img');"
            " return a && a.complete && a.naturalWidth > 0 }", timeout=60_000)
        cho(9.0)
        # Modal không đóng bằng Escape; phải bấm nút X.
        trang.click('button[aria-label="Đóng xem trang"]')
        trang.wait_for_selector('.source-modal', state='detached', timeout=15_000)
    except PWTimeout:
        print('  (không mở được ảnh trang sách)')
    cho(1.0)


@canh(5, 'Hỏi bằng ảnh chụp', 22)
def canh_5(trang: Page) -> None:
    if not ANH_DE_BAI.exists():
        print(f'  THIẾU ẢNH: đặt ảnh đề bài đã chụp vào {ANH_DE_BAI} rồi chạy lại cảnh 5.')
        return
    vao_muc(trang, 'Hỏi Mimo')
    cho(0.8)
    bat_dau(trang)

    # Ô chọn tệp bị ẩn, nút kẹp giấy mới là thứ người xem thấy: đưa chuột tới đó trước cho hiểu
    # chuyện, rồi mới nạp tệp thẳng vào input.
    tro_toi(trang, trang.locator('button[title="Tải hoặc chụp ảnh đề bài"]'), ms=600)
    trang.evaluate('() => window.__nhay()')
    cho(0.6)
    trang.locator('input[type="file"]').set_input_files(str(ANH_DE_BAI))
    cho(3.0)  # để người xem kịp nhìn ảnh đề bài trước khi câu trả lời đè lên

    trang.locator('textarea').first.press('Enter')
    print('  đang chờ Mimo đọc ảnh đề bài...')
    cho_tra_loi(trang, han=120_000)
    cho(5.0)


@canh(6, 'Nghe Mimo đọc', 12)
def canh_6(trang: Page) -> None:
    print('  ⚠ Bản quay này KHÔNG CÓ TIẾNG — cảnh 6 bắt buộc phải tự quay lại có thu tiếng.')
    vao_muc(trang, 'Hỏi Mimo')
    trang.wait_for_load_state('networkidle')
    cho(1.0)
    loa = trang.locator('button[title="Nghe giảng"]').last
    if not loa.count():
        print('  (chưa có câu trả lời nào trong cuộc trò chuyện này — chạy cảnh 4 trước)')
        return
    bat_dau(trang)
    bam(trang, loa, nghi=0.3)
    cho(8.0)


@canh(7, 'Luyện tập', 24)
def canh_7(trang: Page) -> None:
    vao_muc(trang, 'Hỏi Mimo')
    cho(0.8)
    bat_dau(trang)

    for nhan in ('Bắt đầu luyện tập', 'Làm bài luyện tập', 'Luyện tập'):
        nut = trang.locator(f'button:has-text("{nhan}")')
        if nut.count():
            bam(trang, nut.first, nghi=0.3)
            break
    else:
        print('  (không tìm thấy nút luyện tập)')
        return

    print('  đang chờ Mimo soạn câu luyện tập...')
    try:
        trang.wait_for_selector('.quiz-card', timeout=90_000)
    except PWTimeout:
        print('  (Mimo chưa soạn kịp câu luyện tập)')
        return
    trang.locator('.quiz-card').first.scroll_into_view_if_needed()
    cho(2.5)

    # Xin gợi ý trước khi chọn: đúng ý kịch bản — bí thì xin gợi ý, không phải xem đáp án.
    goi_y = trang.locator('.quiz-hint-btn')
    if goi_y.count():
        bam(trang, goi_y.first, nghi=0.4)
        cho(3.5)

    phuong_an = trang.locator('.quiz-options button')
    if phuong_an.count():
        bam(trang, phuong_an.first, nghi=0.8)
    nop = trang.locator('button.quiz-submit')
    if nop.count():
        bam(trang, nop.first, nghi=0.3)
    try:
        trang.wait_for_selector('.quiz-feedback', timeout=60_000)
    except PWTimeout:
        print('  (chưa thấy phần chấm bài)')
        return
    trang.locator('.quiz-feedback').first.scroll_into_view_if_needed()
    cho(5.0)


@canh(8, 'Pomodoro và hồ sơ', 18)
def canh_8(trang: Page) -> None:
    vao_muc(trang, 'Pomodoro')
    cho(0.8)
    bat_dau(trang)

    muc_25 = trang.locator('button:has-text("25 + 5 phút")')
    if muc_25.count():
        bam(trang, muc_25.first, nghi=0.6)
    chay = trang.locator('button:has-text("Bắt đầu")').first
    if chay.count():
        bam(trang, chay, nghi=0.3)
    cho(4.5)  # lúc dựng thì tua nhanh đoạn đồng hồ đang chạy

    vao_muc(trang, 'Hồ sơ')
    cho(1.2)
    cuon(trang, 380)
    cho(3.0)

    # Nút 👍 nằm trên một câu trả lời bên Hỏi Mimo, không nằm ở trang Hồ sơ.
    vao_muc(trang, 'Hỏi Mimo')
    cho(1.0)
    thich = trang.locator('button[title="Thích"]').last
    if not thich.count():
        print('  (chưa có câu trả lời nào để bấm 👍 — chạy cảnh 4 trước)')
        return
    bam(trang, thich, nghi=0.3)
    cho(2.5)


@canh(9, 'Kết', 6, can_phien=False, can_web=False)
def canh_9(trang: Page) -> None:
    trang.set_content(SLIDE % {
        'co': 30,
        'to': 'React (Vercel) → FastAPI (Render) → Pinecone + Gemini → PDF sách giáo khoa',
        'nho': 'Toàn bộ hệ thống chạy trên hạ tầng miễn phí.',
    })
    cho(6)


# --------------------------------------------------------------------------- dựng phiên demo
def dung_phien(trinh_duyet, lam_moi: bool) -> Path:
    """Tạo sẵn một tài khoản đã có lộ trình và đã hỏi một câu, lưu lại để các cảnh dùng chung.

    Phần này KHÔNG quay: nó là đoạn dựng bối cảnh, mà quay vào thì cảnh nào cũng mở đầu bằng hai
    phút đăng ký tài khoản. Lưu ra tệp để chạy lại cảnh khác thì khỏi dựng lại từ đầu — quay đi
    quay lại một cảnh cho vừa ý là chuyện thường.
    """
    if PHIEN.exists() and not lam_moi:
        print(f'Dùng lại phiên đã lưu ({PHIEN.name}). Muốn tài khoản mới thì thêm --phien-moi.')
        return PHIEN

    email = f'minh.anh.demo+{datetime.now():%m%d%H%M%S}@example.com'
    print(f'Dựng phiên demo mới · {email} (không quay đoạn này)')
    ngu_canh = trinh_duyet.new_context(viewport=KHO, locale='vi-VN')
    trang = ngu_canh.new_page()
    trang.set_default_timeout(60_000)

    trang.goto(WEB, wait_until='networkidle')
    trang.wait_for_selector('text=Không gian học tập')
    trang.click('button:has-text("Tạo tài khoản mới")')
    trang.wait_for_selector('h2:has-text("Tạo tài khoản")')
    trang.fill('input[placeholder="Ví dụ: Minh Anh"]', TEN)
    trang.fill('input[type="email"]', email)
    trang.fill('input[placeholder="Ít nhất 6 ký tự"]', MATKHAU)
    trang.fill('label:has-text("Nhập lại mật khẩu") input', MATKHAU)
    trang.select_option('label:has-text("Lớp hiện tại") select', str(LOP))
    trang.click('button[type="submit"]')

    trang.wait_for_selector('h1:has-text("em muốn học môn nào")')
    trang.click('button:has-text("Toán")')
    trang.click('button:has-text("Tiếp tục")')
    trang.wait_for_selector('h1:has-text("Mục tiêu của em")')
    trang.click('button:has-text("45 phút")')
    trang.click('button:has-text("Tiếp tục")')
    trang.wait_for_selector('h1:has-text("Thiết lập lộ trình")')
    trang.click('button:has-text("Tạo lộ trình cho mình")')
    print('  chờ dựng lộ trình...')
    trang.wait_for_selector('nav >> text=Trang chủ', timeout=150_000)
    trang.wait_for_load_state('networkidle')

    # Chọn đúng bài, để cảnh nào cũng nói về một bài.
    trang.click('nav >> text=Lộ trình học')
    trang.wait_for_load_state('networkidle')
    hang = trang.locator(f'.lesson-row:has(strong:text-is("{BAI}"))')
    try:
        hang.scroll_into_view_if_needed(timeout=15_000)
        hang.locator('button').last.click()
        trang.wait_for_load_state('networkidle')
    except PWTimeout:
        print(f'  (không thấy bài "{BAI}" — phiên này để nguyên bài mặc định)')

    # Hỏi sẵn một câu: cảnh 6 cần có câu trả lời để bấm nút loa, cảnh 8 cần có để bấm 👍.
    trang.click('nav >> text=Hỏi Mimo')
    trang.wait_for_load_state('networkidle')
    trang.locator('textarea').first.fill(CAU_HOI)
    trang.locator('textarea').first.press('Enter')
    print('  chờ câu trả lời đầu tiên...')
    cho_tra_loi(trang, han=120_000)

    RA.mkdir(parents=True, exist_ok=True)
    ngu_canh.storage_state(path=str(PHIEN))
    ngu_canh.close()
    print(f'  đã lưu phiên vào {PHIEN}')
    return PHIEN


def quay(trinh_duyet, c: Canh, phien: Path | None) -> None:
    print(f'\n▶ Cảnh {c.so} — {c.ten} (kịch bản: {c.giay} giây)')
    tuy = {'viewport': KHO, 'locale': 'vi-VN',
           'record_video_dir': str(RA), 'record_video_size': KHO}
    if phien is not None:
        tuy['storage_state'] = str(phien)
    ngu_canh = trinh_duyet.new_context(**tuy)
    trang = ngu_canh.new_page()
    trang.set_default_timeout(60_000)
    trang.add_init_script(CON_TRO)
    if c.can_web:
        # Bìa phải tự dựng ngay trong khung hình đầu, không đợi Python gọi: gọi từ đây thì phải
        # chờ goto() xong mới che được, mà lúc đó app đã loé lên vài giây trong đoạn quay rồi.
        trang.add_init_script(
            '(() => { const d = () => window.__bia && window.__bia(%s, %s);'
            " if (document.readyState === 'loading')"
            " addEventListener('DOMContentLoaded', d); else d(); })()"
            % (json.dumps(f'Cảnh {c.so}'), json.dumps(c.ten)))

    if c.can_phien:
        trang.goto(WEB, wait_until='networkidle')
        try:
            trang.wait_for_selector('nav >> text=Trang chủ', timeout=30_000)
        except PWTimeout:
            print('  Phiên đã lưu không còn đăng nhập được (backend dựng lại DB?).'
                  ' Chạy lại với --phien-moi.')
            ngu_canh.close()
            return

    global MOC_CANH
    MOC_CANH = None
    mo_luc = time.time()
    try:
        c.chay(trang)
    except PWTimeout as loi:
        print(f'  Kẹt: {loi}')
    xong_luc = time.time()

    phim = trang.video
    ngu_canh.close()  # phải đóng ngữ cảnh thì Playwright mới ghi xong tệp video

    if phim is None:
        print('  (không có video)')
        return
    dich = RA / f'canh_{c.so}_{khong_dau(c.ten)}.webm'
    if dich.exists():
        dich.unlink()
    shutil.move(phim.path(), str(dich))

    print(f'  → {dich.name}')
    if MOC_CANH is None:
        # Chưa kịp hạ bìa nghĩa là cảnh chết ngay ở đoạn dẫn đường. Nói thẳng, đừng in ra một con
        # số "dài bao nhiêu giây" trông như thật cho một tệp chỉ toàn tấm bìa.
        print(f'    CẢNH KHÔNG CHẠY ĐƯỢC — kẹt {xong_luc - mo_luc:.0f} giây ở đoạn dẫn đường,'
              ' tệp chỉ có tấm bìa. Xem dòng "Kẹt:" ở trên để biết vướng ở đâu.')
        return
    # Đo từ lúc hạ bìa. Đoạn dẫn đường trước đó vẫn nằm trong tệp nhưng không phải là cảnh, tính
    # vào thì cảnh nào cũng "dài hơn kịch bản" mà không biết dài ở đâu.
    bia = MOC_CANH - mo_luc
    dai = xong_luc - MOC_CANH
    print(f'    bìa {bia:.0f} giây, rồi cảnh dài {dai:.0f} giây '
          f'({dai - c.giay:+.0f} so với kịch bản {c.giay} giây)')
    print(f'    cắt từ giây {bia:.0f} của tệp là vào đúng đầu cảnh')


def dia_chi_api() -> str:
    """Backend mà trình duyệt sẽ gọi — phải đọc từ .env.local, không đoán.

    Đặt VITE_API_BASE_URL thì app gọi thẳng địa chỉ đó; để trống thì gọi /api rồi Vite chuyển tiếp
    sang FastAPI ở máy. Kiểm tra nhầm chỗ là báo "backend chết" trong khi app vẫn chạy ngon.
    """
    for ten in ('.env.local', '.env'):
        tep = GOC.parent / ten
        if not tep.exists():
            continue
        for dong in tep.read_text(encoding='utf-8').splitlines():
            dong = dong.strip()
            if dong.startswith('VITE_API_BASE_URL='):
                dia = dong.split('=', 1)[1].strip().strip('"\'').rstrip('/')
                if dia:
                    return dia
    return WEB


def kiem_tra_truoc(can_web: bool, can_backend: bool) -> bool:
    """Kiểm tra web và backend trước khi mở trình duyệt.

    Quay hỏng vì backend chưa chạy là kiểu hỏng tốn nhất: mất mấy phút mới biết, mà đoạn quay ra
    trông vẫn như thật, chỉ là mọi câu trả lời đều lỗi.
    """
    if not can_web:
        return True
    try:
        urllib.request.urlopen(WEB, timeout=5).read(1)
    except (urllib.error.URLError, OSError):
        print(f'Chưa mở được {WEB}. Chạy trước:\n'
              '  npm run dev -- --host 127.0.0.1 --port 5173')
        return False
    if not can_backend:
        return True
    api = dia_chi_api()
    print(f'Backend: {api}' + ('  (Render — nhớ là lần gọi đầu có thể chậm vì phải đánh thức)'
                               if 'onrender.com' in api else ''))
    try:
        # Render ngủ thì lần đánh thức đầu tiên mất tới gần một phút, đừng vội kết luận là chết.
        urllib.request.urlopen(f'{api}/api/health', timeout=90).read(1)
    except (urllib.error.URLError, OSError):
        print('Web chạy nhưng backend không trả lời. Chọn một trong hai:\n'
              '  · Đặt VITE_API_BASE_URL=https://gia-su-ai-api.onrender.com trong .env.local\n'
              '    rồi khởi động lại Vite — nên dùng cách này, vì quay đúng bản đã triển khai\n'
              '  · Hoặc chạy backend ở máy bằng uvicorn, nếu muốn quay bản đang sửa dở')
        return False
    return True


def in_danh_sach() -> None:
    print('Các cảnh quay được (theo bao-cao/KICH_BAN_VIDEO_DEMO.md):\n')
    for c in sorted(DS, key=lambda x: x.so):
        ghi = '' if c.can_phien else '  · không cần tài khoản'
        print(f'  {c.so}  {c.ten:<24} {c.giay:>3} giây{ghi}')
    print('\nGọi tên cảnh muốn quay, ví dụ:')
    print('  .venv\\Scripts\\python.exe bao-cao\\quay_video.py 4')
    print('  .venv\\Scripts\\python.exe bao-cao\\quay_video.py 3 4 7')
    print('  .venv\\Scripts\\python.exe bao-cao\\quay_video.py tat-ca')
    print('\nKhông gọi cảnh nào thì không quay gì — file này không tự chạy.')


def main() -> None:
    global NHANH
    tham_so = sys.argv[1:]
    lam_moi = '--phien-moi' in tham_so
    NHANH = '--nhanh' in tham_so
    da_chon = [t for t in tham_so if not t.startswith('--')]

    if not da_chon:
        in_danh_sach()
        return

    thu_tu = sorted(DS, key=lambda x: x.so)
    if 'tat-ca' in da_chon:
        chon = thu_tu
    else:
        muon = []
        for t in da_chon:
            if not t.isdigit():
                print(f'Không hiểu "{t}". Gọi bằng số cảnh, hoặc tat-ca.')
                return
            muon.append(int(t))
        chon = [c for c in thu_tu if c.so in muon]
        thieu = sorted(set(muon) - {c.so for c in chon})
        if thieu:
            print(f'Không có cảnh: {thieu}')
            return

    if not kiem_tra_truoc(any(c.can_web for c in chon),
                          any(c.can_phien for c in chon)):
        return

    RA.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        trinh_duyet = p.chromium.launch(channel='chrome')
        phien = dung_phien(trinh_duyet, lam_moi) if any(c.can_phien for c in chon) else None
        for c in chon:
            quay(trinh_duyet, c, phien if c.can_phien else None)
        trinh_duyet.close()

    print(f'\nXong. Bản nháp nằm trong {RA}')
    print('Nhớ: video không có tiếng, và chuột là chuột vẽ. Bản nộp thì tự quay lại.')


if __name__ == '__main__':
    main()
