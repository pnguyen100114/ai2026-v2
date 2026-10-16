import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'

type CitationSource = {
  source?: string
  title?: string
  page?: number
  preview_url?: string
}

type ChatMessageContentProps = {
  content: string
  sources?: CitationSource[]
  onCite?: (source: CitationSource) => void
}

const CITE_HREF = '#cite-'
// The model sometimes wraps formulas in backticks (`$x^2$`), which would show raw LaTeX as code.
const MATH_IN_CODE = /`(\$\$?[^`\n]+?\$\$?)`/g
const MATH_SEGMENT = /(\$\$[\s\S]*?\$\$|\$[^$\n]*\$)/
const CITATION = /\[(\d+(?:\s*[,;]\s*\d+)*)\]/g

// Turn "[1]" / "[1, 2]" outside of math into markdown links the renderer shows as citation chips.
export function linkCitations(content: string, sourceCount: number): string {
  if (!sourceCount) return content
  return content
    .split(MATH_SEGMENT)
    .map((segment, index) => (index % 2 === 1 ? segment : segment.replace(CITATION, (match, list: string) => {
      const numbers = list.split(/[,;]/).map((value) => Number(value.trim()))
      if (numbers.some((number) => number < 1 || number > sourceCount)) return match
      return numbers.map((number) => `[${number}](${CITE_HREF}${number})`).join('')
    })))
    .join('')
}

// Source numbers the answer actually cites, in order of first mention.
export function citedSourceNumbers(content: string, sourceCount: number): number[] {
  const numbers = [...linkCitations(normalizeMath(content), sourceCount).matchAll(/\(#cite-(\d+)\)/g)].map((match) => Number(match[1]))
  return [...new Set(numbers)]
}

const SUPERSCRIPT = { '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹' } as const
// "x^2" / "x^{10}" → "x²" / "x¹⁰" ở phần chữ thường (ngoài $...$): prompt đã dặn Gemini viết
// công thức bằng LaTeX, nhưng mô hình không phải lúc nào cũng nghe, và một câu luyện tập hiện
// ra "2x^2 + 1 = 0" thì học sinh đọc là mũ hay là dấu nháy cũng không biết.
// Ngoặc nhọn chỉ được ăn khi đi đủ cặp: "x^2}" phải giữ lại "}" (nó đóng một \frac phía trước).
const PLAIN_POWER = /\^(?:\{(\d+)\}|(\d+))/g

function readablePowers(text: string): string {
  return text.replace(PLAIN_POWER, (_match, braced: string | undefined, bare: string | undefined) =>
    [...(braced ?? bare ?? '')].map((digit) => SUPERSCRIPT[digit as keyof typeof SUPERSCRIPT]).join(''))
}

// Gemini có lúc quên dấu $ ("\frac{5}{x^2}y") hoặc dùng \( … \) / \[ … \]: remark-math chỉ hiểu
// $, còn Markdown coi "\(" là ký tự thoát và nuốt mất "\", nên em thấy LaTeX thô trên màn hình.
const BRACKET_MATH = /\\\[([\s\S]+?)\\\]|\\\(([\s\S]+?)\\\)/g
// Chỉ các lệnh toán quen thuộc mới được coi là công thức trần, để "\n" hay "\*" lạc vào câu
// không bị KaTeX báo lỗi đỏ.
const BARE_COMMAND = /\\(?:[dt]?frac|sqrt|cdot|times|div|pm|mp|leq?|geq?|neq?|approx|infty|pi|alpha|beta|gamma|delta|Delta|lambda|mu|omega|Omega|varphi|phi|theta|sigma|rho|circ|angle|widehat|hat|overline|vec|triangle|perp|parallel|in|notin|subset|subseteq|cup|cap|emptyset|varnothing|mathbb|mathrm|text|left|right|Rightarrow|Leftrightarrow|rightarrow|to|cdots|ldots|dots|sin|cos|tan|cot|log|sum|lt|gt|%)(?![a-zA-Z])/
// Từ đứng cạnh lệnh LaTeX cũng thuộc công thức nếu là dấu phép toán, một chữ cái, hay cụm ASCII
// có số/mũ ("2x", "x^2", "y") — còn "khi", "ta", "của" là chữ thường, công thức dừng ở đó.
const MATH_WORD = /^(?:[-+=<>*/:×·≤≥≠]|[A-Za-z]|[-−]?[A-Za-z0-9^_{}()|',.+\-*/=]*[\d^_{}][A-Za-z0-9^_{}()|',.+\-*/=]*)$/
const TRAILING_PUNCTUATION = /[.,;:!?]+$/
// Không đụng vào code: `\n` trong một đoạn code phải giữ nguyên.
const CODE_SEGMENT = /(```[\s\S]*?```|`[^`\n]*`)/

// Tách theo khoảng trắng nằm ngoài ngoặc nhọn, để "\frac{x + 1}{2}" vẫn là một từ.
// Kết quả xen kẽ: từ ở vị trí chẵn, khoảng trắng ở vị trí lẻ.
function splitWords(text: string): string[] {
  const parts: string[] = []
  let current = ''
  let depth = 0
  let inSpace = false
  for (const char of text) {
    if (char === '{') depth += 1
    else if (char === '}') depth = Math.max(0, depth - 1)
    const isSpace = depth === 0 && /\s/.test(char)
    if (isSpace !== inSpace) { parts.push(current); current = ''; inSpace = isSpace }
    current += char
  }
  parts.push(current)
  return parts
}

