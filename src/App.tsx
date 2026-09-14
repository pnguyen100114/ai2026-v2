import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  BookOpen,
  BookMarked,
  Brain,
  CheckCircle2,
  ChevronRight,
  Circle,
  Copy,
  Clock3,
  Flame,
  GraduationCap,
  Award,
  History,
  Home,
  Lightbulb,
  LoaderCircle,
  LogOut,
  Menu,
  Mic,
  MessageSquare,
  MoreHorizontal,
  Paperclip,
  Pencil,
  Plus,
  RefreshCcw,
  Search,
  Send,
  Sparkles,
  Square,
  ThumbsDown,
  ThumbsUp,
  UserRound,
  Volume2,
  VolumeX,
  Trash2,
  X,
} from 'lucide-react'
import PomodoroState from './components/PomodoroState'
import ProfilePage from './components/ProfilePage'
import { usePomodoro } from './contexts/PomodoroContext'
import ChatMessageContent, { citedSourceNumbers } from './components/ChatMessageContent'
import { useAuth } from './contexts/AuthContext'
import { apiFetch, apiJson, apiUrl } from './lib/api'
import { RecordingTooShortError, startRecording, vietnameseBrowserVoice, voiceInputSupported, type Recorder } from './lib/audio'
import * as repository from './services/chatRepository'

type Page = 'home' | 'roadmap' | 'tutor' | 'pomodoro' | 'profile'
type ChatRole = 'user' | 'assistant'
type SourceRef = {
  source?: string
  page?: number
  chapter?: number
  lesson?: number
  score?: number
  /** Book title from the textbook catalog, e.g. "Toán 6 – Tập một"; `source` is the PDF file name. */
  title?: string
  lesson_title?: string
  preview_url?: string
  pdf_page?: number
}
type ChatMessage = {
  id: string
  sender: ChatRole
  text: string
  timestamp: number
  role: ChatRole
  content: string
  prompt?: string
  sources?: SourceRef[]
  understanding?: 'mất gốc' | 'hiểu sơ' | 'đã hiểu'
  checkQuestion?: string
  quickReplies?: string[]
  quick_replies?: string[]
  feedback?: 'up' | 'down'
  failed?: boolean
  /** The attached photo, kept in memory only for this visit (never cached or stored on the server). */
  imagePreview?: string
  /** The problem Mimo copied out of that photo; sent with later turns so Mimo keeps the context after the photo is gone. */
  imageText?: string
}
// `lesson` is the roadmap lesson label the chat is about; the backend uses it to add that lesson's pages and earlier chats.
type ChatSession = { id: string; title: string; subject: string; grade: string; lesson?: string; createdAt: number; updatedAt: number; messages: ChatMessage[] }
type LearningProfile = {
  concepts?: Record<string, { mastery: number; attempts: number; correct: number; streak: number; common_errors?: string[] }>
}
type QuizQuestion = {
  question_id: string
  concept_id: string
  concept: string
  difficulty: number
  difficulty_label: string
  question: string
  options: string[]
  hint: string
  mastery: number
  reason: string
}
type QuizResult = {
  is_correct: boolean
  feedback: string
  explanation: string
  mastery: number
  next_difficulty: number
  next_action: string
  recommendation: { title: string; reason: string; action: { type: string; concept_id: string; difficulty: number } }
}
// GET /api/progress (backend/db.py learning_progress).
type Progress = {
  streak: number
  activeToday: boolean
  today: { questions: number; quizzes: number; quizCorrect: number }
  studiedLessons: string[]
  concepts: Record<string, { mastery: number; attempts: number }>
  masteredThreshold: number
}
type LessonStatus = 'mastered' | 'studied' | 'new'
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
  // 'ai': no textbook in RAG for this subject/grade, outlined by Gemini from the GDPT 2018 curriculum.
  source?: 'rag' | 'ai'
  chapters: RoadmapChapter[]
}

const defaultStudent: StudentProfile = {
  name: 'Minh Anh',
  age: 13,
  grade: 8,
  subject: 'Toán',
  currentLesson: '',
  currentTopic: '',
}

// The current lesson always comes from the student's own roadmap (subject + grade).
function lessonTopic(lesson: RoadmapLesson) {
  return lesson.title.replace(/^bài\s*\d+\s*[:.\-–]?\s*/i, '').trim() || lesson.title
}

function lessonLabel(lesson: RoadmapLesson) {
  return `Bài ${lesson.lesson}: ${lessonTopic(lesson)}`
}

function topicFromLabel(label: string) {
  return label.replace(/^bài\s*\d+\s*:\s*/i, '').trim()
}

const RECENT_CHAT_LIMIT = 5
// Must match MESSAGE_MAX_LENGTH in backend/app.py.
const MESSAGE_MAX_LENGTH = 2000
const IMAGE_MAX_SIDE = 1600

// Phone photos are several MB; re-encode to a JPEG that is plenty for reading a problem and fits the request limit.
function shrinkImage(file: File): Promise<{ data: string; mime: string }> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const image = new window.Image()
    image.onload = () => {
      URL.revokeObjectURL(url)
      const scale = Math.min(1, IMAGE_MAX_SIDE / Math.max(image.naturalWidth, image.naturalHeight))
      const canvas = document.createElement('canvas')
      canvas.width = Math.max(1, Math.round(image.naturalWidth * scale))
      canvas.height = Math.max(1, Math.round(image.naturalHeight * scale))
      const context = canvas.getContext('2d')
      if (!context) return reject(new Error('canvas'))
      context.fillStyle = '#fff'
      context.fillRect(0, 0, canvas.width, canvas.height)
      context.drawImage(image, 0, 0, canvas.width, canvas.height)
      resolve({ data: canvas.toDataURL('image/jpeg', 0.85), mime: 'image/jpeg' })
    }
    image.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('decode'))
    }
    image.src = url
  })
}

function gradeFromLabel(label: string | undefined, fallback: number) {
  return Number(label?.replace(/\D/g, '')) || fallback
}

// Subject values are what the backend and stored chats use.
export const SUBJECTS = [
  { value: 'Toán', label: 'Toán' },
  { value: 'Ngữ văn', label: 'Ngữ văn' },
  { value: 'Tiếng Anh', label: 'Tiếng Anh' },
  { value: 'KHTN', label: 'Khoa học tự nhiên' },
  { value: 'LSDL', label: 'Lịch sử và Địa lý' },
]

// The student as seen from one chat: that chat's own subject and grade.
function inChatScope(student: StudentProfile, session?: { subject: string; grade: string }): StudentProfile {
  return session ? { ...student, subject: session.subject, grade: gradeFromLabel(session.grade, student.grade) } : student
}

// A chat is only kept (cached, listed) once the student has asked something in it.
function hasQuestion(session: ChatSession) {
  return session.messages.some((message) => message.role === 'user')
}

// Photos live in memory only; caching them would fill localStorage quickly.
function withoutImages(messages: ChatMessage[]) {
  return messages.some((message) => message.imagePreview) ? messages.map(({ imagePreview: _image, ...message }) => message) : messages
}

const navItems: { id: Page; label: string; icon: typeof Home }[] = [
  { id: 'home', label: 'Trang chủ', icon: Home },
  { id: 'roadmap', label: 'Lộ trình học', icon: BookOpen },
  { id: 'tutor', label: 'Hỏi Mimo', icon: Brain },
  { id: 'pomodoro', label: 'Pomodoro', icon: Clock3 },
  { id: 'profile', label: 'Hồ sơ', icon: UserRound },
]

function welcomeMessages(student: StudentProfile, lesson = student.currentLesson): ChatMessage[] {
  const topic = lesson ? topicFromLabel(lesson) : ''
  const intro = topic
    ? `Hôm nay em đang học **${topic}** (${student.subject} lớp ${student.grade}) đúng không?`
    : `Mimo sẽ đồng hành cùng em môn **${student.subject} lớp ${student.grade}**.`
  const content = `Chào ${student.name}! 👋 Mimo đây.\n\n${intro} Chỗ nào chưa hiểu em cứ hỏi, chụp ảnh đề bài gửi lên, hoặc nhờ Mimo kiểm tra nhanh cũng được nhé!`
  const quickReplies = [topic ? `Giảng lại ${topic} cho em` : 'Hôm nay em nên học gì?', 'Em có bài tập cần gợi ý', 'Kiểm tra nhanh em nhé']
  return [{ id: 'welcome', sender: 'assistant', text: content, timestamp: Date.now(), role: 'assistant', content, quickReplies, quick_replies: quickReplies }]
}

// The greeting is generated on the client (never stored in the backend), so it must follow the current profile
// and the lesson of its own chat (chats without a lesson follow the student's current lesson).
function withCurrentWelcome(messages: ChatMessage[], student: StudentProfile, lesson?: string): ChatMessage[] {
  const first = messages[0]
  if (!first || first.role !== 'assistant' || !first.content.startsWith('Chào ') || !first.content.includes('Mimo đây')) return messages
  const [fresh] = welcomeMessages(student, lesson || student.currentLesson)
  if (first.content === fresh.content) return messages
  return [{ ...first, text: fresh.text, content: fresh.content, quickReplies: fresh.quickReplies, quick_replies: fresh.quick_replies }, ...messages.slice(1)]
}

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

