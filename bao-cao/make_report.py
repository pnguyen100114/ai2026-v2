"""Tạo hồ sơ dự án (Word) từ dữ liệu thử nghiệm thật và các hình trong bao-cao/hinh-minh-hoa.

Chạy illustrations.py trước để có hình minh họa.
"""
import json
import os
import re
import sqlite3
import statistics as st
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

# ---------------------------------------------------------------- số liệu từ database thử nghiệm
db = sqlite3.connect(ROOT / 'backend' / 'local.db')
q = lambda s: db.execute(s).fetchall()
n_users = q('select count(*) from users')[0][0]
n_sessions = q('select count(*) from chat_sessions')[0][0]
n_questions = q("select count(*) from messages where role='user'")[0][0]
n_images = q("select count(*) from messages where role='user' and has_image=1")[0][0]
latency = [r[0] / 1000 for r in q("select latency_ms from messages where role='assistant' and latency_ms is not null")]
lat_med = st.median(latency)
cited = q("select count(*) from messages where role='assistant' and sources not in ('[]','') and sources is not null")[0][0]
sessions = q('select subject, grade, count(*) from chat_sessions group by subject, grade order by count(*)')
understanding = dict(q("select coalesce(understanding,'none'), count(*) from messages where role='assistant' group by 1"))
quiz_total = q('select count(*) from quiz_attempts')[0][0]
n_ai_roadmaps = q('select count(*) from ai_roadmaps')[0][0]
# Số sách và số đoạn lấy thẳng từ sổ nạp sách, để hồ sơ không bao giờ lệch với kho thật.
_manifest = json.loads((ROOT / 'backend' / 'rag' / '.ingest_manifest.json').read_text(encoding='utf-8'))
N_BOOKS = len(_manifest)
N_VECTORS = sum(book['chunks'] for book in _manifest.values())
INGEST_DATE = max(book['ingested_at'] for book in _manifest.values())[:10]
INGEST_DATE = f'{INGEST_DATE[8:10]}/{INGEST_DATE[5:7]}/{INGEST_DATE[:4]}'

# Số câu lệnh lấy từ prompt-log/PROMPT_HISTORY.md (chạy scripts/prompt-log/export-history.cjs để cập nhật).
_history = (ROOT / 'prompt-log' / 'PROMPT_HISTORY.md').read_text(encoding='utf-8')
_count = lambda label: int(re.search(rf'\|\s*{label}\s*\|\s*\**(\d+)', _history).group(1))
N_PROMPTS_CLAUDE, N_PROMPTS_COPILOT = _count('Claude Code'), _count('GitHub Copilot')
N_PROMPTS = N_PROMPTS_CLAUDE + N_PROMPTS_COPILOT
N_TESTS = 214     # pytest ngày 17/9/2026: 214 passed
vn = lambda x: f'{x:.1f}'.replace('.', ',')


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


# Hai biểu đồ cột ghép chung một hình: để rời nhau thì hồ sơ vượt 8 trang theo yêu cầu BTC.
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

# Hai biểu đồ trên, xuất thêm bản rời để chiếu toàn màn hình trong video thuyết trình.
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

fig, ax = plt.subplots(figsize=(7.5, 3.0))
ax.hist(latency, bins=[0, 3, 6, 9, 12, 15, 18, 21, 24], color=MUTED, edgecolor='white')
ax.axvline(lat_med, color=CORAL, lw=2.2)
ax.text(lat_med + 0.3, ax.get_ylim()[1] * 0.9, f'một nửa số câu xong dưới {vn(lat_med)} giây', color=CORAL, weight='bold')
ax.set_xlabel('Số giây từ lúc gửi đến khi Mimo trả lời xong')
ax.set_ylabel('Số câu trả lời')
ax.set_title('Mimo trả lời nhanh cỡ nào?', loc='left', weight='bold', color=NAVY)
chart_latency = save(fig, 'bieu_do2_thoi_gian_phan_hoi.png')


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


# ---------------------------------------------------------------- Word
doc = Document()
sec = doc.sections[0]
sec.page_height, sec.page_width = Cm(29.7), Cm(21)
sec.left_margin, sec.right_margin, sec.top_margin, sec.bottom_margin = Cm(3), Cm(2), Cm(2), Cm(2)
FULL = Cm(14)   # hình minh họa thu từ 16cm xuống 14cm để hồ sơ vừa 8 trang

