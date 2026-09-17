"""Vẽ slide chiếu trong video thuyết trình (khổ 1920x1080), chụp bằng Chrome headless.

Khác `illustrations.py`: hình ở đó là hình chèn vào hồ sơ Word, kích thước tùy nội dung.
Slide ở đây phải đúng khổ 16:9 và chữ đủ to để đọc trên màn hình.

Mỗi slide xuất ra nhiều bản dựng dần (b1, b2, ...) để lúc dựng video cắt cảnh theo lời nói.
Phần chưa tới chỉ bị làm trong suốt chứ không bị bỏ khỏi trang, nên bố cục không xê dịch.
"""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'bao-cao' / 'slides'
TMP = OUT / '_html'
OUT.mkdir(parents=True, exist_ok=True)
TMP.mkdir(exist_ok=True)
ICONS = ROOT / 'node_modules' / 'lucide-react' / 'dist' / 'esm' / 'icons'
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'

W, H = 1920, 1080
PAD = 72
INNER = W - 2 * PAD          # 1776
CORAL, NAVY = '#F2704F', '#1B2A4A'


def icon(name, size=28, stroke=2):
    source = (ICONS / f'{name}.mjs').read_text(encoding='utf-8')
    alias = re.search(r"export \{ default \} from '\./([\w-]+)\.mjs'", source)   # tên icon cũ trỏ sang tên mới
    if alias:
        source = (ICONS / f'{alias.group(1)}.mjs').read_text(encoding='utf-8')
    parts = []
    for tag, attrs in re.findall(r'\[\s*"(\w+)",\s*\{([^}]*)\}\s*\]', source):
        pairs = ' '.join(f'{k}="{v}"' for k, v in re.findall(r'(\w+): "([^"]*)"', attrs) if k != 'key')
        parts.append(f'<{tag} {pairs}/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
            f'stroke="currentColor" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round">{"".join(parts)}</svg>')


CSS = f'''
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; width: {W}px; height: {H}px; background: #fff; overflow: hidden; }}
body {{ font-family: 'Segoe UI', Arial, sans-serif; color: {NAVY}; }}
.slide {{ width: {W}px; height: {H}px; padding: {PAD}px; display: flex; flex-direction: column; }}
.ic {{ display: grid; place-items: center; border-radius: 26px; flex: none; }}
.coral {{ background: #FDE7E0; color: {CORAL}; }}
.navy {{ background: #E6EBF3; color: {NAVY}; }}
.green {{ background: #DDF3EA; color: #16875F; }}
.amber {{ background: #FDF1D6; color: #B7791F; }}
.violet {{ background: #ECE8FB; color: #6247C9; }}
.solid {{ background: {CORAL}; color: #fff; }}

.eyebrow {{ font-size: 24px; font-weight: 800; letter-spacing: .16em; color: {CORAL}; margin-bottom: 12px; }}
h1 {{ margin: 0; font-size: 58px; line-height: 1.12; letter-spacing: -.01em; }}
h1 em {{ font-style: normal; color: {CORAL}; }}

.band {{ margin-top: 34px; }}
.band-label {{ display: flex; align-items: center; gap: 14px; font-size: 23px; font-weight: 800;
  letter-spacing: .1em; color: #8E97A5; margin-bottom: 20px; }}
.band-label .tag {{ background: #F1F3F7; border-radius: 999px; padding: 7px 18px; font-size: 20px;
  letter-spacing: .04em; color: #6B7280; font-weight: 700; }}

.row {{ display: grid; grid-template-columns: 1fr 90px 1fr 90px 1fr 90px 1fr; align-items: start; }}
.arrow {{ color: #C3CAD5; display: grid; place-items: center; padding-top: 30px; }}
.node {{ display: flex; flex-direction: column; align-items: center; text-align: center; gap: 14px; }}
.node .ic {{ width: 104px; height: 104px; }}
.node h4 {{ margin: 0; font-size: 29px; line-height: 1.2; }}
.node p {{ margin: 0; font-size: 20px; line-height: 1.45; color: #4B5563; max-width: 330px; }}
.node.key h4 {{ color: {CORAL}; }}

.bypass {{ position: relative; height: 104px; }}
.bypass svg.path {{ position: absolute; left: 0; top: 0; }}
.bypass .stamp {{ position: absolute; display: flex; align-items: center; gap: 12px;
  background: #fff; padding: 0 16px; font-size: 25px; font-weight: 800; color: {CORAL}; }}
.bypass .stamp .x {{ display: grid; place-items: center; width: 44px; height: 44px; border-radius: 50%;
  background: {CORAL}; color: #fff; flex: none; }}

.foot {{ margin-top: auto; padding-top: 34px; display: flex; align-items: center; gap: 16px; }}
.chip {{ display: flex; align-items: center; gap: 12px; background: #FAFBFD; border: 2px solid #EEF1F6;
  border-radius: 999px; padding: 12px 24px; font-size: 22px; font-weight: 600; color: #4B5563; }}
.chip svg {{ color: #8E97A5; }}
.foot .note {{ margin-left: auto; font-size: 22px; color: #9AA3AF; }}
'''


