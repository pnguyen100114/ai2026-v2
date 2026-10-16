"""Child-safety guardrails for the tutor chat.

The prompt asks Gemini to handle bullying, abuse and self-harm with care; these checks make sure the
essentials (tell a trusted adult, hotline 111) reach the student even when the model forgets them,
Gemini is out of quota or the textbook search is down.
"""
from __future__ import annotations

import re
import unicodedata

SELF_HARM = 'self_harm'
HARM = 'harm'

# Matched on lowercase text with accents. Unaccented variants are listed only when they are unambiguous
# ("tu tu" could just be "từ từ", "tu hai" could be "từ hai"). "muốn chết" is caught unless it only
# stresses a feeling ("mệt muốn chết", see _HYPERBOLE).
_SELF_HARM_ACCENTED = (
    'tự tử', 'tự sát', 'không muốn sống', 'chẳng muốn sống', 'tự làm đau', 'tự làm hại', 'rạch tay',
    'chết đi cho xong', 'muốn biến mất mãi mãi', 'kết thúc cuộc đời', 'nhảy lầu', 'tự hại', 'tự cắt tay',
    'cắt tay mình', 'kết liễu', 'chán sống', 'không thiết sống',
)
_SELF_HARM_PLAIN = (
    'muon tu tu', 'tu sat', 'khong muon song', 'chang muon song', 'tu lam dau ban than', 'tu lam hai ban than',
    'rach tay', 'chet di cho xong', 'ket thuc cuoc doi', 'nhay lau', 'tu cat tay', 'cat tay minh', 'ket lieu',
    'chan song', 'khong thiet song',
)
# Teen spelling of "không muốn sống": "ko/k/kh/hong muốn sống", "e k mun song nua". Checked on unaccented text.
_NOT_WANT_TO_LIVE = re.compile(r'\b(?:khong|ko|k|kh|hk|hong|hok|kg|chang)\s+(?:muon|mun|mn|thiet)\s+(?:song|sog)\b')
_WANT_TO_DIE = re.compile(r'\b(?:muon|mun|mn)\s+chet\b')
# "khó muốn chết", "mệt quá muốn chết" only stress a feeling. "em muốn chết", "buồn quá muốn chết" do not.
_HYPERBOLE = frozenset(
    'kho met doi nong lanh cuoi khat ngu dau so ngai chan nho them ghet suong vui ngon nhuc moi tuc ghen me dep'.split()
)
_HARM_ACCENTED = (
    'bắt nạt', 'bị trêu', 'hay trêu', 'trêu chọc', 'cô lập', 'bị đánh', 'đánh em', 'đánh con', 'đe dọa', 'dọa đánh',
    'bạo lực', 'xâm hại', 'sờ vào người', 'động chạm', 'bị chửi', 'chửi em', 'tẩy chay', 'bị ép',
)
_HARM_PLAIN = (
    'bi ep', 'bat nat', 'bi treu', 'hay treu', 'treu choc', 'co lap', 'bi danh', 'danh em', 'de doa', 'doa danh',
    'bao luc', 'xam hai', 'so vao nguoi', 'dong cham', 'bi chui', 'tay chay',
)

HOTLINE_NOTE = (
    '\n\n---\n💛 **Em không phải chịu một mình đâu.** Em hãy nói ngay với một người lớn em tin tưởng '
    '(bố mẹ, thầy cô chủ nhiệm, cô tư vấn tâm lý ở trường). Em cũng có thể gọi **Tổng đài quốc gia bảo vệ trẻ em 111** '
    '(miễn phí, 24/7). Nếu em đang gặp nguy hiểm ngay lúc này, hãy gọi **115** hoặc **113**.'
)
ADULT_NOTE = (
    '\n\n---\n💛 Chuyện này em nên kể với người lớn em tin tưởng như bố mẹ hoặc thầy cô chủ nhiệm để được giúp đỡ nhé. '
    'Em cũng có thể gọi **Tổng đài quốc gia bảo vệ trẻ em 111** (miễn phí, 24/7).'
)
_ADULT_MENTIONS = ('bố mẹ', 'ba mẹ', 'thầy cô', 'người lớn', '111')

SAFETY_QUICK_REPLIES = {
    SELF_HARM: ['Em muốn kể thêm', 'Em nên nói với ai ạ?'],
    HARM: ['Em muốn kể thêm', 'Em nên nói với ai ạ?', 'Mình học tiếp nhé'],
}

SAFETY_PROMPT = '''AN TOÀN VÀ CẢM XÚC (ưu tiên cao nhất, đứng trên mọi quy tắc khác)
- Nếu em kể bị bắt nạt, trêu chọc, cô lập, bị đánh, bị đe dọa, bị ai đó động chạm khiến em sợ, hoặc buồn bã kéo dài: lắng nghe và công nhận cảm xúc của em trước; KHÔNG bảo em "đừng để tâm", không khuyên em nhịn hay đánh trả; khuyến khích em kể với người lớn tin cậy (bố mẹ, thầy cô chủ nhiệm, cô tư vấn tâm lý ở trường) và cho em biết có thể gọi Tổng đài quốc gia bảo vệ trẻ em 111 (miễn phí, 24/7). Hỏi em có muốn kể thêm không. Lượt này KHÔNG kéo em quay lại bài học.
- Nếu em nhắc đến việc muốn chết, tự làm đau bản thân hoặc đang gặp nguy hiểm: trả lời bình tĩnh, ấm áp; nói rõ em không có lỗi và không phải chịu một mình; đề nghị em nói ngay với một người lớn ở gần; nhắc số 111, nếu nguy hiểm tức thì gọi 115 hoặc 113. Không giảng bài.
- Mimo là AI, không thay thế người lớn; không hứa giữ bí mật những chuyện có thể gây nguy hiểm cho em.'''


