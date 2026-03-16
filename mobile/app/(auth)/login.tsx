import { useState } from 'react'
import { View, KeyboardAvoidingView, Platform, ScrollView } from 'react-native'
import { router } from 'expo-router'
import { Text } from '../../src/components/ui/text'
import { Input } from '../../src/components/ui/input'
import { Button } from '../../src/components/ui/button'
import { useAuthStore } from '../../src/store/auth.store'
import { login } from '../../src/services/auth.service'

export default function LoginScreen() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const setToken = useAuthStore((s) => s.setToken)

  const handleLogin = async () => {
    if (!email || !password) {
      setError('Remplissez tous les champs.')
      return
    }
    try {
      setLoading(true)
      setError('')
      const token = await login(email, password)
      setToken(token)
      router.replace('/(tabs)/dashboard')
    } catch (err: any) {
      setError(err.message || 'Erreur de connexion')
    } finally {
      setLoading(false)
    }
  }

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      className="flex-1 bg-canvas"
    >
      <ScrollView
        contentContainerStyle={{ flexGrow: 1, justifyContent: 'center' }}
        keyboardShouldPersistTaps="handled"
      >
        <View className="flex-1 justify-center px-8">
          <View className="items-center mb-10">
            <View className="h-14 w-14 items-center justify-center rounded-2xl bg-brand-700 mb-4">
              <Text variant="h2" className="text-white">N</Text>
            </View>
            <Text variant="label" className="text-brand-700">NovellaForge</Text>
            <Text variant="h2" className="mt-2">Connexion</Text>
          </View>

          <View className="gap-4">
            <Input
              label="Email"
              value={email}
              onChangeText={setEmail}
              placeholder="votre@email.com"
              keyboardType="email-address"
              autoCapitalize="none"
              autoComplete="email"
            />

            <Input
              label="Mot de passe"
              value={password}
              onChangeText={setPassword}
              placeholder="Votre mot de passe"
              secureTextEntry
              autoComplete="password"
            />

            {error ? (
              <View className="rounded-xl border border-red-200 bg-red-50 p-3">
                <Text className="text-sm text-red-700">{error}</Text>
              </View>
            ) : null}

            <Button onPress={handleLogin} isLoading={loading}>
              Se connecter
            </Button>

            <Button variant="ghost" onPress={() => router.push('/(auth)/register')}>
              Creer un compte
            </Button>
          </View>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  )
}
