import axios from 'axios'
import AsyncStorage from '@react-native-async-storage/async-storage'
import { router } from 'expo-router'

const API_BASE = 'http://10.0.2.2:8002/api/v1' // Android emulator; change for physical device

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use(async (config) => {
  const token = await AsyncStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      await AsyncStorage.removeItem('auth_token')
      router.replace('/(auth)/login')
    }
    const message = error.response?.data?.detail || error.message || 'Erreur reseau'
    return Promise.reject(new Error(message))
  }
)

export { api }
