"""Tạo hồ sơ dự án (Word) từ dữ liệu thử nghiệm thật và các hình trong bao-cao/hinh-minh-hoa.

Chạy illustrations.py trước để có hình minh họa.
"""
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
N_VECTORS = 719   # /api/health ngày 14/9/2026
N_TESTS = 194     # pytest ngày 14/9/2026
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


fig, ax = plt.subplots(figsize=(7.5, 3.4))
hbar(ax, [f'{s} – {g}' for s, g, _ in sessions], [n for *_, n in sessions])
ax.set_xlabel('Số cuộc trò chuyện')
ax.set_title('Nhóm đã thử hỏi Mimo ở những môn nào?', loc='left', weight='bold', color=NAVY)
chart_sessions = save(fig, 'bieu_do1_phien_theo_mon.png')

fig, ax = plt.subplots(figsize=(7.5, 3.3))
ax.hist(latency, bins=[0, 3, 6, 9, 12, 15, 18, 21, 24], color=MUTED, edgecolor='white')
ax.axvline(lat_med, color=CORAL, lw=2.2)
ax.text(lat_med + 0.3, ax.get_ylim()[1] * 0.9, f'một nửa số câu xong dưới {vn(lat_med)} giây', color=CORAL, weight='bold')
ax.set_xlabel('Số giây từ lúc gửi đến khi Mimo trả lời xong')
ax.set_ylabel('Số câu trả lời')
ax.set_title('Mimo trả lời nhanh cỡ nào?', loc='left', weight='bold', color=NAVY)
chart_latency = save(fig, 'bieu_do2_thoi_gian_phan_hoi.png')

fig, ax = plt.subplots(figsize=(7.5, 2.9))
hbar(ax, ['Không đánh giá\n(chào hỏi, tâm sự)', 'Mất gốc', 'Hiểu sơ', 'Đã hiểu'],
     [understanding.get('none', 0), understanding.get('mất gốc', 0), understanding.get('hiểu sơ', 0), understanding.get('đã hiểu', 0)], highlight=2)
ax.set_xlabel('Số lượt trả lời')
ax.set_title('Sau mỗi lượt, Mimo đoán em hiểu bài tới đâu', loc='left', weight='bold', color=NAVY)
chart_understanding = save(fig, 'bieu_do3_muc_hieu_bai.png')


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
FULL = Cm(16)

normal = doc.styles['Normal']
normal.font.name = 'Times New Roman'; normal.font.size = Pt(13)
normal.element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
normal.paragraph_format.space_after = Pt(6)
normal.paragraph_format.line_spacing = 1.25
for name, size in (('Heading 1', 14), ('Heading 2', 13)):
    s = doc.styles[name]
    s.font.size = Pt(size); s.font.bold = True; s.font.color.rgb = RGBColor(0x1B, 0x2A, 0x4A)
    rf = s.element.rPr.rFonts
    for attr in ('w:asciiTheme', 'w:hAnsiTheme', 'w:eastAsiaTheme', 'w:cstheme'):
        rf.attrib.pop(qn(attr), None)
    for attr in ('w:ascii', 'w:hAnsi', 'w:eastAsia', 'w:cs'):
        rf.set(qn(attr), 'Times New Roman')
    s.paragraph_format.space_before = Pt(14 if name == 'Heading 1' else 8)
    s.paragraph_format.space_after = Pt(6)


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
    para(caption, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=11, after=12, color='555555')


def illustration(name, caption, width=FULL):
    figure(trimmed(FIG / f'{name}.png'), caption, width)


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
illustration('cong_cu', 'Hình 3. Dữ liệu và công cụ AI nhóm đã dùng')
doc.add_heading('Dữ liệu', level=2)
para(f'Dữ liệu quan trọng nhất là sách giáo khoa bộ Kết nối tri thức với cuộc sống: Toán 6 tập một, Toán 8 tập một và Khoa học tự nhiên 6. '
     f'Sách là file PDF dạng ảnh scan nên nhóm phải OCR để lấy chữ, rồi cắt thành {N_VECTORS} đoạn nhỏ và đưa lên Pinecone. '
     'Nhóm còn tự gõ lại mục lục từng cuốn (chương, bài, số trang) để lộ trình học đi đúng thứ tự trong sách và Mimo biết mỗi đoạn nằm ở trang mấy.')
