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
