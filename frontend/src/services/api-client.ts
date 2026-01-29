const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8002/api/v1'

export interface AuthResponse {
  access_token: string
  token_type?: string
}

export interface LoginCredentials {
  email: string
  password: string
}

export interface RegisterData {
  email: string
  password: string
  full_name?: string
}

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

const getToken = () => {
  if (typeof window === 'undefined') return null
  return window.localStorage.getItem('auth_token')
}

const clearTokenAndRedirect = () => {
  if (typeof window === 'undefined') return
  window.localStorage.removeItem('auth_token')
  window.location.href = '/auth/login'
}

async function parseError(response: Response) {
  const body = await response.json().catch(() => ({ detail: 'Erreur reseau' }))
  return body.detail || `Erreur ${response.status}`
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getToken()
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
    ...options?.headers,
  }

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers })

  if (!response.ok) {
    if (response.status === 401) {
      clearTokenAndRedirect()
    }
    const message = await parseError(response)
    throw new ApiError(response.status, message)
  }

  if (response.status === 204) {
    return null as T
  }

  const text = await response.text()
  if (!text) {
    return null as T
  }

  return JSON.parse(text) as T
}

function getDownloadFilename(disposition: string | null, fallback: string): string {
  if (!disposition) return fallback
  const match = disposition.match(/filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i)
  const filename = match?.[1] || match?.[2]
  if (!filename) return fallback
  try {
    return decodeURIComponent(filename)
  } catch {
    return filename
  }
}

export async function downloadFile(path: string, fallbackName: string): Promise<{ blob: Blob; filename: string }> {
  const token = getToken()
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      ...(token && { Authorization: `Bearer ${token}` }),
    },
  })

  if (!response.ok) {
    if (response.status === 401) {
      clearTokenAndRedirect()
    }
    const message = await parseError(response)
    throw new ApiError(response.status, message)
  }

  const blob = await response.blob()
  const filename = getDownloadFilename(response.headers.get('Content-Disposition'), fallbackName)
  return { blob, filename }
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'PUT', body: body ? JSON.stringify(body) : undefined }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
}
