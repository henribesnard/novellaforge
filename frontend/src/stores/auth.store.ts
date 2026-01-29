import { create } from 'zustand'

interface AuthState {
  token: string | null
  isAuthenticated: boolean
  setToken: (token: string | null) => void
  logout: () => void
}

const getStoredToken = () => {
  if (typeof window === 'undefined') return null
  return window.localStorage.getItem('auth_token')
}

export const useAuthStore = create<AuthState>((set) => ({
  token: getStoredToken(),
  isAuthenticated: !!getStoredToken(),
  setToken: (token) => {
    if (typeof window !== 'undefined') {
      if (token) {
        window.localStorage.setItem('auth_token', token)
      } else {
        window.localStorage.removeItem('auth_token')
      }
    }
    set({ token, isAuthenticated: !!token })
  },
  logout: () => {
    if (typeof window !== 'undefined') {
      window.localStorage.removeItem('auth_token')
    }
    set({ token: null, isAuthenticated: false })
  },
}))
