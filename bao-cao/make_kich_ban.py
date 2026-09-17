"""Xuất kịch bản video thuyết trình ra file Word để in cầm tay lúc quay.

Nguồn duy nhất là KICH_BAN_VIDEO_THUYET_TRINH.md — sửa chữ thì sửa ở đó rồi chạy lại script này,
đừng sửa thẳng trong Word, lần chạy sau sẽ ghi đè.

Chạy slides.py trước để có ảnh slide chèn vào cảnh 4 và cảnh 7.
"""
import re
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'bao-cao'
SRC = OUT / 'KICH_BAN_VIDEO_THUYET_TRINH.md'
DOCX = OUT / 'Kich_ban_video_thuyet_trinh.docx'

CORAL, NAVY, GREY = 'F2704F', '1B2A4A', '6B7280'

# Ảnh chèn thêm vào từng cảnh, đặt ngay trước phần LỜI.
SLIDES = {
    'Cảnh 4': [(OUT / 'slides' / 'so_do_kien_truc.png',
                'Slide sơ đồ kiến trúc, bản đầy đủ. Năm bản dựng dần b1–b5 nằm trong bao-cao/slides/')],
    'Cảnh 6': [(OUT / 'slides' / 'doi_kho_vector.png',
                'Slide đổi kho vector, cắt vào từ câu "chỗ phải sửa lớn nhất là chính kho sách"')],
    'Cảnh 7': [(OUT / 'slides' / 'slide_ket.png', 'Slide kết')],
}

# ---------------------------------------------------------------- tách markdown thành khối
def parse(md):
    lines = md.splitlines()
    blocks, i = [], 0
    while i < len(lines):
        ln = lines[i]
        if not ln.strip() or ln.strip() == '---':
            i += 1
        elif ln.startswith('# '):
            blocks.append(('title', ln[2:].strip())); i += 1
        elif ln.startswith('## '):
            blocks.append(('h1', ln[3:].strip())); i += 1
        elif ln.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                rows.append([c.strip() for c in lines[i].strip().strip('|').split('|')])
                i += 1
            blocks.append(('table', [r for r in rows if not all(set(c) <= set('-: ') for c in r)]))
        elif ln.startswith('>'):
            group = []
            while i < len(lines) and lines[i].startswith('>'):
                group.append(lines[i].lstrip('>').strip()); i += 1
            paras, cur = [], []
            for g in group:                       # dòng `>` trống là chỗ ngắt đoạn trong khối trích
                if g:
                    cur.append(g)
                elif cur:
                    paras.append(' '.join(cur)); cur = []
            if cur:
                paras.append(' '.join(cur))
            blocks.append(('quote', paras))
        elif re.match(r'(- |\d+\. )', ln):
            items = []
            while i < len(lines) and lines[i].strip():
                if re.match(r'(- |\d+\. )', lines[i]):
                    items.append([lines[i][0].isdigit(), re.sub(r'^(- |\d+\. )', '', lines[i]).rstrip()])
                else:
                    items[-1][1] += ' ' + lines[i].strip()   # dòng tiếp của cùng một gạch đầu dòng
                i += 1
            blocks.append(('list', items))
        else:
            text = []
            while i < len(lines) and lines[i].strip() and not re.match(r'[#>|]|- |\d+\. ', lines[i]) \
                    and lines[i].strip() != '---':
                text.append(lines[i].strip()); i += 1
            blocks.append(('para', ' '.join(text)))
    return blocks


# ---------------------------------------------------------------- dựng file Word
doc = Document()
sec = doc.sections[0]
sec.page_height, sec.page_width = Cm(29.7), Cm(21)
sec.left_margin, sec.right_margin, sec.top_margin, sec.bottom_margin = Cm(2.2), Cm(2), Cm(2), Cm(2)
WIDTH = Cm(15)

normal = doc.styles['Normal']
normal.font.name = 'Times New Roman'; normal.font.size = Pt(12)
normal.element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
normal.paragraph_format.space_after = Pt(5)
normal.paragraph_format.line_spacing = 1.15
for name, size in (('Heading 1', 15), ('Heading 2', 13)):
    s = doc.styles[name]
    s.font.size = Pt(size); s.font.bold = True; s.font.color.rgb = RGBColor.from_string(NAVY)
    rf = s.element.rPr.rFonts
    for attr in ('w:asciiTheme', 'w:hAnsiTheme', 'w:eastAsiaTheme', 'w:cstheme'):
        rf.attrib.pop(qn(attr), None)
    for attr in ('w:ascii', 'w:hAnsi', 'w:eastAsia', 'w:cs'):
        rf.set(qn(attr), 'Times New Roman')
    s.paragraph_format.space_before = Pt(14)
    s.paragraph_format.space_after = Pt(6)


