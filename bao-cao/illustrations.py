"""Vẽ hình minh họa cho hồ sơ bằng HTML + icon Lucide, chụp thành PNG bằng Chrome headless."""
import re
import subprocess
from pathlib import Path

import matplotlib.image as mpimg

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'bao-cao' / 'hinh-minh-hoa'
TMP = OUT / '_html'
OUT.mkdir(parents=True, exist_ok=True)
TMP.mkdir(exist_ok=True)
ICONS = ROOT / 'node_modules' / 'lucide-react' / 'dist' / 'esm' / 'icons'
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
SHOTS = ROOT / 'Anh_cac_giai_doan'

CORAL, NAVY = '#F2704F', '#1B2A4A'


def icon(name, size=28, stroke=2):
    source = (ICONS / f'{name}.mjs').read_text(encoding='utf-8')
    parts = []
    for tag, attrs in re.findall(r'\[\s*"(\w+)",\s*\{([^}]*)\}\s*\]', source):
        pairs = ' '.join(f'{k}="{v}"' for k, v in re.findall(r'(\w+): "([^"]*)"', attrs) if k != 'key')
        parts.append(f'<{tag} {pairs}/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
            f'stroke="currentColor" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round">{"".join(parts)}</svg>')


BASE_CSS = f'''
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; background: #fff; }}
body {{ font-family: 'Segoe UI', Arial, sans-serif; color: {NAVY}; }}
.canvas {{ padding: 32px; }}
.ic {{ display: grid; place-items: center; border-radius: 18px; flex: none; }}
.coral {{ background: #FDE7E0; color: {CORAL}; }}
.navy {{ background: #E6EBF3; color: {NAVY}; }}
.green {{ background: #DDF3EA; color: #16875F; }}
.amber {{ background: #FDF1D6; color: #B7791F; }}
.violet {{ background: #ECE8FB; color: #6247C9; }}
.solid {{ background: {CORAL}; color: #fff; }}
h3 {{ margin: 0; font-size: 22px; }}
p {{ margin: 0; }}
'''


def render(name, width, height, body, css=''):
    html = TMP / f'{name}.html'
    html.write_text(f'<!doctype html><meta charset="utf-8"><style>{BASE_CSS}{css}</style><body>{body}</body>', encoding='utf-8')
    png = OUT / f'{name}.png'
    subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--force-device-scale-factor=2',
                    f'--window-size={width},{height}', f'--screenshot={png}', html.as_uri()],
                   check=True, capture_output=True)
    print('ok', png.name)
    return png


# ---------------------------------------------------------------- 1. vấn đề
def card_row(items, cols):
    cells = ''.join(f'''
      <div class="card">
        <div class="ic {tone}" style="width:76px;height:76px">{icon(ic, 38)}</div>
        <h3>{title}</h3><p>{text}</p>
      </div>''' for ic, tone, title, text in items)
    return f'<div class="canvas"><div class="row" style="grid-template-columns:repeat({cols},1fr)">{cells}</div></div>'


CARD_CSS = '''
.row { display: grid; gap: 24px; }
.card { background: #FAFBFD; border: 2px solid #EEF1F6; border-radius: 26px; padding: 28px; display: flex; flex-direction: column; gap: 14px; }
.card p { font-size: 18px; line-height: 1.5; color: #4B5563; }
'''

render('van_de', 1300, 310, card_row([
    ('copy', 'coral', 'Chép đáp án cho xong', 'Chatbot giải luôn cả bài. Làm xong bài tập nhưng gặp dạng tương tự vẫn bí.'),
    ('book-x', 'amber', 'Lệch sách giáo khoa', 'Thuật ngữ, cách giải khác sách đang học, có khi dùng kiến thức lớp trên.'),
    ('shield-alert', 'violet', 'Không ai để ý khi em buồn', 'Bạn nhắn chuyện bị bắt nạt cũng không chắc được chỉ tới người lớn giúp đỡ.'),
], 3), CARD_CSS)