// Ids double as database primary keys, so they must be globally unique.
function uniqueId(prefix: string) {
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2)}${Math.random().toString(36).slice(2)}`
}

function messageId() {
  return uniqueId('message')
}

const DEFAULT_SESSION_TITLE = 'Cuộc trò chuyện mới'

function sessionsFromHistory(history: repository.History, student: StudentProfile): ChatSession[] {
  return history.sessions.map((row) => {
    const createdAt = Date.parse(row.createdAt)
    const messages = history.messages.filter((message) => message.sessionId === row.id).map((message): ChatMessage => ({
      id: message.id,
      sender: message.role,
      role: message.role,
      text: message.content,
      content: message.content,
      prompt: message.prompt ?? undefined,
      imageText: message.imageText ?? undefined,
      timestamp: Date.parse(message.createdAt),
      sources: message.sources as SourceRef[],
      quickReplies: message.quickReplies,
      quick_replies: message.quickReplies,
      understanding: (message.understanding as ChatMessage['understanding']) ?? undefined,
      feedback: message.feedback ?? undefined,
    }))
    const welcome = welcomeMessages(inChatScope(student, row), row.lesson || student.currentLesson).map((message) => ({ ...message, id: messageId(), timestamp: createdAt }))
    return { id: row.id, title: row.title, subject: row.subject, grade: row.grade, lesson: row.lesson || undefined, createdAt, updatedAt: Date.parse(row.updatedAt), messages: [...welcome, ...messages] }
  })
}

function normalizeMessage(raw: Partial<ChatMessage>, index: number): ChatMessage {
  const content = raw.content ?? raw.text ?? ''
  const role = raw.role ?? raw.sender ?? 'assistant'
  return { ...raw, id: raw.id || `message-migrated-${index}-${Date.now()}`, sender: role, text: content, timestamp: raw.timestamp || Date.now(), role, content }
}

function newSession(student: StudentProfile, title = DEFAULT_SESSION_TITLE, lesson = student.currentLesson): ChatSession {
  const now = Date.now()
  return { id: uniqueId('chat'), title, subject: student.subject, grade: `Lớp ${student.grade}`, lesson: lesson || undefined, createdAt: now, updatedAt: now, messages: welcomeMessages(student, lesson).map((message) => ({ ...message, id: messageId(), timestamp: now })) }
}

function normalizeSession(raw: Partial<ChatSession>, index: number, student: StudentProfile): ChatSession {
  const now = Date.now()
  return {
    id: raw.id || `chat-migrated-${index}-${now}`,
    title: raw.title || 'Cuộc trò chuyện mới',
    subject: raw.subject || student.subject,
    grade: raw.grade || `Lớp ${student.grade}`,
    lesson: raw.lesson,
    createdAt: raw.createdAt || now,
    updatedAt: raw.updatedAt || raw.createdAt || now,
    messages: (raw.messages || []).map(normalizeMessage),
  }
}

function App() {
  const auth = useAuth()
  const account = auth.user!
  const userId = account.id
  // localStorage is only a per-account cache for instant paint; the backend database is the source of truth.
  const storageKey = (name: string) => `${name}:${userId}`
  const [page, setPage] = useState<Page>('tutor')
  const [student, setStudent] = useState<StudentProfile>(() => ({ ...defaultStudent, name: account.name, grade: account.grade, subject: account.subject, currentLesson: account.currentLesson, currentTopic: account.currentTopic }))
  const [roadmap, setRoadmap] = useState<RoadmapData | null>(() => readStorage(storageKey('gia-su-ai-roadmap'), null))
  const [sessions, setSessions] = useState<ChatSession[]>(() => {
    const stored = readStorage<ChatSession[]>(storageKey('gia-su-ai-sessions'), [])
    if (stored.length > 0) return stored.map((session, index) => normalizeSession(session, index, student))
    return [{ ...newSession(student, 'Cuộc trò chuyện hiện tại'), messages: readStorage<ChatMessage[]>(storageKey('gia-su-ai-chat'), welcomeMessages(student)).map(normalizeMessage) }]
  })
  const [currentSessionId, setCurrentSessionId] = useState(() => readStorage<string>(storageKey('gia-su-ai-current-session'), ''))
  const [chat, setChat] = useState<ChatMessage[]>(() => readStorage<ChatMessage[]>(storageKey('gia-su-ai-chat'), welcomeMessages(student)).map(normalizeMessage))
  const lastImageRef = useRef<{ userId: string; data: string; mime?: string } | null>(null)
  const [learningProfile, setLearningProfile] = useState<LearningProfile>(() => account.learningProfile as LearningProfile)
  const skipFirstProfileSave = useRef(true)
  const [quiz, setQuiz] = useState<QuizQuestion | null>(null)
  const [quizAnswer, setQuizAnswer] = useState('')
  const [quizResult, setQuizResult] = useState<QuizResult | null>(null)
  const [quizLoading, setQuizLoading] = useState(false)
  const [chatLoading, setChatLoading] = useState(false)
  const [roadmapLoading, setRoadmapLoading] = useState(false)
  const [error, setError] = useState('')
  const [chatError, setChatError] = useState('')
  const [isEditingSessionId, setIsEditingSessionId] = useState<string | null>(null)
  const [editingSessionTitle, setEditingSessionTitle] = useState('')
  const [showAllChats, setShowAllChats] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const [quizError, setQuizError] = useState('')
  const [hintsUsed, setHintsUsed] = useState(0)
  const [progress, setProgress] = useState<Progress | null>(null)
  const [toast, setToast] = useState('')
  const roadmapRequest = useRef(0)
  const pomodoro = usePomodoro()
  const dailyMinutes = account.onboarding.dailyMinutes || 25

  const showToast = useCallback((message: string) => setToast(message), [])

  // While Mimo is answering (or preparing/grading a practice question) the student stays on this page until it is done.
  const busyMessage = chatLoading ? 'Mimo đang trả lời câu hỏi của em.' : quizLoading ? 'Mimo đang chuẩn bị câu luyện tập.' : ''
  const [busyNotice, setBusyNotice] = useState('')
  const stayWhileBusy = () => {
    if (!busyMessage) return false
    setBusyNotice(busyMessage)
    return true
  }
  useEffect(() => {
    if (busyMessage || !busyNotice) return
    setBusyNotice('')
    showToast('Mimo xong rồi, em chuyển trang được rồi nhé!')
  }, [busyMessage, busyNotice, showToast])
  useEffect(() => {
    if (!busyMessage) return
    // Closing or reloading the tab would lose the answer: ask the browser to confirm.
    const onBeforeUnload = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = '' }
    window.addEventListener('beforeunload', onBeforeUnload)
    return () => window.removeEventListener('beforeunload', onBeforeUnload)
  }, [busyMessage])
  useEffect(() => {
    if (!toast) return
    const timer = window.setTimeout(() => setToast(''), 5000)
    return () => window.clearTimeout(timer)
  }, [toast])
  useEffect(() => {
    const onNotification = (event: Event) => showToast(String((event as CustomEvent).detail || ''))
    window.addEventListener('ai-tutor-notification', onNotification)
    return () => window.removeEventListener('ai-tutor-notification', onNotification)
  }, [showToast])

  const refreshProgress = useCallback(async () => {
    try {
      const params = new URLSearchParams({ subject: student.subject, grade: String(student.grade) })
      const response = await apiFetch(`/api/progress?${params}`)
      if (response.ok) setProgress(await response.json())
    } catch {
      // Stats are decoration; the rest of the app works without them.
    }
  }, [student.subject, student.grade])
  useEffect(() => {
    void refreshProgress()
  }, [refreshProgress])

  // Load this account's chat history from the backend once after login.
  useEffect(() => {
    let cancelled = false
    repository.loadHistory().then((history) => {
      if (cancelled) return
      const remote = sessionsFromHistory(history, student)
      const nextSessions = remote.length > 0 ? remote : [newSession(student)]
      setSessions(nextSessions)
      const current = nextSessions.find((session) => session.id === currentSessionId) ?? nextSessions[0]
      setCurrentSessionId(current.id)
      setChat(current.messages)
    }).catch((err) => console.error('Không tải được lịch sử trò chuyện', err))
    return () => { cancelled = true }
  }, [userId])

  // Sync name/grade/subject changes (Home page selectors) to the account, debounced.
  useEffect(() => {
    if (skipFirstProfileSave.current) {
      skipFirstProfileSave.current = false
      return
    }
    const timer = window.setTimeout(() => {
      void repository.saveProfile({ name: student.name, grade: student.grade, subject: student.subject, currentLesson: student.currentLesson, currentTopic: student.currentTopic }).catch((err) => console.error('Không lưu được hồ sơ', err))
    }, 800)
    return () => window.clearTimeout(timer)
  }, [student])

  useEffect(() => {
    writeStorage(storageKey('gia-su-ai-chat'), withoutImages(chat))
    setSessions((current) => current.map((session) => {
      if (session.id !== currentSessionId || session.messages === chat) return session
      // Opening a chat or refreshing its greeting is not activity; only a new or edited last message moves it to the top.
      const changed = session.messages.length !== chat.length || session.messages.at(-1)?.content !== chat.at(-1)?.content
      const firstQuestion = chat.find((item) => item.role === 'user')
      return { ...session, messages: chat, updatedAt: changed ? Date.now() : session.updatedAt, title: session.title === DEFAULT_SESSION_TITLE && firstQuestion ? firstQuestion.content.slice(0, 42) : session.title }
    }))
  }, [chat, currentSessionId])

  useEffect(() => {
    if ((!currentSessionId || !sessions.some((session) => session.id === currentSessionId)) && sessions[0]) {
      setCurrentSessionId(sessions[0].id)
      setChat(sessions[0].messages)
    }
  }, [currentSessionId, sessions])

  useEffect(() => {
    writeStorage(storageKey('gia-su-ai-sessions'), sessions.filter(hasQuestion).map((session) => ({ ...session, messages: withoutImages(session.messages) })))
    writeStorage(storageKey('gia-su-ai-current-session'), currentSessionId)
  }, [sessions, currentSessionId])

  useEffect(() => {
    writeStorage(storageKey('gia-su-ai-roadmap'), roadmap)
  }, [roadmap])

  useEffect(() => {
    writeStorage(storageKey('gia-su-ai-learning-profile'), learningProfile)
  }, [learningProfile])

  const fetchRoadmap = async () => {
    // Switching subject/grade quickly fires several requests; only the latest one may update the page.
    const requestId = ++roadmapRequest.current
    setRoadmapLoading(true)
    setError('')
    try {
      const response = await apiFetch('/api/roadmap/generate', {
        method: 'POST',
        body: JSON.stringify({ student }),
      })
      const payload = await response.json().catch(() => ({}))
      if (requestId !== roadmapRequest.current) return
      if (!response.ok || !payload.success) {
        if (response.status === 404) throw new Error(`Mimo chưa có lộ trình cho ${student.subject} lớp ${student.grade}. Em thử lại sau hoặc chọn môn khác nhé.`)
        throw new Error(typeof payload.detail === 'string' ? payload.detail : 'Mimo chưa soạn được lộ trình, em bấm "Tạo lại lộ trình" nhé.')
      }
      setRoadmap(payload.roadmap)
    } catch (err) {
      if (requestId !== roadmapRequest.current) return
      setError(err instanceof Error && !(err instanceof TypeError) ? err.message : 'Mimo chưa kết nối được máy chủ, em kiểm tra mạng rồi thử lại nhé.')
    } finally {
      if (requestId === roadmapRequest.current) setRoadmapLoading(false)
    }
  }

  useEffect(() => {
    void fetchRoadmap()
  }, [student.subject, student.grade])

  const selectLesson = (lesson: RoadmapLesson) => {
    setStudent((current) => ({ ...current, currentLesson: lessonLabel(lesson), currentTopic: lessonTopic(lesson) }))
  }

  // Keep the current lesson inside this grade/subject roadmap: start at its first lesson when none (or a stale one) is set.
  useEffect(() => {
    if (!roadmap || roadmap.grade !== student.grade || roadmap.subject !== student.subject) return
    const lessons = roadmap.chapters.flatMap((chapter) => chapter.lessons)
    if (lessons.length === 0 || lessons.some((lesson) => lessonLabel(lesson) === student.currentLesson)) return
    selectLesson(lessons[0])
  }, [roadmap, student.grade, student.subject, student.currentLesson])

  // Refresh the greeting in every chat when name/grade/subject/lesson change (it may have been created for another grade).
  useEffect(() => {
    const open = sessions.find((session) => session.id === currentSessionId)
    setChat((current) => withCurrentWelcome(current, inChatScope(student, open), open?.lesson))
    setSessions((current) => current.map((session) => {
      const messages = withCurrentWelcome(session.messages, inChatScope(student, session), session.lesson)
      return messages === session.messages ? session : { ...session, messages }
    }))
  }, [student.name, student.grade, student.subject, student.currentTopic])

  // A practice question belongs to one lesson; drop it when the lesson changes.
  useEffect(() => {
    setQuiz(null)
    setQuizAnswer('')
    setQuizResult(null)
    setQuizError('')
    setHintsUsed(0)
  }, [student.grade, student.subject, student.currentLesson])

  const sendMessage = async (messageBody: string, imageData?: string, imageMimeType?: string, baseChat: ChatMessage[] = chat, replacesMessageId?: string) => {
    if ((!messageBody.trim() && !imageData) || chatLoading) return
    const submittedMessage = messageBody.trim() || 'Em gửi ảnh đề bài, Mimo đọc và gợi ý cách làm giúp em nhé.'
    const currentSession = sessions.find((session) => session.id === currentSessionId)
    const lesson = currentSession?.lesson || student.currentLesson
    // A chat keeps the subject/grade it was started in, even when opened while studying another subject.
    const chatSubject = currentSession?.subject || student.subject
    const chatGrade = gradeFromLabel(currentSession?.grade, student.grade)

    const userContent = imageData ? `${submittedMessage}\n\n📷 Ảnh đề bài đã đính kèm.` : submittedMessage
    const userMessage: ChatMessage = { id: messageId(), sender: 'user', text: userContent, timestamp: Date.now(), role: 'user', content: userContent, prompt: submittedMessage, imagePreview: imageData }
    const assistantMessage: ChatMessage = { id: messageId(), sender: 'assistant', text: '', timestamp: Date.now(), role: 'assistant', content: '' }
    if (imageData) lastImageRef.current = { userId: userMessage.id, data: imageData, mime: imageMimeType }
    // Patch a message by id in both the open chat and the stored sessions: the student may switch chats while Mimo is still writing.
    const patchMessage = (id: string, patch: (item: ChatMessage) => ChatMessage) => {
      const apply = (messages: ChatMessage[]) => messages.some((item) => item.id === id) ? messages.map((item) => item.id === id ? patch(item) : item) : messages
      setChat(apply)
      setSessions((current) => current.map((session) => {
        const messages = apply(session.messages)
        return messages === session.messages ? session : { ...session, messages }
      }))
    }
    const patchAnswer = (patch: (item: ChatMessage) => ChatMessage) => patchMessage(assistantMessage.id, patch)
    setChat([...baseChat, userMessage, assistantMessage])
    setChatLoading(true)
    setChatError('')

    try {
      const response = await apiFetch('/api/chat/stream', {
        method: 'POST',
        body: JSON.stringify({
          session: currentSession && {
            id: currentSession.id,
            title: currentSession.title === DEFAULT_SESSION_TITLE || currentSession.title === 'Cuộc trò chuyện hiện tại' ? (baseChat.find((item) => item.role === 'user')?.content ?? userContent).slice(0, 42) : currentSession.title,
            subject: currentSession.subject,
            grade: currentSession.grade,
            lesson,
          },
          user_message_id: userMessage.id,
          assistant_message_id: assistantMessage.id,
          replaces_message_id: replacesMessageId,
          message: submittedMessage,
          student: { ...student, subject: chatSubject, grade: chatGrade },
          context: {
            currentLesson: lesson,
            currentTopic: lesson ? topicFromLabel(lesson) : '',
            subject: chatSubject,
            grade: chatGrade,
          },
          messages: baseChat.filter((item) => item.content.trim()).map((item) => ({ role: item.role, content: item.content, ...(item.imageText ? { image_text: item.imageText } : {}) })),
          image_data: imageData,
          image_mime_type: imageMimeType,
        }),
      })
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}))
        if (response.status === 422) throw new Error('Tin nhắn hoặc ảnh của em dài quá. Em rút gọn câu hỏi hoặc chọn ảnh khác rồi gửi lại nhé.')
        throw new Error(typeof payload.detail === 'string' ? payload.detail : 'Mimo chưa trả lời được lượt này. Em bấm "Thử lại" nhé.')
      }
      if (!response.body) throw new Error('Mimo chưa trả lời được lượt này. Em bấm "Thử lại" nhé.')
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      const processEvent = (event: string) => {
        const line = event.split(/\r?\n/).find((item) => item.startsWith('data: '))
        if (!line) return
        const payload = JSON.parse(line.slice(6)) as { type: string; text?: string; content?: string; sources?: SourceRef[]; quick_replies?: string[]; understanding?: ChatMessage['understanding'] | null; image_text?: string; message?: string }
        if (payload.type === 'error') throw new Error(payload.message || 'Mimo chưa trả lời được lượt này.')
        if (payload.type === 'chunk' && payload.text) {
          const text = payload.text
          patchAnswer((item) => ({ ...item, content: item.content + text, text: item.text + text }))
        }
        // The server sends a cleaned copy of the answer (stray citations removed) to replace the streamed text.
        if (payload.type === 'done' && payload.image_text) {
          const imageText = payload.image_text
          patchMessage(userMessage.id, (item) => ({ ...item, imageText }))
        }
        if (payload.type === 'done') patchAnswer((item) => ({ ...item, content: payload.content ?? item.content, text: payload.content ?? item.text, sources: payload.sources || [], understanding: payload.understanding || undefined, quickReplies: payload.quick_replies || [], quick_replies: payload.quick_replies || [] }))
      }
      while (true) {
        const { value, done } = await reader.read()
        buffer += decoder.decode(value || new Uint8Array(), { stream: !done })
        const events = buffer.split(/\r?\n\r?\n/)
        buffer = events.pop() || ''
        for (const event of events) processEvent(event)
        if (done) {
          if (buffer.trim()) processEvent(buffer)
          break
        }
      }
    } catch (err) {
      const message = err instanceof Error && !(err instanceof TypeError) ? err.message : 'Mimo chưa kết nối được. Em kiểm tra mạng rồi bấm "Thử lại" nhé.'
      patchAnswer((item) => item.content.trim() ? item : { ...item, content: message, text: message, failed: true })
      setChatError('')
    } finally {
      setChatLoading(false)
      void refreshProgress()
    }
  }

  // Re-ask the student question that produced the assistant message at `assistantIndex`, replacing that answer.
  const retryFrom = (assistantIndex: number) => {
    const userIndex = chat.slice(0, assistantIndex).map((item) => item.role).lastIndexOf('user')
    if (userIndex < 0) return
    const userMessage = chat[userIndex]
    const image = lastImageRef.current?.userId === userMessage.id ? lastImageRef.current : null
    if (!image && userMessage.content.endsWith('📷 Ảnh đề bài đã đính kèm.')) showToast('Ảnh đề bài không còn sau khi tải lại trang. Mimo trả lời lại theo phần chữ, em gửi lại ảnh nếu cần nhé.')
    const prompt = userMessage.prompt ?? userMessage.content.replace(/\n\n📷 Ảnh đề bài đã đính kèm\.$/, '')
    void sendMessage(prompt, image?.data, image?.mime, chat.slice(0, userIndex), userMessage.id)
  }

  // A new chat replaces any other chat nobody has asked anything in yet, so empty chats never pile up.
  const startChat = (title?: string, lesson?: string) => {
    const session = newSession(student, title, lesson)
    setSessions((current) => [session, ...current.filter(hasQuestion)])
    setCurrentSessionId(session.id)
    setChat(session.messages)
    setPage('tutor')
  }

  const createNewChat = () => {
    if (stayWhileBusy()) return
    startChat()
  }

  const selectChat = (session: ChatSession) => {
    if (stayWhileBusy()) return
    // Leaving an empty chat drops it.
    setSessions((current) => current.filter((item) => item.id === session.id || hasQuestion(item)))
    setCurrentSessionId(session.id)
    setChat(session.messages)
    setPage('tutor')
    // Reopening a lesson chat of this roadmap makes that lesson the current one, so practice follows the chat.
    const { lesson } = session
    if (lesson && lesson !== student.currentLesson && session.subject === student.subject && session.grade === `Lớp ${student.grade}`) {
      setStudent((current) => ({ ...current, currentLesson: lesson, currentTopic: topicFromLabel(lesson) }))
    }
  }

  // Studying a lesson starts a fresh chat titled with the lesson; earlier chats of that lesson still reach Mimo
  // through the backend's lesson history. An untouched chat of the same lesson is reused instead of piling up empty ones.
  const openLessonChat = (lesson: string) => {
    if (stayWhileBusy()) return
    const grade = `Lớp ${student.grade}`
    const unused = sessions.find((session) => session.lesson === lesson && session.subject === student.subject && session.grade === grade && !hasQuestion(session))
    if (unused) selectChat(unused)
    else startChat(lesson, lesson)
  }

  // The open chat is kept only if it belongs to the selected subject, grade and lesson; otherwise switch to (or start) one that does.
  const openTutor = () => {
    if (stayWhileBusy()) return
    const open = sessions.find((session) => session.id === currentSessionId)
    const inScope = open?.subject === student.subject && open.grade === `Lớp ${student.grade}`
    if (inScope && (!student.currentLesson || open?.lesson === student.currentLesson)) setPage('tutor')
    else if (student.currentLesson) openLessonChat(student.currentLesson)
    // The new roadmap (and so the lesson) is not loaded yet: start a chat for this subject/grade.
    else startChat()
  }

  const startRenameChat = (event: React.MouseEvent, session: ChatSession) => {
    event.stopPropagation()
    setIsEditingSessionId(session.id)
    setEditingSessionTitle(session.title)
  }

  const finishRenameChat = (sessionId: string, save: boolean) => {
    const nextTitle = editingSessionTitle.trim()
    const previousTitle = sessions.find((item) => item.id === sessionId)?.title
    setIsEditingSessionId(null)
    setEditingSessionTitle('')
    if (!save || !nextTitle || nextTitle === previousTitle) return
    setSessions((current) => current.map((item) => item.id === sessionId ? { ...item, title: nextTitle } : item))
    repository.renameSession(sessionId, nextTitle).catch(() => {
      setSessions((current) => current.map((item) => item.id === sessionId && item.title === nextTitle ? { ...item, title: previousTitle ?? item.title } : item))
      showToast('Mimo chưa đổi được tên cuộc trò chuyện, em kiểm tra mạng rồi thử lại nhé.')
    })
  }

  const deleteChat = async (sessionId: string) => {
    if (stayWhileBusy() || !window.confirm('Xóa cuộc trò chuyện này?')) return
    try {
      await repository.deleteSession(sessionId)
    } catch {
      showToast('Mimo chưa xóa được cuộc trò chuyện, em kiểm tra mạng rồi thử lại nhé.')
      return
    }
    const remaining = sessions.filter((item) => item.id !== sessionId)
    const replacement = remaining.length === 0 ? newSession(student) : null
    setSessions((current) => {
      const rest = current.filter((item) => item.id !== sessionId)
      return rest.length > 0 ? rest : [replacement ?? newSession(student)]
    })
    if (replacement) {
      setCurrentSessionId(replacement.id)
      setChat(replacement.messages)
    } else if (sessionId === currentSessionId) {
      setCurrentSessionId(remaining[0].id)
      setChat(remaining[0].messages)
    }
  }

  const loadQuiz = async () => {
    setQuizLoading(true)
    setQuizError('')
    try {
      const response = await apiFetch('/api/quiz/next', {
        method: 'POST',
        body: JSON.stringify({ student, context: { currentLesson: student.currentLesson, currentTopic: student.currentTopic } }),
      })
      const payload = await response.json()
      if (!response.ok || !payload.question) throw new Error(payload.detail || 'Không thể tạo câu hỏi luyện tập.')
      setQuiz(payload.question)
      setQuizAnswer('')
      setQuizResult(null)
      setHintsUsed(0)
    } catch (err) {
      setQuizError(err instanceof Error && !(err instanceof TypeError) ? err.message : 'Mimo chưa tạo được câu luyện tập, em thử lại nhé.')
    } finally {
      setQuizLoading(false)
    }
  }

  const submitQuizAnswer = async () => {
    if (!quiz || !quizAnswer.trim()) return
    setQuizLoading(true)
    setQuizError('')
    try {
      const response = await apiFetch('/api/quiz/answer', {
        method: 'POST',
        body: JSON.stringify({ question_id: quiz.question_id, answer: quizAnswer, hints_used: hintsUsed }),
      })
      const payload = await response.json()
      if (!response.ok) throw new Error(payload.detail || 'Không thể chấm câu trả lời.')
      setQuizResult(payload)
      setLearningProfile(payload.profile)
    } catch (err) {
      setQuizError(err instanceof Error && !(err instanceof TypeError) ? err.message : 'Mimo chưa chấm được câu này, em thử lại nhé.')
    } finally {
      setQuizLoading(false)
      void refreshProgress()
    }
  }

  const signOut = () => {
    if (stayWhileBusy()) return
    if (window.confirm('Đăng xuất khỏi Gia Sư AI? Lịch sử học của em vẫn được lưu, lần sau em đăng nhập bằng email và mật khẩu nhé.')) auth.signOut()
  }

  const giveFeedback =(index: number, rating: 'up' | 'down', comment?: string) => {
    const message = chat[index]
    if (!message) return
    setChat((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, feedback: rating } : item))
    void repository.saveFeedback(message.id, rating, comment).catch((err) => console.error('Không lưu được đánh giá', err))
  }

  // Only chats with a question are listed; the open empty chat is not saved yet.
  const sortedSessions = useMemo(() => sessions.filter(hasQuestion).sort((left, right) => right.updatedAt - left.updatedAt), [sessions])
  const subjectSessions = useMemo(() => sortedSessions.filter((session) => session.subject === student.subject && session.grade === `Lớp ${student.grade}`), [sortedSessions, student.subject, student.grade])

  const renderSessionItem = (session: ChatSession) => (
    <div key={session.id} className={`chat-history-item ${session.id === currentSessionId ? 'active' : ''}`}>
      {isEditingSessionId === session.id ? <input className="chat-history-edit" autoFocus value={editingSessionTitle} title={editingSessionTitle} onChange={(event) => setEditingSessionTitle(event.target.value)} onClick={(event) => event.stopPropagation()} onBlur={() => finishRenameChat(session.id, true)} onKeyDown={(event) => { if (event.key === 'Enter') { event.preventDefault(); finishRenameChat(session.id, true) } if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); finishRenameChat(session.id, false) } }} /> : <button type="button" className="chat-history-select" onClick={() => { selectChat(session); setShowAllChats(false) }} title={`${session.title} · ${session.subject} · ${session.grade}`}><MessageSquare size={14} /><span><strong>{session.title}</strong><small>{session.lesson && session.lesson !== session.title ? `${session.lesson} · ` : ''}{new Date(session.updatedAt).toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' })} ({SUBJECTS.find((item) => item.value === session.subject)?.label ?? session.subject} - {session.grade})</small></span></button>}
      <details className="chat-history-menu"><summary aria-label="Tùy chọn cuộc trò chuyện"><MoreHorizontal size={14} /></summary><div className="chat-history-actions"><button type="button" onClick={(event) => { event.currentTarget.closest('details')?.removeAttribute('open'); startRenameChat(event, session) }}><Pencil size={12} /> Đổi tên</button><button type="button" onClick={(event) => { event.currentTarget.closest('details')?.removeAttribute('open'); void deleteChat(session.id) }}><Trash2 size={12} /> Xóa</button></div></details>
    </div>
  )

  const lessonStatus = useCallback((lesson: RoadmapLesson): LessonStatus => {
    const concept = progress?.concepts[lessonTopic(lesson)]
    if (concept && concept.mastery >= (progress?.masteredThreshold ?? 0.7)) return 'mastered'
    if (progress?.studiedLessons.includes(lessonLabel(lesson)) || (concept?.attempts ?? 0) > 0) return 'studied'
    return 'new'
  }, [progress])

  const stats = useMemo(() => {
    const lessons = roadmap && roadmap.subject === student.subject && roadmap.grade === student.grade ? roadmap.chapters.flatMap((chapter) => chapter.lessons) : []
    const statuses = lessons.map(lessonStatus)
    const studied = statuses.filter((status) => status !== 'new').length
    const focusDone = Math.min(1, pomodoro.todayFocusMinutes / dailyMinutes)
    const tasks = [
      { label: 'Hỏi Mimo ít nhất 1 câu về bài đang học', done: (progress?.today.questions ?? 0) > 0 },
      { label: 'Làm 1 câu luyện tập', done: (progress?.today.quizzes ?? 0) > 0 },
      { label: `Tập trung ${dailyMinutes} phút (${Math.min(pomodoro.todayFocusMinutes, dailyMinutes)}/${dailyMinutes})`, done: focusDone >= 1 },
    ]
    return {
      streak: progress?.streak ?? 0,
      totalLessons: lessons.length,
      studied,
      mastered: statuses.filter((status) => status === 'mastered').length,
      lessonPercent: lessons.length ? Math.round(studied / lessons.length * 100) : 0,
      tasks,
      goalPercent: Math.round((Number(tasks[0].done) + Number(tasks[1].done) + focusDone) / 3 * 100),
    }
  }, [roadmap, student.subject, student.grade, lessonStatus, progress, pomodoro.todayFocusMinutes, dailyMinutes])

  const openSession = sessions.find((session) => session.id === currentSessionId)
  const chatScope = openSession ? `${openSession.subject} · ${openSession.grade}` : `${student.subject} · Lớp ${student.grade}`
  // "Theo sách giáo khoa" only when Mimo can actually cite pages: a textbook roadmap, or answers in this chat that cited the book.
  const chatFollowsCurriculumOnly = Boolean(roadmap?.source === 'ai' && `${roadmap.subject} · Lớp ${roadmap.grade}` === chatScope && !chat.some((message) => message.sources?.length))

  return (
    <div className="app-shell">
      {menuOpen && <div className="scrim" role="presentation" onClick={() => setMenuOpen(false)} />}
      <aside className={`sidebar ${menuOpen ? 'is-open' : ''}`}>
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
            <button key={id} className={`nav-item ${page === id ? 'active' : ''}`} onClick={() => { setMenuOpen(false); if (id === 'tutor' && page !== 'tutor') openTutor(); else if (id === page || !stayWhileBusy()) setPage(id) }}>
              <Icon size={19} />
              <span>{label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-tip">
          <div className="tip-icon"><Flame size={17} /></div>
          <strong>Mục tiêu hôm nay</strong>
          <span>{stats.tasks.filter((task) => task.done).length}/{stats.tasks.length} việc: hỏi Mimo, luyện tập, tập trung {dailyMinutes} phút.</span>
          <div className="mini-progress"><b style={{ width: `${stats.goalPercent}%` }} /></div>
          <small>{stats.goalPercent}% hoàn thành</small>
        </div>

        <button type="button" className="sidebar-logout" onClick={signOut}><LogOut size={17} /> Đăng xuất</button>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <button type="button" className="mobile-menu" onClick={() => setMenuOpen(true)} aria-label="Mở menu" aria-expanded={menuOpen}><Menu size={22} /></button>
          <div className="crumb">
            <span>Hôm nay</span>
            <strong>{navItems.find((item) => item.id === page)?.label}</strong>
          </div>
          <div className="top-actions">
            <div className="streak-pill" title={progress?.activeToday ? 'Hôm nay em đã học rồi, giữ chuỗi nhé!' : 'Học hôm nay để giữ chuỗi ngày học'}><Flame size={17} fill="currentColor" /> {stats.streak} ngày</div>
            <details className="account-menu">
              <summary className="avatar small" aria-label="Tài khoản">{student.name.charAt(0).toUpperCase()}</summary>
              <div className="account-menu-panel">
                <strong>{student.name}</strong>
                <small>{account.email}</small>
                <button type="button" onClick={(event) => { event.currentTarget.closest('details')?.removeAttribute('open'); if (page === 'profile' || !stayWhileBusy()) setPage('profile') }}><UserRound size={14} /> Hồ sơ & mật khẩu</button>
                <button type="button" onClick={signOut}><LogOut size={14} /> Đăng xuất</button>
              </div>
            </details>
          </div>
        </header>

        {page === 'home' && (
          <HomePage student={student} setStudent={setStudent} stats={stats} schoolGrade={account.onboarding.schoolGrade} onSelectTutor={openTutor} onSelectRoadmap={() => setPage('roadmap')} />
        )}

        {page === 'roadmap' && (
          <RoadmapPage student={student} roadmap={roadmap} loading={roadmapLoading} error={error} stats={stats} lessonStatus={lessonStatus} onRefresh={fetchRoadmap} onSelectLesson={(lesson) => { selectLesson(lesson); openLessonChat(lessonLabel(lesson)) }} />
        )}

        {page === 'tutor' && (
          <TutorPage student={student} chatScope={chatScope} curriculumOnly={chatFollowsCurriculumOnly} lessonName={openSession?.lesson || student.currentLesson} recentSessions={subjectSessions.slice(0, RECENT_CHAT_LIMIT)} totalSessions={sortedSessions.length} renderSessionItem={renderSessionItem} onNewChat={createNewChat} onShowAllChats={() => setShowAllChats(true)} chat={chat} loading={chatLoading} error={chatError} onSend={(message, imageData, imageMimeType) => void sendMessage(message, imageData, imageMimeType)} onFeedback={giveFeedback} onRetry={retryFrom} quiz={quiz} quizAnswer={quizAnswer} quizResult={quizResult} quizLoading={quizLoading} quizError={quizError} hintShown={hintsUsed > 0} onShowHint={() => setHintsUsed((count) => Math.max(count, 1))} onQuizAnswer={setQuizAnswer} onLoadQuiz={loadQuiz} onSubmitQuiz={submitQuizAnswer} />
        )}

        {page === 'profile' && <ProfilePage name={student.name} email={account.email} grade={student.grade} onRename={(name) => setStudent((current) => ({ ...current, name }))} />}

        {page === 'pomodoro' && <PomodoroState streak={stats.streak} lesson={student.currentLesson} dailyMinutes={dailyMinutes} />}
      </main>
      {toast && <div className="app-toast" role="status"><span>{toast}</span><button type="button" onClick={() => setToast('')} aria-label="Đóng thông báo"><X size={14} /></button></div>}
      {busyNotice && (
        <div className="source-modal-backdrop busy-backdrop" role="presentation" onClick={() => setBusyNotice('')}>
          <div className="source-modal busy-modal" role="alertdialog" aria-modal="true" aria-labelledby="busy-title" onClick={(event) => event.stopPropagation()}>
            <div className="busy-spinner" aria-hidden="true" />
            <strong id="busy-title">Em đợi Mimo một chút nhé!</strong>
            <p>{busyNotice} Khi Mimo xong, em chuyển trang được ngay, câu trả lời sẽ không bị mất.</p>
            <button type="button" className="primary-btn" autoFocus onClick={() => setBusyNotice('')}>Em đợi</button>
          </div>
        </div>
      )}
      {showAllChats && <AllChatsModal sessions={sortedSessions} currentGroup={`${student.subject} · Lớp ${student.grade}`} renderItem={renderSessionItem} onClose={() => setShowAllChats(false)} onNewChat={() => { createNewChat(); setShowAllChats(false) }} />}
    </div>
  )
}

type Stats = { streak: number; totalLessons: number; studied: number; mastered: number; lessonPercent: number; tasks: { label: string; done: boolean }[]; goalPercent: number }

function HomePage({ student, setStudent, stats, schoolGrade, onSelectTutor, onSelectRoadmap }: { student: StudentProfile; setStudent: React.Dispatch<React.SetStateAction<StudentProfile>>; stats: Stats; schoolGrade?: number; onSelectTutor: () => void; onSelectRoadmap: () => void }) {
  const subjectLabel = SUBJECTS.find((item) => item.value === student.subject)?.label ?? student.subject
  return (
    <div className="page">
      <div className="welcome-row">
        <div>
          <span className="eyebrow"><span className="eyebrow-dot" /> Chào {student.name}</span>
          <h1>Mỗi ngày một chút,<br /><em>{subjectLabel}</em> lớp {student.grade}</h1>
          <p className="lead">Mimo đồng hành cùng em trên từng bài học, bám sát sách giáo khoa và nhịp học của em.</p>
          <div className="home-actions">
            <button className="primary-btn" onClick={onSelectTutor}>Hỏi Mimo <ChevronRight size={17} /></button>
            <button className="primary-btn secondary" onClick={onSelectRoadmap}>Xem lộ trình</button>
          </div>
          <div className="home-selectors">
            <label>
              Môn học
              <select value={student.subject} onChange={(event) => setStudent((current) => ({ ...current, subject: event.target.value, currentLesson: '', currentTopic: '' }))}>
                {SUBJECTS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
              </select>
            </label>
            <label>
              Lớp
              <select value={student.grade} onChange={(event) => setStudent((current) => ({ ...current, grade: Number(event.target.value), currentLesson: '', currentTopic: '' }))}>
                {[6, 7, 8, 9].map((grade) => <option key={grade} value={grade}>{grade}</option>)}
              </select>
            </label>
          </div>
          {schoolGrade && schoolGrade !== student.grade && <p className="grade-note">Em đang học lớp {schoolGrade} và {schoolGrade < student.grade ? 'học trước' : 'ôn lại'} chương trình lớp {student.grade}.</p>}
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
          <div className="art-note note-one">{stats.streak > 0 ? `🔥 ${stats.streak} ngày` : 'Bắt đầu chuỗi học!'}</div>
          <div className="art-note note-two">{student.currentLesson || 'Chọn bài trong lộ trình'}</div>
        </div>
      </div>

      <div className="stats-grid">
        <StatCard label="Bài đã học" value={stats.totalLessons ? `${stats.studied}/${stats.totalLessons}` : '0'} icon={<GraduationCap size={18} />} tone="orange" />
        <StatCard label="Bài hiện tại" value={student.currentLesson.split(':')[0] || 'Chưa chọn'} icon={<BookOpen size={18} />} tone="yellow" />
        <StatCard label="Bài đã vững" value={stats.mastered} icon={<Award size={18} />} tone="teal" />
        <StatCard label="Chuỗi học" value={`${stats.streak} ngày`} icon={<Flame size={18} />} tone="violet" />
      </div>

      <div className="content-grid">
        <div className="section-block">
          <div className="section-head">
            <div>
              <span className="section-kicker">TIẾN ĐỘ</span>
              <h2>Lộ trình của em</h2>
            </div>
            <button className="text-btn" onClick={onSelectRoadmap}>Xem chi tiết <ChevronRight size={15} /></button>
          </div>
          <div className="journey-body">
            <div className="journey-progress">
              <div className="circle-progress"><div><strong>{stats.lessonPercent}%</strong><span>đã học</span></div></div>
              <div>
                <strong>{student.currentTopic ? `Bài hiện tại: ${student.currentTopic}` : 'Chưa chọn bài – mở Lộ trình học để bắt đầu'}</strong>
                <p>{stats.studied === 0 ? 'Em chưa học bài nào trong lộ trình này. Bắt đầu từ bài đầu tiên nhé!' : `Em đã học ${stats.studied} bài, trong đó ${stats.mastered} bài đã vững (làm luyện tập đạt từ 70%).`}</p>
                <div className="progress-line"><b style={{ width: `${stats.lessonPercent}%` }} /></div>
                <small>{stats.totalLessons ? `Đã học ${stats.studied}/${stats.totalLessons} bài` : 'Đang tải lộ trình...'}</small>
              </div>
            </div>
            <button className="lesson-cta" onClick={onSelectTutor}>Hỏi Mimo về bài đang học</button>
          </div>
        </div>

        <div className="section-block">
          <div className="section-head">
            <div>
              <span className="section-kicker">HÔM NAY</span>
              <h2>Việc cần làm</h2>
            </div>
            <span className="task-percent">{stats.goalPercent}%</span>
          </div>
          <div className="task-list">
            {stats.tasks.map((task) => (
              <div key={task.label} className={`task ${task.done ? 'done' : ''}`}><span className="task-check">{task.done && <CheckCircle2 size={13} />}</span><span>{task.label}</span></div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

const LESSON_BADGES: Record<LessonStatus, { icon: React.ReactNode; label: string }> = {
  mastered: { icon: <Award size={14} />, label: 'Đã vững' },
  studied: { icon: <CheckCircle2 size={14} />, label: 'Đã học' },
  new: { icon: <Circle size={14} />, label: 'Chưa học' },
}

function RoadmapPage({ student, roadmap, loading, error, stats, lessonStatus, onRefresh, onSelectLesson }: { student: StudentProfile; roadmap: RoadmapData | null; loading: boolean; error: string; stats: Stats; lessonStatus: (lesson: RoadmapLesson) => LessonStatus; onRefresh: () => void; onSelectLesson: (lesson: RoadmapLesson) => void }) {
  const matches = roadmap && roadmap.subject === student.subject && roadmap.grade === student.grade
  return (
    <div className="page">
      <div className="section-head roadmap-head">
        <div>
          <span className="section-kicker">LỘ TRÌNH HỌC</span>
          <h1>{matches ? roadmap.title : `Lộ trình ${student.subject} ${student.grade}`}</h1>
          {matches && stats.totalLessons > 0 && <p className="subtext">Đã học {stats.studied}/{stats.totalLessons} bài · {stats.mastered} bài đã vững</p>}
        </div>
        <button className="primary-btn" onClick={onRefresh} disabled={loading}>
          {loading ? 'Đang tải...' : 'Tạo lại lộ trình'}
        </button>
      </div>

      {error && <div className="alert-box">{error}</div>}

      {loading && <div className="alert-box">Mimo đang chuẩn bị lộ trình {student.subject} lớp {student.grade} cho em...</div>}

      {!loading && matches && roadmap.source === 'ai' && <div className="alert-box info">Lộ trình {roadmap.subject} lớp {roadmap.grade} được Mimo soạn theo chương trình GDPT 2018. Bài nào có trong sách của Mimo thì khi trả lời, Mimo sẽ gắn số [1], [2]… để em bấm xem trang sách.</div>}

      {!loading && matches && (
        <div className="roadmap-list">
          {roadmap.chapters.map((chapter) => (
            <div key={chapter.id} className="section-block roadmap-chapter">
              <div className="section-head">
                <h2>Chương {chapter.chapter}: {chapter.title}</h2>
              </div>
              <div className="lesson-stack">
                {chapter.lessons.map((lesson) => {
                  const status = lessonStatus(lesson)
                  const current = lessonLabel(lesson) === student.currentLesson
                  return (
                    <div key={lesson.id} className="lesson-row">
                      <div className={`lesson-badge status-${status}`} title={LESSON_BADGES[status].label}>{LESSON_BADGES[status].icon}</div>
                      <div className="lesson-meta">
                        <strong>{lesson.lesson}. {lesson.title}</strong>
                        <small>{LESSON_BADGES[status].label} · {lesson.sources?.[0]?.source ? `${lesson.sources[0].source} · Trang ${lesson.sources[0].page || '-'}` : roadmap.source === 'ai' ? 'Theo chương trình GDPT 2018' : 'Mimo chưa có trang sách của bài này'}</small>
                      </div>
                      {current && <span className="status-pill">Đang học</span>}
                      <button type="button" className="text-btn" onClick={() => onSelectLesson(lesson)}>{current ? 'Học tiếp' : status === 'new' ? 'Học bài này' : 'Ôn lại'} <ChevronRight size={14} /></button>
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function TutorPage({ student, chatScope, curriculumOnly, lessonName, recentSessions, totalSessions, renderSessionItem, onNewChat, onShowAllChats, chat, loading, error, onSend, onFeedback, onRetry, quiz, quizAnswer, quizResult, quizLoading, quizError, hintShown, onShowHint, onQuizAnswer, onLoadQuiz, onSubmitQuiz }: { student: StudentProfile; chatScope: string; curriculumOnly: boolean; lessonName: string; recentSessions: ChatSession[]; totalSessions: number; renderSessionItem: (session: ChatSession) => React.ReactNode; onNewChat: () => void; onShowAllChats: () => void; chat: ChatMessage[]; loading: boolean; error: string; onSend: (message: string, imageData?: string, imageMimeType?: string) => void; onFeedback: (index: number, feedback: 'up' | 'down', comment?: string) => void; onRetry: (assistantIndex: number) => void; quiz: QuizQuestion | null; quizAnswer: string; quizResult: QuizResult | null; quizLoading: boolean; quizError: string; hintShown: boolean; onShowHint: () => void; onQuizAnswer: (answer: string) => void; onLoadQuiz: () => void; onSubmitQuiz: () => void }) {
  const [draft, setDraft] = useState('')
  const [previewSource, setPreviewSource] = useState<SourceRef | null>(null)
  const [imageAttachment, setImageAttachment] = useState<{ data: string; mime: string; name: string } | null>(null)
  const [inputNotice, setInputNotice] = useState('')
  const [voiceState, setVoiceState] = useState<'idle' | 'recording' | 'transcribing'>('idle')
  const [speakingIndex, setSpeakingIndex] = useState<number | null>(null)
  const [speechLoading, setSpeechLoading] = useState(false)
  const [commentIndex, setCommentIndex] = useState<number | null>(null)
  const [commentDraft, setCommentDraft] = useState('')
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const chatWindowRef = useRef<HTMLDivElement | null>(null)
  const recorderRef = useRef<Recorder | null>(null)
  const recordTimerRef = useRef<number | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  // Spoken answers are cached per message for this visit, so replaying does not synthesize again.
  const speechCache = useRef(new Map<string, string>())
  const speakRequest = useRef(0)

  useEffect(() => {
    const cache = speechCache.current
    return () => {
      audioRef.current?.pause()
      if ('speechSynthesis' in window) window.speechSynthesis.cancel()
      recorderRef.current?.cancel()
      if (recordTimerRef.current) window.clearTimeout(recordTimerRef.current)
      cache.forEach((url) => URL.revokeObjectURL(url))
    }
  }, [])

  useEffect(() => {
    const chatWindow = chatWindowRef.current
    if (chatWindow) chatWindow.scrollTo({ top: chatWindow.scrollHeight, behavior: 'smooth' })
  }, [chat, loading])

  const submitDraft = () => {
    if (loading || (!draft.trim() && !imageAttachment)) return
    onSend(draft.trim(), imageAttachment?.data, imageAttachment?.mime)
    setDraft('')
    setImageAttachment(null)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    submitDraft()
  }

  const stopSpeaking = () => {
    speakRequest.current += 1
    audioRef.current?.pause()
    audioRef.current = null
    if ('speechSynthesis' in window) window.speechSynthesis.cancel()
    setSpeakingIndex(null)
    setSpeechLoading(false)
  }

  // The backend reads with a Vietnamese neural voice; browsers without a Vietnamese voice would read in English.
  const handleSpeak = async (entry: ChatMessage, index: number) => {
    const wasSpeaking = speakingIndex === index
    stopSpeaking()
    if (wasSpeaking) return
    const request = speakRequest.current
    setSpeakingIndex(index)
    try {
      let url = speechCache.current.get(entry.id)
      if (!url) {
        setSpeechLoading(true)
        // A stalled backend must not leave the button stuck on "Dừng đọc" forever.
        const response = await apiFetch('/api/speech/tts', { method: 'POST', body: JSON.stringify({ text: entry.content }), signal: AbortSignal.timeout(45000) })
        if (!response.ok) throw new Error('tts')
        url = URL.createObjectURL(await response.blob())
        speechCache.current.set(entry.id, url)
      }
      if (request !== speakRequest.current) return
      const audio = new Audio(url)
      audioRef.current = audio
      const finish = () => {
        if (audioRef.current !== audio) return
        audioRef.current = null
        setSpeakingIndex(null)
      }
      audio.onended = finish
      audio.onerror = finish
      await audio.play()
      if (request === speakRequest.current) setSpeechLoading(false)
    } catch {
      if (request !== speakRequest.current) return
      setSpeechLoading(false)
      const voice = vietnameseBrowserVoice()
      if (!voice) {
        setSpeakingIndex(null)
        setInputNotice('Mimo chưa đọc được lúc này, em kiểm tra mạng rồi thử lại nhé.')
        return
      }
      const utterance = new SpeechSynthesisUtterance(entry.content.replace(/\[\d+(?:\s*[,;]\s*\d+)*\]/g, '').replace(/[*_#`$\\{}^]/g, ' ').replace(/\s+/g, ' ').trim())
      utterance.voice = voice
      utterance.lang = voice.lang
      utterance.onend = () => { if (request === speakRequest.current) setSpeakingIndex(null) }
      window.speechSynthesis.speak(utterance)
    }
  }

  const finishRecording = async () => {
    const recorder = recorderRef.current
    recorderRef.current = null
    if (recordTimerRef.current) window.clearTimeout(recordTimerRef.current)
    recordTimerRef.current = null
    if (!recorder) return
    setVoiceState('transcribing')
    try {
      const audio = await recorder.stop()
      const { text } = await apiJson<{ text: string }>('/api/speech/transcribe', { method: 'POST', body: JSON.stringify({ audio_data: audio, mime_type: 'audio/wav' }) })
      if (text) setDraft((current) => `${current} ${text}`.trim().slice(0, MESSAGE_MAX_LENGTH))
      else setInputNotice('Mimo chưa nghe rõ, em nói to và gần micro hơn một chút nhé.')
    } catch (err) {
      console.error('Voice input failed', err)
      setInputNotice(
        err instanceof RecordingTooShortError ? 'Đoạn ghi âm ngắn quá, em bấm micro, nói xong câu hỏi rồi mới bấm nút vuông nhé.'
          // TypeError from fetch: the backend could not be reached.
          : err instanceof TypeError ? 'Mimo chưa kết nối được máy chủ, em kiểm tra mạng rồi thử lại nhé.'
            : err instanceof Error && !(err instanceof DOMException) ? err.message
              : 'Mimo chưa nghe được đoạn ghi âm này, em nói lại nhé.',
      )
    } finally {
      setVoiceState('idle')
    }
  }

  const handleVoiceInput = async () => {
    if (voiceState === 'transcribing') return
    if (voiceState === 'recording') return finishRecording()
    if (!voiceInputSupported()) {
      setInputNotice(window.isSecureContext ? 'Trình duyệt này chưa ghi âm được, em thử Chrome, Edge hoặc Safari bản mới nhé.' : 'Micro chỉ dùng được khi mở trang bằng https:// hoặc localhost.')
      return
    }
    try {
      stopSpeaking()
      recorderRef.current = await startRecording()
      setInputNotice('')
      setVoiceState('recording')
      // Keeps the upload small (~2 MB) and stops a recording the student forgot about.
      recordTimerRef.current = window.setTimeout(() => void finishRecording(), 60_000)
    } catch (err) {
      console.error('Could not start recording', err)
      const name = err instanceof DOMException ? err.name : ''
      setInputNotice(
        name === 'NotAllowedError' || name === 'SecurityError' ? 'Em cho phép trang web dùng micro nhé: bấm biểu tượng ổ khóa cạnh thanh địa chỉ → Micro → Cho phép.'
          : name === 'NotFoundError' ? 'Mimo không tìm thấy micro trên máy của em.'
            : 'Mimo chưa bật được micro, em thử lại nhé.',
      )
    }
  }

  const handleFile = (file?: File) => {
    if (!file) return
    if (!file.type.startsWith('image/')) {
      setInputNotice('Mimo chỉ đọc được file ảnh (JPG, PNG) thôi nhé.')
      return
    }
    setInputNotice('')
    shrinkImage(file)
      .then((image) => setImageAttachment({ ...image, name: file.name }))
      .catch(() => setInputNotice('Mimo chưa mở được ảnh này (ví dụ ảnh HEIC của iPhone). Em chụp màn hình ảnh đó hoặc chọn ảnh JPG/PNG nhé.'))
  }

  return (
    <div className="page">
      <div className="tutor-intro">
        <div>
          <span className="section-kicker">GÓC HỌC CÙNG MIMO</span>
          <h1>Hỏi bài, hiểu thật lâu.</h1>
          <p>{curriculumOnly ? 'Mimo giải thích từng bước theo chương trình GDPT 2018.' : 'Mimo giải thích từng bước, bám sát sách giáo khoa của em.'}</p>
        </div>
        <div className="tutor-subject-chip"><BookMarked size={17} /><span>{chatScope}</span></div>
      </div>

      {error && (
        <div className="alert-box">
          {error}
        </div>
      )}

      <div className="tutor-workspace">
        <aside className="tutor-context">
          <button className="new-chat-btn" type="button" onClick={onNewChat}><Plus size={16} /> Cuộc trò chuyện mới</button>
          <div className="tutor-history">
            <span className="context-label">GẦN ĐÂY</span>
            <div className="chat-history-list">{recentSessions.map(renderSessionItem)}</div>
            {totalSessions > recentSessions.length && <button type="button" className="all-chats-btn" onClick={onShowAllChats}><History size={14} /> Xem tất cả <b>{totalSessions}</b></button>}
          </div>
          <div className="context-divider" />
          <div className="tutor-lesson">
            <span className="context-label"><BookOpen size={11} /> ĐANG HỌC</span>
            <strong>{lessonName || 'Chưa chọn bài'}</strong>
            <p>{chatScope}</p>
          </div>
        </aside>

        <section className="chat-shell" aria-label="Hội thoại với Gia sư AI">
          <div className="chat-header">
            <div className="chat-avatar"><Sparkles size={18} /></div>
            <div><strong>Mimo, Gia sư AI</strong><span><i /> Đang sẵn sàng hỗ trợ</span></div>
            <span className="grounded-label">{curriculumOnly ? 'Theo chương trình GDPT 2018' : 'Theo sách giáo khoa'}</span>
            <button type="button" className="chat-header-btn" onClick={onShowAllChats} title="Các cuộc trò chuyện" aria-label="Các cuộc trò chuyện"><History size={16} /></button>
            <button type="button" className="chat-header-btn" onClick={onNewChat} title="Cuộc trò chuyện mới" aria-label="Cuộc trò chuyện mới"><Plus size={16} /></button>
          </div>
        <div className="chat-window" ref={chatWindowRef}>
          {chat.map((entry, index) => {
            const isLast = index === chat.length - 1
            const isThinking = loading && isLast && entry.role === 'assistant' && !entry.content
            return (
            <div key={entry.id || `${entry.role}-${index}`} className={`chat-message-row ${entry.role === 'user' ? 'is-user' : ''}`}>
              <div className="message-avatar">{entry.role === 'user' ? <UserRound size={15} /> : <Sparkles size={15} />}</div>
              <div className={`chat-bubble ${entry.role === 'user' ? 'user' : 'assistant'} ${isThinking ? 'typing-bubble' : ''}`}>
                <span className="message-author">{entry.role === 'user' ? 'Em' : 'Mimo'}</span>
              {isThinking ? <div className="typing-indicator"><i /><i /><i /><span>Mimo đang suy nghĩ...</span></div> : <div className="chat-body">
                {entry.failed && <strong className="failed-title">Ôi, Mimo gặp trục trặc rồi 😥</strong>}
                {entry.imagePreview && <img className="message-image" src={entry.imagePreview} alt="Ảnh đề bài em đã gửi" />}
                <ChatMessageContent content={entry.content} sources={entry.sources} onCite={setPreviewSource} />
              </div>}
              {entry.failed && <button type="button" className="retry-btn" disabled={loading} onClick={() => onRetry(index)}><RefreshCcw size={15} /> Thử lại</button>}
              {isLast && !loading && entry.role === 'assistant' && entry.quickReplies && entry.quickReplies.length > 0 && <div className="reply-chips">{entry.quickReplies.slice(0, 3).map((reply) => <button key={reply} type="button" onClick={() => onSend(reply)}>{reply}</button>)}</div>}
              {entry.role === 'assistant' && <SourcePageThumbs content={entry.content} sources={entry.sources} onOpen={setPreviewSource} />}
              {entry.role === 'assistant' && entry.content && !entry.failed && index > 0 && !(loading && isLast) && <div className="message-action-bar">
                <button type="button" title={speakingIndex === index ? (speechLoading ? 'Mimo đang chuẩn bị giọng đọc…' : 'Dừng đọc') : 'Nghe giảng'} onClick={() => void handleSpeak(entry, index)}>{speakingIndex === index ? (speechLoading ? <LoaderCircle size={14} className="spin" /> : <VolumeX size={14} />) : <Volume2 size={14} />}</button>
                <button type="button" title="Sao chép" onClick={() => void navigator.clipboard?.writeText(entry.content.replace(/[*_#`$]/g, '').replace(/\\[a-zA-Z]+/g, ' '))}><Copy size={14} /></button>
                <button type="button" title="Thích" onClick={() => onFeedback(index, 'up')}><ThumbsUp size={14} /></button>
                <button type="button" title="Không thích" onClick={() => { onFeedback(index, 'down'); setCommentIndex(index); setCommentDraft('') }}><ThumbsDown size={14} /></button>
                <button type="button" title="Trả lời lại câu này" disabled={loading} onClick={() => onRetry(index)}><RefreshCcw size={14} /></button>
                {entry.feedback && <span className="feedback-note">{entry.feedback === 'up' ? 'Mimo vui quá! 💛' : 'Mimo sẽ cố gắng hơn'}</span>}
                {commentIndex === index && entry.feedback === 'down' && (
                  <form className="feedback-comment" onSubmit={(event) => { event.preventDefault(); if (commentDraft.trim()) onFeedback(index, 'down', commentDraft); setCommentIndex(null) }}>
                    <input autoFocus value={commentDraft} maxLength={500} onChange={(event) => setCommentDraft(event.target.value)} onKeyDown={(event) => { if (event.key === 'Escape') setCommentIndex(null) }} placeholder="Mimo trả lời chưa tốt ở đâu? (không bắt buộc)" />
                    <button type="submit">Gửi</button>
                  </form>
                )}
              </div>}
              </div>
            </div>
          )})}
        </div>

        <form className="chat-form" onSubmit={handleSubmit} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); handleFile(event.dataTransfer.files[0]) }}>
          {inputNotice && <div className="attachment-chip input-notice" role="alert"><span>{inputNotice}</span><button type="button" onClick={() => setInputNotice('')} aria-label="Đóng thông báo"><X size={13} /></button></div>}
          {imageAttachment && <div className="attachment-chip"><img src={imageAttachment.data} alt="" className="attachment-preview" /><span>{imageAttachment.name}</span><button type="button" onClick={() => setImageAttachment(null)} aria-label="Bỏ ảnh"><X size={13} /></button></div>}
          <textarea
            value={draft}
            maxLength={MESSAGE_MAX_LENGTH}
            onChange={(event) => setDraft(event.target.value)}
            onPaste={(event) => { const image = Array.from(event.clipboardData.files).find((file) => file.type.startsWith('image/')); if (image) { event.preventDefault(); handleFile(image) } }}
            rows={3}
            placeholder="Nhắn cho Mimo... (ví dụ: Em chưa hiểu bước 2 của bài này)"
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
                event.preventDefault()
                submitDraft()
              }
            }}
          />
          <div className="chat-form-footer"><div className="input-tools"><button type="button" title={voiceState === 'recording' ? 'Bấm để dừng ghi âm' : 'Hỏi bằng giọng nói'} aria-label={voiceState === 'recording' ? 'Dừng ghi âm' : 'Hỏi bằng giọng nói'} aria-pressed={voiceState === 'recording'} disabled={voiceState === 'transcribing'} onClick={() => void handleVoiceInput()} className={voiceState === 'recording' ? 'active recording' : ''}>{voiceState === 'recording' ? <Square size={13} fill="currentColor" /> : <Mic size={15} />}</button><button type="button" title="Tải hoặc chụp ảnh đề bài" onClick={() => fileInputRef.current?.click()}><Paperclip size={15} /></button><input ref={fileInputRef} type="file" accept="image/*" capture="environment" hidden onChange={(event) => handleFile(event.target.files?.[0])} /><span className={voiceState !== 'idle' ? 'voice-status' : undefined} role={voiceState !== 'idle' ? 'status' : undefined}>{voiceState === 'recording' ? 'Mimo đang nghe em nói... bấm nút vuông để dừng' : voiceState === 'transcribing' ? 'Mimo đang chép lại lời em nói...' : draft.length > MESSAGE_MAX_LENGTH - 300 ? `${draft.length}/${MESSAGE_MAX_LENGTH} ký tự` : 'Enter để gửi · Shift + Enter để xuống dòng'}</span></div><button className="send-btn" type="submit" disabled={loading || (!draft.trim() && !imageAttachment)} aria-label="Gửi câu hỏi">
            <Send size={16} /> <span>Gửi câu hỏi</span>
          </button>
          </div>
        </form>
        </section>
      </div>
      <section className="adaptive-quiz-panel" aria-label="Bài luyện tập thích ứng">
        <div className="adaptive-quiz-head">
          <div><span className="section-kicker">LUYỆN TẬP CÙNG MIMO</span><h2>Luyện tập vừa sức em</h2><p>{student.currentTopic ? `Mimo soạn câu hỏi riêng cho bài ${student.currentTopic}, độ khó theo năng lực và lỗi gần đây của em.` : 'Chọn một bài trong Lộ trình học để Mimo soạn câu luyện tập đúng bài đó.'}</p></div>
          <button className="primary-btn" type="button" onClick={onLoadQuiz} disabled={quizLoading}>{quizLoading ? 'Đang tạo...' : quiz ? 'Câu khác' : 'Bắt đầu luyện tập'}</button>
        </div>
        {quizError && <div className="alert-box quiz-error" role="alert">{quizError}</div>}
        {quiz && <div className="quiz-card">
          <div className="quiz-meta"><span>{quiz.concept}</span><strong>Mức {quiz.difficulty}: {quiz.difficulty_label}</strong><small>Năng lực hiện tại {Math.round(quiz.mastery * 100)}%</small></div>
          <h3>{quiz.question}</h3>
          <div className="quiz-options">{quiz.options.map((option) => <button key={option} type="button" className={quizAnswer === option ? 'selected' : ''} onClick={() => onQuizAnswer(option)} disabled={Boolean(quizResult)}>{option}</button>)}</div>
          {!quizResult && quiz.hint && (hintShown
            ? <p className="quiz-hint"><Lightbulb size={14} /> {quiz.hint}</p>
            : <button type="button" className="text-btn quiz-hint-btn" onClick={onShowHint}><Lightbulb size={14} /> Xem gợi ý (được ít điểm hơn một chút)</button>)}
          {!quizResult && <button className="quiz-submit" type="button" onClick={onSubmitQuiz} disabled={quizLoading || !quizAnswer}>{quizLoading ? 'Đang chấm...' : 'Kiểm tra câu trả lời'}</button>}
          {quizResult && <div className={`quiz-feedback ${quizResult.is_correct ? 'correct' : 'incorrect'}`}><strong>{quizResult.is_correct ? 'Tốt lắm!' : 'Mình cùng sửa lại nhé'}</strong><p>{quizResult.feedback}</p><small>{quizResult.explanation}</small><div className="recommendation"><b>{quizResult.recommendation.title}</b><span>{quizResult.recommendation.reason}</span></div><button className="text-btn" type="button" onClick={onLoadQuiz}>Làm câu tiếp theo <ChevronRight size={14} /></button></div>}
        </div>}
      </section>
      {previewSource?.preview_url && <div className="source-modal-backdrop" role="presentation" onClick={() => setPreviewSource(null)}><div className="source-modal" role="dialog" aria-modal="true" aria-label="Xem trang sách" onClick={(event) => event.stopPropagation()}><div className="source-modal-head"><div><strong>{previewSource.title || previewSource.source || 'Trang SGK'}</strong><span>{[previewSource.lesson_title, `Trang ${previewSource.page || '-'}`].filter(Boolean).join(' · ')}</span></div><button type="button" onClick={() => setPreviewSource(null)} aria-label="Đóng xem trang"><X size={18} /></button></div><img src={apiUrl(previewSource.preview_url)} alt={`Trang ${previewSource.page || ''} trong ${previewSource.source || 'sách giáo khoa'}`} /></div></div>}
    </div>
  )
}

