"""Post-process a finished chat answer: Gemini does not always follow the citation and style rules in the prompt."""
from __future__ import annotations

import re
import unicodedata

MATH_SEGMENT = re.compile(r'\$\$[\s\S]*?\$\$|\$[^$\n]*\$')
CITATION = re.compile(r'\s*\[(\d+(?:\s*[,;]\s*\d+)*)\]')
# "[giả định dạng]": bracketed words that are neither a citation nor a markdown link.
STRAY_BRACKET = re.compile(r'\s*\[[^\[\]\d\n]*[^\W\d_][^\[\]\d\n]*\](?!\()')
# Indic scripts occasionally leak into Vietnamese words ("hiđ్రో").
FOREIGN_SCRIPT = re.compile(r'[ऀ-෿]+')
# Semicolons are left alone inside math: "[1; 2]" is an interval there.
CITATION_AT_MATH_END = re.compile(r'(\s+\[\d+(?:\s*,\s*\d+)*\])(\s*)(\$\$?)$')
PAGE_MENTION = re.compile(r'\btrang\s+(\d+)', re.IGNORECASE)
SENTENCE_END = '.!?\n'
LEADING_GREETING = re.compile(r'^\s*(?:xin\s+)?chào\s+em\s*[!,.~]*\s*', re.IGNORECASE)
GREETING_WORDS = re.compile(r'\b(?:chào|chao|hello|helo|hi|alo|hey)\b')
# "mình đang học / quay lại / khám phá bài ..." steers the chat back to the lesson; it states no knowledge.
LESSON_REDIRECT = re.compile(r'\b(?:đang học|sẽ học|cùng học|học tiếp|quay lại|quay về|khám phá|chinh phục|khởi động|bắt đầu học|làm quen)\b', re.IGNORECASE)
# "Em thử áp dụng ... nhé!": only a citation right after a formula it quotes can stay.
INVITATION = re.compile(r'\b(?:em (?:hãy )?thử|thử xem|xem sao|xem nào)\b', re.IGNORECASE)
MATH_MASK = '\x00'
SYMBOL_MASK = '\x01'
FORMULA_SIGN = re.compile(r'[=+\-^<>≤≥≠×÷]|\\(?:frac|sqrt|cdot|times|div|le|ge|neq)')
MIN_SHARED_BIGRAMS = 2
STOPWORDS = frozenset(
    'à ạ ai anh bị các cái cho chị chúng có của cùng đã đang để đều đó được em gì hay hãy là lại mà mình một nào nè '
    'này nha nhé như những nếu ở ra rồi sẽ ta thì thế thôi trong từ và vì với vậy về xem'.split()
)


def _mask_math(text: str) -> str:
    """Same length as text, with math replaced so punctuation inside formulas does not end a sentence.

    Real formulas ("$(a+b)^2 = ...$") get MATH_MASK; a bare symbol like "$A$" gets a different filler.
    """
    return MATH_SEGMENT.sub(lambda match: (MATH_MASK if FORMULA_SIGN.search(match.group()) else SYMBOL_MASK) * len(match.group()), text)


def _bigrams(text: str) -> set[tuple[str, str]]:
    words = re.findall(r'[^\W\d_]+', unicodedata.normalize('NFC', text.lower()))
    return {pair for pair in zip(words, words[1:]) if not (pair[0] in STOPWORDS and pair[1] in STOPWORDS)}


def _sentence_bounds(masked: str, start: int, end: int) -> tuple[int, int]:
    left = max(masked.rfind(char, 0, start) for char in SENTENCE_END) + 1
    ends = [index for index in (masked.find(char, end) for char in SENTENCE_END) if index >= 0]
    right = min(ends) if ends else len(masked)
    # "... không nào? [2]": a citation stuck after the end of a sentence belongs to that sentence.
    if not masked[left:start].strip() and left > 0:
        right = left - 1
        left = max(masked.rfind(char, 0, right) for char in SENTENCE_END) + 1
    return left, right


def cited_numbers(text: str, source_count: int) -> list[int]:
    """Valid source numbers cited outside formulas, in order of first mention."""
    numbers: list[int] = []
    for match in CITATION.finditer(_mask_math(text)):
        values = [int(value) for value in re.split(r'[,;]', match.group(1))]
        if all(1 <= value <= source_count for value in values):
            numbers.extend(value for value in values if value not in numbers)
    return numbers