# ---------------------------------------------------------------- 2. đối tượng
render('doi_tuong', 1300, 340, card_row([
    ('graduation-cap', 'solid', 'Học sinh lớp 6 – 9', 'Hỏi bài lúc tự học ở nhà, hiểu cách làm, luyện tập vừa sức để không nản.'),
    ('house', 'navy', 'Phụ huynh', 'Con có người kèm bài miễn phí, không làm bài hộ, biết khuyên con tìm người lớn khi cần.'),
    ('school', 'green', 'Thầy cô', 'Học sinh ôn đúng nội dung, đúng thuật ngữ trong sách; biết các em hay vướng ở đâu.'),
], 3), CARD_CSS)

# ---------------------------------------------------------------- 3. công cụ
TOOL_CSS = CARD_CSS + '''
.label { font-size: 17px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: #9AA3AF; margin: 0 0 14px 4px; }
.tile { display: flex; gap: 18px; align-items: flex-start; background: #FAFBFD; border: 2px solid #EEF1F6; border-radius: 22px; padding: 20px; }
.tile h4 { margin: 0 0 6px; font-size: 20px; }
.tile p { font-size: 16px; line-height: 1.45; color: #4B5563; }
.grid3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; }
'''


def tiles(items):
    return ''.join(f'''<div class="tile"><div class="ic {tone}" style="width:62px;height:62px">{icon(ic, 30)}</div>
      <div><h4>{title}</h4><p>{text}</p></div></div>''' for ic, tone, title, text in items)


render('cong_cu', 1300, 560, f'''<div class="canvas">
  <div class="label">Dữ liệu và AI bên trong Mimo</div>
  <div class="grid3">{tiles([
    ('library', 'amber', 'Sách giáo khoa', 'Toán 6, Toán 8 tập một và KHTN 6, bộ Kết nối tri thức'),
    ('scan-line', 'navy', 'OCR', 'Đọc chữ từ các trang sách scan'),
    ('layers', 'violet', 'Gemini Embedding', 'Biến đoạn sách và câu hỏi thành vector để so nghĩa'),
    ('database', 'green', 'Pinecone', 'Kho 719 đoạn sách, tìm đúng trang trong tích tắc'),
    ('sparkles', 'solid', 'Gemini 3.5 Flash', 'Giảng bài, đọc ảnh đề, nghe giọng nói, soạn câu luyện tập'),
    ('volume-2', 'coral', 'Edge TTS', 'Đọc bài giảng bằng giọng tiếng Việt'),
  ])}</div>
  <div class="label" style="margin-top:30px">Công cụ giúp nhóm làm sản phẩm</div>
  <div class="grid3">{tiles([
    ('terminal', 'navy', 'Claude Code', '49 câu lệnh: đọc mã, sửa lỗi, viết kiểm thử'),
    ('code-xml', 'navy', 'GitHub Copilot', '29 câu lệnh: dựng backend, sửa lỗi giao diện'),
    ('user-round', 'amber', 'Hồ sơ & lịch sử học', 'Lớp, bài đang học, kết quả luyện tập để dạy nối tiếp'),
  ])}</div>
</div>''', TOOL_CSS)

# ---------------------------------------------------------------- 4a. chuẩn bị dữ liệu
PIPE_CSS = '''
.pipe { display: flex; align-items: flex-start; justify-content: space-between; }
.pipe .arrow { margin-top: 28px; }
.node { width: 190px; text-align: center; display: flex; flex-direction: column; align-items: center; gap: 12px; }
.node h4 { margin: 0; font-size: 20px; }
.node p { font-size: 15px; color: #4B5563; line-height: 1.4; }
.arrow { color: #C3CAD5; }
'''
steps = [
    ('file-text', 'amber', 'Sách PDF', 'Toán 6, Toán 8, KHTN 6'),
    ('scan-line', 'navy', 'OCR', 'đọc chữ từ trang scan'),
    ('scissors', 'violet', 'Cắt đoạn', 'mỗi đoạn khoảng 1.000 ký tự'),
    ('layers', 'coral', 'Vector hóa', 'Gemini Embedding'),
    ('database', 'green', 'Pinecone', '719 đoạn kèm môn, lớp, bài, trang'),
]
nodes = f'<span class="arrow">{icon("arrow-right", 40, 2.5)}</span>'.join(
    f'<div class="node"><div class="ic {t}" style="width:96px;height:96px;border-radius:28px">{icon(i, 48)}</div><h4>{h}</h4><p>{d}</p></div>'
    for i, t, h, d in steps)
