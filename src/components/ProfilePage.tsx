import { useState } from 'react'
import { CheckCircle2, Eye, EyeOff, KeyRound, UserRound } from 'lucide-react'
import { changePassword } from '../services/chatRepository'

type Props = {
  name: string
  email: string
  grade: number
  onRename: (name: string) => void
}

export default function ProfilePage({ name, email, grade, onRename }: Props) {
  return (
    <div className="page profile-page">
      <div className="page-title-row">
        <div>
          <span className="eyebrow"><span className="eyebrow-dot" /> TÀI KHOẢN</span>
          <h1>Hồ sơ của em</h1>
          <p className="subtext">Đổi tên hiển thị và mật khẩu đăng nhập.</p>
        </div>
      </div>
      <div className="profile-sections">
        <NameSection name={name} email={email} grade={grade} onRename={onRename} />
        <PasswordSection />
      </div>
    </div>
  )
}

function NameSection({ name, email, grade, onRename }: Props) {
  const [draft, setDraft] = useState(name)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const save = (event: React.FormEvent) => {
    event.preventDefault()
    setMessage('')
    const value = draft.trim()
    if (!value) {
      setError('Tên không được để trống nhé.')
      return
    }
    setError('')
    onRename(value)
    setDraft(value)
    setMessage('Đã lưu tên mới.')
  }

  return (
    <section className="section-block">
      <div className="profile-section-head"><div className="profile-section-icon"><UserRound size={18} /></div><h2>Thông tin</h2></div>
      <form className="profile-form" noValidate onSubmit={save}>
        <label>Họ và tên<input value={draft} onChange={(event) => { setDraft(event.target.value); setMessage('') }} maxLength={80} autoComplete="name" /></label>
        <label>Email đăng nhập<input value={email} readOnly disabled /></label>
        <label>Lớp đang học<input value={`Lớp ${grade}`} readOnly disabled /></label>
        {error && <div className="profile-alert error" role="alert">{error}</div>}
        {message && <div className="profile-alert success" role="status"><CheckCircle2 size={15} /> {message}</div>}
        <button type="submit" className="primary-btn" disabled={draft.trim() === name}>Lưu tên</button>
      </form>
    </section>
  )
}

function PasswordSection() {
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [show, setShow] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError('')
    setMessage('')
    if (!current) return setError('Em nhập mật khẩu hiện tại nhé.')
    if (next.length < 6) return setError('Mật khẩu mới cần ít nhất 6 ký tự nhé.')
    if (next !== confirm) return setError('Hai mật khẩu mới chưa giống nhau, em nhập lại nhé.')
    setBusy(true)
    try {
      await changePassword(current, next)
      setCurrent('')
      setNext('')
      setConfirm('')
      setMessage('Đã đổi mật khẩu. Lần sau em đăng nhập bằng mật khẩu mới nhé.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Có lỗi xảy ra, em thử lại nhé.')
    } finally {
      setBusy(false)
    }
  }

  const type = show ? 'text' : 'password'
  return (
    <section className="section-block">
      <div className="profile-section-head"><div className="profile-section-icon"><KeyRound size={18} /></div><h2>Đổi mật khẩu</h2></div>
      <form className="profile-form" noValidate onSubmit={(event) => void submit(event)}>
        <label>Mật khẩu hiện tại<input type={type} value={current} onChange={(event) => setCurrent(event.target.value)} autoComplete="current-password" maxLength={128} /></label>
        <label>Mật khẩu mới<input type={type} value={next} onChange={(event) => setNext(event.target.value)} placeholder="Ít nhất 6 ký tự" autoComplete="new-password" maxLength={128} /></label>
        <label>Nhập lại mật khẩu mới<input type={type} value={confirm} onChange={(event) => setConfirm(event.target.value)} autoComplete="new-password" maxLength={128} /></label>
        <button type="button" className="profile-show-toggle" onClick={() => setShow((value) => !value)}>{show ? <EyeOff size={14} /> : <Eye size={14} />} {show ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}</button>
        {error && <div className="profile-alert error" role="alert">{error}</div>}
        {message && <div className="profile-alert success" role="status"><CheckCircle2 size={15} /> {message}</div>}
        <button type="submit" className="primary-btn" disabled={busy}>{busy ? 'Đang lưu...' : 'Đổi mật khẩu'}</button>
      </form>
    </section>
  )
}
