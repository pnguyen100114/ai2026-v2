import { useEffect, useMemo, useRef, useState } from 'react'
import {
  BookOpen,
  Brain,
  CheckCircle2,
  ChevronRight,
  Clock3,
  Flame,
  GraduationCap,
  Home,
  LockKeyhole,
  RefreshCcw,
  Send,
  Sparkles,
} from 'lucide-react'
import PomodoroState from './components/PomodoroState'

type Page = 'home' | 'roadmap' | 'tutor' | 'pomodoro'
type ChatRole = 'user' | 'assistant'
type SourceRef = {
  source?: string
  page?: number
  chapter?: number
  lesson?: number
  score?: number
}
type ChatMessage = {
  role: ChatRole
  content: string
  sources?: SourceRef[]
}
type StudentProfile = {
  name: string
  age: number
  grade: number
  subject: string
  currentLesson: string
  currentTopic: string
}
type RoadmapLesson = {
  id: string
  lesson: number
  title: string
  volume?: number
  status: 'locked' | 'recommended' | 'review' | 'active'
  progress: number
  sources?: { source?: string; page?: number }[]
}
type RoadmapChapter = {
  id: string
  chapter: number
  title: string
  lessons: RoadmapLesson[]
}
type RoadmapData = {
  id: string
  subject: string
  grade: number
  title: string
  progress: number
  chapters: RoadmapChapter[]
}

const defaultStudent: StudentProfile = {
  name: 'Minh Anh',
  age: 13,
  grade: 8,
  subject: 'Toán',
  currentLesson: 'Bài 1: Phép nhân đa thức',
  currentTopic: 'Phép nhân đa thức',
}

const navItems: { id: Page; label: string; icon: typeof Home }[] = [
  { id: 'home', label: 'Trang chủ', icon: Home },
  { id: 'roadmap', label: 'Lộ trình học', icon: BookOpen },
  { id: 'tutor', label: 'AI Tutor', icon: Brain },
  { id: 'pomodoro', label: 'Pomodoro', icon: Clock3 },
]

const initialMessages: ChatMessage[] = [
  { role: 'assistant', content: 'Xin chào! Mình là Gia sư AI. Hãy cho mình biết bạn đang học môn gì và bài nào để mình hỗ trợ theo đúng tài liệu SGK.' },
]

function readStorage<T>(key: string, fallback: T): T {
  if (typeof window === 'undefined') return fallback
  try {
    const stored = window.localStorage.getItem(key)
    return stored ? (JSON.parse(stored) as T) : fallback
  } catch {
    return fallback
  }
}

function writeStorage<T>(key: string, value: T) {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // ignore storage errors
  }
}

