import { apiJson } from '../lib/api'
import type { ProfilePatch } from '../contexts/AuthContext'

// Shapes returned by GET /api/history (see backend/db.py load_history).
export type HistorySession = { id: string; title: string; subject: string; grade: string; lesson: string; createdAt: string; updatedAt: string }
export type HistoryMessage = {
  id: string
  sessionId: string
  role: 'user' | 'assistant'
  content: string
  prompt: string | null
  sources: unknown[]
  quickReplies: string[]
  understanding: string | null
  createdAt: string
  feedback: 'up' | 'down' | null
}
export type History = { sessions: HistorySession[]; messages: HistoryMessage[] }

export function loadHistory() {
  return apiJson<History>('/api/history')
}

export function saveProfile(patch: ProfilePatch) {
  return apiJson('/api/me', { method: 'PATCH', body: JSON.stringify(patch) })
}

export function changePassword(currentPassword: string, newPassword: string) {
  return apiJson('/api/me/password', { method: 'POST', body: JSON.stringify({ currentPassword, newPassword }) })
}

export function renameSession(sessionId: string, title: string) {
  return apiJson(`/api/sessions/${encodeURIComponent(sessionId)}`, { method: 'PATCH', body: JSON.stringify({ title }) })
}

export function deleteSession(sessionId: string) {
  return apiJson(`/api/sessions/${encodeURIComponent(sessionId)}`, { method: 'DELETE' })
}

export function saveFeedback(messageId: string, rating: 'up' | 'down', comment?: string) {
  return apiJson('/api/feedback', { method: 'POST', body: JSON.stringify({ message_id: messageId, rating, comment }) })
}
