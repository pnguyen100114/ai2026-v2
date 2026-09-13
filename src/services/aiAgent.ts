import { readStorage, storageKeys, writeStorage } from './storageService'

export type StudentContext = {
  profile: { name: string; grade: string; subjects: string[]; goals: string[] }
  learning: { currentSubject: string; currentGrade: string; currentChapter: string; currentLesson: string; completedLessons: number[]; roadmapProgress: number; assessmentResults: unknown; weaknesses: Record<string, number> }
  pomodoro: { focusTime: number; studySessions: number; currentSession: number; status: string; remainingTime: number }
  posture: { postureScore: number | null; goodPercentage: number; badPercentage: number }
}

export type StudentMemory = { strengths: string[]; weaknesses: string[]; learningPreferences: string[]; recentMistakes: string[]; masteredTopics: string[]; recommendedTopics: string[]; recentQuestions: string[] }
export type AgentMessage = { from: 'ai' | 'student'; text: string }

const defaultMemory: StudentMemory = { strengths: ['Hằng đẳng thức'], weaknesses: ['Phương trình', 'Biến đổi biểu thức'], learningPreferences: ['Giải thích từng bước'], recentMistakes: [], masteredTopics: [], recommendedTopics: ['Phân thức đại số'], recentQuestions: [] }

export function getStudentMemory() { return readStorage<StudentMemory>(storageKeys.memory, defaultMemory) }
export function saveStudentMemory(memory: StudentMemory) { writeStorage(storageKeys.memory, memory); return memory }

export function getStudentContext(): StudentContext {
  const user = readStorage<{ name?: string; grade?: string; subjects?: string[]; goals?: string[]; completedLessons?: number[]; progress?: number; assessmentResults?: unknown }>(storageKeys.user, {})
  const pomodoro = readStorage<{ todayFocusTime?: number; sessionCount?: number; currentSession?: number; status?: string; remainingTime?: number }>(storageKeys.pomodoro, {})
  const memory = getStudentMemory()
  return { profile: { name: user.name || 'bạn', grade: user.grade || 'Lớp 8', subjects: user.subjects || ['Toán'], goals: user.goals || [] }, learning: { currentSubject: 'Toán', currentGrade: user.grade || 'Lớp 8', currentChapter: 'Chương II · Phân thức', currentLesson: 'Phân thức đại số', completedLessons: user.completedLessons || [], roadmapProgress: user.progress || 12, assessmentResults: user.assessmentResults || null, weaknesses: Object.fromEntries(memory.weaknesses.map((topic, index) => [topic, Math.max(40, 80 - index * 15)])) }, pomodoro: { focusTime: pomodoro.todayFocusTime || 0, studySessions: pomodoro.sessionCount || 0, currentSession: pomodoro.currentSession || 1, status: pomodoro.status || 'IDLE', remainingTime: pomodoro.remainingTime || 0 }, posture: { postureScore: null, goodPercentage: 0, badPercentage: 0 } }
}

export const agentTools = {
  getStudentProfile: () => getStudentContext().profile,
  getCurrentLesson: () => getStudentContext().learning.currentLesson,
  getRoadmap: () => ({ subject: 'Toán', progress: getStudentContext().learning.roadmapProgress, currentLesson: getStudentContext().learning.currentLesson }),
  getAssessmentResults: () => getStudentContext().learning.assessmentResults,
  getWeaknesses: () => getStudentContext().learning.weaknesses,
  getPostureStats: () => getStudentContext().posture,
  getPomodoroStatus: () => getStudentContext().pomodoro,
  createPracticeQuestions: () => ['Giải phương trình 3x + 4 = 19', 'Rút gọn (x + 3)² - x²', 'Tìm điều kiện xác định của 2 / (x - 5)'],
  checkAnswer: (answer: string, expected: string) => answer.trim().toLowerCase() === expected.trim().toLowerCase(),
  explainLesson: () => `Mình sẽ giải thích bài ${getStudentContext().learning.currentLesson} theo từng bước, bắt đầu bằng một gợi ý nhỏ nhé.`,
  updateProgress: (topic: string, correct: boolean) => { const memory = getStudentMemory(); if (!correct && !memory.weaknesses.includes(topic)) memory.weaknesses = [...memory.weaknesses, topic]; if (correct && !memory.masteredTopics.includes(topic)) memory.masteredTopics = [...memory.masteredTopics, topic]; return saveStudentMemory(memory) },
  recommendLesson: () => getStudentMemory().recommendedTopics[0] || 'Ôn lại bài đang học',
}

export function runLearningAgent(question: string, context = getStudentContext()): string {
  const normalized = question.toLowerCase()
  const memory = getStudentMemory()
  memory.recentQuestions = [...memory.recentQuestions.slice(-4), question]
  saveStudentMemory(memory)
  if (normalized.includes('hôm nay') || normalized.includes('nên học')) return `Hôm nay mình đề xuất bạn học ${agentTools.recommendLesson()}. Bạn đang học ${context.learning.currentLesson} và cần củng cố nhiều nhất ở ${memory.weaknesses[0] || 'phần kiến thức đang học'}. Bạn có muốn mình tạo một phiên Pomodoro 25 phút không?`
  if (normalized.includes('tạo bài') || normalized.includes('bài tập')) return `Mình đã xem điểm cần cải thiện và ưu tiên phần ${memory.weaknesses[0] || 'phương trình'}. Đây là 3 bài khởi động:\n\n1. ${agentTools.createPracticeQuestions()[0]}\n2. ${agentTools.createPracticeQuestions()[1]}\n3. ${agentTools.createPracticeQuestions()[2]}\n\nBạn làm bài 1 trước, mình sẽ kiểm tra và điều chỉnh độ khó.`
  if (normalized.includes('pomodoro') || normalized.includes('tập trung')) return `Bạn đã học ${Math.round(context.pomodoro.focusTime / 60)} phút hôm nay qua ${context.pomodoro.studySessions} phiên. Mình có thể gắn phiên tiếp theo với bài ${context.learning.currentLesson}.`
  if (normalized.includes('tư thế') || normalized.includes('ngồi')) return 'AI Posture Monitor chỉ nhận diện tư thế học trong ảnh/video, không chẩn đoán sức khỏe. Nếu cảnh báo bad xuất hiện nhiều lần, bạn thử điều chỉnh lưng và vị trí ngồi nhé.'
  if (normalized.includes('giải') || normalized.includes('bài này')) return `Mình biết bạn đang học ${context.learning.currentLesson}. Gợi ý đầu tiên: hãy viết lại đề bài và xác định đại lượng cần tìm. Bạn thử làm bước đó trước, mình sẽ kiểm tra rồi hướng dẫn từng bước tiếp theo.`
  return `Mình đang đồng hành với ${context.profile.name}, ${context.profile.grade}. Bạn có thể hỏi về bài ${context.learning.currentLesson}, yêu cầu tạo bài tập phần ${memory.weaknesses[0] || 'đang yếu'}, hoặc hỏi hôm nay nên học gì.`
}
