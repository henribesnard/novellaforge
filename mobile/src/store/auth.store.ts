import { create } from 'zustand'
import AsyncStorage from '@react-native-async-storage/async-storage'

interface AuthState {
  token: string | null
  hydrated: boolean
  setToken: (token: string | null) => void
  hydrate: () => Promise<void>
  clear: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  hydrated: false,

  setToken: (token) => {
    set({ token })
    if (token) {
      AsyncStorage.setItem('auth_token', token)
    } else {
      AsyncStorage.removeItem('auth_token')
    }
  },

  hydrate: async () => {
    const token = await AsyncStorage.getItem('auth_token')
    set({ token, hydrated: true })
  },

  clear: async () => {
    await AsyncStorage.removeItem('auth_token')
    set({ token: null })
  },
}))

// Auto-hydrate on import
useAuthStore.getState().hydrate()
