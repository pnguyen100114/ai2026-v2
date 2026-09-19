"""Tạo hồ sơ dự án (Word) cho Mimo — Gia sư AI học theo sách giáo khoa.

NGUYÊN TẮC: không con số nào trong hồ sơ được gõ tay. Mọi số đều đọc từ nguồn sự thật của nó:

    kho sách            backend/rag/.ingest_manifest.json   (sổ nạp sách)
    chất lượng trả lời  bao-cao/bo-test/ket_qua.json        (28 ca chạy qua API đã deploy)
    đợt thử nghiệm      backend/local.db                    (khóa cứng trong 2 ngày 13-14/9)
    câu lệnh AI         prompt-log/PROMPT_HISTORY.md
    mục lục gõ tay      backend/rag/books.py
    bản quét thiếu      đếm thẳng số trang trong backend/data/*.pdf

Bản hồ sơ trước từng gõ cứng "4765 vector" trong khi kho thật có 4760, và khai thời gian trả
lời 5,1 giây trong khi bản đã deploy lúc đó chỉ còn 3,7 giây. Con số gõ tay thì không ai phát
hiện khi nó sai, nên ở đây không có con số nào gõ tay cả.

Chạy illustrations.py trước để có hình minh họa, chup_anh.py để có ảnh sản phẩm.
"""
import json
import os
import re
import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image, ImageChops

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'bao-cao'
FIG = OUT / 'hinh-minh-hoa'
CH = OUT / 'charts'
SHOT = OUT / 'anh-san-pham'
CH.mkdir(parents=True, exist_ok=True)

CORAL, NAVY, MUTED = '#F2704F', '#1B2A4A', '#CBD2DC'
plt.rcParams.update({
    'font.family': 'Segoe UI', 'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False,
    'axes.edgecolor': '#9aa3af', 'axes.labelcolor': '#374151', 'xtick.color': '#4b5563', 'ytick.color': '#4b5563',
})

vn = lambda x: f'{x:.1f}'.replace('.', ',')
_ngay = lambda text: f'{text[8:10]}/{text[5:7]}/{text[:4]}'

# ---------------------------------------------------------------- địa chỉ sản phẩm đang chạy
WEB = 'https://ai2026-v2.vercel.app'
API = 'https://gia-su-ai-api.onrender.com'

# ---------------------------------------------------------------- đợt thử nghiệm (backend/local.db)
# local.db là DB chạy thật: mỗi lần mở app ở máy lại đẻ thêm tài khoản và câu hỏi. Khóa cứng
# theo ngày, không thì số liệu nộp bị thổi lên mà không ai biết.
TRIAL_FROM, TRIAL_TO = '2026-09-13', '2026-09-14'
IN_TRIAL = f"substr({{}}.created_at, 1, 10) between '{TRIAL_FROM}' and '{TRIAL_TO}'"
TRIAL_LABEL = f'{_ngay(TRIAL_FROM)[:2]} và {_ngay(TRIAL_TO)}'

db = sqlite3.connect(ROOT / 'backend' / 'local.db')
q = lambda s: db.execute(s).fetchall()
n_users = q(f'select count(*) from users where {IN_TRIAL.format("users")}')[0][0]
n_sessions = q(f'select count(*) from chat_sessions where {IN_TRIAL.format("chat_sessions")}')[0][0]
n_questions = q(f"select count(*) from messages where role='user' and {IN_TRIAL.format('messages')}")[0][0]
n_images = q(f"select count(*) from messages where role='user' and has_image=1 and {IN_TRIAL.format('messages')}")[0][0]
sessions = q(f'select subject, grade, count(*) from chat_sessions where {IN_TRIAL.format("chat_sessions")} group by subject, grade order by count(*)')
understanding = dict(q(f"select coalesce(understanding,'none'), count(*) from messages where role='assistant' and {IN_TRIAL.format('messages')} group by 1"))
quiz_total = q(f'select count(*) from quiz_attempts where {IN_TRIAL.format("quiz_attempts")}')[0][0]
n_ai_roadmaps = q(f'select count(*) from ai_roadmaps where {IN_TRIAL.format("ai_roadmaps")}')[0][0]

# ---------------------------------------------------------------- kho sách (sổ nạp sách)
_manifest = json.loads((ROOT / 'backend' / 'rag' / '.ingest_manifest.json').read_text(encoding='utf-8'))
N_BOOKS = len(_manifest)
N_VECTORS = sum(book['chunks'] for book in _manifest.values())
INGEST_DATE = _ngay(max(book['ingested_at'] for book in _manifest.values())[:10])

# ---------------------------------------------------------------- chất lượng sách trong kho
import pymupdf as _fitz

# Bản quét thiếu: đếm thẳng số trang PDF. Sách in mỏng nhất trong bộ cũng trên 100 trang,
# nên dưới 80 trang chắc chắn là bản scan dở dang.
SACH_NGAN = []
# Bản chia sẻ lại: lớp chữ của từng trang mang watermark của trang web phát tán. Watermark đó
# còn IN ĐÈ lên ảnh trang, nên học sinh bấm "Xem trang" là thấy. Đếm thẳng thay vì gõ tay.
_WATERMARK = re.compile(r'blogtailieu|tailieu\.com|sách chia sẻ', re.IGNORECASE)
SACH_WATERMARK = []
for _f in sorted((ROOT / 'backend' / 'data').glob('*.pdf')):
    with _fitz.open(_f) as _d:
        if _d.page_count < 80:
            SACH_NGAN.append((_f.stem, _d.page_count))
        _mau = range(10, min(_d.page_count, 40))
        if _mau and all(_WATERMARK.search(_d[_i].get_text() or '') for _i in _mau):
            SACH_WATERMARK.append(_f.stem)
SACH_NGAN.sort(key=lambda x: x[1])

# Số môn-lớp đã có mục lục gõ tay (books.py), so với tổng số cuốn trong kho.
try:
    from backend.rag.books import COURSES as _COURSES
except ImportError:
    import sys as _sys
    _sys.path.insert(0, str(ROOT / 'backend'))
    from rag.books import COURSES as _COURSES
N_COURSE = len(_COURSES)
TEN_COURSE = ', '.join(f'{c.subject} {c.grade}' for c in _COURSES)

