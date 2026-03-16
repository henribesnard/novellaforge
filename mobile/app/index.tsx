import { useEffect } from 'react'
import { router } from 'expo-router'
import { View, ActivityIndicator } from 'react-native'
import { useAuthStore } from '../src/store/auth.store'

export default function Index() {
  const token = useAuthStore((s) => s.token)
  const hydrated = useAuthStore((s) => s.hydrated)

  useEffect(() => {
    if (!hydrated) return
    if (token) {
      router.replace('/(tabs)/dashboard')
    } else {
      router.replace('/(auth)/login')
    }
  }, [token, hydrated])

  return (
    <View className="flex-1 items-center justify-center bg-canvas">
      <ActivityIndicator size="large" color="#2f8578" />
    </View>
  )
}
