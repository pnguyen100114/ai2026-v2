import { Component, StrictMode, type ErrorInfo, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './styles.css'
import './flow.css'
import './gate.css'
import 'katex/dist/katex.min.css'
import { GlobalPomodoroProvider } from './contexts/PomodoroContext'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import AuthPage from './components/AuthPage'
import Onboarding from './components/Onboarding'
import { storageKeys } from './services/storageService'

// A crash in one screen shows a friendly message instead of a blank white page.
class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Gia Sư AI gặp lỗi giao diện', error, info.componentStack)
  }

  render() {
    if (!this.state.failed) return this.props.children
    return (
      <div className="gate-status">
        <strong>Ôi, Mimo gặp trục trặc rồi 😥</strong>
        <span>Lịch sử học của em vẫn được lưu an toàn. Em tải lại trang để học tiếp nhé.</span>
        <button type="button" className="gate-button primary" onClick={() => window.location.reload()}>Tải lại trang</button>
      </div>
    )
  }
}

function AppGate() {
  const auth = useAuth()
  if (!auth.ready) return <div className="gate-status">Mimo đang chuẩn bị...</div>
  if (auth.connectionError) {
    return (
      <div className="gate-status">
        <strong>Mimo chưa kết nối được máy chủ 😥</strong>
        <span>{auth.connectionError}</span>
        <button type="button" className="gate-button primary" onClick={auth.retry}>Thử lại</button>
      </div>
    )
  }
  if (!auth.user) return <AuthPage />
  if (!auth.user.onboarded) return <Onboarding user={auth.user} />
  // key: remount with fresh per-account state (chats, timer) when a different student signs in.
  return (
    <GlobalPomodoroProvider key={auth.user.id} storageKey={`${storageKeys.pomodoro}:${auth.user.id}`}>
      <App key={auth.user.id} />
    </GlobalPomodoroProvider>
  )
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <AuthProvider>
        <AppGate />
      </AuthProvider>
    </ErrorBoundary>
  </StrictMode>,
)