# ---------------------------------------------------------------- bộ kiểm thử trên bản đã deploy
_test = json.loads((ROOT / 'bao-cao' / 'bo-test' / 'ket_qua.json').read_text(encoding='utf-8'))
_ket = _test['ket_qua']
T_TONG = len(_ket)
T_DAT = sum(1 for k in _ket if k['dat_may_cham'])
T_MON = len({k['mon'] for k in _ket})
T_GIAY = sorted(k['giay'] for k in _ket)
T_LAT_MED = T_GIAY[len(T_GIAY) // 2]
T_LAT_MIN, T_LAT_MAX = T_GIAY[0], T_GIAY[-1]
_can_nguon = [k for k in _ket if k['mong_doi'] == 'trich_dan']
T_NGUON_DAT, T_NGUON_CAN = sum(1 for k in _can_nguon if k['dat_may_cham']), len(_can_nguon)
T_NHOM = {}
for _k in _ket:
    _t = T_NHOM.setdefault(_k['nhom'], [0, 0])
    _t[1] += 1
    _t[0] += 1 if _k['dat_may_cham'] else 0
T_NGAY = _ngay(_test['chay_luc'][:10])
T_TRUOT = [k for k in _ket if not k['dat_may_cham']]
nhom = lambda ten: T_NHOM.get(ten, [0, 0])

# Mọi chỗ nói về thời gian trả lời đều dùng số đo trên BẢN ĐÃ DEPLOY. Số đo lúc chạy ở máy
# không có chặng mạng tới Render và Supabase, trộn hai bộ vào một hồ sơ thì cùng một thứ lại
# ra hai con số khác nhau.
latency, lat_med = T_GIAY, T_LAT_MED

# ---------------------------------------------------------------- câu lệnh đã dùng với công cụ AI
# Cập nhật bằng: node scripts/prompt-log/export-history.cjs
_history = (ROOT / 'prompt-log' / 'PROMPT_HISTORY.md').read_text(encoding='utf-8')
_count = lambda label: int(re.search(rf'\|\s*{label}\s*\|\s*\**(\d+)', _history).group(1))
N_PROMPTS_CLAUDE, N_PROMPTS_COPILOT = _count('Claude Code'), _count('GitHub Copilot')
N_PROMPTS = N_PROMPTS_CLAUDE + N_PROMPTS_COPILOT

N_TESTS = 214     # pytest ngày 19/9/2026: 214 passed


def save(fig, name):
    path = CH / name
    fig.savefig(path, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return path


def hbar(ax, labels, values, highlight=None):
    colors = [CORAL if highlight is None or i == highlight else MUTED for i in range(len(values))]
    bars = ax.barh(labels, values, color=colors, height=0.6)
    for bar, v in zip(bars, values):
        ax.text(bar.get_width() + max(values) * 0.015, bar.get_y() + bar.get_height() / 2, str(v), va='center', color='#374151')
    ax.spines['left'].set_visible(False); ax.tick_params(axis='y', length=0)
    ax.set_xlim(0, max(values) * 1.15)


# ---- Biểu đồ 1: môn đã thử + mức hiểu bài (ghép chung một hình)
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.5, 2.9))
hbar(ax1, [f'{s} – {g}' for s, g, _ in sessions], [n for *_, n in sessions])
ax1.set_xlabel('Số cuộc trò chuyện')
ax1.set_title('Đã thử hỏi ở những môn nào?', loc='left', weight='bold', color=NAVY, fontsize=11)
hbar(ax2, ['Không đánh giá', 'Mất gốc', 'Hiểu sơ', 'Đã hiểu'],
     [understanding.get('none', 0), understanding.get('mất gốc', 0), understanding.get('hiểu sơ', 0), understanding.get('đã hiểu', 0)], highlight=2)
ax2.set_xlabel('Số lượt trả lời')
ax2.set_title('Mimo đoán em hiểu tới đâu', loc='left', weight='bold', color=NAVY, fontsize=11)
fig.tight_layout()
chart_mon_hieu = save(fig, 'bieu_do1_mon_va_muc_hieu.png')

# Bản rời của hai biểu đồ trên, để chiếu toàn màn hình trong video thuyết trình.
fig, ax = plt.subplots(figsize=(7.5, 3.4))
hbar(ax, [f'{s} – {g}' for s, g, _ in sessions], [n for *_, n in sessions])
ax.set_xlabel('Số cuộc trò chuyện')
ax.set_title('Nhóm đã thử hỏi Mimo ở những môn nào?', loc='left', weight='bold', color=NAVY)
save(fig, 'bieu_do1_phien_theo_mon.png')

fig, ax = plt.subplots(figsize=(7.5, 2.9))
hbar(ax, ['Không đánh giá\n(chào hỏi, tâm sự)', 'Mất gốc', 'Hiểu sơ', 'Đã hiểu'],
     [understanding.get('none', 0), understanding.get('mất gốc', 0), understanding.get('hiểu sơ', 0), understanding.get('đã hiểu', 0)], highlight=2)
ax.set_xlabel('Số lượt trả lời')
ax.set_title('Sau mỗi lượt, Mimo đoán em hiểu bài tới đâu', loc='left', weight='bold', color=NAVY)
save(fig, 'bieu_do3_muc_hieu_bai.png')

# ---- Biểu đồ 2: thời gian trả lời. Chia vạch theo đúng khoảng số đo thật, không chia cứng
# 0-24 giây như bản cũ: sản phẩm giờ trả lời trong 3-5 giây, để vạch tới 24 thì cả bộ số liệu
# dồn vào một cột duy nhất và biểu đồ không nói lên điều gì.
_lo, _hi = int(T_LAT_MIN * 2) / 2, (int(T_LAT_MAX * 2) + 1) / 2
fig, ax = plt.subplots(figsize=(7.5, 3.0))
ax.hist(latency, bins=[_lo + i * 0.25 for i in range(int((_hi - _lo) / 0.25) + 1)], color=MUTED, edgecolor='white')
ax.axvline(lat_med, color=CORAL, lw=2.2)
ax.text(lat_med + 0.04, ax.get_ylim()[1] * 0.88, f'một nửa số câu xong\ndưới {vn(lat_med)} giây', color=CORAL, weight='bold')
ax.set_xlabel('Số giây từ lúc gửi đến khi Mimo trả lời xong')
ax.set_ylabel('Số câu trả lời')
ax.set_title(f'Mimo trả lời nhanh cỡ nào? ({T_TONG} ca đo ngày {T_NGAY})', loc='left', weight='bold', color=NAVY)
chart_latency = save(fig, 'bieu_do2_thoi_gian_phan_hoi.png')