def runs(p, text, italic=False, size=None, color=None, bold_all=False):
    """Hiểu **đậm** và `mã` trong markdown."""
    for chunk in re.split(r'(\*\*[^*]+\*\*|`[^`]+`)', text):
        if not chunk:
            continue
        r = p.add_run(chunk.strip('*`'))
        r.bold = bold_all or chunk.startswith('**')
        r.italic = italic
        if chunk.startswith('`'):
            r.font.name = 'Consolas'
            r.font.size = Pt((size or 12) - 1.5)
            r.font.color.rgb = RGBColor.from_string(CORAL)
        else:
            if size:
                r.font.size = Pt(size)
            if color:
                r.font.color.rgb = RGBColor.from_string(color)


def bar(p, color):
    """Vạch màu dọc bên trái đoạn, cho dễ phân biệt lời nói với ghi chú."""
    pbdr = OxmlElement('w:pBdr')
    left = OxmlElement('w:left')
    left.set(qn('w:val'), 'single'); left.set(qn('w:sz'), '18')
    left.set(qn('w:space'), '8'); left.set(qn('w:color'), color)
    pbdr.append(left)
    p._p.get_or_add_pPr().append(pbdr)


def para(text, **kw):
    align = kw.pop('align', None)
    after = kw.pop('after', None)
    indent = kw.pop('indent', None)
    spacing = kw.pop('spacing', None)
    p = doc.add_paragraph()
    runs(p, text, **kw)
    if align is not None:
        p.alignment = align
    if after is not None:
        p.paragraph_format.space_after = Pt(after)
    if indent is not None:
        p.paragraph_format.left_indent = Cm(indent)
    if spacing is not None:
        p.paragraph_format.line_spacing = spacing
    return p


def table(rows):
    t = doc.add_table(rows=0, cols=len(rows[0]))
    t.style = 'Table Grid'; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for n, row in enumerate(rows):
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].paragraphs[0].paragraph_format.space_after = Pt(2)
            runs(cells[i].paragraphs[0], v, size=11, bold_all=n == 0)
            if n == 0:
                shd = OxmlElement('w:shd')
                shd.set(qn('w:val'), 'clear'); shd.set(qn('w:fill'), 'FDE7E0')
                cells[i]._tc.get_or_add_tcPr().append(shd)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def picture(path, caption):
    doc.add_picture(str(path), width=WIDTH)
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.paragraphs[-1].paragraph_format.keep_with_next = True
    para(caption, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=10.5, color=GREY, after=10)


scene, in_loi = '', False
for kind, payload in parse(SRC.read_text(encoding='utf-8')):
    if kind == 'title':
        para(payload, align=WD_ALIGN_PARAGRAPH.CENTER, size=16, color=NAVY, after=12, bold_all=True)
    elif kind == 'h1':
        doc.add_heading(payload, level=1)
        scene, in_loi = payload.split(' —')[0].strip(), False
    elif kind == 'table':
        table(payload)
    elif kind == 'list':
        for ordered, item in payload:
            box = item.startswith('[')                 # ô đánh dấu trong phần "Trước khi quay"
            p = doc.add_paragraph(style=None if box else ('List Number' if ordered else 'List Bullet'))
            p.paragraph_format.space_after = Pt(3)
            if box:
                p.paragraph_format.left_indent = Cm(0.6)
                runs(p, ('☑ ' if item[1].lower() == 'x' else '☐ ') + item[3:].strip())
            else:
                runs(p, item)
    elif kind == 'quote':
        for text in payload:
            # Chỉ khối trích nằm sau **LỜI:** mới là câu phải nói; còn lại là ghi chú cho người quay.
            spoken = in_loi and not text.startswith(('💡', '⚠️', '✔️'))
            p = para(text.lstrip('💡⚠️✔️ '), italic=not spoken, size=13.5 if spoken else 11,
                     color=NAVY if spoken else GREY, indent=0.6, after=6,
                     spacing=1.35 if spoken else None)
            bar(p, CORAL if spoken else 'B7791F')
    else:
        if payload.startswith('**LỜI:**'):
            in_loi = True
            for path, caption in SLIDES.get(scene, []):
                picture(path, caption)
        para(payload, after=6, color=GREY if payload.startswith('**HÌNH:**') else None)

doc.save(DOCX)
print('ok', DOCX.name)