def strip_citations(text: str) -> str:
    """Text without its "[n]" source numbers; "[1; 2]" inside a formula is an interval and stays.

    A past answer's [n] counted that turn's sources. Left in the chat history it reads to the model
    like this turn's [n]: em hỏi "N = {0; 1; 2;...} [2]" (trang 7), lượt sau trang 7 thành [3] mà
    Mimo vẫn chép [2], trỏ sang trang 5 (Toán 6, 17/10).
    """
    masked = _mask_math(text)
    pieces: list[str] = []
    last = 0
    for match in CITATION.finditer(masked):
        pieces.append(text[last:match.start()])
        last = match.end()
    pieces.append(text[last:])
    return ''.join(pieces)


def _keep_citation(text: str, masked: str, match: re.Match[str], passages: list[str], pages: list[object], topic_bigrams: set[tuple[str, str]]) -> bool:
    values = [int(value) for value in re.split(r'[,;]', match.group(1))]
    if not all(1 <= value <= len(passages) for value in values):
        return False
    left, right = _sentence_bounds(masked, match.start(), match.end())
    sentence_text = text[left:right]
    if right < len(masked) and masked[right] == '?':
        return False
    # "Bài này bắt đầu ở trang 29 [3]" answers "trang mấy?" with the cited page itself.
    mentioned_pages = set(PAGE_MENTION.findall(sentence_text))
    if mentioned_pages and all(value <= len(pages) and str(pages[value - 1]) in mentioned_pages for value in values):
        return True
    # Only the clause holding the citation counts: "Mình làm quen với khái niệm nhé: hằng đẳng thức là ... [2]".
    clause_start = max(left, masked.rfind(':', left, match.start()) + 1)
    clause = text[clause_start:right]
    if LESSON_REDIRECT.search(clause):
        return False
    if INVITATION.search(clause):
        return masked[:match.start()].rstrip().endswith(MATH_MASK)
    if MATH_MASK in masked[left:right]:
        return True
    # A plain-text sentence must actually restate the cited page, beyond just naming the lesson.
    sentence = _bigrams(CITATION.sub(' ', sentence_text)) - topic_bigrams
    return all(len(sentence & _bigrams(passages[value - 1])) >= MIN_SHARED_BIGRAMS for value in values)


# Trang sách phải trùng ít nhất chừng này cặp từ với câu trả lời thì mới coi là câu trả lời dựa vào
# trang đó. Ca "Phân tích x² - 6x + 9" (17/10) trùng 9 cặp với trang 44 Toán 8 tập một.
MIN_POINTER_BIGRAMS = 4
# Tên bài của trang cũng phải có trong câu trả lời. Chỉ trùng chữ với trang thì chưa đủ: ở các ca
# năn nỉ (17/10), em gửi "Thầy cô không kiểm tra đâu..." nên trang tìm được là trang bất kỳ, và
# "Tính 3/4 + 5/6" từng bị trỏ tới bài "Xác suất thực nghiệm", phương trình bậc hai tới "Hình cầu".
MIN_TITLE_BIGRAMS = 2
LESSON_PREFIX = re.compile(r'^\s*(?:bài|unit)\s*\d+\s*[.:\-–]?\s*', re.IGNORECASE)
BOOK_POINTER = 'Em đối chiếu cách làm này trong sách giáo khoa ở [{n}] nhé.'