normal = doc.styles['Normal']
normal.font.name = 'Times New Roman'; normal.font.size = Pt(13)
normal.element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
# Giãn dòng và khoảng cách đoạn ép sát mức còn dễ đọc: hồ sơ phải vừa 8 trang theo yêu cầu BTC.
normal.paragraph_format.space_after = Pt(4)
normal.paragraph_format.line_spacing = 1.15
for name, size in (('Heading 1', 14), ('Heading 2', 13)):
    s = doc.styles[name]
    s.font.size = Pt(size); s.font.bold = True; s.font.color.rgb = RGBColor(0x1B, 0x2A, 0x4A)
    rf = s.element.rPr.rFonts
    for attr in ('w:asciiTheme', 'w:hAnsiTheme', 'w:eastAsiaTheme', 'w:cstheme'):
        rf.attrib.pop(qn(attr), None)
    for attr in ('w:ascii', 'w:hAnsi', 'w:eastAsia', 'w:cs'):
        rf.set(qn(attr), 'Times New Roman')
    s.paragraph_format.space_before = Pt(10 if name == 'Heading 1' else 6)
    s.paragraph_format.space_after = Pt(4)


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
    para(caption, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=11, after=8, color='555555')


def illustration(name, caption, width=FULL):
    figure(trimmed(FIG / f'{name}.png'), caption, width)


def screenshot(name, caption, width=FULL):
    """Ảnh chụp màn hình sản phẩm đang chạy (bao-cao/anh-san-pham)."""
    figure(SHOT / f'{name}.png', caption, width)


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


# ---- bìa
para('**HỒ SƠ DỰ ÁN**', align=WD_ALIGN_PARAGRAPH.CENTER, size=16, after=2)
para('**MIMO – GIA SƯ AI HỌC THEO SÁCH GIÁO KHOA CHO HỌC SINH THCS**', align=WD_ALIGN_PARAGRAPH.CENTER, size=14, after=10)
for line in ('Tên đội: ……………………………………………', 'Học sinh thực hiện: ……………………………………………',
             'Trường: ……………………………………………', 'Giáo viên hướng dẫn: ……………………………………………'):
    para(line, align=WD_ALIGN_PARAGRAPH.CENTER, after=0)
para('', after=8)

# ---- 1
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

# ---- 2
doc.add_heading('2. Đối tượng sử dụng', level=1)
illustration('doi_tuong', 'Hình 2. Những ai dùng và được lợi từ Mimo')
para('Người dùng chính là học sinh từ lớp 6 đến lớp 9. Các bạn cần được giải đáp ngay lúc đang tự học, cần hiểu cách làm chứ không chỉ có đáp số, '
     'và cần bài luyện tập vừa sức để không bị nản.')
para('Phụ huynh là người được lợi gián tiếp. Con có người kèm bài mà không tốn tiền gia sư, bố mẹ cũng yên tâm hơn vì Mimo không làm bài hộ '
     'và biết khuyên con nói với người lớn khi gặp chuyện không hay.')
para('Thầy cô cũng được lợi vì học sinh ôn ở nhà đúng nội dung, đúng thuật ngữ trong sách thầy cô đang dạy. '
     'Lịch sử hỏi đáp và lượt bấm thích hay không thích cho thấy các bạn thường vướng ở phần nào.')

# ---- 3
doc.add_heading('3. Dữ liệu, câu lệnh, công cụ trí tuệ nhân tạo đã sử dụng', level=1)
doc.add_heading('Dữ liệu', level=2)
para(f'Dữ liệu quan trọng nhất là sách giáo khoa bộ Kết nối tri thức với cuộc sống: đủ {N_BOOKS} cuốn của 5 môn Toán, Ngữ văn, '
     f'Tiếng Anh, Khoa học tự nhiên, Lịch sử và Địa lí cho cả bốn lớp 6, 7, 8, 9 (môn nào có hai tập thì nạp cả hai). '
     f'Sách là file PDF dạng ảnh scan nên nhóm phải OCR để lấy chữ, rồi cắt thành {N_VECTORS} đoạn nhỏ, nạp xong ngày {INGEST_DATE}. '
     'Nhóm còn tự gõ lại mục lục từng cuốn (chương, bài, số trang) để lộ trình học đi đúng thứ tự trong sách và Mimo biết mỗi đoạn nằm ở trang mấy.')
