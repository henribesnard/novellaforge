import AsyncStorage from '@react-native-async-storage/async-storage'
import { api } from './api-client'

interface AuthResponse {
  access_token: string
  token_type?: string
}

export async function login(email: string, password: string): Promise<string> {
  const { data } = await api.post<AuthResponse>('/auth/login', { email, password })
  await AsyncStorage.setItem('auth_token', data.access_token)
  return data.access_token
}

export async function register(email: string, password: string, fullName?: string): Promise<string> {
  const { data } = await api.post<AuthResponse>('/auth/register', {
    email,
    password,
    full_name: fullName,
  })
  await AsyncStorage.setItem('auth_token', data.access_token)
  return data.access_token
}

export async function logout(): Promise<void> {
  try {
    await api.post('/auth/logout')
  } catch {
    // Ignore logout errors
  }
  await AsyncStorage.removeItem('auth_token')
}
