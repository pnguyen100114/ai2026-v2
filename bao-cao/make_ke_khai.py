"""Kê khai công cụ AI / API / thư viện / mã nguồn mở — nộp kèm hồ sơ (mục 8).

Cùng nguyên tắc với make_report.py: không gõ tay phiên bản nào. Mọi con số đọc từ nguồn của nó:

    thư viện backend    backend/requirements.txt
    thư viện giao diện  package.json
    mô hình Gemini      backend/app.py, backend/rag/embeddings.py
    giọng đọc           backend/speech.py
    câu lệnh AI         prompt-log/PROMPT_HISTORY.md

Giấy phép thì phải tra tay (requirements.txt không ghi), nên nằm thẳng trong các bảng dưới đây;
đổi thư viện thì sửa ở đúng một chỗ.

Chạy:  .venv\\Scripts\\python.exe bao-cao\\make_ke_khai.py [thư mục đích]
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'bao-cao'
OUT.mkdir(parents=True, exist_ok=True)

NAVY = '1B2A4A'

# ---------------------------------------------------------------- đọc phiên bản từ nguồn thật
_req = (ROOT / 'backend' / 'requirements.txt').read_text(encoding='utf-8')
_pkg = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))
_app = (ROOT / 'backend' / 'app.py').read_text(encoding='utf-8')
_emb = (ROOT / 'backend' / 'rag' / 'embeddings.py').read_text(encoding='utf-8')
_speech = (ROOT / 'backend' / 'speech.py').read_text(encoding='utf-8')
_history = (ROOT / 'prompt-log' / 'PROMPT_HISTORY.md').read_text(encoding='utf-8')


def pyver(ten):
    """Phiên bản khai trong requirements.txt: 'fastapi==0.115.0' -> '0.115.0'."""
    m = re.search(rf'^{re.escape(ten)}(\[[^\]]*\])?\s*([=<>~!][^#\n]*)', _req, re.M | re.I)
    return m.group(2).strip().lstrip('=') if m else '—'


def npmver(ten):
    return (_pkg['dependencies'].get(ten) or _pkg['devDependencies'].get(ten) or '—').lstrip('^~')


MODEL = re.search(r"GEMINI_MODEL = os\.getenv\('GEMINI_MODEL', '([^']+)'\)", _app).group(1)
FALLBACK = re.search(r"getenv\('GEMINI_FALLBACK_MODELS',\s*'([^']+)'", _app).group(1)
EMBED = re.search(r'EMBEDDING_MODEL = os\.getenv\(\s*"EMBEDDING_MODEL",\s*"([^"]+)"', _emb).group(1)
VOICE = re.search(r"TTS_VOICE = os\.getenv\('TTS_VOICE', '([^']+)'\)", _speech).group(1)
_count = lambda label: int(re.search(rf'\|\s*{label}\s*\|\s*\**(\d+)', _history).group(1))
N_CLAUDE, N_COPILOT = _count('Claude Code'), _count('GitHub Copilot')

# ---------------------------------------------------------------- Word
doc = Document()
sec = doc.sections[0]
sec.page_height, sec.page_width = Cm(29.7), Cm(21)
sec.left_margin, sec.right_margin, sec.top_margin, sec.bottom_margin = Cm(3), Cm(2), Cm(2), Cm(2)

normal = doc.styles['Normal']
normal.font.name = 'Times New Roman'
normal.font.size = Pt(13)
normal.element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
normal.paragraph_format.space_after = Pt(5)
normal.paragraph_format.line_spacing = 1.2
for name, size in (('Heading 1', 14), ('Heading 2', 13)):
    s = doc.styles[name]
    s.font.size = Pt(size)
    s.font.bold = True
    s.font.color.rgb = RGBColor(0x1B, 0x2A, 0x4A)
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


def para(text, italic=False, align=None, size=None, color=None, indent=False):
    p = doc.add_paragraph()
    runs(p, text, italic, size, color)
    if align is not None:
        p.alignment = align
    elif indent:
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.first_line_indent = Cm(1)
    return p


def bullet(text):
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.space_after = Pt(3)
    runs(p, text)


def table(header, rows, widths):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = 'Table Grid'
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for cell, text in zip(t.rows[0].cells, header):
        cell.text = ''
        r = cell.paragraphs[0].add_run(text)
        r.bold = True
        r.font.size = Pt(11)
        shd = OxmlElement('w:shd')
        shd.set(qn('w:fill'), 'EAEEF3')
        cell._tc.get_or_add_tcPr().append(shd)
    for row in rows:
        for cell, text in zip(t.add_row().cells, row):
            cell.text = ''
            cell.paragraphs[0].add_run(text).font.size = Pt(11)
    for row in t.rows:
        for cell, w in zip(row.cells, widths):
            cell.width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


# ================================================================ đầu trang
h = doc.add_paragraph()
h.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = h.add_run('KÊ KHAI CÔNG CỤ AI, API, THƯ VIỆN VÀ MÃ NGUỒN MỞ')
r.bold = True
r.font.size = Pt(15)
r.font.color.rgb = RGBColor.from_string(NAVY)
para('Sản phẩm: Gia Sư AI Mimo — gia sư AI trả lời theo sách giáo khoa cho học sinh lớp 6–9',
     align=WD_ALIGN_PARAGRAPH.CENTER)
para(f'Bản kê khai ngày {date.today().strftime("%d/%m/%Y")} · nộp kèm mục 8 của hồ sơ dự án',
     align=WD_ALIGN_PARAGRAPH.CENTER, italic=True, size=11)
para('Phiên bản thư viện trong bản kê khai này đọc thẳng từ backend/requirements.txt và package.json '
     'bằng script bao-cao/make_ke_khai.py, không gõ tay.', italic=True, size=11)

# ================================================================ 1
doc.add_heading('1. Mô hình AI và API', level=1)
table(['Mô hình / API', 'Dùng để làm gì', 'Nhà cung cấp, gói dùng'], [
    [MODEL, 'Mô hình chính: giảng bài, đọc ảnh đề bài, soạn câu luyện tập.', 'Google, gói miễn phí'],
    [FALLBACK.replace(',', ', '), 'Mô hình dự phòng, tự chuyển sang khi mô hình chính hết lượt.', 'Google, gói miễn phí'],
    [f'{EMBED} (1536 chiều)', 'Vector hóa từng đoạn sách giáo khoa và từng câu hỏi để so nghĩa.', 'Google, gói miễn phí'],
    ['Microsoft Edge Read Aloud (qua edge-tts)', f'Đọc câu trả lời bằng giọng tiếng Việt {VOICE}.', 'Microsoft, không cần khóa API'],
], [5.2, 7.3, 3.5])
para('Nhóm không huấn luyện lại (fine-tune) mô hình nào, cũng không gửi dữ liệu học sinh đi huấn luyện. '
     'Mọi lời gọi mô hình đều diễn ra ngay lúc học sinh hỏi.', indent=True)

# ================================================================ 2
doc.add_heading('2. Dịch vụ hạ tầng', level=1)
table(['Dịch vụ', 'Dùng để làm gì', 'Gói'], [
    ['Render', 'Chạy máy chủ FastAPI (backend).', 'Miễn phí'],
    ['Vercel', 'Chạy giao diện web React (frontend).', 'Miễn phí'],
    ['Supabase — Postgres + pgvector', 'Tài khoản, lịch sử học và kho vector sách giáo khoa (bảng sgk_chunks).', 'Miễn phí'],
    ['Supabase Storage', 'Lưu ảnh trang sách render sẵn cho nút “Xem trang”.', 'Miễn phí'],
    ['GitHub', 'Lưu mã nguồn, chạy kiểm thử tự động.', 'Miễn phí'],
], [5.2, 7.3, 3.5])
para('Kho vector nằm trong chính database của dự án, nhóm tự viết (backend/rag/vector_store.py), '
     'không dùng dịch vụ vector bên ngoài.', indent=True)

# ================================================================ 3
doc.add_heading('3. Thư viện mã nguồn mở — máy chủ (Python)', level=1)
table(['Thư viện', 'Phiên bản', 'Giấy phép', 'Dùng để làm gì'], [
    ['FastAPI', pyver('fastapi'), 'MIT', 'Khung máy chủ web, định tuyến API.'],
    ['Uvicorn', pyver('uvicorn'), 'BSD-3-Clause', 'Máy chủ chạy FastAPI.'],
    ['google-genai', pyver('google-genai'), 'Apache-2.0', 'Thư viện chính thức gọi Gemini.'],
    ['python-dotenv', pyver('python-dotenv'), 'BSD-3-Clause', 'Đọc cấu hình từ file .env.'],
    ['httpx', pyver('httpx'), 'BSD-3-Clause', 'Gọi REST của Supabase Storage.'],
    ['pypdf', pyver('pypdf'), 'BSD-3-Clause', 'Đọc chữ từ file PDF sách giáo khoa.'],
    ['PyMuPDF', pyver('pymupdf'), 'AGPL-3.0 (xem mục 8)', 'Đọc chữ và render ảnh từng trang sách.'],
    ['SQLAlchemy', pyver('sqlalchemy'), 'MIT', 'Truy cập cơ sở dữ liệu.'],
    ['psycopg', pyver('psycopg'), 'LGPL-3.0', 'Trình điều khiển Postgres.'],
    ['NumPy', pyver('numpy'), 'BSD-3-Clause', 'So khớp vector trong bộ nhớ khi không có pgvector.'],
    ['PyJWT', pyver('PyJWT'), 'MIT', 'Sinh và kiểm tra vé đăng nhập.'],
    ['edge-tts', pyver('edge-tts'), 'LGPL-3.0 (xem mục 8)', 'Đọc câu trả lời thành giọng nói tiếng Việt.'],
], [3.6, 2.2, 3.4, 6.8])

# ================================================================ 4
doc.add_heading('4. Thư viện mã nguồn mở — giao diện (npm)', level=1)
table(['Thư viện', 'Phiên bản', 'Giấy phép', 'Dùng để làm gì'], [
    ['React', npmver('react'), 'MIT', 'Dựng giao diện web.'],
    ['React DOM', npmver('react-dom'), 'MIT', 'Hiển thị React lên trình duyệt.'],
    ['Vite', npmver('vite'), 'MIT', 'Công cụ dựng và đóng gói giao diện.'],
    ['TypeScript', npmver('typescript'), 'Apache-2.0', 'Ngôn ngữ viết giao diện, bắt lỗi kiểu dữ liệu.'],
    ['KaTeX', npmver('katex'), 'MIT', 'Hiển thị công thức toán.'],
    ['react-markdown', npmver('react-markdown'), 'MIT', 'Hiển thị câu trả lời có định dạng.'],
    ['remark-math', npmver('remark-math'), 'MIT', 'Nhận diện công thức toán trong câu trả lời.'],
    ['rehype-katex', npmver('rehype-katex'), 'MIT', 'Nối công thức đã nhận diện sang KaTeX.'],
    ['lucide-react', npmver('lucide-react'), 'ISC', 'Bộ biểu tượng giao diện.'],
    ['oxlint', npmver('oxlint'), 'MIT', 'Soát lỗi mã nguồn giao diện.'],
], [3.6, 2.2, 3.4, 6.8])

# ================================================================ 5
doc.add_heading('5. Công cụ chỉ dùng để làm hồ sơ (không nằm trong sản phẩm)', level=1)
table(['Công cụ', 'Giấy phép', 'Dùng để làm gì'], [
    ['python-docx', 'MIT', 'Sinh file hồ sơ Word và bản kê khai này.'],
    ['Matplotlib', 'Giấy phép Matplotlib (kiểu BSD)', 'Vẽ 4 biểu đồ trong hồ sơ.'],
    ['Pillow', 'MIT-CMU', 'Cắt viền thừa của ảnh minh họa.'],
    ['Playwright', 'Apache-2.0', 'Tự chụp ảnh màn hình sản phẩm và quay video demo.'],
    ['pytest', 'MIT', 'Chạy bộ kiểm thử tự động.'],
], [4.2, 4.6, 7.2])

# ================================================================ 6
doc.add_heading('6. Công cụ AI hỗ trợ lập trình', level=1)
table(['Công cụ', 'Số câu lệnh đã dùng', 'Dùng để làm gì'], [
    ['Claude Code (Anthropic)', str(N_CLAUDE), 'Đọc hiểu mã nguồn, tìm nguyên nhân lỗi, viết nháp hàm và ca kiểm thử.'],
    ['GitHub Copilot', str(N_COPILOT), 'Gợi ý hoàn thành câu lệnh ngay trong trình soạn thảo.'],
    ['Cộng', str(N_CLAUDE + N_COPILOT), 'Toàn bộ câu lệnh lưu trong thư mục Lich_su_cau_lenh nộp kèm.'],
], [4.2, 3.6, 8.2])
para('Nhóm đọc lại và tự chịu trách nhiệm về mọi dòng mã do công cụ AI gợi ý. '
     'Phần nhóm tự xây dựng: toàn bộ luồng học (lộ trình theo mục lục sách, hỏi bài có trích dẫn trang, '
     'luyện tập thích ứng, lọc tin nhắn nguy hiểm), kho vector thay cho Pinecone, mục lục sách gõ tay và bộ kiểm thử.',
     indent=True)

# ================================================================ 7
doc.add_heading('7. Nguồn dữ liệu', level=1)
table(['Nguồn', 'Dùng để làm gì', 'Ghi chú bản quyền'], [
    ['Sách giáo khoa bộ “Kết nối tri thức với cuộc sống”, chương trình GDPT 2018',
     'Nạp vào kho vector để Mimo trả lời theo đúng sách và trích dẫn số trang.',
     'Bản quyền thuộc Nhà xuất bản Giáo dục Việt Nam. Nhóm dùng cho mục đích học tập phi thương mại; '
     'file PDF không kèm theo bản nộp và không phát hành lại.'],
    ['Chương trình GDPT 2018 (Bộ Giáo dục và Đào tạo)',
     'Dựng lộ trình học cho môn/lớp chưa có mục lục sách.', 'Văn bản công khai của Bộ GD&ĐT.'],
], [4.6, 5.6, 5.8])

# ================================================================ 8
doc.add_heading('8. Hai giấy phép nhóm lưu ý', level=1)
para('Hai thư viện dưới đây có giấy phép chặt hơn phần còn lại, nhóm nêu rõ để thầy cô nắm:', indent=True)
bullet('**PyMuPDF** theo giấy phép AGPL-3.0 (hoặc mua giấy phép thương mại). Mimo là sản phẩm dự thi phi thương mại '
       'và mã nguồn công khai, nên nhóm dùng theo nhánh AGPL. Nếu sau này thương mại hóa, nhóm sẽ chuyển phần đọc chữ '
       'sang pypdf hoặc mua giấy phép.')
bullet('**edge-tts** theo giấy phép LGPL-3.0, gọi tới dịch vụ đọc văn bản của trình duyệt Microsoft Edge. '
       'Nhóm chỉ gọi thư viện qua API công khai, không sửa mã nguồn của nó.')
para('Các thư viện còn lại thuộc nhóm giấy phép dễ dùng (MIT, BSD, Apache-2.0, ISC): được phép dùng, sửa và phát hành '
     'kèm, chỉ cần giữ ghi nhận tác giả — bản kê khai này chính là phần ghi nhận đó.', indent=True)

out = OUT / 'Ke_khai_cong_cu.docx'
doc.save(out)
print('Đã lưu', out)
print(f'  backend   FastAPI {pyver("fastapi")} · Gemini {MODEL} · embedding {EMBED}')
print(f'  frontend  React {npmver("react")} · Vite {npmver("vite")} · TypeScript {npmver("typescript")}')
print(f'  câu lệnh  {N_CLAUDE + N_COPILOT} ({N_CLAUDE} Claude Code + {N_COPILOT} Copilot)')