para('Trong lúc học, hệ thống lưu thêm hồ sơ của học sinh (lớp, môn, bài đang học), lịch sử trò chuyện và kết quả luyện tập. '
     'Nhờ vậy lần sau em hỏi lại bài cũ, Mimo biết em từng sai ở đâu để giảng tiếp chứ không giảng lại từ đầu.')
doc.add_heading('Công cụ AI', level=2)
para('Bảng dưới là toàn bộ công cụ AI, mô hình, API và thư viện nhóm đã dùng, kèm phần nào tự viết, phần nào AI hỗ trợ, phần nào kế thừa nguồn mở.')
table(['Công cụ / thư viện', 'Vai trò trong sản phẩm', 'Nguồn'], [
    ['gemini-3.1-flash-lite (Google)', 'Mô hình chính: giảng bài, đọc ảnh đề, soạn câu luyện tập.', 'API trả phí theo lượt, gói miễn phí'],
    ['gemini-3.5-flash-lite, gemini-3.5-flash', 'Mô hình dự phòng, tự chuyển khi mô hình chính hết lượt.', 'API Google'],
    ['gemini-embedding-001 (1536 chiều)', 'Biến mỗi đoạn sách và mỗi câu hỏi thành vector để so nghĩa.', 'API Google'],
    ['Kho vector trong cơ sở dữ liệu dự án', 'Lưu 4765 vector đoạn sách, tìm đoạn gần nghĩa nhất. Nhóm tự viết (rag/vector_store.py) để thay Pinecone, vì gói Pinecone miễn phí tính hạn mức theo lượt đọc nên hết hạn mức là sản phẩm ngừng trả lời.', 'Nhóm tự viết'],
    ['PyMuPDF, pypdf, edge-tts, FastAPI, Uvicorn, SQLAlchemy, PyJWT, React, Vite, TypeScript, KaTeX',
     'Đọc chữ và cắt trang sách PDF; giọng đọc tiếng Việt HoaiMy; máy chủ, cơ sở dữ liệu, đăng nhập; giao diện web và hiển thị công thức toán.', 'Nguồn mở'],
    ['Claude Code, GitHub Copilot', f'Hỗ trợ viết mã: đọc hiểu mã nguồn, tìm lỗi, viết kiểm thử. {N_PROMPTS} câu lệnh, xem mục 8.', 'Công cụ AI lập trình'],
], [4.6, 8.4, 3.0])
para(f'Phần nhóm tự xây dựng: toàn bộ luồng học (lộ trình theo mục lục sách, hỏi bài có trích dẫn trang, luyện tập thích ứng, lọc tin nhắn nguy hiểm), '
     f'kho vector, mục lục {N_BOOKS} cuốn sách gõ tay và {N_TESTS} ca kiểm thử. '
     'Phần AI hỗ trợ: gợi ý cách sửa lỗi và viết nháp một số hàm, nhóm đọc lại và tự chịu trách nhiệm về kết quả. '
     'Phần kế thừa nguồn mở: các thư viện trong bảng trên, dùng đúng giấy phép của từng thư viện.')