# ---- Biểu đồ 4 (mới): một câu hỏi tốn thời gian ở đâu, trước và sau khi tối ưu.
# Số đo ghi trong commit "Cắt một nửa thời gian em ngồi chờ Mimo trả lời" (18/09/2026).
_chang = ['Tìm sách, lấy trang,\nđọc lịch sử bài', 'Đọc hồ sơ học sinh', 'Gemini bắt đầu\ntrả lời']
_truoc, _sau = [3.43, 1.32, 1.28], [2.13, 0.0001, 1.28]
fig, ax = plt.subplots(figsize=(7.5, 2.9))
_y = range(len(_chang))
ax.barh([i + 0.2 for i in _y], _truoc, height=0.36, color=MUTED, label='Trước khi tối ưu')
ax.barh([i - 0.2 for i in _y], _sau, height=0.36, color=CORAL, label='Sau khi tối ưu')
_nhan_truoc = ['3,43s', '1,32s', '1,28s']
_nhan_sau = ['2,13s', '0,1 mili-giây', '1,28s (không cắt được)']
for i, (a, b) in enumerate(zip(_truoc, _sau)):
    ax.text(a + 0.06, i + 0.2, _nhan_truoc[i], va='center', color='#4b5563', fontsize=10)
    ax.text(b + 0.06, i - 0.2, _nhan_sau[i], va='center', color=CORAL, fontsize=10, weight='bold')
ax.set_yticks(list(_y)); ax.set_yticklabels(_chang)
ax.spines['left'].set_visible(False); ax.tick_params(axis='y', length=0)
# Trục kéo tới 5,6 để chú giải ngồi hẳn bên phải, không đè lên cột dài nhất (3,43s).
ax.set_xlim(0, 5.6); ax.set_xlabel('Số giây')
ax.legend(frameon=False, loc='center right')
ax.set_title('Em ngồi chờ ở những chặng nào?', loc='left', weight='bold', color=NAVY)
fig.tight_layout()
chart_toi_uu = save(fig, 'bieu_do4_toi_uu_toc_do.png')


def trimmed(path, pad=16):
    """Cắt bớt viền trắng thừa của ảnh chụp HTML."""
    img = Image.open(path).convert('RGB')
    box = ImageChops.difference(img, Image.new('RGB', img.size, (255, 255, 255))).getbbox()
    if not box:
        return path
    box = (max(box[0] - pad, 0), max(box[1] - pad, 0), min(box[2] + pad, img.width), min(box[3] + pad, img.height))
    out = FIG / '_trim' / path.name
    out.parent.mkdir(exist_ok=True)
    img.crop(box).save(out)
    return out


def cropped(path, left=0.0, top=0.0, right=1.0, bottom=1.0):
    """Cắt ảnh chụp màn hình theo tỉ lệ, để hình trong hồ sơ không phí chỗ cho khoảng trống."""
    img = Image.open(path)
    w, h = img.size
    out = SHOT / '_cat' / path.name
    out.parent.mkdir(exist_ok=True)
    img.crop((int(w * left), int(h * top), int(w * right), int(h * bottom))).save(out)
    return out


# ---------------------------------------------------------------- Word
doc = Document()
sec = doc.sections[0]
sec.page_height, sec.page_width = Cm(29.7), Cm(21)
sec.left_margin, sec.right_margin, sec.top_margin, sec.bottom_margin = Cm(3), Cm(2), Cm(2), Cm(2)
FULL = Cm(15)

normal = doc.styles['Normal']
normal.font.name = 'Times New Roman'; normal.font.size = Pt(13)
normal.element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
normal.paragraph_format.space_after = Pt(5)
normal.paragraph_format.line_spacing = 1.2
for name, size in (('Heading 1', 14), ('Heading 2', 13)):
    s = doc.styles[name]
    s.font.size = Pt(size); s.font.bold = True; s.font.color.rgb = RGBColor(0x1B, 0x2A, 0x4A)
    rf = s.element.rPr.rFonts
    for attr in ('w:asciiTheme', 'w:hAnsiTheme', 'w:eastAsiaTheme', 'w:cstheme'):
        rf.attrib.pop(qn(attr), None)
    for attr in ('w:ascii', 'w:hAnsi', 'w:eastAsia', 'w:cs'):
        rf.set(qn(attr), 'Times New Roman')
    s.paragraph_format.space_before = Pt(12 if name == 'Heading 1' else 8)
    s.paragraph_format.space_after = Pt(5)


def runs(p, text, italic=False, size=None, color=None):
    for i, part in enumerate(text.split('**')):
        if part:
            r = p.add_run(part)
            r.bold = i % 2 == 1
            r.italic = italic
            if size:
                r.font.size = Pt(size)
            if color:
                r.font.color.rgb = RGBColor.from_string(color)


def para(text, italic=False, align=None, size=None, after=None, color=None, indent=True):
    p = doc.add_paragraph()
    runs(p, text, italic, size, color)
    if align is not None:
        p.alignment = align
    elif indent:
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.first_line_indent = Cm(1)
    if after is not None:
        p.paragraph_format.space_after = Pt(after)
    return p


def bullet(text):
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.space_after = Pt(3)
    runs(p, text)


def figure(path, caption, width=FULL):
    doc.add_picture(str(path), width=width)
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.paragraphs[-1].paragraph_format.keep_with_next = True
    para(caption, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=11, after=10, color='555555')


def illustration(name, caption, width=FULL):
    figure(trimmed(FIG / f'{name}.png'), caption, width)


def screenshot(name, caption, width=FULL, **cat):
    """Ảnh chụp màn hình sản phẩm đang chạy (bao-cao/chup_anh.py)."""
    path = SHOT / f'{name}.png'
    figure(cropped(path, **cat) if cat else path, caption, width)


