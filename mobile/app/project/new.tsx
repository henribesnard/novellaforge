import { useState } from 'react'
import { View, ScrollView, KeyboardAvoidingView, Platform } from 'react-native'
import { router } from 'expo-router'
import { SafeAreaView } from 'react-native-safe-area-context'
import { Text } from '../../src/components/ui/text'
import { Input } from '../../src/components/ui/input'
import { Button } from '../../src/components/ui/button'
import { createProject } from '../../src/services/project.service'

const GENRES = ['werewolf', 'billionaire', 'mafia', 'fantasy', 'romance', 'thriller', 'scifi', 'mystery', 'horror', 'historical']

export default function NewProjectScreen() {
  const [title, setTitle] = useState('')
  const [genre, setGenre] = useState('')
  const [description, setDescription] = useState('')
  const [notes, setNotes] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleCreate = async () => {
    if (!title.trim()) {
      setError('Le titre est requis.')
      return
    }
    try {
      setLoading(true)
      setError('')
      const project = await createProject({
        title: title.trim(),
        genre: genre || undefined,
        description: description.trim() || undefined,
        notes: notes.trim() || undefined,
      })
      router.replace(`/project/${project.id}`)
    } catch (err: any) {
      setError(err.message || 'Erreur lors de la creation')
    } finally {
      setLoading(false)
    }
  }

  return (
    <SafeAreaView className="flex-1 bg-canvas">
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        className="flex-1"
      >
        <ScrollView contentContainerStyle={{ padding: 20 }} keyboardShouldPersistTaps="handled">
          <View className="flex-row items-center justify-between mb-6">
            <Text variant="h2">Nouveau projet</Text>
            <Button variant="ghost" size="sm" onPress={() => router.back()}>
              Annuler
            </Button>
          </View>

          <View className="gap-4">
            <Input
              label="Titre du projet"
              value={title}
              onChangeText={setTitle}
              placeholder="Mon roman..."
            />

            <View>
              <Text variant="caption" className="mb-2">Genre</Text>
              <View className="flex-row flex-wrap gap-2">
                {GENRES.map((g) => (
                  <Button
                    key={g}
                    variant={genre === g ? 'primary' : 'outline'}
                    size="sm"
                    onPress={() => setGenre(genre === g ? '' : g)}
                  >
                    {g}
                  </Button>
                ))}
              </View>
            </View>

            <Input
              label="Description"
              value={description}
              onChangeText={setDescription}
              placeholder="Resume de votre histoire..."
              multiline
              numberOfLines={3}
            />

            <Input
              label="Notes pour l'IA"
              value={notes}
              onChangeText={setNotes}
              placeholder="Instructions supplementaires..."
              multiline
              numberOfLines={3}
            />

            {error ? (
              <View className="rounded-xl border border-red-200 bg-red-50 p-3">
                <Text className="text-sm text-red-700">{error}</Text>
              </View>
            ) : null}

            <Button onPress={handleCreate} isLoading={loading}>
              Creer le projet
            </Button>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  )
}
