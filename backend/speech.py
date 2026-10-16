"""Vietnamese speech for the tutor: text-to-speech (neural voice) and the transcription prompt for voice questions.

Browsers read Vietnamese with an English voice when no Vietnamese voice is installed (most Windows machines),
and the Web Speech recognition API only works in some browsers, so both go through the backend.
"""
from __future__ import annotations

import os
import re

TTS_VOICE = os.getenv('TTS_VOICE', 'vi-VN-HoaiMyNeural')
TTS_MAX_CHARS = 3000

TRANSCRIBE_PROMPT = (
    'Đây là đoạn ghi âm một học sinh THCS Việt Nam đang nói với gia sư AI tên là "Mimo" (viết đúng "Mimo"). '
    'Hãy chép lại chính xác nguyên văn lời em nói bằng tiếng Việt có dấu, đúng chính tả. '
    'Biểu thức toán đọc thành lời thì viết lại bằng ký hiệu ngắn gọn (ví dụ "x bình phương cộng hai x" viết "x^2 + 2x"). '
    'Không trả lời câu hỏi, không giải thích, không thêm dấu ngoặc kép. '
    'Nếu không nghe rõ lời nói nào thì trả về chuỗi rỗng.'
)

_LATEX_WORDS = [
    (r'\\(?:left|right|displaystyle|,|;|!|quad|qquad)', ' '),
    (r'\\(?:cdot|times)', ' nhân '),
    (r'\\div', ' chia '),
    (r'\\pm', ' cộng trừ '),
    (r'\\(?:neq|ne)\b', ' khác '),
    (r'\\(?:leq|le)\b', ' nhỏ hơn hoặc bằng '),
    (r'\\(?:geq|ge)\b', ' lớn hơn hoặc bằng '),
    (r'\\approx', ' xấp xỉ '),
    (r'\\notin', ' không thuộc '),
    (r'\\in\b', ' thuộc '),
    (r'\\subset(?:eq)?', ' là tập con của '),
    (r'\\(?:Rightarrow|implies)', ' suy ra '),
    (r'\\(?:Leftrightarrow|iff)', ' tương đương '),
    (r'\\infty', ' vô cực '),
    (r'\\pi', ' pi '),
    (r'\\alpha', ' anpha '),
    (r'\\beta', ' bêta '),
    (r'\\Delta', ' đenta '),
    (r'\\triangle', ' tam giác '),
    (r'\\angle', ' góc '),
    (r'\\parallel', ' song song với '),
    (r'\\perp', ' vuông góc với '),
    (r'\^\s*\{?\\circ\}?', ' độ '),
    (r'\\%', ' phần trăm '),
    (r'\\mathbb\{(\w)\}', r' \1 '),
    (r'\\(?:text|mathrm|mathbf|operatorname)\{([^{}]*)\}', r' \1 '),
]


def _speak_math(expression: str) -> str:
    text = expression.replace('²', '^2').replace('³', '^3')
    # Innermost first so nested fractions and roots read in order.
    for _ in range(4):
        text = re.sub(r'\\[dt]?frac\{([^{}]*)\}\{([^{}]*)\}', r' \1 phần \2 ', text)
        text = re.sub(r'\\sqrt\[3\]\{([^{}]*)\}', r' căn bậc ba của \1 ', text)
        text = re.sub(r'\\sqrt\{([^{}]*)\}', r' căn bậc hai của \1 ', text)
    # A minus at the start, after a bracket or after an operator/relation is a negative sign.
    text = re.sub(r'(^|[(=,\[{<>]|\\(?:neq|ne|leq|le|geq|ge|approx|cdot|times|div|pm)\b)\s*-\s*', r'\1 âm ', text)
    for pattern, replacement in _LATEX_WORDS:
        text = re.sub(pattern, replacement, text)
    # "(a+b)^2" is read "a cộng b, tất cả bình phương", as teachers say it.
    text = re.sub(r'\(([^()]+)\)\s*\^', r' \1, tất cả ^', text)
    text = re.sub(r'\^\s*\{?\s*2\s*\}?', ' bình phương ', text)
    text = re.sub(r'\^\s*\{?\s*3\s*\}?', ' lập phương ', text)
    text = re.sub(r'\^\s*\{([^{}]*)\}', r' mũ \1 ', text)
    text = re.sub(r'\^\s*(\S)', r' mũ \1 ', text)
    text = re.sub(r'_\s*\{([^{}]*)\}|_\s*(\w)', r' \1\2 ', text)
    text = text.replace('+', ' cộng ').replace('-', ' trừ ').replace('−', ' trừ ').replace('=', ' bằng ')
    text = text.replace('<', ' nhỏ hơn ').replace('>', ' lớn hơn ').replace(':', ' chia ')
    text = re.sub(r'\\[a-zA-Z]+', ' ', text)
    return re.sub(r'[{}()\[\]|]', ' ', text)