para('Trong lúc học, hệ thống lưu thêm hồ sơ của học sinh (lớp, môn, bài đang học), lịch sử trò chuyện và kết quả luyện tập. '
     'Nhờ vậy lần sau em hỏi lại bài cũ, Mimo biết em từng sai ở đâu để giảng tiếp chứ không giảng lại từ đầu.')
doc.add_heading('Công cụ AI', level=2)
para('Gemini 3.5 Flash của Google là “bộ não” của Mimo: giảng bài, đọc ảnh đề, nghe giọng nói và soạn câu luyện tập. '
     'Khi dùng gói miễn phí bị hết lượt, hệ thống tự chuyển sang Gemini 3.5 Flash-Lite hoặc 3.6 Flash. '
     'Gemini Embedding biến mỗi đoạn sách và mỗi câu hỏi thành một dãy số (vector), còn Pinecone là nơi lưu các vector này '
     'để tìm ra đoạn sách gần nghĩa nhất với câu hỏi. Nút “Nghe giảng” dùng giọng đọc tiếng Việt HoaiMy của Microsoft Edge.')
para('Để viết code, nhóm dùng Claude Code (49 câu lệnh) và GitHub Copilot (29 câu lệnh). Tụi em nhờ các công cụ này đọc hiểu mã nguồn, tìm lỗi và viết kiểm thử. '
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
para('Toàn bộ 78 câu lệnh nhóm dùng với công cụ AI được lưu lại trong thư mục prompt-log (xem mục 8).')

# ---- 4
doc.add_heading('4. Sơ đồ mô tả dữ liệu đầu vào, quá trình xử lý bằng AI và kết quả đầu ra', level=1)
para('Trước khi Mimo trả lời được, sách giáo khoa phải được đưa vào kho. Việc này chỉ làm một lần cho mỗi cuốn sách.')
illustration('chuan_bi_du_lieu', 'Hình 4. Đưa sách giáo khoa vào kho dữ liệu')
para('Sau đó, mỗi lần học sinh hỏi, dữ liệu đi qua ba chặng như hình dưới.')
illustration('dau_vao_xu_ly_dau_ra', 'Hình 5. Dữ liệu đầu vào → Mimo xử lý → Kết quả đầu ra')
para('Lấy ví dụ một bạn lớp 8 gõ “đa thức là gì”. Câu hỏi được đổi thành vector rồi so với kho sách, tìm ra trang nói về đa thức trong Toán 8. '
     'Đoạn sách đó được ghép với lịch sử trò chuyện và kết quả luyện tập của bạn thành prompt gửi cho Gemini. '
     'Mimo trả lời bằng một ví dụ mua vở, mua bút cho dễ hình dung, gắn số [1] ở câu lấy từ sách để bạn bấm vào xem đúng trang, '
     'rồi hỏi lại một câu nhỏ để bạn tự kiểm tra xem mình hiểu chưa.')
para('Phần luyện tập chạy thành một vòng lặp. Câu nào làm đúng liên tiếp thì câu sau khó hơn, làm sai thì Mimo cho ôn lại và ưu tiên hỏi đúng chỗ em hay nhầm.')
illustration('vong_luyen_tap', 'Hình 6. Vòng luyện tập tự điều chỉnh độ khó', width=Cm(14))

# ---- 5
doc.add_heading('5. Hình ảnh quá trình thử nghiệm', level=1)
para('Mimo không làm một lần là chạy. Các ảnh dưới đây được chụp qua từng lần thử, từ lúc còn báo lỗi tới khi dùng được.')
shots = [
    ('anh_1', 'Hình 7. Bản đầu tiên: Mimo chưa đọc được kho sách nên chỉ báo lỗi “Không tìm thấy dữ liệu”.'),
    ('anh_3', 'Hình 8. Hỏi “giải thích cho em bài 1 trang 1” mà Mimo chỉ trả lời chưa tìm thấy thông tin. Nhóm phát hiện lỗi tìm kiếm và lỗi đăng nhập.'),
    ('anh_2', 'Hình 9. Lần đầu Mimo trả lời được từ sách Toán 8, nhưng công thức còn hiện ký hiệu thô và phần nguồn dính vào nhau.'),
    ('anh_dn1', 'Hình 10. Làm lại giao diện: tạo tài khoản bằng email và lớp, sau đó khảo sát để cá nhân hóa lộ trình.'),
    ('anh_4', 'Hình 11. Giao diện trò chuyện mới có lịch sử, nhãn môn và lớp, các nút nghe, sao chép, thích, không thích.'),
    ('anh_5', 'Hình 12. Thử với KHTN 6: bạn hỏi “tế bào nào cũng giống quả trứng ạ?”, Mimo sửa hiểu lầm rồi hỏi lại để bạn tự nhớ.'),
    ('anh_6', 'Hình 13. Kiểm tra cùng Claude Code: chạy bộ kiểm thử và xem số [n] có trỏ đúng trang sách bài “Đa thức” không.'),
]
for name, cap in shots:
    illustration(name, cap, width=Cm(13.5))
para('(Nhóm sẽ bổ sung ảnh các bạn học sinh dùng thử sản phẩm.)', italic=True, color='C0392B', indent=False)
para(f'Trong hai ngày 13 và 14/9/2026, nhóm tự dùng thử với {n_users} tài khoản, mở {n_sessions} cuộc trò chuyện và hỏi {n_questions} câu '
     f'(có {n_images} câu gửi kèm ảnh đề bài). Ba biểu đồ dưới đây lấy trực tiếp từ dữ liệu lưu trong lúc thử.')
figure(chart_sessions, 'Biểu đồ 1. Các cuộc trò chuyện thử ở 3 môn Toán, KHTN, Ngữ văn, lớp 6 đến 8', width=Cm(13))
figure(chart_latency, 'Biểu đồ 2. Thời gian trả lời. Chữ bắt đầu hiện ra sau vài giây, không phải chờ hết mới thấy.', width=Cm(13))
figure(chart_understanding, 'Biểu đồ 3. Mimo tự đoán mức hiểu bài để chọn cách giảng dễ hơn hoặc khó hơn', width=Cm(13))

# ---- 6
doc.add_heading('6. Kết quả trình diễn sản phẩm', level=1)
illustration('chuc_nang', 'Hình 14. Các chức năng chính của Mimo')
para('Khi trình diễn, nhóm đi theo đúng một buổi học của học sinh. Bạn tạo tài khoản, chọn môn và lớp, Mimo dựng lộ trình theo mục lục sách. '
     'Bạn chọn một bài rồi hỏi Mimo bằng cách gõ, chụp ảnh đề hoặc bấm micro nói. Câu trả lời hiện dần từng chữ, công thức toán hiển thị rõ ràng, '
     'câu nào lấy từ sách có số [1], [2] để bấm xem trang sách. Học xong, bạn bấm luyện tập để làm vài câu trắc nghiệm vừa sức, '
     'hoặc bật Pomodoro để học tập trung. Với môn chưa có sách trong kho, Mimo tự soạn lộ trình theo chương trình GDPT 2018 '
     f'(đã tạo {n_ai_roadmaps} lộ trình như Toán 7, Toán 9, Ngữ văn 6 đến 8, Tiếng Anh 7 và 8).')
illustration('con_so', 'Hình 15. Một vài con số sau khi thử nghiệm')
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
    ['Kho mới có 3 cuốn sách. Các môn và lớp khác chưa có trích dẫn trang.', 'Đưa thêm sách Toán, KHTN, Ngữ văn lớp 6 đến 9, cả tập hai.'],
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
bullet('File PROMPT_HISTORY.md ghi 78 câu lệnh nhóm dùng với Claude Code và GitHub Copilot, kèm thời gian.')
bullet('File PROMPT_LOG.md là nhật ký câu lệnh ghi tự động khi sửa lỗi và hoàn thiện sản phẩm.')
bullet('Thư mục Anh_cac_giai_doan chứa ảnh chụp màn hình qua từng giai đoạn (Hình 7 đến 13).')
bullet('Mã nguồn, bộ kiểm thử và các hình, biểu đồ trong hồ sơ này.')

out = OUT / 'Ho_so_du_an_Gia_Su_AI_Mimo_v2.docx'
doc.save(out)
print('saved', out)