render('chuan_bi_du_lieu', 1300, 250, f'<div class="canvas"><div class="pipe">{nodes}</div></div>', PIPE_CSS)

# ---------------------------------------------------------------- 4b. đầu vào → AI → đầu ra
FLOW_CSS = f'''
.flow {{ display: grid; grid-template-columns: 1fr 70px 1.15fr 70px 1fr; align-items: start; }}
.flow > .mid {{ align-self: center; }}
.col-title {{ text-align: center; font-weight: 800; font-size: 19px; letter-spacing: .06em; margin-bottom: 16px; }}
.item {{ display: flex; align-items: center; gap: 16px; background: #FAFBFD; border: 2px solid #EEF1F6; border-radius: 20px; padding: 14px 16px; margin-bottom: 14px; }}
.item h4 {{ margin: 0 0 2px; font-size: 19px; }}
.item p {{ font-size: 15px; color: #4B5563; }}
.mid {{ color: #C3CAD5; display: grid; place-items: center; }}
.brain {{ background: linear-gradient(160deg, {CORAL}, #E85A3A); color: #fff; border-radius: 30px; padding: 26px 26px 12px; }}
.brain .head {{ display: flex; align-items: center; gap: 16px; margin-bottom: 18px; }}
.brain .head .ic {{ background: rgba(255,255,255,.2); color: #fff; }}
.brain h3 {{ font-size: 25px; }}
.brain .sub {{ font-size: 15px; opacity: .9; }}
.step {{ display: flex; align-items: center; gap: 14px; background: rgba(255,255,255,.14); border-radius: 16px; padding: 11px 14px; margin-bottom: 11px; font-size: 17px; }}
.step svg {{ flex: none; }}
'''


def items(rows):
    return ''.join(f'<div class="item"><div class="ic {t}" style="width:56px;height:56px;border-radius:16px">{icon(i, 28)}</div>'
                   f'<div><h4>{h}</h4><p>{d}</p></div></div>' for i, t, h, d in rows)


ai_steps = [
    ('mic', 'Nghe giọng nói, đổi thành chữ'),
    ('shield-check', 'Kiểm tra tin nhắn có nguy hiểm không'),
    ('search', 'Tìm trang sách liên quan trong kho'),
    ('notebook-pen', 'Ghép sách + lịch sử học của em'),
    ('sparkles', 'Gemini đọc ảnh đề và soạn lời giảng'),
    ('badge-check', 'Soát lại: gắn nguồn, không lộ đáp án'),
]
arrow_mid = f'<div class="mid">{icon("arrow-right", 44, 2.5)}</div>'
render('dau_vao_xu_ly_dau_ra', 1300, 620, f'''<div class="canvas"><div class="flow">
  <div><div class="col-title" style="color:{NAVY}">EM GỬI GÌ</div>{items([
    ('keyboard', 'navy', 'Câu hỏi gõ phím', 'bài tập, khái niệm, tâm sự'),
    ('camera', 'navy', 'Ảnh chụp đề bài', 'chụp từ điện thoại, máy tính'),
    ('mic', 'navy', 'Giọng nói', 'bấm micro và nói'),
    ('user-round', 'amber', 'Hồ sơ của em', 'lớp, bài đang học, lỗi hay sai'),
    ('database', 'green', 'Kho sách Pinecone', '719 đoạn sách giáo khoa'),
  ])}</div>
  {arrow_mid}
  <div><div class="col-title" style="color:{CORAL}">MIMO XỬ LÝ</div><div class="brain">
    <div class="head"><div class="ic" style="width:64px;height:64px">{icon('bot', 36)}</div><div><h3>Mimo</h3><div class="sub">chạy trên Gemini 3.5 Flash</div></div></div>
    {''.join(f'<div class="step">{icon(i, 24)}<span>{t}</span></div>' for i, t in ai_steps)}
  </div></div>
  {arrow_mid}
  <div><div class="col-title" style="color:{NAVY}">EM NHẬN ĐƯỢC</div>{items([
    ('message-circle', 'coral', 'Lời giảng từng bước', 'gợi ý để em tự làm tiếp'),
    ('book-open', 'amber', 'Nguồn trong sách [1]', 'bấm vào xem đúng trang'),
    ('zap', 'violet', 'Gợi ý hỏi tiếp', 'kèm đánh giá mức hiểu bài'),
    ('volume-2', 'green', 'Nghe giảng', 'giọng đọc tiếng Việt'),
    ('target', 'coral', 'Câu luyện tập', 'độ khó vừa với em'),
  ])}</div>
</div></div>''', FLOW_CSS)

