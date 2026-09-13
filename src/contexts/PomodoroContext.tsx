import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { readStorage, storageKeys, writeStorage } from '../services/storageService'

export type PomodoroMode = 'FOCUS' | 'BREAK'
export type PomodoroStatus = 'IDLE' | 'RUNNING' | 'PAUSED' | 'COMPLETED'
export type PomodoroSession = {
  mode: PomodoroMode
  startedAt: number | null
  duration: number
  pausedAt: number | null
  pausedRemaining: number | null
  isRunning: boolean
  sessionCount: number
  totalSessions: number
  currentSession: number
  linkedLesson: string | null
  todayFocusTime: number
  status: PomodoroStatus
  updatedAt: number
}

type PomodoroContextValue = PomodoroSession & {
  remainingTime: number
  start: (lesson?: string | null) => void
  pause: () => void
  reset: () => void
  stop: () => void
  setDurations: (focusMinutes: number, breakMinutes: number, totalSessions?: number) => void
  linkLesson: (lesson: string | null) => void
}

const defaultSession: PomodoroSession = { mode: 'FOCUS', startedAt: null, duration: 25 * 60 * 1000, pausedAt: null, pausedRemaining: null, isRunning: false, sessionCount: 0, totalSessions: 4, currentSession: 1, linkedLesson: null, todayFocusTime: 0, status: 'IDLE', updatedAt: Date.now() }
const PomodoroContext = createContext<PomodoroContextValue | null>(null)

function safeSession(): PomodoroSession {
  const stored = readStorage<Partial<PomodoroSession>>(storageKeys.pomodoro, {})
  return { ...defaultSession, ...stored, duration: stored.duration || defaultSession.duration, totalSessions: stored.totalSessions || 4 }
}

function elapsedRemaining(session: PomodoroSession, now: number) {
  if (!session.isRunning || !session.startedAt) return session.pausedRemaining ?? session.duration
  return Math.max(0, session.duration - (now - session.startedAt))
}

export function GlobalPomodoroProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<PomodoroSession>(safeSession)
  const [now, setNow] = useState(Date.now)

  useEffect(() => writeStorage(storageKeys.pomodoro, session), [session])
  useEffect(() => {
    if (!session.isRunning) return
    const interval = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(interval)
  }, [session.isRunning])

  const remaining = elapsedRemaining(session, now)
  useEffect(() => {
    if (!session.isRunning || remaining > 0) return
    setSession((current) => {
      if (!current.isRunning) return current
      const completedFocus = current.mode === 'FOCUS'
      const nextSession = completedFocus ? current.sessionCount + 1 : current.sessionCount
      const completedAll = completedFocus && current.sessionCount + 1 >= current.totalSessions
      const nextMode: PomodoroMode = completedFocus ? 'BREAK' : 'FOCUS'
      const nextDuration = nextMode === 'FOCUS' ? 25 * 60 * 1000 : 5 * 60 * 1000
      if (completedAll) {
        notify('🎉 Bạn đã hoàn thành buổi học!')
        return { ...current, isRunning: false, status: 'COMPLETED', sessionCount: nextSession, pausedRemaining: 0, updatedAt: Date.now() }
      }
      notify(completedFocus ? '☕ Đã hết giờ tập trung! Đến giờ nghỉ.' : '🚀 Hết giờ nghỉ! Tiếp tục học nhé.')
      return { ...current, mode: nextMode, duration: nextDuration, startedAt: Date.now(), pausedAt: null, pausedRemaining: null, isRunning: true, status: 'RUNNING', sessionCount: nextSession, currentSession: completedFocus ? current.currentSession : current.currentSession + 1, updatedAt: Date.now() }
    })
  }, [remaining, session.isRunning])

  const value = useMemo<PomodoroContextValue>(() => ({
    ...session,
    remainingTime: remaining,
    start: (lesson = session.linkedLesson) => setSession((current) => {
      const duration = current.status === 'COMPLETED' ? 25 * 60 * 1000 : current.pausedRemaining ?? current.duration
      return { ...current, linkedLesson: lesson, duration, startedAt: Date.now(), pausedAt: null, pausedRemaining: null, isRunning: true, status: 'RUNNING', updatedAt: Date.now() }
    }),
    pause: () => setSession((current) => current.isRunning ? { ...current, isRunning: false, status: 'PAUSED', pausedAt: Date.now(), pausedRemaining: elapsedRemaining(current, Date.now()), updatedAt: Date.now() } : current),
    reset: () => setSession((current) => ({ ...defaultSession, totalSessions: current.totalSessions, linkedLesson: current.linkedLesson, updatedAt: Date.now() })),
    stop: () => setSession((current) => ({ ...current, isRunning: false, status: 'COMPLETED', pausedRemaining: elapsedRemaining(current, Date.now()), updatedAt: Date.now() })),
    setDurations: (focusMinutes, breakMinutes, totalSessions = session.totalSessions) => setSession((current) => ({ ...current, duration: current.mode === 'FOCUS' ? focusMinutes * 60 * 1000 : breakMinutes * 60 * 1000, totalSessions, updatedAt: Date.now() })),
    linkLesson: (linkedLesson) => setSession((current) => ({ ...current, linkedLesson, updatedAt: Date.now() })),
  }), [session, remaining])

  return <PomodoroContext.Provider value={value}>{children}</PomodoroContext.Provider>
}

function notify(message: string) {
  window.dispatchEvent(new CustomEvent('ai-tutor-notification', { detail: message }))
  if ('Notification' in window && Notification.permission === 'granted') new Notification(message)
}

export function usePomodoro() {
  const context = useContext(PomodoroContext)
  if (!context) throw new Error('usePomodoro must be used inside GlobalPomodoroProvider')
  return context
}
