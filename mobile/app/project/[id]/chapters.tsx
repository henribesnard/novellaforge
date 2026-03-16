import { View, FlatList, Pressable, RefreshControl } from 'react-native'
import { router, useLocalSearchParams } from 'expo-router'
import { useQuery } from '@tanstack/react-query'
import { SafeAreaView } from 'react-native-safe-area-context'
import { ArrowLeft } from 'lucide-react-native'
import { Text } from '../../../src/components/ui/text'
import { Card } from '../../../src/components/ui/card'
import { Badge } from '../../../src/components/ui/badge'
import { Skeleton } from '../../../src/components/ui/skeleton'
import { getDocuments, type Document } from '../../../src/services/chapter.service'

function ChapterRow({ doc, projectId }: { doc: Document; projectId: string }) {
  const meta = (doc.metadata || {}) as Record<string, any>
  const chapterIndex = Number(meta.chapter_index ?? doc.order_index ?? 0)
  const status = String(meta.status || meta.chapter_status || 'draft').toLowerCase()

  return (
    <Pressable onPress={() => router.push(`/project/${projectId}/chapter/${chapterIndex}`)}>
      <Card variant="elevated" className="p-4 mb-3">
        <View className="flex-row items-center justify-between">
          <View className="flex-1 mr-3">
            <Text variant="h4" numberOfLines={1}>
              {chapterIndex}. {doc.title}
            </Text>
            <Text variant="caption" className="mt-1">
              {doc.word_count.toLocaleString('fr-FR')} mots
            </Text>
          </View>
          <Badge variant={status === 'approved' ? 'success' : 'default'}>
            {status === 'approved' ? 'Approuve' : 'Brouillon'}
          </Badge>
        </View>
      </Card>
    </Pressable>
  )
}

export default function ChaptersScreen() {
  const { id } = useLocalSearchParams<{ id: string }>()

  const { data: documents, isLoading, refetch, isRefetching } = useQuery({
    queryKey: ['documents', id],
    queryFn: () => getDocuments(id!),
    enabled: !!id,
  })

  const chapters = (documents || [])
    .filter((d) => d.document_type === 'chapter')
    .sort((a, b) => a.order_index - b.order_index)

  return (
    <SafeAreaView className="flex-1 bg-canvas" edges={['top']}>
      <View className="px-5 pt-2 pb-4">
        <Pressable onPress={() => router.back()} className="flex-row items-center gap-2 mb-2">
          <ArrowLeft size={20} color="#6a5746" />
          <Text variant="caption">Retour</Text>
        </Pressable>
        <Text variant="h2">Chapitres</Text>
        <Text variant="caption">{chapters.length} chapitre{chapters.length !== 1 ? 's' : ''}</Text>
      </View>

      {isLoading ? (
        <View className="px-5 gap-3">
          {[0, 1, 2].map((i) => (
            <View key={i} className="rounded-2xl bg-white border border-stone-100 p-4">
              <Skeleton width="60%" height={18} />
              <Skeleton width="30%" height={14} style={{ marginTop: 8 }} />
            </View>
          ))}
        </View>
      ) : (
        <FlatList
          data={chapters}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => <ChapterRow doc={item} projectId={id!} />}
          contentContainerStyle={{ paddingHorizontal: 20, paddingBottom: 40 }}
          refreshControl={
            <RefreshControl refreshing={isRefetching} onRefresh={() => refetch()} tintColor="#2f8578" />
          }
          ListEmptyComponent={
            <Card variant="outlined" className="p-8 items-center">
              <Text variant="h3">Aucun chapitre</Text>
              <Text variant="caption" className="mt-2 text-center">
                Generez des chapitres depuis la page du projet.
              </Text>
            </Card>
          }
        />
      )}
    </SafeAreaView>
  )
}
