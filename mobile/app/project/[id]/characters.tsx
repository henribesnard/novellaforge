import { useState } from 'react'
import { View, FlatList, Pressable, RefreshControl } from 'react-native'
import { router, useLocalSearchParams } from 'expo-router'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { SafeAreaView } from 'react-native-safe-area-context'
import { ArrowLeft } from 'lucide-react-native'
import { Text } from '../../../src/components/ui/text'
import { Card } from '../../../src/components/ui/card'
import { Badge } from '../../../src/components/ui/badge'
import { Button } from '../../../src/components/ui/button'
import { Fab } from '../../../src/components/ui/fab'
import { Skeleton } from '../../../src/components/ui/skeleton'
import { getCharacters, generateCharacters, type Character } from '../../../src/services/character.service'

function CharacterCard({ character }: { character: Character }) {
  const [expanded, setExpanded] = useState(false)
  const role = character.character_metadata?.role

  return (
    <Pressable onPress={() => setExpanded(!expanded)}>
      <Card variant="elevated" className="p-4 mb-3">
        <View className="flex-row items-center justify-between">
          <View className="flex-1 mr-3">
            <Text variant="h4">{character.name}</Text>
            {role ? <Badge variant="brand">{role}</Badge> : null}
          </View>
        </View>
        {expanded && (
          <View className="mt-3 pt-3 border-t border-stone-200">
            {character.description ? (
              <View className="mb-2">
                <Text variant="label" className="mb-1">Description</Text>
                <Text variant="body">{character.description}</Text>
              </View>
            ) : null}
            {character.personality ? (
              <View className="mb-2">
                <Text variant="label" className="mb-1">Personnalite</Text>
                <Text variant="body">{character.personality}</Text>
              </View>
            ) : null}
            {character.backstory ? (
              <View>
                <Text variant="label" className="mb-1">Backstory</Text>
                <Text variant="body">{character.backstory}</Text>
              </View>
            ) : null}
          </View>
        )}
      </Card>
    </Pressable>
  )
}

export default function CharactersScreen() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const queryClient = useQueryClient()
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState('')

  const { data: characters, isLoading, refetch, isRefetching } = useQuery({
    queryKey: ['characters', id],
    queryFn: () => getCharacters(id!),
    enabled: !!id,
  })

  const handleGenerate = async () => {
    try {
      setGenerating(true)
      setError('')
      await generateCharacters(id!)
      await refetch()
    } catch (err: any) {
      setError(err.message || 'Erreur lors de la generation')
    } finally {
      setGenerating(false)
    }
  }

  return (
    <SafeAreaView className="flex-1 bg-canvas" edges={['top']}>
      <View className="px-5 pt-2 pb-4">
        <Pressable onPress={() => router.back()} className="flex-row items-center gap-2 mb-2">
          <ArrowLeft size={20} color="#6a5746" />
          <Text variant="caption">Retour</Text>
        </Pressable>
        <Text variant="h2">Personnages</Text>
        <Text variant="caption">
          {(characters || []).length} personnage{(characters || []).length !== 1 ? 's' : ''}
        </Text>
      </View>

      {error ? (
        <View className="mx-5 rounded-xl border border-red-200 bg-red-50 p-3 mb-3">
          <Text className="text-sm text-red-700">{error}</Text>
        </View>
      ) : null}

      {isLoading ? (
        <View className="px-5 gap-3">
          {[0, 1, 2].map((i) => (
            <View key={i} className="rounded-2xl bg-white border border-stone-100 p-4">
              <Skeleton width="50%" height={18} />
              <Skeleton width="30%" height={14} style={{ marginTop: 8 }} />
            </View>
          ))}
        </View>
      ) : (
        <FlatList
          data={characters || []}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => <CharacterCard character={item} />}
          contentContainerStyle={{ paddingHorizontal: 20, paddingBottom: 100 }}
          refreshControl={
            <RefreshControl refreshing={isRefetching} onRefresh={() => refetch()} tintColor="#2f8578" />
          }
          ListEmptyComponent={
            <Card variant="outlined" className="p-8 items-center">
              <Text variant="h3">Aucun personnage</Text>
              <Text variant="caption" className="mt-2 text-center">
                Generez des personnages avec le bouton ci-dessous.
              </Text>
              <Button
                variant="primary"
                className="mt-4"
                onPress={handleGenerate}
                isLoading={generating}
              >
                Generer les personnages
              </Button>
            </Card>
          }
        />
      )}

      <Fab onPress={handleGenerate} />
    </SafeAreaView>
  )
}