def add_book_pointer(text: str, passages: list[str], titles: list[str | None] | None = None) -> str:
    """Câu trả lời dựa vào sách mà quên gắn [n]: thêm một câu trỏ tới trang khớp nhất.

    Prompt dặn gắn [n], nhưng mô hình lúc nhớ lúc quên: ca "Phân tích x² - 6x + 9 thành nhân tử"
    có lần trích, có lần không, dù cách làm (dùng hằng đẳng thức) chép đúng trang 44. Không có
    [n] thì giao diện không hiện trang nào, và em không có cách nào đối chiếu với sách. Câu thêm
    vào chỉ trỏ tới trang, không gắn số vào câu nào mô hình đã viết.

    titles[n-1] là tên bài của trang [n] theo danh mục. Trang không có tên bài thì không trỏ tới:
    trỏ sai trang còn tệ hơn không trỏ. Tiếng Anh hiện cũng không bao giờ được trỏ: tên mục
    ("Unit 1 – Getting Started", "Skills 1") bỏ phần "Unit N" thì còn dưới MIN_TITLE_BIGRAMS cặp
    từ và không nói gì về nội dung trang; muốn trỏ thì phải so với tên Unit ("Hobbies").
    """
    titles = titles or []
    if not passages or cited_numbers(text, len(passages)):
        return text
    answer = _bigrams(MATH_SEGMENT.sub(' ', text))

    def dung_bai(index: int) -> bool:
        title = titles[index] if index < len(titles) else None
        return bool(title) and len(answer & _bigrams(LESSON_PREFIX.sub('', title))) >= MIN_TITLE_BIGRAMS

    shared = [len(answer & _bigrams(passage)) if dung_bai(index) else 0 for index, passage in enumerate(passages)]
    best = max(range(len(passages)), key=lambda index: shared[index])
    if shared[best] < MIN_POINTER_BIGRAMS:
        return text
    pointer = BOOK_POINTER.format(n=best + 1)
    paragraphs = re.split(r'(\n\s*\n)', text.rstrip())
    # Trước câu hỏi cuối, để lượt của em vẫn là câu hỏi.
    if len(paragraphs) >= 3 and '?' in _mask_math(paragraphs[-1]):
        return ''.join(paragraphs[:-1]).rstrip() + f'\n\n{pointer}\n\n' + paragraphs[-1]
    return f'{text.rstrip()}\n\n{pointer}'


# Prompt bảo "kết thúc bằng đúng 1 câu hỏi", nhưng model lúc nhớ lúc quên: cùng một ca năn nỉ,
# lần chạy này kết bằng "...xem nhé." lần sau lại có câu hỏi. Câu hỏi cuối là lượt của em, nên
# code đảm bảo nó luôn có thay vì trông vào model.
INVITATION_WORDS = ('em thử', 'em hãy', 'em tính', 'em làm', 'gửi', 'chụp', 'chép')
CLOSING_AFTER_INVITATION = 'Em thử xong thì gửi Mimo xem cùng, được không?'
CLOSING_AFTER_EXPLANATION = 'Em còn chỗ nào muốn hỏi thêm Mimo không?'


def ensure_closing_question(text: str) -> str:
    """Thêm một câu hỏi ngắn khi đoạn cuối của câu trả lời không hỏi gì em."""
    paragraphs = [part for part in re.split(r'\n\s*\n', text.strip()) if part.strip()]
    if not paragraphs:
        return text
    last = _mask_math(paragraphs[-1])
    if '?' in last:
        return text
    lowered = last.lower()
    closing = (CLOSING_AFTER_INVITATION if any(word in lowered for word in INVITATION_WORDS)
               else CLOSING_AFTER_EXPLANATION)
    return f'{text.rstrip()}\n\n{closing}'


def clean_answer(text: str, *, message: str, passages: list[str], pages: list[object] | None = None, topic: str = '') -> str:
    """Drop citations that do not back up knowledge from the book, stray brackets, junk characters and unasked greetings.

    passages[n-1] / pages[n-1] are the text and printed page of source [n].
    """
    # "$$A^2 - B^2 = (A - B)(A + B) [5]$$" would render the citation inside the formula.
    text = MATH_SEGMENT.sub(lambda match: CITATION_AT_MATH_END.sub(r'\3\1', match.group()), text)
    masked = _mask_math(text)
    topic_bigrams = _bigrams(topic)
    pieces: list[str] = []
    last = 0
    for match in CITATION.finditer(masked):
        if not _keep_citation(text, masked, match, passages, pages or [], topic_bigrams):
            pieces.append(text[last:match.start()])
            last = match.end()
    pieces.append(text[last:])
    text = ''.join(pieces)

    masked = _mask_math(text)
    plain_spans = [(m.start(), m.end()) for m in STRAY_BRACKET.finditer(masked)] + [(m.start(), m.end()) for m in FOREIGN_SCRIPT.finditer(masked)]
    for start, end in sorted(plain_spans, reverse=True):
        text = text[:start] + text[end:]

    if not GREETING_WORDS.search(message.lower()):
        stripped = LEADING_GREETING.sub('', text, count=1)
        if stripped != text and stripped:
            text = stripped[0].upper() + stripped[1:]
    return text