def _plain(text: str) -> str:
    return unicodedata.normalize('NFKD', text.replace('đ', 'd').replace('Đ', 'D')).encode('ascii', 'ignore').decode()


def _wants_to_die(plain: str) -> bool:
    for match in _WANT_TO_DIE.finditer(plain):
        # Only the clause the phrase sits in: "em chán lắm, muốn chết" is not hyperbole.
        clause = re.split(r'[.,!?;:\n]', plain[:match.start()])[-1].split()
        if not _HYPERBOLE.intersection(clause[-2:]):
            return True
    return False


def detect_risk(message: str) -> str | None:
    # NFC first: text typed with Unikey's "Unicode tổ hợp" or pasted from some phones arrives decomposed.
    lowered = re.sub(r'\s+', ' ', unicodedata.normalize('NFC', message or '').lower())
    plain = _plain(lowered)
    if (any(phrase in lowered for phrase in _SELF_HARM_ACCENTED) or any(phrase in plain for phrase in _SELF_HARM_PLAIN)
            or _NOT_WANT_TO_LIVE.search(plain) or _wants_to_die(plain)):
        return SELF_HARM
    if any(phrase in lowered for phrase in _HARM_ACCENTED) or any(phrase in plain for phrase in _HARM_PLAIN):
        return HARM
    return None


# "Mình học tiếp nhé" is one of SAFETY_QUICK_REPLIES[HARM]: the student chose to go back to the lesson.
_BACK_TO_LESSON = re.compile(r'\bhọc tiếp\b|\bquay lại bài\b|\bôn bài\b')
_CARRY_TURNS = 3


def conversation_risk(message: str, earlier_user_messages: list[str]) -> str | None:
    """Risk of this turn, counting a disclosure in the last few student turns.

    "Em nên nói với ai ạ?" or "Em muốn kể thêm" carry no risk words of their own; judged alone they
    would be treated as a lesson question, right after the student said they want to die.
    """
    risk = detect_risk(message)
    if risk or _BACK_TO_LESSON.search(unicodedata.normalize('NFC', message or '').lower()):
        return risk
    for earlier in reversed(earlier_user_messages[-_CARRY_TURNS:]):
        risk = detect_risk(earlier)
        if risk:
            return risk
        if _BACK_TO_LESSON.search(unicodedata.normalize('NFC', earlier or '').lower()):
            return None
    return None


def safety_addendum(risk: str | None, answer: str) -> str:
    """Text to append so the answer always points the student to real help."""
    lowered = (answer or '').lower()
    if risk == SELF_HARM:
        return '' if '111' in lowered else HOTLINE_NOTE
    if risk == HARM:
        return '' if any(mention in lowered for mention in _ADULT_MENTIONS) else ADULT_NOTE
    return ''


# "Em tính ra x = 6 rồi" / "khai triển ra là x^2 + 4x + 4" reveal the answer to the question Mimo just asked.
_ANSWER_IN_REPLY = re.compile(r'(=|≈|\b(?:bằng|là|ra|được|thành)\s)\s*[-−(]?\s*\$?\s*(?:\d|[a-z](?:\d|\s*[\^+\-−*/]))')
# "Đó là hằng đẳng thức ạ" / "Biểu thức đó không phải đơn thức ạ" state an answer in words.
_ANSWER_STATEMENT = re.compile(r'^(?:dạ,?\s*)?(?:(?:đó|nó|đây|cái này|câu này|biểu thức (?:đó|này)|đẳng thức (?:đó|này))\s+)?(?:là|chính là|không phải|có phải|phải là|đúng là)\s')
_QUESTION_WORD = re.compile(r'\?|\b(?:gì|sao|nào|ai|đâu|chưa)\b|(?:\S+\s+){2,}không(?:\s+ạ)?$')


# "Có dùng Mimo ơi" / "Không ạ" answer a yes/no question; "Không hiểu lắm ạ" does not.
_YES_NO_ANSWER = re.compile(r'^(?:dạ,?\s*)?(?:có|không)(?:\s+(?:ạ|dùng|phải|đúng|là)\b|\s*[.!]*$)')


def leaks_answer(reply: str) -> bool:
    lowered = reply.lower().strip()
    if _ANSWER_IN_REPLY.search(lowered):
        return True
    return bool((_ANSWER_STATEMENT.search(lowered) or _YES_NO_ANSWER.search(lowered)) and not _QUESTION_WORD.search(lowered))

# Used when Gemini could not answer a safety-sensitive message at all.
SAFETY_OPENING = 'Mimo đã đọc tin nhắn của em. Cảm ơn em đã tin tưởng kể cho Mimo nghe, chuyện em đang trải qua là quan trọng và em không có lỗi gì cả.'
