export const storageKeys = {
  user: 'aiTutor_user',
  roadmap: 'aiTutor_roadmap',
  memory: 'aiTutor_memory',
  assessment: 'aiTutor_assessment',
  pomodoro: 'aiTutor_pomodoro',
  settings: 'aiTutor_settings',
} as const

export function readStorage<T>(key: string, fallback: T): T {
  try {
    const value = localStorage.getItem(key)
    return value ? JSON.parse(value) as T : fallback
  } catch {
    return fallback
  }
}

export function writeStorage<T>(key: string, value: T) {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // The UI continues to work if storage is unavailable or full.
  }
}

export function removeStorage(key: string) {
  try { localStorage.removeItem(key) } catch { /* Ignore storage failures. */ }
}