# ---------------------------------------------------------------- 4c. vòng luyện tập
LOOP_CSS = f'''
.loop {{ display: grid; grid-template-columns: 1fr 170px 1fr; grid-template-rows: auto auto; gap: 18px 22px; align-items: center; }}
.lc {{ display: flex; gap: 16px; align-items: center; background: #FAFBFD; border: 2px solid #EEF1F6; border-radius: 22px; padding: 18px; }}
.lc h4 {{ margin: 0 0 4px; font-size: 20px; }}
.lc p {{ font-size: 15px; color: #4B5563; line-height: 1.4; }}
.center {{ grid-column: 2; grid-row: 1 / span 2; justify-self: center; width: 150px; height: 150px; border-radius: 50%; background: #FDE7E0; color: {CORAL}; display: flex; flex-direction: column; gap: 6px; align-items: center; justify-content: center; text-align: center; font-weight: 700; font-size: 15px; }}
'''


def lc(i, t, h, d, n, col, row):
    return f'<div class="lc" style="grid-column:{col};grid-row:{row}"><div class="ic {t}" style="width:60px;height:60px">{icon(i, 30)}</div><div><h4>{n}. {h}</h4><p>{d}</p></div></div>'


render('vong_luyen_tap', 1100, 290, f'''<div class="canvas"><div class="loop">
  {lc('sparkles', 'solid', 'Mimo soạn câu hỏi', 'đúng bài em đang học, độ khó từ 1 đến 5', 1, 1, 1)}
  <div class="center">{icon('refresh-cw', 40)}<div>lặp lại<br>mỗi câu</div></div>
  {lc('pen-line', 'navy', 'Em chọn đáp án', 'có thể xem gợi ý nếu bí', 2, 3, 1)}
  {lc('trending-up', 'green', 'Chỉnh độ khó', 'đúng liên tiếp thì khó hơn, sai thì ôn lại', 4, 1, 2)}
  {lc('circle-check', 'amber', 'Chấm và ghi lỗi sai', 'mức nắm bài tăng hoặc giảm 10%', 3, 3, 2)}
</div></div>''', LOOP_CSS)