// Small images of the cited textbook pages, so figures (geometry, science diagrams) are visible right under the answer.
function SourcePageThumbs({ content, sources, onOpen }: { content: string; sources?: SourceRef[]; onOpen: (source: SourceRef) => void }) {
  if (!sources?.length) return null
  // Only pages the answer actually cites: a greeting or a talk about feelings should not show random textbook pages.
  const pages = citedSourceNumbers(content, sources.length).map((number) => sources[number - 1]).filter((source) => source?.preview_url)
  if (pages.length === 0) return null
  return (
    <div className="source-thumbs" aria-label="Trang sách được trích dẫn">
      {pages.map((source) => (
        <button key={source.preview_url} type="button" className="source-thumb" onClick={() => onOpen(source)} title={`Phóng to trang ${source.page ?? ''} · ${source.title ?? source.source ?? 'SGK'}`}>
          <img src={apiUrl(`${source.preview_url}&thumb=true`)} alt={`Trang ${source.page ?? ''} trong ${source.source ?? 'sách giáo khoa'}`} loading="lazy" />
          <span>{sources.indexOf(source) + 1} · Trang {source.page ?? '-'}</span>
        </button>
      ))}
    </div>
  )
}

// Answers that cite inline ("... [1]") don't need the source list under the bubble; older answers without markers keep it.