// Bọc từng cụm công thức trần trong $...$: mỗi cụm là chuỗi từ liền nhau trên cùng một dòng, có lệnh
// LaTeX hoặc số mũ, ví dụ "2x + \frac{1}{2}" trong "Tính 2x + \frac{1}{2}." hay "3x^2 - 2y" trong một
// gợi ý trả lời (dấu chấm câu ở cuối để ngoài).
const isFormula = (text: string) => BARE_COMMAND.test(text) || /\^\{?[A-Za-z0-9]/.test(text)
function wrapBareLatex(text: string): string {
  if (!isFormula(text)) return readablePowers(text)
  const parts = splitWords(text)
  const isMath = (index: number) => BARE_COMMAND.test(parts[index]) || MATH_WORD.test(parts[index])
  let result = ''
  let index = 0
  while (index < parts.length) {
    if (index % 2 === 1 || !isMath(index)) { result += readablePowers(parts[index]); index += 1; continue }
    let last = index
    while (last + 2 < parts.length && !parts[last + 1].includes('\n') && isMath(last + 2)) last += 2
    const run = parts.slice(index, last + 1).join('')
    if (!isFormula(run)) result += readablePowers(run)
    else {
      const punctuation = run.match(TRAILING_PUNCTUATION)?.[0] ?? ''
      result += `$${run.slice(0, run.length - punctuation.length)}$${punctuation}`
    }
    index = last + 1
  }
  return result
}

// Đưa mọi cách viết công thức của mô hình về $...$ mà remark-math hiểu.
export function normalizeMath(content: string): string {
  return (content || '')
    .replace(MATH_IN_CODE, '$1')
    .replace(BRACKET_MATH, (_match, display: string | undefined, inline: string | undefined) =>
      display !== undefined ? `$$${display.trim()}$$` : `$${(inline ?? '').trim()}$`)
    .split(CODE_SEGMENT)
    .map((part, index) => index % 2 === 1 ? part : part
      .split(MATH_SEGMENT)
      .map((segment, segmentIndex) => (segmentIndex % 2 === 1 ? segment : wrapBareLatex(segment)))
      .join(''))
    .join('')
}

// Bản chữ thường của công thức, cho chỗ không vẽ được KaTeX (tiêu đề cuộc trò chuyện, nội dung
// sao chép): "Vì sao $3x^2 - 2y$ ạ?" → "Vì sao 3x² - 2y ạ?", "$\frac{1}{2}$" → "1/2".
// Tử/mẫu chỉ là một số hay một đơn thức thì không cần ngoặc: "1/2", "5/x^2y", "(x + 1)/2".
const group = (text: string) => (/^[\w^.,]+$/.test(text) ? text : `(${text})`)
const PLAIN_LATEX: [RegExp, string | ((...groups: string[]) => string)][] = [
  [/\\[dt]?frac\{([^{}]*)\}\{([^{}]*)\}/g, (_match, top, bottom) => `${group(top)}/${group(bottom)}`],
  [/\\sqrt\{([^{}]*)\}/g, (_match, inside) => `√${group(inside)}`],
  [/\\(?:cdot|times)(?![a-zA-Z])/g, '·'],
  [/\\div(?![a-zA-Z])/g, ':'],
  [/\\pm(?![a-zA-Z])/g, '±'],
  [/\\(?:leq?)(?![a-zA-Z])/g, '≤'],
  [/\\(?:geq?)(?![a-zA-Z])/g, '≥'],
  [/\\(?:neq?)(?![a-zA-Z])/g, '≠'],
  [/\\approx(?![a-zA-Z])/g, '≈'],
  [/\\pi(?![a-zA-Z])/g, 'π'],
  [/\^\{?\\circ\}?/g, '°'],
  [/\\%/g, '%'],
]

export function plainMath(content: string): string {
  return normalizeMath(content)
    .split(MATH_SEGMENT)
    .map((segment, index) => {
      if (index % 2 === 0) return segment
      let text = segment.replace(/^\$+|\$+$/g, '')
      // Lặp vài lượt để phân số lồng nhau mở từ trong ra ngoài.
      for (let round = 0; round < 3; round += 1) {
        for (const [pattern, replacement] of PLAIN_LATEX) text = text.replace(pattern, replacement as string)
      }
      return readablePowers(text).replace(/\\[a-zA-Z]+/g, '').replace(/[{}]/g, '')
    })
    .join('')
}

// Công thức trong một dòng chữ ngắn: câu luyện tập, phương án, gợi ý, lời chấm.
// Khác ChatMessageContent ở chỗ không có trích dẫn và không sinh thẻ khối: <p> bị đổi thành
// <span> để dùng được cả bên trong <button> (phương án trả lời), nơi HTML không cho đặt <p>.
export function MathText({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkMath]}
      rehypePlugins={[rehypeKatex]}
      components={{ p: ({ children }) => <span>{children}</span> }}
    >
      {normalizeMath(content)}
    </ReactMarkdown>
  )
}

export default function ChatMessageContent({ content, sources = [], onCite }: ChatMessageContentProps) {
  return (
    <div className="markdown-content">
      <ReactMarkdown
        remarkPlugins={[remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          a: ({ href, children }) => {
            if (href?.startsWith(CITE_HREF)) {
              const source = sources[Number(href.slice(CITE_HREF.length)) - 1]
              const label = [source?.title || source?.source || 'SGK', source?.page ? `trang ${source.page}` : ''].filter(Boolean).join(', ')
              return (
                <button type="button" className="cite-ref" title={label} aria-label={`Nguồn ${children}: ${label}`} disabled={!source?.preview_url || !onCite} onClick={() => source && onCite?.(source)}>
                  {children}
                </button>
              )
            }
            return <a href={href} target="_blank" rel="noreferrer">{children}</a>
          },
        }}
      >
        {linkCitations(normalizeMath(content), sources.length)}
      </ReactMarkdown>
    </div>
  )
}