function App() {
  const [page, setPage] = useState<Page>('home')
  const [student, setStudent] = useState<StudentProfile>(() => readStorage('gia-su-ai-student', defaultStudent))
  const [roadmap, setRoadmap] = useState<RoadmapData | null>(() => readStorage('gia-su-ai-roadmap', null))
  const [chat, setChat] = useState<ChatMessage[]>(() => readStorage('gia-su-ai-chat', initialMessages))
  const [chatLoading, setChatLoading] = useState(false)
  const [roadmapLoading, setRoadmapLoading] = useState(false)
  const [error, setError] = useState('')
  const chatEndRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    writeStorage('gia-su-ai-student', student)
  }, [student])

  useEffect(() => {
    writeStorage('gia-su-ai-chat', chat)
  }, [chat])

  useEffect(() => {
    writeStorage('gia-su-ai-roadmap', roadmap)
  }, [roadmap])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chat, chatLoading])

  const fetchRoadmap = async () => {
    setRoadmapLoading(true)
    setError('')
    try {
      const response = await fetch('/api/roadmap/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ student }),
      })
      const payload = await response.json()
      if (!response.ok || !payload.success) {
        throw new Error(payload.detail || payload.error || 'Không thể tạo lộ trình học từ dữ liệu RAG.')
      }
      setRoadmap(payload.roadmap)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể tạo lộ trình học từ dữ liệu RAG.')
    } finally {
      setRoadmapLoading(false)
    }
  }

  useEffect(() => {
    void fetchRoadmap()
  }, [student.subject, student.grade])

  const sendMessage = async (messageBody: string) => {
    if (!messageBody.trim()) return

    const userMessage: ChatMessage = { role: 'user', content: messageBody.trim() }
    setChat((prev) => [...prev, userMessage])
    setChatLoading(true)
    setError('')

    try {
      const response = await fetch('/api/agent/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: messageBody.trim(),
          student,
          context: {
            currentLesson: student.currentLesson,
            currentTopic: student.currentTopic,
            subject: student.subject,
            grade: student.grade,
          },
          messages: chat.map((item) => ({ role: item.role, content: item.content })),
        }),
      })
      const payload = await response.json()
      if (!response.ok) {
        throw new Error(payload.detail || payload.error || 'AI Tutor không phản hồi được.')
      }
      const answerText = payload.answer || 'Mình chưa có câu trả lời phù hợp lúc này.'
      const sourceList = Array.isArray(payload.sources) ? payload.sources : []
      setChat((prev) => [...prev, { role: 'assistant', content: answerText, sources: sourceList }])
    } catch (err) {
      setChat((prev) => [...prev, { role: 'assistant', content: 'Mình gặp sự cố khi gọi AI Tutor. Hãy thử lại nhé.' }])
      setError(err instanceof Error ? err.message : 'Lỗi không xác định.')
    } finally {
      setChatLoading(false)
    }
  }

  const stats = useMemo(() => ({
    completed: roadmap ? roadmap.chapters.reduce((count, chapter) => count + chapter.lessons.length, 0) : 0,
    current: student.currentLesson,
    streak: 7,
  }), [roadmap, student.currentLesson])

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><Sparkles size={20} /></div>
          <span>Gia Sư AI<span className="brand-dot">.</span></span>
        </div>

        <div className="student-mini">
          <div className="avatar">{student.name.charAt(0).toUpperCase()}</div>
          <div>
            <strong>{student.name}</strong>
            <small>{student.subject} · Lớp {student.grade}</small>
          </div>
        </div>

        <nav>
          {navItems.map(({ id, label, icon: Icon }) => (
            <button key={id} className={`nav-item ${page === id ? 'active' : ''}`} onClick={() => setPage(id)}>
              <Icon size={19} />
              <span>{label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-tip">
          <div className="tip-icon"><Flame size={17} /></div>
          <strong>Mục tiêu hôm nay</strong>
          <span>Hoàn thành 1 bài và 1 mini quiz.</span>
          <div className="mini-progress"><b style={{ width: '58%' }} /></div>
          <small>58% tiến độ</small>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="crumb">
            <span>Hôm nay</span>
            <strong>{page === 'home' ? 'Trang chủ' : page === 'roadmap' ? 'Lộ trình học' : page === 'tutor' ? 'AI Tutor' : 'Pomodoro'}</strong>
          </div>
          <div className="top-actions">
            <div className="streak-pill"><Flame size={17} fill="currentColor" /> {stats.streak} ngày</div>
            <button className="avatar small">{student.name.charAt(0).toUpperCase()}</button>
          </div>
        </header>

        {page === 'home' && (
          <HomePage student={student} setStudent={setStudent} stats={stats} onSelectTutor={() => setPage('tutor')} onSelectRoadmap={() => setPage('roadmap')} />
        )}

        {page === 'roadmap' && (
          <RoadmapPage student={student} roadmap={roadmap} loading={roadmapLoading} error={error} onRefresh={fetchRoadmap} />
        )}

        {page === 'tutor' && (
          <TutorPage student={student} chat={chat} loading={chatLoading} error={error} onSend={sendMessage} onRetry={() => { if (chat.at(-1)?.role === 'user') void sendMessage(chat.at(-1)!.content) }} />
        )}

        {page === 'pomodoro' && <PomodoroState />}
      </main>
    </div>
  )
}

function HomePage({ student, setStudent, stats, onSelectTutor, onSelectRoadmap }: { student: StudentProfile; setStudent: React.Dispatch<React.SetStateAction<StudentProfile>>; stats: { completed: number; current: string; streak: number }; onSelectTutor: () => void; onSelectRoadmap: () => void }) {
  return (
    <div className="page">
      <div className="welcome-row">
        <div>
          <span className="eyebrow"><span className="eyebrow-dot" /> Chào mừng trở lại</span>
          <h1>Học đúng người.<br /><em>{student.subject}</em> lớp {student.grade}</h1>
          <p className="lead">Mình sẽ đồng hành cùng bạn trên từng bài học, dựa trên dữ liệu SGK được truy xuất từ hệ thống RAG.</p>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <button className="primary-btn" onClick={onSelectTutor}>Bắt đầu hỏi AI <ChevronRight size={17} /></button>
            <button className="primary-btn" style={{ background: '#f3f6fb', color: '#1c2d47' }} onClick={onSelectRoadmap}>Xem roadmap</button>
          </div>
          <div style={{ display: 'flex', gap: 12, marginTop: 18, flexWrap: 'wrap' }}>
            <label style={{ fontSize: 12, color: '#5d6d82' }}>
              Môn học
              <select value={student.subject} onChange={(event) => setStudent((current) => ({ ...current, subject: event.target.value }))} style={{ display: 'block', marginTop: 6, padding: '8px 12px', borderRadius: 10, border: '1px solid #dfe7f0' }}>
                <option value="Toán">Toán</option>
                <option value="Ngữ văn">Ngữ văn</option>
                <option value="KHTN">KHTN</option>
                <option value="LSDL">LSDL</option>
              </select>
            </label>
            <label style={{ fontSize: 12, color: '#5d6d82' }}>
              Lớp
              <select value={student.grade} onChange={(event) => setStudent((current) => ({ ...current, grade: Number(event.target.value) }))} style={{ display: 'block', marginTop: 6, padding: '8px 12px', borderRadius: 10, border: '1px solid #dfe7f0' }}>
                <option value={6}>6</option>
                <option value={7}>7</option>
                <option value={8}>8</option>
                <option value={9}>9</option>
              </select>
            </label>
          </div>
        </div>
        <div className="hero-art">
          <div className="sun" />
          <div className="orbit orbit-one" />
          <div className="orbit orbit-two" />
          <div className="bot">
            <div className="antenna" />
            <div className="bot-head"><span /><span /></div>
            <div className="bot-body"><div /></div>
          </div>
          <div className="art-note note-one">+{stats.streak} ngày</div>
          <div className="art-note note-two">{student.currentLesson}</div>
        </div>
      </div>

      <div className="stats-grid">
        <StatCard label="Bài đã học" value={stats.completed} icon={<GraduationCap size={18} />} tone="orange" />
        <StatCard label="Bài hiện tại" value={student.currentLesson.split(':')[0] || 'Bài 1'} icon={<BookOpen size={18} />} tone="yellow" />
        <StatCard label="AI Tutor" value="RAG" icon={<Brain size={18} />} tone="teal" />
        <StatCard label="Chuỗi học" value={`${stats.streak} ngày`} icon={<Flame size={18} />} tone="violet" />
      </div>

      <div className="content-grid">
        <div className="section-block">
          <div className="section-head">
            <div>
              <span className="section-kicker">KHUYẾN NGHỊ</span>
              <h2>Học theo nhịp hiện tại</h2>
            </div>
            <button className="text-btn" onClick={onSelectRoadmap}>Xem chi tiết <ChevronRight size={15} /></button>
          </div>
          <div className="journey-body">
            <div className="journey-progress">
              <div className="circle-progress"><div><strong>58%</strong><span>tiến độ</span></div></div>
              <div>
                <strong>Chương hiện tại: {student.currentTopic}</strong>
                <p>Bạn đang trong giai đoạn luyện tập và củng cố kiến thức hỗ trợ bằng câu hỏi từ AI Tutor.</p>
                <div className="progress-line"><b style={{ width: '58%' }} /></div>
                <small>Đã hoàn thành 12/21 bước học</small>
              </div>
            </div>
            <button className="lesson-cta" onClick={onSelectTutor}>Hỏi AI Tutor về bài đang học</button>
          </div>
        </div>

        <div className="section-block">
          <div className="section-head">
            <div>
              <span className="section-kicker">NHIỆM VỤ</span>
              <h2>Việc cần làm</h2>
            </div>
          </div>
          <div className="task-list">
            <div className="task done"><span className="task-check"><CheckCircle2 size={13} /></span><span>Ôn tập {student.currentTopic}</span></div>
            <div className="task"><span className="task-check" /><span>Hoàn thành bài tập mini trong AI Tutor</span></div>
            <div className="task"><span className="task-check" /><span>Chuẩn bị trước bài tiếp theo trong roadmap</span></div>
          </div>
        </div>
      </div>
    </div>
  )
}

function RoadmapPage({ student, roadmap, loading, error, onRefresh }: { student: StudentProfile; roadmap: RoadmapData | null; loading: boolean; error: string; onRefresh: () => void }) {
  return (
    <div className="page">
      <div className="section-head" style={{ marginBottom: 18 }}>
        <div>
          <span className="section-kicker">ROADMAP</span>
          <h1>{roadmap?.title || `Lộ trình ${student.subject} ${student.grade}`}</h1>
        </div>
        <button className="primary-btn" onClick={onRefresh} style={{ marginTop: 0 }}>
          {loading ? 'Đang tạo...' : 'Tạo lại roadmap'}
        </button>
      </div>

      {error && <div className="alert-box">{error}</div>}

      {loading && <div className="alert-box">Đang truy xuất curriculum từ Pinecone và xây dựng roadmap...</div>}

      {!loading && roadmap && (
        <div className="roadmap-list">
          {roadmap.chapters.map((chapter) => (
            <div key={chapter.id} className="section-block" style={{ marginBottom: 16 }}>
              <div className="section-head">
                <h2>Chương {chapter.chapter}: {chapter.title}</h2>
              </div>
              <div className="lesson-stack">
                {chapter.lessons.map((lesson) => (
                  <div key={lesson.id} className="lesson-row">
                    <div className="lesson-badge">
                      {lesson.status === 'locked' ? <LockKeyhole size={14} /> : <CheckCircle2 size={14} />}
                    </div>
                    <div className="lesson-meta">
                      <strong>{lesson.lesson}. {lesson.title}</strong>
                      <small>{lesson.sources?.[0]?.source || 'SGK'} · Trang {lesson.sources?.[0]?.page || '-'}</small>
                    </div>
                    <span className="status-pill">{lesson.status}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function TutorPage({ student, chat, loading, error, onSend, onRetry }: { student: StudentProfile; chat: ChatMessage[]; loading: boolean; error: string; onSend: (message: string) => void; onRetry: () => void }) {
  const [draft, setDraft] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!draft.trim()) return
    const value = draft.trim()
    setDraft('')
    onSend(value)
  }

  return (
    <div className="page">
      <div className="section-head" style={{ marginBottom: 18 }}>
        <div>
          <span className="section-kicker">AI TUTOR</span>
          <h1>{student.subject} · Lớp {student.grade}</h1>
        </div>
      </div>

      {error && (
        <div className="alert-box">
          {error}
          <button className="text-btn" onClick={onRetry}>Thử lại <RefreshCcw size={14} /></button>
        </div>
      )}

      <div className="chat-shell">
        <div className="chat-window">
          {chat.map((entry, index) => (
            <div key={`${entry.role}-${index}`} className={`chat-bubble ${entry.role === 'user' ? 'user' : 'assistant'}`}>
              <div className="chat-body">
                {entry.content}
              </div>
              {entry.sources && entry.sources.length > 0 && (
                <div className="chat-sources">
                  <strong>Nguồn:</strong>
                  {entry.sources.map((source, sIndex) => (
                    <span key={`${source.source || 'source'}-${sIndex}`}>
                      {source.source || 'SGK'} · {source.chapter ? `Chương ${source.chapter}` : ''} {source.lesson ? `· Bài ${source.lesson}` : ''} {source.page ? `· Trang ${source.page}` : ''}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
          {loading && <div className="chat-bubble assistant"><div className="chat-body">Mình đang kiểm tra context từ Pinecone và xây dựng câu trả lời…</div></div>}
        </div>

        <form className="chat-form" onSubmit={handleSubmit}>
          <textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            rows={3}
            placeholder="Ví dụ: Giải thích cho em bài này từng bước..."
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                if (draft.trim()) {
                  onSend(draft.trim())
                  setDraft('')
                }
              }
            }}
          />
          <button className="primary-btn" type="submit" disabled={loading}>
            <Send size={16} /> Gửi
          </button>
        </form>
      </div>
    </div>
  )
}

function StatCard({ label, value, icon, tone }: { label: string; value: string | number; icon: React.ReactNode; tone: 'orange' | 'yellow' | 'teal' | 'violet' }) {
  return (
    <div className="stat-card">
      <div className={`stat-icon ${tone}`}>{icon}</div>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
    </div>
  )
}

export default App
