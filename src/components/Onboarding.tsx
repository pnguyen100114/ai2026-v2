import { useState } from 'react'
import { ArrowRight, BookOpen, Check, Sparkles, Zap } from 'lucide-react'
import { useAuth, type Account } from '../contexts/AuthContext'

// Values match the subject codes used by the tutor/roadmap backend.
const subjects = [
  { value: 'Toán', label: 'Toán', icon: '∑' },
  { value: 'Ngữ văn', label: 'Ngữ văn', icon: 'Aa' },
  { value: 'Tiếng Anh', label: 'Tiếng Anh', icon: 'En' },
  { value: 'KHTN', label: 'Khoa học tự nhiên', icon: '⚗' },
  { value: 'LSDL', label: 'Lịch sử và Địa lý', icon: '◈' },
]
const goals = [
  { value: 'Cải thiện điểm số', icon: '📈' },
  { value: 'Ôn thi', icon: '🎯' },
  { value: 'Học trước chương trình', icon: '🚀' },
  { value: 'Củng cố kiến thức nền tảng', icon: '🧱' },
]

export default function Onboarding({ user }: { user: Account }) {
  const auth = useAuth()
  const [step, setStep] = useState(1)
  const [selected, setSelected] = useState<string[]>(user.onboarding.subjects?.length ? user.onboarding.subjects : ['Toán'])
  const [favorite, setFavorite] = useState(user.onboarding.favorite || 'Toán')
  const [goal, setGoal] = useState(user.onboarding.goal || 'Cải thiện điểm số')
  const [minutes, setMinutes] = useState(user.onboarding.dailyMinutes || 25)
  const nextGrade = Math.min(9, user.grade + 1)
  const [target, setTarget] = useState(user.onboarding.targetGrade || user.grade)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const toggleSubject = (subject: string) => {
    const next = selected.includes(subject) ? selected.filter((item) => item !== subject) : [...selected, subject]
    setSelected(next)
    if (!next.includes(favorite)) setFavorite(next[0] || 'Toán')
  }

  const save = async (patch: Parameters<typeof auth.updateProfile>[0]) => {
    setBusy(true)
    setError('')
    try {
      await auth.updateProfile(patch)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Mimo chưa lưu được, em thử lại nhé.')
      setBusy(false)
    }
  }

  const next = () => {
    if (step < 3) {
      setStep(step + 1)
      return
    }
    const chosen = selected.length ? selected : ['Toán']
    void save({
      onboarding: { subjects: chosen, favorite, goal, dailyMinutes: minutes, targetGrade: target, schoolGrade: user.onboarding.schoolGrade ?? user.grade },
      onboarded: true,
      subject: chosen.includes(favorite) ? favorite : chosen[0],
      grade: target,
    })
  }

  return (
    <div className="gate-onboarding">
      <div className="gate-onboarding-top">
        <div className="gate-brand dark"><div className="brand-mark"><Sparkles size={20} /></div><strong>Gia Sư AI<span className="brand-dot">.</span></strong></div>
        <button type="button" className="gate-skip" disabled={busy} onClick={() => void save({ onboarded: true, onboarding: { ...user.onboarding, schoolGrade: user.onboarding.schoolGrade ?? user.grade } })}>Bỏ qua khảo sát</button>
      </div>
      <div className="gate-onboarding-content">
        <div className="gate-progress"><span style={{ width: `${(step / 3) * 100}%` }} /></div>
        <span className="gate-eyebrow">BƯỚC {step}/3 · CÁ NHÂN HÓA LỘ TRÌNH</span>

        {step === 1 && <>
          <h1>Chào {user.name}, em muốn học môn nào?</h1>
          <p>Chọn một hoặc nhiều môn để Mimo chuẩn bị nội dung phù hợp.</p>
          <div className="gate-subject-grid">
            {subjects.map((subject) => {
              const isSelected = selected.includes(subject.value)
              return (
                <button key={subject.value} type="button" className={`gate-choice ${isSelected ? 'selected' : ''}`} aria-pressed={isSelected} onClick={() => toggleSubject(subject.value)}>
                  <span className="gate-choice-icon">{subject.icon}</span>
                  <strong>{subject.label}</strong>
                  <span>{isSelected ? 'Đã chọn' : 'Chọn môn'}</span>
                  {isSelected && <Check className="gate-choice-check" size={16} />}
                </button>
              )
            })}
          </div>
          <label className="gate-label">Môn em muốn học trước
            <select value={favorite} onChange={(event) => setFavorite(event.target.value)}>
              {(selected.length ? selected : ['Toán']).map((value) => <option key={value} value={value}>{subjects.find((item) => item.value === value)?.label ?? value}</option>)}
            </select>
          </label>
        </>}

        {step === 2 && <>
          <h1>Mục tiêu của em là gì?</h1>
          <p>Điều này giúp Mimo sắp xếp tốc độ và dạng bài phù hợp.</p>
          <div className="gate-goal-list">
            {goals.map((item) => (
              <button key={item.value} type="button" className={`gate-option ${goal === item.value ? 'selected' : ''}`} aria-pressed={goal === item.value} onClick={() => setGoal(item.value)}>
                <span>{item.icon}</span><strong>{item.value}</strong>{goal === item.value && <Check size={17} />}
              </button>
            ))}
          </div>
          <div className="gate-label">Em muốn học bao nhiêu phút mỗi ngày?
            <div className="gate-minutes">
              {[15, 25, 45, 60].map((value) => <button key={value} type="button" className={minutes === value ? 'selected' : ''} aria-pressed={minutes === value} onClick={() => setMinutes(value)}>{value} phút</button>)}
            </div>
          </div>
        </>}

        {step === 3 && <>
          <h1>Thiết lập lộ trình của em</h1>
          <p>Em có muốn thử sức với chương trình cao hơn không?</p>
          <div className="gate-path">
            <button type="button" className={target === user.grade ? 'selected' : ''} aria-pressed={target === user.grade} onClick={() => setTarget(user.grade)}>
              <BookOpen size={21} /><span><strong>Học đúng lớp {user.grade}</strong><small>Ôn chắc kiến thức hiện tại</small></span>{target === user.grade && <Check size={17} />}
            </button>
            {nextGrade !== user.grade && (
              <button type="button" className={target === nextGrade ? 'selected' : ''} aria-pressed={target === nextGrade} onClick={() => setTarget(nextGrade)}>
                <Zap size={21} /><span><strong>Thử sức lớp {nextGrade}</strong><small>Học trước kiến thức lớp trên</small></span>{target === nextGrade && <Check size={17} />}
              </button>
            )}
          </div>
          {target !== user.grade && <div className="gate-warning"><Sparkles size={17} /><span><strong>Lộ trình vượt cấp</strong><br />Mimo sẽ bắt đầu từ kiến thức nền của lớp {target}, em có thể đổi lại lớp ở Trang chủ.</span></div>}
        </>}

        {error && <div className="gate-error" role="alert">{error}</div>}
        <div className="gate-actions">
          {step > 1 && <button type="button" className="gate-button outline" disabled={busy} onClick={() => setStep(step - 1)}>Quay lại</button>}
          <button type="button" className="gate-button primary" disabled={busy} onClick={next}>{busy ? 'Đang lưu...' : step === 3 ? 'Tạo lộ trình cho mình' : 'Tiếp tục'} {!busy && <ArrowRight size={17} />}</button>
        </div>
      </div>
    </div>
  )
}
