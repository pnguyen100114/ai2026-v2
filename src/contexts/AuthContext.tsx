import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { apiJson, getToken, setToken, UNAUTHORIZED_EVENT } from '../lib/api'

export type OnboardingAnswers = {
  subjects?: string[]
  favorite?: string
  goal?: string
  dailyMinutes?: number
  targetGrade?: number
  /** The grade the student is actually in at school; `Account.grade` becomes the grade they chose to study. */
  schoolGrade?: number
}

export type Account = {
  id: string
  email: string
  name: string
  grade: number
  subject: string
  currentLesson: string
  currentTopic: string
  learningProfile: Record<string, unknown>
  onboarding: OnboardingAnswers
  onboarded: boolean
}

export type ProfilePatch = Partial<Pick<Account, 'name' | 'grade' | 'subject' | 'currentLesson' | 'currentTopic' | 'onboarding' | 'onboarded'>>

type AuthContextValue = {
  ready: boolean
  /** Set when the saved session could not be checked because the backend is unreachable. */
  connectionError: string
  user: Account | null
  signIn: (email: string, password: string, mode: 'login' | 'register', name?: string, grade?: number) => Promise<void>
  signOut: () => void
  updateProfile: (patch: ProfilePatch) => Promise<void>
  retry: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Account | null>(null)
  const [ready, setReady] = useState(false)
  const [connectionError, setConnectionError] = useState('')

  const restore = useCallback(async () => {
    setConnectionError('')
    if (!getToken()) {
      setReady(true)
      return
    }
    try {
      const { user: account } = await apiJson<{ user: Account }>('/api/me')
      setUser(account)
    } catch (err) {
      if ((err as { status?: number }).status === 401) setToken(null)
      else setConnectionError(err instanceof Error ? err.message : 'Không kết nối được máy chủ.')
    } finally {
      setReady(true)
    }
  }, [])

  useEffect(() => {
    void restore()
    const onUnauthorized = () => {
      setToken(null)
      setUser(null)
    }
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized)
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized)
  }, [restore])

  const value: AuthContextValue = {
    ready,
    connectionError,
    user,
    signIn: async (email, password, mode, name, grade) => {
      const { token, user: account } = await apiJson<{ token: string; user: Account }>('/api/auth/email', {
        method: 'POST',
        body: JSON.stringify({ email, password, mode, name, grade }),
      })
      setToken(token)
      setUser(account)
    },
    signOut: () => {
      setToken(null)
      setUser(null)
    },
    updateProfile: async (patch) => {
      const { user: account } = await apiJson<{ user: Account }>('/api/me', { method: 'PATCH', body: JSON.stringify(patch) })
      setUser(account)
    },
    retry: () => {
      setReady(false)
      void restore()
    },
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside AuthProvider')
  return value
}