def render(name, body, stage=None, last=99):
    """stage = bước đang hiện; mọi phần tử data-s lớn hơn bị ẩn nhưng vẫn giữ chỗ."""
    hide = ''
    if stage is not None and stage < last:
        sel = ', '.join(f'[data-s="{n}"]' for n in range(stage + 1, last + 1))
        hide = f'{sel} {{ opacity: 0; }}'
    html = TMP / f'{name}.html'
    html.write_text(f'<!doctype html><meta charset="utf-8"><style>{CSS}{hide}</style><body>{body}</body>',
                    encoding='utf-8')
    png = OUT / f'{name}.png'
    subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars',
                    '--force-device-scale-factor=1', f'--window-size={W},{H}',
                    f'--screenshot={png}', html.as_uri()], check=True, capture_output=True)
    print('ok', png.name)


# ---------------------------------------------------------------- Cảnh 4 · sơ đồ kiến trúc
def node(ic, tone, title, desc, s, key=False):
    return (f'<div class="node{" key" if key else ""}" data-s="{s}">'
            f'<div class="ic {tone}">{icon(ic, 52)}</div>'
            f'<h4>{title}</h4><p>{desc}</p></div>')


def row(cells):
    """cells: [(html, stage)] — mũi tên chen giữa mang stage của ô phía sau nó."""
    out = []
    for i, (html, s) in enumerate(cells):
        if i:
            out.append(f'<div class="arrow" data-s="{s}">{icon("arrow-right", 46, 2.5)}</div>')
        out.append(html)
    return f'<div class="row">{"".join(out)}</div>'


# tâm 4 cột của .row: mỗi cột rộng (INNER - 3*90) / 4
COL = (INNER - 3 * 90) / 4
CX = [COL / 2 + i * (COL + 90) for i in range(4)]

BYPASS = f'''<div class="bypass" data-s="4">
  <svg class="path" width="{INNER}" height="104" xmlns="http://www.w3.org/2000/svg">
    <defs><marker id="head" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M 0 1 L 9 5 L 0 9" fill="none" stroke="#C3CAD5" stroke-width="2"
            stroke-linecap="round" stroke-linejoin="round"/></marker></defs>
    <path d="M {CX[0]:.0f} 98 C {CX[0]:.0f} 16, {CX[2]:.0f} 16, {CX[2]:.0f} 96"
          fill="none" stroke="#C3CAD5" stroke-width="4" stroke-dasharray="12 12"
          stroke-linecap="round" marker-end="url(#head)"/>
  </svg>
  <div class="stamp" style="left: {CX[1] - 200:.0f}px; top: 2px">
    <span class="x">{icon('x', 26, 3)}</span><span>KHÔNG hỏi thẳng AI</span>
  </div>
</div>'''

