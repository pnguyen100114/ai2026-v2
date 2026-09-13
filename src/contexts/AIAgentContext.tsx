import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'
import { getStudentContext, runLearningAgent, type AgentMessage, type StudentContext } from '../services/aiAgent'
import { readStorage, writeStorage } from '../services/storageService'

const initialMessages: AgentMessage[] = [{ from: 'ai', text: 'Chào bạn! Mình là Mimo, AI Learning Agent. Mình đã sẵn sàng đồng hành cùng lộ trình của bạn. ✨' }]
type AgentContextValue = { messages: AgentMessage[]; context: StudentContext; send: (question: string) => void; refreshContext: () => void }
const AgentContext = createContext<AgentContextValue | null>(null)

export function AIAgentProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<AgentMessage[]>(() => readStorage<AgentMessage[]>('aiTutor_messages', initialMessages))
  const [context, setContext] = useState(getStudentContext)
  const value = useMemo(() => ({ messages, context, send: (question: string) => { const answer = runLearningAgent(question, context); const next = [...messages, { from: 'student' as const, text: question }, { from: 'ai' as const, text: answer }]; setMessages(next); writeStorage('aiTutor_messages', next); setContext(getStudentContext()) }, refreshContext: () => setContext(getStudentContext()) }), [context, messages])
  return <AgentContext.Provider value={value}>{children}</AgentContext.Provider>
}

export function useAIAgent() { const context = useContext(AgentContext); if (!context) throw new Error('useAIAgent must be used inside AIAgentProvider'); return context }

export function getAgentContextSnapshot() { return getStudentContext() }
