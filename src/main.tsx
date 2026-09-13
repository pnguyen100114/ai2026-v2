import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './styles.css'
import './flow.css'
import { GlobalPomodoroProvider } from './contexts/PomodoroContext'
import { AIAgentProvider } from './contexts/AIAgentContext'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <GlobalPomodoroProvider>
      <AIAgentProvider>
        <App />
      </AIAgentProvider>
    </GlobalPomodoroProvider>
  </StrictMode>,
)