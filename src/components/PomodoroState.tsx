import { BellOff, Check, Coffee, Flame, Pause, Play, Sparkles, Square } from 'lucide-react'
import { usePomodoro } from '../contexts/PomodoroContext'

const PRESETS = [
  { focus: 25, rest: 5 },
  { focus: 45, rest: 10 },
  { focus: 60, rest: 15 },
]

function formatTime(milliseconds: number) {
  const seconds = Math.ceil(milliseconds / 1000)
  return `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`
}

export default function PomodoroState({ streak, lesson, dailyMinutes }: { streak: number; lesson: string; dailyMinutes: number }) {
  const timer = usePomodoro()
  const progress = Math.max(0, Math.min(100, 100 - timer.remainingTime / (timer.duration || 1) * 100))
  const status = timer.status === 'COMPLETED' ? 'HOÀN THÀNH' : timer.status === 'PAUSED' ? 'ĐANG TẠM DỪNG' : timer.mode === 'BREAK' ? 'GIỜ NGHỈ' : 'TẬP TRUNG'
  const goalPercent = Math.min(100, Math.round(timer.todayFocusMinutes / Math.max(1, dailyMinutes) * 100))
  const notificationsBlocked = 'Notification' in window && Notification.permission === 'denied'

  return (
    <div className="page focus-page">
      <div className="page-title-row">
        <div>
          <span className="section-kicker">GÓC TẬP TRUNG</span>
          <h1>Thời gian tập trung</h1>
          <p className="subtext">Đồng hồ vẫn chạy khi em chuyển sang hỏi Mimo hoặc xem lộ trình.</p>
        </div>
        <div className="focus-streak"><Flame size={20} fill="currentColor" /><strong>{streak}</strong><span>ngày học liên tiếp</span></div>
      </div>
      <div className="focus-layout">
        <section className={`timer-panel state-${timer.status.toLowerCase()}`}>
          <div className="mode-tabs" role="tablist" aria-label="Chế độ">
            <button type="button" role="tab" aria-selected={timer.mode === 'FOCUS'} className={timer.mode === 'FOCUS' ? 'active' : ''} disabled={timer.isRunning} onClick={() => timer.switchMode('FOCUS')}><Sparkles size={13} /> Tập trung {timer.focusMinutes}′</button>
            <button type="button" role="tab" aria-selected={timer.mode === 'BREAK'} className={timer.mode === 'BREAK' ? 'active' : ''} disabled={timer.isRunning} onClick={() => timer.switchMode('BREAK')}><Coffee size={13} /> Nghỉ {timer.breakMinutes}′</button>
          </div>
          <div className="timer-state-label"><span>{timer.status === 'COMPLETED' ? <Check size={17} /> : timer.mode === 'BREAK' ? <Coffee size={17} /> : <Sparkles size={17} />}</span>{status}</div>
          <div className="timer-ring" style={{ '--progress': `${progress}%` } as React.CSSProperties}>
            <div>
              <span>{formatTime(timer.remainingTime)}</span>
              <small>{timer.status === 'COMPLETED' ? 'Buổi học đã hoàn tất' : timer.status === 'IDLE' ? 'Sẵn sàng bắt đầu' : `Phiên ${timer.currentSession} / ${timer.totalSessions}`}</small>
            </div>
          </div>
          <div className="timer-actions">
            {timer.isRunning
              ? <button type="button" className="primary-btn large" onClick={timer.pause}><Pause size={17} fill="currentColor" /> Tạm dừng</button>
              : <button type="button" className="primary-btn large" onClick={() => timer.start(lesson || null)}><Play size={17} fill="currentColor" /> {timer.status === 'PAUSED' ? 'Tiếp tục' : timer.status === 'COMPLETED' ? 'Học buổi mới' : 'Bắt đầu'}</button>}
            {(timer.isRunning || timer.status === 'PAUSED') && <button type="button" className="stop-btn" onClick={timer.stop}><Square size={16} fill="currentColor" /> Kết thúc</button>}
          </div>
          {timer.linkedLesson && <div className="timer-notice">📚 Đang học: {timer.linkedLesson}</div>}
          <div className="timer-presets">
            <span>Thời lượng:</span>
            {PRESETS.map((preset) => (
              <button key={preset.focus} type="button" className={timer.focusMinutes === preset.focus ? 'selected' : ''} disabled={timer.isRunning} aria-pressed={timer.focusMinutes === preset.focus} onClick={() => timer.setDurations(preset.focus, preset.rest)}>{preset.focus} + {preset.rest} phút</button>
            ))}
          </div>
          {timer.isRunning && <small className="timer-hint">Tạm dừng để đổi thời lượng hoặc chế độ.</small>}
        </section>
        <aside className="focus-side">
          <div className="focus-note">
            <div className="note-icon"><Sparkles /></div>
            <strong>Mẹo tập trung</strong>
            <p>Úp điện thoại xuống và chỉ mở bài đang học. Hết mỗi phiên, Mimo sẽ báo em nghỉ ngơi một chút.</p>
            {notificationsBlocked && <p className="focus-warning"><BellOff size={13} /> Trình duyệt đang chặn thông báo, Mimo sẽ báo bằng âm thanh khi em mở trang này.</p>}
          </div>
          <div className="session-card">
            <div className="section-head"><h3>Hôm nay</h3><span>{timer.sessionCount} phiên</span></div>
            <div className="session-number"><strong>{timer.todayFocusMinutes} phút</strong><span>đã tập trung · mục tiêu {dailyMinutes} phút</span></div>
            <div className="session-bar"><b style={{ width: `${goalPercent}%` }} /></div>
            <div className="session-meta"><span><Check size={15} /> {goalPercent >= 100 ? 'Đạt mục tiêu hôm nay!' : `Còn ${Math.max(0, dailyMinutes - timer.todayFocusMinutes)} phút`}</span><span>{goalPercent}%</span></div>
          </div>
        </aside>
      </div>
    </div>
  )
}
