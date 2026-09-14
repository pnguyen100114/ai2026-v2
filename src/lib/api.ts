// Empty in dev (Vite proxies /api to FastAPI). In production set it to the backend URL, e.g. https://gia-su-ai-api.onrender.com
const apiBase = ((import.meta.env.VITE_API_BASE_URL as string | undefined) || '').replace(/\/$/, '')
const TOKEN_KEY = 'gia-su-ai-token'
export const UNAUTHORIZED_EVENT = 'gia-su-ai:unauthorized'

export function getToken() {
  try { return localStorage.getItem(TOKEN_KEY) } catch { return null }
}

export function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch { /* storage unavailable: the session just won't survive a reload */ }
}

export function apiUrl(path: string) {
  return path.startsWith('/api') ? `${apiBase}${path}` : path
}

export async function apiFetch(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers)
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(apiUrl(path), { ...init, headers })
  if (response.status === 401 && token) window.dispatchEvent(new Event(UNAUTHORIZED_EVENT))
  return response
}

/** JSON request that throws an Error carrying the backend's Vietnamese `detail` message. */
export async function apiJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await apiFetch(path, init)
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    const error = new Error(typeof payload.detail === 'string' ? payload.detail : 'Mimo chưa kết nối được máy chủ, em thử lại nhé.') as Error & { status?: number }
    error.status = response.status
    throw error
  }
  return payload as T
}
