import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { readStorage, writeStorage } from '../services/storageService'

export type PomodoroMode = 'FOCUS' | 'BREAK'
export type PomodoroStatus = 'IDLE' | 'RUNNING' | 'PAUSED' | 'COMPLETED'
export type PomodoroSession = {
  mode: PomodoroMode
  focusMinutes: number
  breakMinutes: number
  startedAt: number | null
  /** Length of the current run: a full phase, or what was left when it was paused. */
  duration: number
  pausedRemaining: number | null
  isRunning: boolean
  /** Focus phases finished today. */
  sessionCount: number
  totalSessions: number
  /** Position inside the current cycle of `totalSessions` focus phases. */
  currentSession: number
  linkedLesson: string | null
  /** Milliseconds of focus time today, including unfinished phases. */
  todayFocusTime: number
  /** Local date (YYYY-MM-DD) the daily counters belong to. */
  day: string
  status: PomodoroStatus
  updatedAt: number
}

type PomodoroContextValue = PomodoroSession & {
  remainingTime: number
  todayFocusMinutes: number
  start: (lesson?: string | null) => void
  pause: () => void
  stop: () => void
  setDurations: (focusMinutes: number, breakMinutes: number) => void
  switchMode: (mode: PomodoroMode) => void
}

const MINUTE = 60 * 1000
const localDay = () => new Date().toLocaleDateString('sv-SE')
const phaseLength = (session: Pick<PomodoroSession, 'mode' | 'focusMinutes' | 'breakMinutes'>, mode = session.mode) => (mode === 'FOCUS' ? session.focusMinutes : session.breakMinutes) * MINUTE

const defaultSession = (): PomodoroSession => ({ mode: 'FOCUS', focusMinutes: 25, breakMinutes: 5, startedAt: null, duration: 25 * MINUTE, pausedRemaining: null, isRunning: false, sessionCount: 0, totalSessions: 4, currentSession: 1, linkedLesson: null, todayFocusTime: 0, day: localDay(), status: 'IDLE', updatedAt: Date.now() })
const PomodoroContext = createContext<PomodoroContextValue | null>(null)

// Daily counters start from zero on a new day.
function forToday(session: PomodoroSession): PomodoroSession {
  return session.day === localDay() ? session : { ...session, day: localDay(), sessionCount: 0, todayFocusTime: 0 }
}

function restore(storageKey: string): PomodoroSession {
  const stored = readStorage<Partial<PomodoroSession>>(storageKey, {})
  const base = defaultSession()
  return forToday({ ...base, ...stored, focusMinutes: stored.focusMinutes || base.focusMinutes, breakMinutes: stored.breakMinutes || base.breakMinutes, duration: stored.duration || base.duration, totalSessions: stored.totalSessions || 4, day: stored.day || base.day })
}

function remainingOf(session: PomodoroSession, now: number) {
  if (!session.isRunning || !session.startedAt) return session.pausedRemaining ?? session.duration
  return Math.max(0, session.duration - (now - session.startedAt))
}

// Focus time spent in the run that is ending now (pause, stop), counted towards today.
function withElapsedFocus(session: PomodoroSession, now: number): PomodoroSession {
  if (!session.isRunning || session.mode !== 'FOCUS') return session
  return { ...session, todayFocusTime: session.todayFocusTime + (session.duration - remainingOf(session, now)) }
}