# Gemini có lúc quên dấu $ ("\frac{5}{x^2}y", "x^2 - 4"). Giao diện bọc lại các cụm đó để vẽ
# (normalizeMath trong ChatMessageContent.tsx); giọng đọc cũng phải đọc chúng như công thức.
_BARE_COMMAND = re.compile(
    r'\\(?:[dt]?frac|sqrt|cdot|times|div|pm|neq?|leq?|geq?|approx|infty|pi|alpha|beta|Delta|triangle|angle'
    r'|parallel|perp|circ|in|notin|subset|subseteq|Rightarrow|Leftrightarrow|implies|iff|text|mathrm|mathbb|left|right|%)(?![a-zA-Z])'
)
# Dấu phép toán, một chữ cái, hay cụm ASCII có số/mũ ("2x", "x^2"); "khi", "của" là chữ thường.
_MATH_WORD = re.compile(r"[-+=<>*/:×·≤≥≠]|[A-Za-z]|[-−]?[A-Za-z0-9^_{}()|',.²³]*[\d^_{}²³][A-Za-z0-9^_{}()|',.²³]*")
_IS_FORMULA = re.compile(r'\\[a-zA-Z%]|[\^²³]')


def _split_words(text: str) -> list[str]:
    """Tách theo khoảng trắng ngoài ngoặc nhọn; từ ở vị trí chẵn, khoảng trắng ở vị trí lẻ."""
    parts, current, depth, in_space = [], '', 0, False
    for char in text:
        if char == '{':
            depth += 1
        elif char == '}':
            depth = max(0, depth - 1)
        is_space = depth == 0 and char.isspace()
        if is_space != in_space:
            parts.append(current)
            current, in_space = '', is_space
        current += char
    parts.append(current)
    return parts


def _speak_bare_math(text: str) -> str:
    if not _BARE_COMMAND.search(text) and not re.search(r'[\^²³]', text):
        return text
    parts = _split_words(text)

    def is_math(index: int) -> bool:
        return bool(_BARE_COMMAND.search(parts[index]) or _MATH_WORD.fullmatch(parts[index]))

    result, index = [], 0
    while index < len(parts):
        if index % 2 or not is_math(index):
            result.append(parts[index])
            index += 1
            continue
        last = index
        while last + 2 < len(parts) and '\n' not in parts[last + 1] and is_math(last + 2):
            last += 2
        run = ''.join(parts[index:last + 1])
        if _IS_FORMULA.search(run):
            body = run.rstrip('.,;:!?')
            run = _speak_math(body) + run[len(body):]
        result.append(run)
        index = last + 1
    return ''.join(result)


def speakable_text(markdown: str) -> str:
    """Turn a Markdown + LaTeX answer into plain Vietnamese a voice can read ("x^2" -> "x bình phương")."""
    text = markdown or ''
    text = re.sub(r'\[\d+(?:\s*[,;]\s*\d+)*\]', '', text)  # citation markers
    text = re.sub(r'\$\$(.+?)\$\$|\$(.+?)\$', lambda match: _speak_math(match.group(1) or match.group(2)), text, flags=re.DOTALL)
    text = re.sub(r'\\\((.+?)\\\)|\\\[(.+?)\\\]', lambda match: _speak_math(match.group(1) or match.group(2)), text, flags=re.DOTALL)
    text = _speak_bare_math(text)
    text = re.sub(r'`+', '', text)
    text = re.sub(r'!?\[([^\]]*)\]\([^)]*\)', r'\1', text)  # links, images
    text = re.sub(r'^\s{0,3}(?:#{1,6}|>|[-*+]|\d+[.)])\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'[*_~#]', '', text)
    # Emoji and pictographs are read out as their English names.
    text = re.sub(r'[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u200D]', '', text)
    text = re.sub(r'\n{2,}', '. ', text)
    text = re.sub(r'[ \t\r\n]+', ' ', text)
    text = re.sub(r'\s+([,.;!?])', r'\1', text)
    return text.strip()[:TTS_MAX_CHARS]


async def synthesize_mp3(text: str) -> bytes:
    import edge_tts

    audio = bytearray()
    async for chunk in edge_tts.Communicate(text, TTS_VOICE).stream():
        if chunk.get('type') == 'audio':
            audio.extend(chunk['data'])
    if not audio:
        raise RuntimeError('TTS returned no audio')
    return bytes(audio)
