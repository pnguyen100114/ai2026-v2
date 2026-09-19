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
  const numbers = [...linkCitations(content, sourceCount).matchAll(/\(#cite-(\d+)\)/g)].map((match) => Number(match[1]))
  return [...new Set(numbers)]
}

const SUPERSCRIPT = { '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹' } as const
// "x^2" / "x^{10}" → "x²" / "x¹⁰". Chỉ dùng cho chuỗi KHÔNG có "$": prompt đã dặn Gemini viết
// công thức bằng LaTeX, nhưng mô hình không phải lúc nào cũng nghe, và một câu luyện tập hiện
// ra "2x^2 + 1 = 0" thì học sinh đọc là mũ hay là dấu nháy cũng không biết.
const PLAIN_POWER = /\^\{?(\d+)\}?/g

function readablePowers(text: string): string {
  if (text.includes('$')) return text
  return text.replace(PLAIN_POWER, (match, digits: string) =>
    [...digits].map((digit) => SUPERSCRIPT[digit as keyof typeof SUPERSCRIPT] ?? match).join(''))
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
      {readablePowers((content || '').replace(MATH_IN_CODE, '$1'))}
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
        {linkCitations(content.replace(MATH_IN_CODE, '$1'), sources.length)}
      </ReactMarkdown>
    </div>
  )
}