export function GlobalPomodoroProvider({ storageKey, children }: { storageKey: string; children: ReactNode }) {
  const [session, setSession] = useState<PomodoroSession>(() => restore(storageKey))
  const [now, setNow] = useState(Date.now)

  useEffect(() => writeStorage(storageKey, session), [storageKey, session])
  useEffect(() => {
    if (!session.isRunning) return
    const interval = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(interval)
  }, [session.isRunning])

  const remaining = remainingOf(session, now)
  useEffect(() => {
    if (!session.isRunning || remaining > 0) return
    setSession((previous) => {
      if (!previous.isRunning) return previous
      const current = forToday(previous)
      const at = Date.now()
      if (current.mode === 'FOCUS') {
        const counted = { ...current, todayFocusTime: current.todayFocusTime + current.duration, sessionCount: current.sessionCount + 1 }
        if (current.currentSession >= current.totalSessions) {
          notify('🎉 Em đã hoàn thành cả buổi học rồi, giỏi quá!')
          return { ...counted, isRunning: false, status: 'COMPLETED', startedAt: null, pausedRemaining: null, duration: phaseLength(current, 'FOCUS'), updatedAt: at }
        }
        notify('☕ Hết giờ tập trung! Em nghỉ ngơi một chút nhé.')
        return { ...counted, mode: 'BREAK', duration: phaseLength(current, 'BREAK'), startedAt: at, pausedRemaining: null, status: 'RUNNING', updatedAt: at }
      }
      notify('🚀 Hết giờ nghỉ! Mình học tiếp nhé.')
      return { ...current, mode: 'FOCUS', duration: phaseLength(current, 'FOCUS'), startedAt: at, pausedRemaining: null, status: 'RUNNING', currentSession: current.currentSession + 1, updatedAt: at }
    })
  }, [remaining, session.isRunning])

  const value = useMemo<PomodoroContextValue>(() => {
    const today = forToday(session)
    const liveFocus = session.isRunning && session.mode === 'FOCUS' ? session.duration - remaining : 0
    return {
      ...today,
      remainingTime: remaining,
      todayFocusMinutes: Math.floor((today.todayFocusTime + liveFocus) / MINUTE),
      start: (lesson = session.linkedLesson) => {
        // Asked on a click, which browsers require for the permission prompt.
        if ('Notification' in window && Notification.permission === 'default') void Notification.requestPermission()
        setSession((previous) => {
          const current = forToday(previous)
          if (current.isRunning) return current
          const at = Date.now()
          if (current.status === 'COMPLETED') return { ...current, linkedLesson: lesson, mode: 'FOCUS', currentSession: 1, duration: phaseLength(current, 'FOCUS'), startedAt: at, pausedRemaining: null, isRunning: true, status: 'RUNNING', updatedAt: at }
          return { ...current, linkedLesson: lesson, duration: current.pausedRemaining ?? current.duration, startedAt: at, pausedRemaining: null, isRunning: true, status: 'RUNNING', updatedAt: at }
        })
      },
      pause: () => setSession((previous) => {
        if (!previous.isRunning) return previous
        const at = Date.now()
        return { ...withElapsedFocus(forToday(previous), at), isRunning: false, status: 'PAUSED', startedAt: null, pausedRemaining: remainingOf(previous, at), updatedAt: at }
      }),
      stop: () => setSession((previous) => {
        const at = Date.now()
        const current = withElapsedFocus(forToday(previous), at)
        return { ...current, isRunning: false, status: 'IDLE', mode: 'FOCUS', currentSession: 1, startedAt: null, pausedRemaining: null, duration: phaseLength(current, 'FOCUS'), updatedAt: at }
      }),
      setDurations: (focusMinutes, breakMinutes) => setSession((previous) => {
        if (previous.isRunning) return previous
        const next = { ...forToday(previous), focusMinutes, breakMinutes }
        return { ...next, duration: phaseLength(next), pausedRemaining: null, status: 'IDLE', updatedAt: Date.now() }
      }),
      switchMode: (mode) => setSession((previous) => {
        if (previous.isRunning) return previous
        return { ...forToday(previous), mode, duration: phaseLength(previous, mode), pausedRemaining: null, status: 'IDLE', updatedAt: Date.now() }
      }),
    }
  }, [session, remaining])

  return <PomodoroContext.Provider value={value}>{children}</PomodoroContext.Provider>
}

function notify(message: string) {
  window.dispatchEvent(new CustomEvent('ai-tutor-notification', { detail: message }))
  if ('Notification' in window && Notification.permission === 'granted') new Notification(message)
  playChime()
}

// A short two-note chime, so the end of a phase is noticed even without notifications.
function playChime() {
  try {
    const AudioContextClass = window.AudioContext || (window as Window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
    if (!AudioContextClass) return
    const audio = new AudioContextClass()
    ;[660, 880].forEach((frequency, index) => {
      const oscillator = audio.createOscillator()
      const gain = audio.createGain()
      const startAt = audio.currentTime + index * 0.22
      oscillator.frequency.value = frequency
      gain.gain.setValueAtTime(0.0001, startAt)
      gain.gain.exponentialRampToValueAtTime(0.25, startAt + 0.02)
      gain.gain.exponentialRampToValueAtTime(0.0001, startAt + 0.2)
      oscillator.connect(gain).connect(audio.destination)
      oscillator.start(startAt)
      oscillator.stop(startAt + 0.22)
    })
    window.setTimeout(() => void audio.close(), 800)
  } catch {
    // Sound is a nice-to-have.
  }
}

export function usePomodoro() {
  const context = useContext(PomodoroContext)
  if (!context) throw new Error('usePomodoro must be used inside GlobalPomodoroProvider')
  return context
}