SO_DO = f'''<div class="slide">
  <div data-s="1">
    <div class="eyebrow">CÁCH MIMO TRẢ LỜI</div>
    <h1>RAG — <em>tìm trong sách trước</em>, trả lời sau</h1>
  </div>

  <div class="band">
    <div class="band-label" data-s="2">CHUẨN BỊ KHO SÁCH <span class="tag">làm một lần</span></div>
    {row([
      (node('file-text', 'amber', 'Sách giáo khoa PDF', '29 cuốn · 5 môn · lớp 6 đến lớp 9', 2), 2),
      (node('scissors', 'violet', 'Tách trang, cắt đoạn', 'mỗi đoạn khoảng 1.000 ký tự', 2), 2),
      (node('layers', 'coral', 'Nhúng thành vector', 'Gemini Embedding', 2), 2),
      (node('database', 'green', 'Lưu vào Pinecone', '4.765 đoạn, kèm môn – lớp – bài – trang', 2), 2),
    ])}
  </div>

  <div class="band">
    <div class="band-label" data-s="3">KHI HỌC SINH HỎI <span class="tag">mỗi câu hỏi</span></div>
    {BYPASS}
    {row([
      (node('message-circle-question', 'navy', 'Câu hỏi của học sinh', 'gõ chữ, chụp ảnh đề hoặc nói', 3), 3),
      (node('search', 'green', 'Tìm trang sách liên quan', 'so nghĩa trong kho, lấy những đoạn sát nhất', 3, key=True), 3),
      (node('sparkles', 'solid', 'Gemini giảng bài', 'chỉ được dựa trên các trang vừa tìm, phải ghi rõ trang', 4), 4),
      (node('book-open-check', 'amber', 'Trả lời kèm trang sách', 'giảng từng bước, bấm nguồn là mở đúng trang', 4), 4),
    ])}
  </div>

  <div class="foot" data-s="5">
    <div class="chip">{icon('code-xml', 26)} Giao diện React</div>
    <div class="chip">{icon('server', 26)} Máy chủ FastAPI</div>
    <div class="chip">{icon('cloud', 26)} Chạy trên hạ tầng miễn phí</div>
    <div class="note">Mimo · Gia sư AI học theo sách giáo khoa</div>
  </div>
</div>'''

for step in range(1, 6):
    render(f'so_do_kien_truc_b{step}', SO_DO, stage=step, last=5)
render('so_do_kien_truc', SO_DO)

# ---------------------------------------------------------------- Cảnh 7 · slide kết
DOI = 'LD-14'
TRUONG = 'THCS Tân An Hội'
KHAU_HIEU = 'Học đúng sách, hiểu đúng bài.'

KET_CSS = f'''
.slide.dark {{ position: relative; background: {NAVY};
  background-image: radial-gradient(900px 620px at 82% 16%, rgba(242,112,79,.22), transparent 70%);
  color: #fff; align-items: center; justify-content: center; text-align: center; }}
.mark {{ width: 132px; height: 132px; border-radius: 38px; background: {CORAL}; color: #fff;
  display: grid; place-items: center; margin-bottom: 34px; }}
.brand {{ font-size: 132px; font-weight: 800; line-height: 1; letter-spacing: -.02em; }}
.tagline {{ font-size: 38px; color: rgba(255,255,255,.72); margin-top: 18px; }}
.rule {{ width: 120px; height: 4px; border-radius: 2px; background: rgba(255,255,255,.2); margin: 46px 0; }}
.slogan {{ font-size: 64px; font-weight: 700; color: {CORAL}; line-height: 1.2; }}
.team {{ font-size: 31px; color: rgba(255,255,255,.8); margin-top: 52px; }}
.team b {{ font-weight: 700; color: #fff; }}
.thanks {{ position: absolute; bottom: {PAD}px; font-size: 26px; color: rgba(255,255,255,.42); }}
'''

KET = f'''<div class="slide dark">
  <div class="mark">{icon('bot', 68)}</div>
  <div class="brand">Mimo</div>
  <div class="tagline">Gia sư AI học theo sách giáo khoa</div>
  <div class="rule"></div>
  <div class="slogan">{KHAU_HIEU}</div>
  <div class="team">Đội <b>{DOI}</b> · Trường {TRUONG}</div>
  <div class="thanks">Cảm ơn thầy cô đã lắng nghe</div>
</div>'''

CSS += KET_CSS
render('slide_ket', KET)