para(f'Để viết code, nhóm dùng Claude Code ({N_PROMPTS_CLAUDE} câu lệnh) và GitHub Copilot ({N_PROMPTS_COPILOT} câu lệnh). Tụi em nhờ các công cụ này đọc hiểu mã nguồn, tìm lỗi và viết kiểm thử. '
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

# ---- 4
doc.add_heading('4. Sơ đồ mô tả dữ liệu đầu vào, quá trình xử lý bằng AI và kết quả đầu ra', level=1)
para('Trước khi Mimo trả lời được, sách giáo khoa phải được đưa vào kho. Việc này chỉ làm một lần cho mỗi cuốn sách.')
illustration('chuan_bi_du_lieu', 'Hình 3. Đưa sách giáo khoa vào kho dữ liệu')
para('Sau đó, mỗi lần học sinh hỏi, dữ liệu đi qua ba chặng như hình dưới.')
illustration('dau_vao_xu_ly_dau_ra', 'Hình 4. Dữ liệu đầu vào → Mimo xử lý → Kết quả đầu ra')
para('Lấy ví dụ một bạn lớp 8 gõ “đa thức là gì”. Câu hỏi được đổi thành vector rồi so với kho sách, tìm ra trang nói về đa thức trong Toán 8. '
     'Đoạn sách đó được ghép với lịch sử trò chuyện và kết quả luyện tập của bạn thành prompt gửi cho Gemini. '
     'Mimo trả lời bằng một ví dụ mua vở, mua bút cho dễ hình dung, gắn số [1] ở câu lấy từ sách để bạn bấm vào xem đúng trang, '
     'rồi hỏi lại một câu nhỏ để bạn tự kiểm tra xem mình hiểu chưa.')
para('Phần luyện tập chạy thành một vòng lặp. Câu nào làm đúng liên tiếp thì câu sau khó hơn, làm sai thì Mimo cho ôn lại và ưu tiên hỏi đúng chỗ em hay nhầm.')
illustration('vong_luyen_tap', 'Hình 5. Vòng luyện tập tự điều chỉnh độ khó', width=Cm(14))

# ---- 5
doc.add_heading('5. Hình ảnh quá trình thử nghiệm', level=1)
para('Mimo không làm một lần là chạy. Bản đầu chỉ báo “Không tìm thấy dữ liệu”, bản sau trả lời được nhưng công thức toán hiện ký hiệu thô '
     'và phần nguồn dính vào nhau. Nhóm sửa qua nhiều lần thử mới ra sản phẩm dưới đây. Ảnh chụp từng giai đoạn hỏng và sửa được để trong thư mục '
     'minh chứng ở mục 8; phần này chỉ đưa ảnh sản phẩm đang chạy.')
screenshot('sp_5_lotrinh_crop', 'Hình 6. Lộ trình học dựng theo đúng mục lục sách giáo khoa, mỗi bài có tên chương, tên bài và số trang.', width=Cm(14.5))
screenshot('sp_6_hoibai_crop', 'Hình 7. Mimo giảng bài Đơn thức (Toán 8) và gắn số [1] vào câu lấy từ sách, kèm ảnh nhỏ của trang được trích.', width=Cm(14.5))
para('(Nhóm sẽ bổ sung ảnh các bạn học sinh dùng thử sản phẩm.)', italic=True, color='C0392B', indent=False)
para(f'Trong hai ngày 13 và 14/9/2026, nhóm tự dùng thử với {n_users} tài khoản, mở {n_sessions} cuộc trò chuyện và hỏi {n_questions} câu '
     f'(có {n_images} câu gửi kèm ảnh đề bài). Hai biểu đồ dưới đây lấy trực tiếp từ dữ liệu lưu trong lúc thử.')
figure(chart_mon_hieu, 'Biểu đồ 1. Trái: các cuộc trò chuyện thử ở 3 môn Toán, KHTN, Ngữ văn, lớp 6 đến 8. '
                       'Phải: mức hiểu bài Mimo tự đoán sau mỗi lượt để chọn cách giảng dễ hơn hoặc khó hơn.', width=Cm(14))
figure(chart_latency, 'Biểu đồ 2. Thời gian trả lời. Chữ bắt đầu hiện ra sau vài giây, không phải chờ hết mới thấy.', width=Cm(13))

# ---- 6
doc.add_heading('6. Kết quả trình diễn sản phẩm', level=1)
illustration('chuc_nang', 'Hình 8. Các chức năng chính của Mimo')
para('Khi trình diễn, nhóm đi theo đúng một buổi học của học sinh. Bạn tạo tài khoản, chọn môn và lớp, Mimo dựng lộ trình theo mục lục sách. '
     'Bạn chọn một bài rồi hỏi Mimo bằng cách gõ, chụp ảnh đề hoặc bấm micro nói. Câu trả lời hiện dần từng chữ, công thức toán hiển thị rõ ràng, '
     'câu nào lấy từ sách có số [1], [2] để bấm xem trang sách. Học xong, bạn bấm luyện tập để làm vài câu trắc nghiệm vừa sức, '
     f'hoặc bật Pomodoro để học tập trung. Với môn hoặc lớp nằm ngoài {N_BOOKS} cuốn trong kho, Mimo vẫn tự soạn lộ trình theo chương trình GDPT 2018 '
     f'(trong lúc thử nghiệm, khi kho còn ít sách, Mimo đã tự soạn {n_ai_roadmaps} lộ trình kiểu này).')
screenshot('sp_8_luyentap_crop', 'Hình 9. Luyện tập: Mimo soạn câu riêng cho bài đang học, có mức độ khó và phần trăm nắm bài.', width=Cm(14.5))
illustration('con_so', 'Hình 10. Một vài con số sau khi thử nghiệm')
para('Kết quả nhóm thấy rõ nhất:')
bullet(f'Câu hỏi kiến thức Toán 6, Toán 8, KHTN 6 đều có trích dẫn trang sách. Có {cited} trên {n_questions} lượt trả lời gắn nguồn; '
       'những lượt còn lại là chào hỏi, tâm sự hoặc môn chưa có sách, và Mimo không bịa ra nguồn cho các lượt đó.')
bullet('Khi bạn gửi bài tập, Mimo gợi ý bước đầu rồi hỏi lại, chỉ đưa lời giải đầy đủ khi bạn xin. Các nút gợi ý trả lời nhanh cũng được lọc để không lộ đáp án.')
bullet('Nhóm thử nhắn “em không muốn sống nữa”. Mimo trả lời nhẹ nhàng, khuyên bạn nói ngay với người lớn và đưa số Tổng đài 111, 115, 113. '
       'Phần nhắc số điện thoại vẫn hiện ra kể cả khi Gemini bị lỗi hoặc hết lượt.')
bullet(f'Một nửa số câu Mimo trả lời xong trong khoảng {vn(lat_med)} giây. Luyện tập chạy đúng: {quiz_total} lượt trả lời thử, '
       f'mức nắm bài và độ khó thay đổi theo đúng hay sai. {N_TESTS} ca kiểm thử tự động của phần máy chủ đều đạt.')

# ---- 7
doc.add_heading('7. Hạn chế và hướng cải tiến', level=1)
para('Mimo vẫn còn nhiều chỗ nhóm muốn làm tốt hơn:')
table(['Còn hạn chế', 'Nhóm dự định'], [
    ['Ba cuốn nạp sớm nhất mới quét được một phần (Toán 6 tập một đến trang 62, Toán 8 tập một đến trang 37, '
     'KHTN 6 đến trang 192) nên phần sau của ba cuốn này chưa có trích dẫn trang.', 'Quét nốt số trang còn thiếu và nạp lại ba cuốn đó.'],
    ['OCR còn đọc sai một số công thức và hình vẽ.', 'Soát lại chữ theo từng trang, lưu kèm ảnh hình vẽ để Gemini nhìn trực tiếp.'],
    [f'Dùng gói Gemini miễn phí nên có lúc quá tải; trả lời mất khoảng {vn(lat_med)} giây.', 'Lưu sẵn câu trả lời cho câu hỏi hay gặp, rút gọn prompt.'],
    [f'Mới thử trong nhóm ({n_users} tài khoản, {n_questions} câu hỏi).', 'Cho 1 đến 2 lớp dùng thử, làm phiếu khảo sát và so điểm trước, sau.'],
    ['Luyện tập mới có trắc nghiệm, chưa chấm được bài tự luận viết tay.', 'Thêm câu điền đáp án; chụp bài làm để Mimo nhận xét từng bước.'],
    ['Chưa có trang riêng cho thầy cô và phụ huynh.', 'Làm bảng theo dõi tiến độ lớp và báo cáo hằng tuần cho phụ huynh.'],
    ['Lọc tin nhắn nguy hiểm dựa vào từ khóa nên có thể sót cách nói tránh.', 'Kết hợp AI nhận biết cảm xúc, báo cho thầy cô tư vấn khi cần.'],
], [8.0, 8.0])

# ---- 8
doc.add_heading('8. Lịch sử câu lệnh và hình ảnh minh chứng quá trình phát triển sản phẩm', level=1)
para('Link thư mục Google Drive (đã mở quyền xem cho bất kỳ ai có link):', indent=False)
para('https://drive.google.com/drive/folders/……………………………… (nhóm dán link sau khi tải lên)', italic=True, color='C0392B', indent=False)
para('Trong thư mục có:', indent=False)
bullet(f'File PROMPT_HISTORY.md ghi {N_PROMPTS} câu lệnh ({N_PROMPTS_CLAUDE} Claude Code, {N_PROMPTS_COPILOT} GitHub Copilot), kèm thời gian từng câu.')
bullet('File PROMPT_LOG.md là nhật ký câu lệnh ghi tự động khi sửa lỗi và hoàn thiện sản phẩm.')
bullet('Thư mục Anh_cac_giai_doan chứa ảnh chụp màn hình qua từng giai đoạn hỏng và sửa được, từ bản đầu báo lỗi tới bản chạy ổn.')
bullet('Mã nguồn, bộ kiểm thử và các hình, biểu đồ trong hồ sơ này.')

out = OUT / os.getenv('REPORT_NAME', 'Ho_so_du_an_Gia_Su_AI_Mimo_v3.docx')
doc.save(out)
print('saved', out)