# ---------------------------------------------------------------- 6a. chức năng
render('chuc_nang', 1300, 400, f'''<div class="canvas"><div class="grid3">{tiles([
    ('user-round', 'navy', 'Đăng ký & khảo sát', 'Nhập tên, email, lớp; chọn môn, mục tiêu, số phút học mỗi ngày'),
    ('book-marked', 'amber', 'Lộ trình học', 'Theo đúng mục lục sách; bài có trạng thái chưa học, đã học, đã vững'),
    ('message-square-text', 'solid', 'Hỏi Mimo', 'Gõ, chụp ảnh đề hoặc nói; câu trả lời có nguồn trong sách'),
    ('target', 'coral', 'Luyện tập vừa sức', 'Câu hỏi soạn riêng, có gợi ý, chỉ ra lỗi sai'),
    ('timer', 'green', 'Pomodoro', 'Hẹn giờ học và nghỉ, giữ chuỗi ngày học'),
    ('volume-2', 'violet', 'Nghe giảng', 'Bấm loa để Mimo đọc bài bằng giọng Việt'),
  ])}</div></div>''', TOOL_CSS)

# ---------------------------------------------------------------- 6b. con số
KPI_CSS = TOOL_CSS + f'''
.kpis {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px; }}
.kpi {{ background: #FAFBFD; border: 2px solid #EEF1F6; border-radius: 24px; padding: 22px; display: flex; flex-direction: column; gap: 10px; }}
.kpi b {{ font-size: 44px; line-height: 1; color: {NAVY}; }}
.kpi span {{ font-size: 16px; color: #4B5563; line-height: 1.4; }}
'''


import sqlite3
import statistics
_db = sqlite3.connect(ROOT / 'backend' / 'local.db')
N_QUESTIONS = _db.execute("select count(*) from messages where role='user'").fetchone()[0]
LAT_MED = statistics.median(r[0] / 1000 for r in _db.execute("select latency_ms from messages where role='assistant' and latency_ms is not null"))


def kpi(i, t, v, text):
    return f'<div class="kpi"><div class="ic {t}" style="width:56px;height:56px;border-radius:16px">{icon(i, 28)}</div><b>{v}</b><span>{text}</span></div>'


render('con_so', 1300, 260, f'''<div class="canvas"><div class="kpis">
  {kpi('database', 'green', '719', 'đoạn sách giáo khoa trong kho để Mimo tra cứu')}
  {kpi('message-circle', 'coral', str(N_QUESTIONS), 'câu hỏi thử ở 3 môn Toán, KHTN, Ngữ văn')}
  {kpi('timer', 'amber', f"{LAT_MED:.1f} giây".replace('.', ','), 'một nửa số câu Mimo trả lời xong trong khoảng này')}
  {kpi('circle-check', 'navy', '194/194', 'ca kiểm thử tự động đều chạy đúng')}
</div></div>''', KPI_CSS)

# ---------------------------------------------------------------- 5. ảnh chụp trong khung trình duyệt
FRAME_CSS = '''
.frame { border-radius: 18px; overflow: hidden; border: 2px solid #E3E7EE; box-shadow: 0 10px 30px rgba(27,42,74,.12); }
.bar { height: 42px; background: #F1F3F7; display: flex; align-items: center; gap: 9px; padding: 0 18px; }
.dot { width: 13px; height: 13px; border-radius: 50%; }
.url { margin-left: 18px; background: #fff; border-radius: 9px; padding: 5px 16px; font-size: 14px; color: #6B7280; }
.frame img { display: block; width: 100%; }
'''
FRAME_W = 1200
for shot in ['1.jpg', '3.jpg', '2.jpg', 'dn 1.jpg', '4.jpg', '5.jpg', '6.jpg']:
    h, w = mpimg.imread(SHOTS / shot).shape[:2]
    inner_w = FRAME_W - 48
    height = int(h * inner_w / w) + 42 + 4 + 48 + 12
    name = 'anh_' + shot.replace(' ', '').replace('.jpg', '')
    render(name, FRAME_W, height, f'''<div style="padding:24px 24px 36px"><div class="frame">
      <div class="bar"><span class="dot" style="background:#FF6159"></span><span class="dot" style="background:#FFBD2E"></span><span class="dot" style="background:#28C941"></span>
      <span class="url">Gia Sư AI · Mimo</span></div><img src="{(SHOTS / shot).as_uri()}"></div></div>''', FRAME_CSS)
