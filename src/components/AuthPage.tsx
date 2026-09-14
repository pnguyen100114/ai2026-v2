import { useRef, useState } from 'react'
import { ArrowRight, Bot, Eye, EyeOff, Sparkles } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

type View = 'welcome' | 'login' | 'register'

export default function AuthPage() {
  const [view, setView] = useState<View>('welcome')
  const [email, setEmail] = useState('')

  return (
    <div className="gate-auth">
      <div className="gate-visual">
        <div className="gate-brand"><div className="brand-mark"><Sparkles size={20} /></div><strong>Gia Sư AI<span className="brand-dot">.</span></strong></div>
        <div className="gate-visual-copy">
          <span className="gate-eyebrow light">GIA SƯ THÔNG MINH CHO THCS</span>
          <h1>Mỗi ngày một chút,<br /><span>tiến bộ thật nhiều.</span></h1>
          <p>Học vui hơn, hiểu sâu hơn cùng Mimo – người bạn AI luôn đồng hành bên em.</p>
        </div>
        <div className="gate-orbit" aria-hidden="true"><div className="gate-bot"><Bot size={54} /></div><Sparkles className="gate-spark" size={23} /></div>
        <div className="gate-quote">“Không cần phải giỏi ngay từ đầu. Chỉ cần bắt đầu!”</div>
      </div>
      <div className="gate-panel">
        {view === 'welcome'
          ? <Welcome onView={setView} />
          : <EmailForm key={view} mode={view} email={email} setEmail={setEmail} onView={setView} />}
      </div>
    </div>
  )
}

function Welcome({ onView }: { onView: (view: View) => void }) {
  return (
    <div className="gate-welcome">
      <div className="gate-mobile-brand"><div className="brand-mark"><Sparkles size={18} /></div><strong>Gia Sư AI</strong></div>
      <div className="gate-welcome-icon"><Sparkles size={25} /></div>
      <span className="gate-eyebrow">CHÀO MỪNG EM ĐẾN VỚI</span>
      <h2>Không gian học tập<br /><span>của riêng em</span></h2>
      <p>Chọn cách bắt đầu để Mimo có thể đồng hành cùng em trên hành trình chinh phục THCS.</p>
      <button type="button" className="gate-button primary full" onClick={() => onView('register')}>Tạo tài khoản mới <ArrowRight size={17} /></button>
      <button type="button" className="gate-button outline full" onClick={() => onView('login')}>Mình đã có tài khoản</button>
      <small>Miễn phí · Học theo tốc độ của em</small>
    </div>
  )
}

function EmailForm({ mode, email, setEmail, onView }: { mode: 'login' | 'register'; email: string; setEmail: (email: string) => void; onView: (view: View) => void }) {
  const auth = useAuth()
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [grade, setGrade] = useState(8)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [unknownEmail, setUnknownEmail] = useState(false)
  const passwordRef = useRef<HTMLInputElement>(null)

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError('')
    setUnknownEmail(false)
    // Validate here instead of relying on native bubbles, which embedded browsers don't show.
    if (mode === 'register' && !name.trim()) {
      setError('Em nhập họ và tên nhé.')
      return
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      setError(email.trim() ? 'Email chưa đúng định dạng, ví dụ: em@example.com' : 'Em nhập email nhé.')
      return
    }
    if (!password) {
      setError('Em nhập mật khẩu nhé.')
      passwordRef.current?.focus()
      return
    }
    if (mode === 'register' && password.length < 6) {
      setError('Mật khẩu cần ít nhất 6 ký tự nhé.')
      return
    }
    if (mode === 'register' && password !== confirm) {
      setError('Hai mật khẩu chưa giống nhau, em nhập lại nhé.')
      return
    }
    setBusy(true)
    try {
      await auth.signIn(email.trim(), password, mode, name.trim(), grade)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Có lỗi xảy ra, em thử lại nhé.')
      setUnknownEmail((err as { status?: number }).status === 404)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="gate-form-panel">
      <button type="button" className="gate-back" onClick={() => onView('welcome')}>← Quay lại</button>
      <span className="gate-eyebrow">{mode === 'register' ? 'BẮT ĐẦU HÀNH TRÌNH' : 'CHÀO MỪNG TRỞ LẠI'}</span>
      <h2>{mode === 'register' ? 'Tạo tài khoản' : 'Đăng nhập'}</h2>
      <p>{mode === 'register' ? 'Để Mimo cá nhân hóa lộ trình học cho em.' : 'Nhập email em đã đăng ký để học tiếp nhé.'}</p>
      <form noValidate onSubmit={(event) => void submit(event)}>
        {mode === 'register' && <label>Họ và tên<input value={name} onChange={(event) => setName(event.target.value)} placeholder="Ví dụ: Minh Anh" autoComplete="name" maxLength={80} required /></label>}
        <label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="em@example.com" autoComplete="email" required autoFocus={mode === 'login'} /></label>
        <label>Mật khẩu
          <span className="gate-password">
            <input ref={passwordRef} type={showPassword ? 'text' : 'password'} value={password} onChange={(event) => setPassword(event.target.value)} placeholder={mode === 'register' ? 'Ít nhất 6 ký tự' : 'Mật khẩu của em'} autoComplete={mode === 'register' ? 'new-password' : 'current-password'} minLength={mode === 'register' ? 6 : undefined} maxLength={128} required />
            <button type="button" onClick={() => { setShowPassword((value) => !value); passwordRef.current?.focus() }} aria-label={showPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}>{showPassword ? <EyeOff size={16} /> : <Eye size={16} />}</button>
          </span>
        </label>
        {mode === 'register' && <label>Nhập lại mật khẩu<input type={showPassword ? 'text' : 'password'} value={confirm} onChange={(event) => setConfirm(event.target.value)} autoComplete="new-password" maxLength={128} required /></label>}
        {mode === 'register' && (
          <label>Lớp hiện tại
            <select value={grade} onChange={(event) => setGrade(Number(event.target.value))}>
              {[6, 7, 8, 9].map((item) => <option key={item} value={item}>Lớp {item}</option>)}
            </select>
          </label>
        )}
        {error && (
          <div className="gate-error" role="alert">
            {error}
            {unknownEmail && <button type="button" onClick={() => onView('register')}>Tạo tài khoản với email này</button>}
          </div>
        )}
        <button className="gate-button primary full" type="submit" disabled={busy}>
          {busy ? 'Đang xử lý...' : mode === 'register' ? 'Tiếp tục khảo sát' : 'Vào học'} {!busy && <ArrowRight size={16} />}
        </button>
      </form>
      <p className="gate-hint">{mode === 'register' ? 'Em nhớ email và mật khẩu để lần sau đăng nhập lại. Không chia sẻ mật khẩu cho bạn bè nhé!' : 'Quên mật khẩu? Em nhờ thầy cô hoặc bố mẹ liên hệ quản trị viên để được đặt lại nhé.'}</p>
      <div className="gate-switch">
        {mode === 'register' ? 'Đã có tài khoản?' : 'Chưa có tài khoản?'}{' '}
        <button type="button" onClick={() => onView(mode === 'register' ? 'login' : 'register')}>{mode === 'register' ? 'Đăng nhập' : 'Đăng ký ngay'}</button>
      </div>
    </div>
  )
}