function AllChatsModal({ sessions, currentGroup, renderItem, onClose, onNewChat }: { sessions: ChatSession[]; currentGroup: string; renderItem: (session: ChatSession) => React.ReactNode; onClose: () => void; onNewChat: () => void }) {
  const [query, setQuery] = useState('')

  useEffect(() => {
    const handleKey = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose() }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [onClose])

  const normalize = (value: string) => value.normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/đ/g, 'd').toLowerCase()
  const keyword = normalize(query.trim())
  const matched = keyword ? sessions.filter((session) => normalize(`${session.title} ${session.subject} ${session.messages.map((message) => message.content).join(' ')}`).includes(keyword)) : sessions
  // One group per subject and grade (sessions arrive newest first); the one being studied comes first.
  const groups = matched.reduce<{ label: string; items: ChatSession[] }[]>((result, session) => {
    const label = `${session.subject} · ${session.grade}`
    const group = result.find((item) => item.label === label)
    if (group) group.items.push(session)
    else result.push({ label, items: [session] })
    return result
  }, []).sort((left, right) => Number(right.label === currentGroup) - Number(left.label === currentGroup))

  return (
    <div className="source-modal-backdrop" role="presentation" onClick={onClose}>
      <div className="source-modal all-chats-modal" role="dialog" aria-modal="true" aria-label="Tất cả cuộc trò chuyện" onClick={(event) => event.stopPropagation()}>
        <div className="source-modal-head">
          <div><strong>Các cuộc trò chuyện với Mimo</strong><span>{sessions.length} cuộc trò chuyện đã lưu</span></div>
          <button type="button" onClick={onClose} aria-label="Đóng"><X size={18} /></button>
        </div>
        <div className="all-chats-toolbar">
          <label className="all-chats-search"><Search size={15} /><input autoFocus value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Tìm theo tên hoặc nội dung..." /></label>
          <button type="button" className="new-chat-btn" onClick={onNewChat}><Plus size={15} /> Mới</button>
        </div>
        <div className="all-chats-body">
          {groups.length === 0 && <p className="all-chats-empty">Mimo không tìm thấy cuộc trò chuyện nào khớp với “{query}”.</p>}
          {groups.map((group) => (
            <section key={group.label}>
              <h3>{group.label}{group.label === currentGroup ? ' · đang học' : ''} ({group.items.length})</h3>
              <div className="all-chats-list">{group.items.map(renderItem)}</div>
            </section>
          ))}
        </div>
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