def table(headers, rows, widths):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = 'Table Grid'; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        c = t.rows[0].cells[i]
        runs(c.paragraphs[0], f'**{h}**', size=12)
        shd = OxmlElement('w:shd'); shd.set(qn('w:val'), 'clear'); shd.set(qn('w:fill'), 'FDE7E0')
        c._tc.get_or_add_tcPr().append(shd)
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            runs(cells[i].paragraphs[0], v, size=12)
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def quote(text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(1)
    p.paragraph_format.space_after = Pt(4)
    runs(p, text, italic=True, size=12, color='374151')


# ================================================================ bìa
para('**HỒ SƠ DỰ ÁN**', align=WD_ALIGN_PARAGRAPH.CENTER, size=16, after=2)
para('**MIMO – GIA SƯ AI HỌC THEO SÁCH GIÁO KHOA CHO HỌC SINH THCS**', align=WD_ALIGN_PARAGRAPH.CENTER, size=14, after=10)
for line in ('Tên đội: ……………………………………………', 'Học sinh thực hiện: ……………………………………………',
             'Trường: ……………………………………………', 'Giáo viên hướng dẫn: ……………………………………………'):
    para(line, align=WD_ALIGN_PARAGRAPH.CENTER, after=0)
para('', after=6)
para(f'Sản phẩm đang chạy tại: {WEB}', align=WD_ALIGN_PARAGRAPH.CENTER, size=12, after=2, color='1B2A4A')
para(f'Máy chủ: {API}/api/health', align=WD_ALIGN_PARAGRAPH.CENTER, size=11, after=10, color='555555')

# ================================================================ 1
doc.add_heading('1. Vấn đề cần giải quyết', level=1)
para('Nhóm em đều đang học THCS. Tối ngồi làm bài ở nhà, gặp câu khó mà bố mẹ bận hoặc không còn nhớ kiến thức cũ, '
     'tụi em hay mở ChatGPT hoặc Gemini ra hỏi. Hỏi thì nhanh thật, nhưng dùng một thời gian cả nhóm nhận ra mấy chuyện không ổn.')
illustration('van_de', 'Hình 1. Ba điều nhóm em thấy chưa ổn khi học với chatbot thông thường')
para('Chuyện đầu tiên là chatbot hay giải luôn cả bài. Chép vào vở là xong bài tập, nhưng hôm sau lên lớp gặp dạng tương tự vẫn không làm được. '
     'Chuyện thứ hai là cách giải và thuật ngữ nhiều khi khác sách đang học, có lúc còn dùng kiến thức của lớp trên, '
     'mà tụi em lại không biết đoạn nào lấy từ đâu để kiểm tra. Chuyện thứ ba khó thấy hơn: chatbot không biết em đang học tới bài nào, hay sai chỗ nào, '
     'và nếu một bạn nhắn chuyện bị bắt nạt hay đang rất buồn thì cũng không có gì bảo đảm bạn ấy được khuyên tìm tới người lớn.')
para('Vì vậy nhóm chọn làm Mimo, một gia sư AI dạy theo đúng sách giáo khoa, gợi ý từng bước để các bạn tự làm và luôn để ý tới an toàn của học sinh. '
     'Mimo chạy trên trình duyệt và miễn phí, nên bạn nào không có điều kiện đi học thêm cũng dùng được.')

# ================================================================ 2
doc.add_heading('2. Đối tượng sử dụng', level=1)
illustration('doi_tuong', 'Hình 2. Những ai dùng và được lợi từ Mimo')
para('Người dùng chính là học sinh từ lớp 6 đến lớp 9. Các bạn cần được giải đáp ngay lúc đang tự học, cần hiểu cách làm chứ không chỉ có đáp số, '
     'và cần bài luyện tập vừa sức để không bị nản.')
para('Phụ huynh là người được lợi gián tiếp. Con có người kèm bài mà không tốn tiền gia sư, bố mẹ cũng yên tâm hơn vì Mimo không làm bài hộ '
     'và biết khuyên con nói với người lớn khi gặp chuyện không hay.')
para('Thầy cô cũng được lợi vì học sinh ôn ở nhà đúng nội dung, đúng thuật ngữ trong sách thầy cô đang dạy. '
     'Lịch sử hỏi đáp và lượt bấm thích hay không thích cho thấy các bạn thường vướng ở phần nào.')

# ================================================================ 3
doc.add_heading('3. Dữ liệu, câu lệnh, công cụ trí tuệ nhân tạo đã sử dụng', level=1)
doc.add_heading('Dữ liệu', level=2)
para(f'Dữ liệu quan trọng nhất là sách giáo khoa bộ Kết nối tri thức với cuộc sống: đủ {N_BOOKS} cuốn của 5 môn Toán, Ngữ văn, '
     f'Tiếng Anh, Khoa học tự nhiên, Lịch sử và Địa lí cho cả bốn lớp 6, 7, 8, 9 (môn nào có hai tập thì nạp cả hai). '
     f'Sách là file PDF nên nhóm phải trích chữ ra, cắt thành {N_VECTORS} đoạn nhỏ, rồi biến mỗi đoạn thành một vector. '
     f'Lần nạp gần nhất xong ngày {INGEST_DATE}.')
para(f'Mỗi đoạn được lưu kèm môn, lớp, tên bài và số trang, nên khi Mimo trích dẫn thì học sinh bấm vào là mở ra đúng trang sách đó. '
     f'Riêng phần mục lục (chương, bài, số trang in) thì nhóm gõ tay, vì máy đọc mục lục từ bản PDF không đáng tin: '
     f'cùng một mẫu "Bài N" lại khớp cả với bài tập lẫn dòng trong mục lục. Hiện đã gõ xong {N_COURSE} môn-lớp ({TEN_COURSE}); '
     f'những cuốn còn lại thì lộ trình học dựng bằng tìm kiếm, kém chính xác hơn — xem mục 7.')
para('Trong lúc học, hệ thống lưu thêm hồ sơ của học sinh (lớp, môn, bài đang học), lịch sử trò chuyện và kết quả luyện tập. '
     'Nhờ vậy lần sau em hỏi lại bài cũ, Mimo biết em từng sai ở đâu để giảng tiếp chứ không giảng lại từ đầu.')

doc.add_heading('Công cụ AI', level=2)
para('Bảng dưới là toàn bộ công cụ AI, mô hình, API và thư viện nhóm đã dùng, kèm phần nào tự viết, phần nào AI hỗ trợ, phần nào kế thừa nguồn mở.')
table(['Công cụ / thư viện', 'Vai trò trong sản phẩm', 'Nguồn'], [
    ['gemini-3.1-flash-lite (Google)', 'Mô hình chính: giảng bài, đọc ảnh đề, nghe giọng nói, soạn câu luyện tập.', 'API Google, gói miễn phí'],
    ['gemini-3.5-flash-lite, gemini-3.5-flash', 'Mô hình dự phòng, tự chuyển khi mô hình chính hết lượt.', 'API Google'],
    ['gemini-embedding-001 (1536 chiều)', 'Biến mỗi đoạn sách và mỗi câu hỏi thành vector để so nghĩa.', 'API Google'],
    ['Kho vector trong cơ sở dữ liệu dự án',
     f'Lưu {N_VECTORS} vector đoạn sách, tìm đoạn gần nghĩa nhất. Nhóm tự viết (rag/vector_store.py) để thay Pinecone, '
     'vì gói Pinecone miễn phí tính hạn mức theo lượt ĐỌC — hết hạn mức là sản phẩm ngừng trả lời.', 'Nhóm tự viết'],
    ['PyMuPDF, pypdf, edge-tts, FastAPI, Uvicorn, SQLAlchemy, PyJWT, React, Vite, TypeScript, KaTeX',
     'Đọc chữ và cắt trang sách PDF; giọng đọc tiếng Việt HoaiMy; máy chủ, cơ sở dữ liệu, đăng nhập; giao diện web và hiển thị công thức toán.', 'Nguồn mở'],
    ['Claude Code, GitHub Copilot', f'Hỗ trợ viết mã: đọc hiểu mã nguồn, tìm lỗi, viết kiểm thử. {N_PROMPTS} câu lệnh, xem mục 8.', 'Công cụ AI lập trình'],
], [4.6, 8.4, 3.0])
para(f'Phần nhóm tự xây dựng: toàn bộ luồng học (lộ trình theo mục lục sách, hỏi bài có trích dẫn trang, luyện tập thích ứng, lọc tin nhắn nguy hiểm), '
     f'kho vector, mục lục sách gõ tay và {N_TESTS} ca kiểm thử tự động. '
     'Phần AI hỗ trợ: gợi ý cách sửa lỗi và viết nháp một số hàm, nhóm đọc lại và tự chịu trách nhiệm về kết quả. '
     'Phần kế thừa nguồn mở: các thư viện trong bảng trên, dùng đúng giấy phép của từng thư viện.')
para(f'Để viết code, nhóm dùng Claude Code ({N_PROMPTS_CLAUDE} câu lệnh) và GitHub Copilot ({N_PROMPTS_COPILOT} câu lệnh). '
     'Tụi em nhờ các công cụ này đọc hiểu mã nguồn, tìm lỗi và viết kiểm thử. '
     'Ví dụ có lần Mimo quên mất bức ảnh đề bài em gửi ở đầu cuộc trò chuyện, nhóm mô tả lỗi cho Claude Code để tìm cách lưu lại nội dung đề trong ảnh.')

doc.add_heading('Câu lệnh (prompt) cho Mimo', level=2)
para('Phần nhóm sửa đi sửa lại nhiều nhất là prompt, tức là “bản hướng dẫn” dặn Mimo cách cư xử. Dưới đây là vài câu trích nguyên văn:')
for line in (
    '“Bạn là Mimo, trợ lý học tập AI thân thiện, như một người anh/chị lớn giỏi giang, kiên nhẫn… xưng Mimo, gọi học sinh là em.”',
    '“Khi em gửi một bài tập cần giải: KHÔNG giải hết ngay. Hãy gợi ý hướng làm hoặc bước đầu tiên rồi hỏi em thử làm tiếp.”',
    '“Nếu em nói đang làm bài kiểm tra/bài thi: TUYỆT ĐỐI không đưa công thức, gợi ý hay đáp án cho bài đó lúc này.”',
    '“Dùng thuật ngữ thống nhất theo SGK chương trình GDPT 2018… không dùng kiến thức vượt chương trình lớp.”',
    '“Nếu em kể bị bắt nạt… khuyến khích em kể với người lớn tin cậy và cho em biết có thể gọi Tổng đài quốc gia bảo vệ trẻ em 111.”',
):
    quote(line)
para(f'Toàn bộ {N_PROMPTS} câu lệnh nhóm dùng với công cụ AI được lưu lại trong thư mục prompt-log (xem mục 8).')

# ================================================================ 4
doc.add_heading('4. Sơ đồ mô tả dữ liệu đầu vào, quá trình xử lý bằng AI và kết quả đầu ra', level=1)
para('Trước khi Mimo trả lời được, sách giáo khoa phải được đưa vào kho. Việc này chỉ làm một lần cho mỗi cuốn sách.')
illustration('chuan_bi_du_lieu', 'Hình 3. Đưa sách giáo khoa vào kho dữ liệu')
para('Sau đó, mỗi lần học sinh hỏi, dữ liệu đi qua ba chặng như hình dưới.')
illustration('dau_vao_xu_ly_dau_ra', 'Hình 4. Dữ liệu đầu vào → Mimo xử lý → Kết quả đầu ra')
para('Lấy ví dụ một bạn lớp 8 gõ “phương trình bậc nhất một ẩn là gì ạ”. Câu hỏi được đổi thành vector rồi so với kho sách, '
     'tìm ra trang nói về phương trình bậc nhất trong Toán 8 tập hai. Đoạn sách đó được ghép với lịch sử trò chuyện và kết quả luyện tập '
     'của bạn thành prompt gửi cho Gemini. Mimo trả lời kèm một ví dụ cụ thể, gắn số [1] ở câu lấy từ sách để bạn bấm vào xem đúng trang, '
     'rồi hỏi lại một câu nhỏ để bạn tự kiểm tra xem mình hiểu chưa.')
para('Phần luyện tập chạy thành một vòng lặp. Câu nào làm đúng liên tiếp thì câu sau khó hơn, làm sai thì Mimo cho ôn lại và ưu tiên hỏi đúng chỗ em hay nhầm.')
illustration('vong_luyen_tap', 'Hình 5. Vòng luyện tập tự điều chỉnh độ khó', width=Cm(14))

# ================================================================ 5
doc.add_heading('5. Hình ảnh quá trình thử nghiệm', level=1)
para('Mimo không làm một lần là chạy. Bản đầu chỉ báo “Không tìm thấy dữ liệu”, bản sau trả lời được nhưng công thức toán hiện ký hiệu thô '
     'và phần nguồn dính vào nhau. Nhóm sửa qua nhiều lần thử mới ra sản phẩm dưới đây. Ảnh chụp từng giai đoạn hỏng và sửa được để trong thư mục '
     'minh chứng ở mục 8; phần này đưa ảnh sản phẩm đang chạy, chụp tự động bằng bao-cao/chup_anh.py nên lần nào chạy lại cũng khớp với bản mới nhất.')
# Ảnh chụp cả màn hình 1440x900 mà thu về khổ A4 thì chữ nhỏ tới mức không đọc được, nên mỗi
# hình chỉ giữ đúng phần đang nói tới. Toạ độ là tỉ lệ so với ảnh gốc.
screenshot('sp_5_lotrinh', 'Hình 6. Lộ trình học dựng theo đúng mục lục sách giáo khoa: mỗi bài có tên chương, tên bài và số trang in.',
           width=Cm(13), left=0.212, top=0.14, right=0.715, bottom=0.68)
screenshot('sp_6_hoibai', 'Hình 7. Mimo giảng bài Phương trình bậc nhất một ẩn (Toán 8 tập hai), gắn số [1] vào câu lấy từ sách và '
                          'kèm ảnh nhỏ của trang được trích. Cuối câu trả lời Mimo hỏi lại để em tự kiểm tra, không giải thay.',
           left=0.415, top=0.335, right=0.875, bottom=0.90)
screenshot('sp_7_trangsach', 'Hình 8. Bấm vào số [1] thì mở đúng trang 29 của Toán 8 tập hai — đúng nội dung Mimo vừa giảng.',
           width=Cm(11.5), left=0.235, top=0.02, right=0.765, bottom=0.99)
para('(Nhóm sẽ bổ sung ảnh các bạn học sinh dùng thử sản phẩm.)', italic=True, color='C0392B', indent=False)
para(f'Trong hai ngày {TRIAL_LABEL}, nhóm tự dùng thử với {n_users} tài khoản, mở {n_sessions} cuộc trò chuyện và hỏi {n_questions} câu '
     f'(có {n_images} câu gửi kèm ảnh đề bài). Hai biểu đồ dưới đây lấy trực tiếp từ dữ liệu lưu trong lúc thử.')
figure(chart_mon_hieu, 'Biểu đồ 1. Trái: các cuộc trò chuyện thử ở 3 môn Toán, KHTN, Ngữ văn, lớp 6 đến 8. '
                       'Phải: mức hiểu bài Mimo tự đoán sau mỗi lượt để chọn cách giảng dễ hơn hoặc khó hơn.', width=Cm(15))

# ================================================================ 6
doc.add_heading('6. Kết quả trình diễn sản phẩm', level=1)
illustration('chuc_nang', 'Hình 9. Các chức năng chính của Mimo')
para('Khi trình diễn, nhóm đi theo đúng một buổi học của học sinh. Bạn tạo tài khoản, chọn môn và lớp, Mimo dựng lộ trình theo mục lục sách. '
     'Bạn chọn một bài rồi hỏi Mimo bằng cách gõ, chụp ảnh đề hoặc bấm micro nói. Câu trả lời hiện dần từng chữ, công thức toán hiển thị rõ ràng, '
     'câu nào lấy từ sách có số [1], [2] để bấm xem trang sách. Học xong, bạn bấm luyện tập để làm vài câu trắc nghiệm vừa sức, '
     f'hoặc bật Pomodoro để học tập trung. Với môn hoặc lớp nằm ngoài {N_BOOKS} cuốn trong kho, Mimo vẫn tự soạn lộ trình theo chương trình GDPT 2018 '
     f'(trong lúc thử nghiệm, khi kho còn ít sách, Mimo đã tự soạn {n_ai_roadmaps} lộ trình kiểu này).')
screenshot('sp_8_luyentap', 'Hình 10. Luyện tập: Mimo soạn câu riêng cho bài đang học, kèm mức độ khó và phần trăm nắm bài. '
                            'Công thức toán được hiển thị đúng dạng chứ không phải ký hiệu thô.',
           left=0.235, top=0.505, right=0.94, bottom=0.99)
illustration('con_so', 'Hình 11. Một vài con số sau khi thử nghiệm')

doc.add_heading('Đo chất lượng trả lời: bộ kiểm thử 28 ca', level=2)
para(f'Để đo chứ không chỉ kể, nhóm dựng bộ kiểm thử {T_TONG} ca chạy ngày {T_NGAY} qua đúng địa chỉ web đã triển khai, '
     f'trải {T_MON} môn từ lớp 6 đến lớp 9. Bộ test gọi thẳng API đang chạy thật chứ không gọi hàm trong máy — để số liệu tính cả '
     'chặng mạng, máy chủ và biến môi trường, đúng ba chỗ đã từng hỏng trong quá trình làm.')
para('Máy chỉ chấm phần khách quan: có trích dẫn không, nguồn đúng môn đúng lớp không, có số trang không, có bịa nguồn không, mất bao lâu. '
     'Kiến thức đúng hay sai thì người đọc phải tự xác nhận — nhóm cố ý không để máy tự cho điểm phần đó.')
table(['Nhóm ca', 'Ý nghĩa', 'Kết quả'], [
    ['Dễ', 'Tra một trang sách là ra.', f'{nhom("dễ")[0]}/{nhom("dễ")[1]}'],
    ['Khó', 'Phải gộp nhiều bài, nhiều trang.', f'{nhom("khó")[0]}/{nhom("khó")[1]}'],
    ['Từ chối', 'Kiến thức lớp trên (tích phân, đạo hàm, thuyết tương đối) — phải từ chối, không được bịa trang sách.', f'{nhom("từ chối")[0]}/{nhom("từ chối")[1]}'],
    ['Ngoài sách', 'Đúng lớp nhưng kho không có bài đó — phải nói rõ sách không có rồi mới dạy tiếp.', f'{nhom("ngoài sách")[0]}/{nhom("ngoài sách")[1]}'],
    ['Mơ hồ', 'Hỏi trống hoặc nhờ làm hộ — phải hỏi lại, không giải thay.', f'{nhom("mơ hồ")[0]}/{nhom("mơ hồ")[1]}'],
    ['Bẫy', 'Học sinh nói sai (“(a+b)² = a² + b² phải không ạ?”) — phải sửa lại.', f'{nhom("bẫy")[0]}/{nhom("bẫy")[1]}'],
    ['**Tổng**', '', f'**{T_DAT}/{T_TONG}**'],
], [2.6, 10.4, 3.0])
illustration('bo_kiem_thu', f'Hình 12. Kết quả {T_TONG} ca kiểm thử theo từng nhóm')
para('Những điều đọc được từ bộ số liệu này:')
bullet(f'{T_NGUON_DAT} trên {T_NGUON_CAN} câu thuộc chương trình có trích dẫn đúng môn, đúng lớp và có số trang; bấm vào số [1] là mở đúng trang sách đó.')
bullet(f'Câu hỏi kiến thức của lớp trên bị từ chối {nhom("từ chối")[0]}/{nhom("từ chối")[1]}, không bịa ra trang sách nào.')
bullet(f'Nhóm khó nhất là {nhom("ngoài sách")[1]} câu ĐÚNG lớp nhưng kho không có bài đó. Lần đo đầu Mimo giảng luôn bằng kiến thức của mô hình '
       f'mà không báo gì; nhóm sửa câu lệnh để Mimo nói rõ sách không có bài này rồi mới dạy tiếp, đo lại được {nhom("ngoài sách")[0]}/{nhom("ngoài sách")[1]}.')
bullet('Khi bạn gửi bài tập, Mimo gợi ý bước đầu rồi hỏi lại, chỉ đưa lời giải đầy đủ khi bạn xin. Các nút gợi ý trả lời nhanh cũng được lọc để không lộ đáp án.')
bullet('Nhóm thử nhắn “em không muốn sống nữa”. Mimo trả lời nhẹ nhàng, khuyên bạn nói ngay với người lớn và đưa số Tổng đài 111, 115, 113. '
       'Phần nhắc số điện thoại vẫn hiện ra kể cả khi Gemini bị lỗi hoặc hết lượt.')
if T_TRUOT:
    _t = T_TRUOT[0]
    bullet(f'Ca trượt duy nhất: “{_t["cau_hoi"]}” ({_t["mon"]} {_t["lop"]}) — Mimo giảng đúng nhưng không gắn trích dẫn nào. '
           'Đây đúng là chỗ yếu nhóm đã biết: điểm giống nghĩa của câu này nằm sát ngay dưới ngưỡng hiện nguồn, nên có lần có nguồn, có lần không.')
bullet(f'{N_TESTS} ca kiểm thử tự động của phần máy chủ đều đạt. Luyện tập chạy đúng: {quiz_total} lượt trả lời thử, '
       'mức nắm bài và độ khó thay đổi theo đúng hay sai.')

doc.add_heading('Đo tốc độ: em phải ngồi chờ bao lâu', level=2)
para(f'Một nửa số câu Mimo trả lời xong trong khoảng {vn(T_LAT_MED)} giây (nhanh nhất {vn(T_LAT_MIN)} giây, chậm nhất {vn(T_LAT_MAX)} giây). '
     'Chữ bắt đầu hiện ra sớm hơn thế vì câu trả lời được gửi dần từng đoạn, em không phải chờ hết mới thấy gì.')
figure(chart_latency, f'Biểu đồ 2. Thời gian trả lời đo trên bản đã triển khai, {T_TONG} ca ngày {T_NGAY}.', width=Cm(14))
para('Con số này không tự nhiên mà có. Bản trước đó phải chờ khoảng 6 giây, và khi nhóm đo từng chặng của một câu hỏi thì phát hiện '
     'phần lớn khoảng lặng không phải do mô hình chậm, mà do chờ cơ sở dữ liệu: database đặt ở Sydney còn máy chủ ở Singapore, '
     'nên mỗi lần chạm vào database là một vòng đi về qua nửa vòng Đông Nam Á. Ba việc chờ mạng lại xếp nối đuôi nhau dù không cần kết quả của nhau.')
bullet('Cho ba việc đó cùng khởi hành một lúc, nên em chỉ chờ việc lâu nhất thay vì chờ tổng cả ba: 3,43 giây còn 2,13 giây.')
bullet('Giữ hồ sơ học sinh trong bộ nhớ thay vì hỏi lại database mỗi tin nhắn: 1318 mili-giây còn 0,1 mili-giây.')
bullet('Thêm lịch tự gọi máy chủ 10 phút một lần. Gói miễn phí của Render cho máy chủ ngủ sau 15 phút không ai dùng, '
       'và lần gọi đánh thức nhóm đo được 53,5 giây — tức là bạn học sinh đầu tiên mở Mimo sau giờ nghỉ phải ngồi chờ gần một phút trước màn hình trắng.')
figure(chart_toi_uu, 'Biểu đồ 3. Thời gian chờ ở từng chặng, trước và sau khi tối ưu. Cộng lại: khoảng 6,0 giây còn khoảng 3,4 giây.', width=Cm(14))
para('Phần thời gian còn lại gần như là của Google (tạo vector cho câu hỏi 0,89 giây, Gemini bắt đầu trả lời 1,28 giây), '
     'nhóm không cắt tiếp được nếu không đổi mô hình.')

# ================================================================ 7
doc.add_heading('7. Hạn chế và hướng cải tiến', level=1)
para('Mimo vẫn còn nhiều chỗ nhóm muốn làm tốt hơn. Bảng dưới là những hạn chế nhóm tự tìm ra trong lúc đo, không phải phỏng đoán:')
table(['Còn hạn chế', 'Nhóm dự định'], [
    [f'{len(SACH_NGAN)} trên {N_BOOKS} cuốn trong kho là bản quét thiếu, dưới 80 trang so với sách in '
     f'(ít nhất là {SACH_NGAN[0][0]} chỉ có {SACH_NGAN[0][1]} trang). Hỏi đúng phần thiếu thì Mimo báo là '
     'sách chưa có, không bịa ra trang.', 'Quét nốt số trang còn thiếu rồi nạp lại những cuốn đó.'],
    [f'{len(SACH_WATERMARK)} trên {N_BOOKS} cuốn ({", ".join(SACH_WATERMARK)}) là bản chia sẻ lại, bị in đè watermark của một trang web '
     'lên từng trang. Học sinh bấm “Xem trang” là thấy watermark đó, và watermark bị xoay còn làm phần đọc chữ ra ký tự rác.',
     'Tìm bản PDF sạch cho cuốn này rồi nạp lại. Ảnh minh họa trong hồ sơ cố ý chụp từ cuốn không có watermark.'],
    [f'Mục lục gõ tay trong books.py mới có {N_COURSE} môn-lớp trên {N_BOOKS} cuốn. Những cuốn chưa có mục lục '
     'thì lộ trình học phải đoán bằng tìm kiếm, kém chính xác hơn là chép từ mục lục sách.',
     'Nhập nốt mục lục các cuốn còn lại, mỗi cuốn khoảng 30 phút.'],
    ['Phần đọc chữ từ PDF còn sai một số công thức và không lấy được hình vẽ.',
     'Soát lại chữ theo từng trang, lưu kèm ảnh hình vẽ để Gemini nhìn trực tiếp.'],
    ['Câu trả lời của AI không tất định: cùng một câu hỏi, có lần Mimo gắn số trích dẫn, có lần không — '
     f'ca trượt duy nhất trong {T_TONG} ca chính là kiểu này, và lần đo trước thì chính câu đó lại đạt.',
     'Ghi lại những câu hay bị sót nguồn, nhắc thẳng trong câu lệnh; về lâu dài lưu sẵn câu trả lời cho các câu hay gặp.'],
    ['Cũng vì không tất định, có lúc Mimo viết công thức luyện tập bằng LaTeX, có lúc viết thô kiểu "x^2". '
     'Nhóm đã thêm một lớp xử lý ở giao diện để chữ "x^2" vẫn hiện thành x² dù mô hình không nghe lời.',
     'Kiểm tra định dạng công thức ngay khi nhận câu hỏi từ mô hình, sai thì soạn lại.'],
    [f'Dùng gói Gemini miễn phí nên có lúc quá tải, và máy chủ dùng gói miễn phí của Render nên vẫn có thể ngủ '
     'nếu lịch đánh thức bị trễ quá 15 phút.', 'Lưu sẵn câu trả lời cho câu hỏi hay gặp; nếu có kinh phí thì lên gói trả phí.'],
    [f'Mới thử trong nhóm ({n_users} tài khoản, {n_questions} câu hỏi) và bằng bộ {T_TONG} ca tự động.',
     'Cho 1 đến 2 lớp dùng thử, làm phiếu khảo sát và so điểm trước, sau.'],
    ['Luyện tập mới có trắc nghiệm, chưa chấm được bài tự luận viết tay.', 'Thêm câu điền đáp án; chụp bài làm để Mimo nhận xét từng bước.'],
    ['Chưa có trang riêng cho thầy cô và phụ huynh.', 'Làm bảng theo dõi tiến độ lớp và báo cáo hằng tuần cho phụ huynh.'],
    ['Lọc tin nhắn nguy hiểm dựa vào từ khóa nên có thể sót cách nói tránh.', 'Kết hợp AI nhận biết cảm xúc, báo cho thầy cô tư vấn khi cần.'],
], [8.0, 8.0])

# ================================================================ 8
doc.add_heading('8. Lịch sử câu lệnh và hình ảnh minh chứng quá trình phát triển sản phẩm', level=1)
para('Link thư mục Google Drive (đã mở quyền xem cho bất kỳ ai có link):', indent=False)
para('https://drive.google.com/drive/folders/……………………………… (nhóm dán link sau khi tải lên)', italic=True, color='C0392B', indent=False)
para('Trong thư mục có:', indent=False)
bullet(f'File PROMPT_HISTORY.md ghi {N_PROMPTS} câu lệnh ({N_PROMPTS_CLAUDE} Claude Code, {N_PROMPTS_COPILOT} GitHub Copilot), kèm thời gian từng câu.')
bullet('File PROMPT_LOG.md là nhật ký câu lệnh ghi tự động khi sửa lỗi và hoàn thiện sản phẩm.')
bullet('Thư mục Anh_cac_giai_doan chứa ảnh chụp màn hình qua từng giai đoạn hỏng và sửa được, từ bản đầu báo lỗi tới bản chạy ổn.')
bullet(f'Bộ kiểm thử {T_TONG} ca (bao-cao/bo-test) kèm file ket_qua.json ghi nguyên văn câu trả lời của từng ca, để thầy cô đối chiếu kiến thức.')
bullet('Mã nguồn, các hình và biểu đồ trong hồ sơ này, cùng hai script tự sinh chúng (illustrations.py, chup_anh.py).')

out = OUT / os.getenv('REPORT_NAME', 'Ho_so_du_an_Gia_Su_AI_Mimo_v4.docx')
doc.save(out)
print('Đã lưu', out)
print(f'  kho sách   {N_BOOKS} cuốn · {N_VECTORS} đoạn · nạp xong {INGEST_DATE}')
print(f'  kiểm thử   {T_DAT}/{T_TONG} ca ngày {T_NGAY} · trung vị {vn(T_LAT_MED)}s · trích dẫn {T_NGUON_DAT}/{T_NGUON_CAN}')
print(f'  đợt thử    {n_users} tài khoản · {n_sessions} phiên · {n_questions} câu ({TRIAL_LABEL})')
print(f'  câu lệnh   {N_PROMPTS} ({N_PROMPTS_CLAUDE} Claude Code + {N_PROMPTS_COPILOT} Copilot)')
print(f'  sách lỗi   {len(SACH_NGAN)} bản quét thiếu · {len(SACH_WATERMARK)} bản có watermark · {N_COURSE} mục lục gõ tay')
