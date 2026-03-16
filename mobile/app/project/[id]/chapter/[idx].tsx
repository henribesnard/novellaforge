import { useState, useCallback } from 'react'
import { View, ScrollView, Pressable } from 'react-native'
import { router, useLocalSearchParams } from 'expo-router'
import { useQuery } from '@tanstack/react-query'
import { SafeAreaView } from 'react-native-safe-area-context'
import { ArrowLeft, Volume2, VolumeX, Check } from 'lucide-react-native'
import * as Speech from 'expo-speech'
import { Text } from '../../../../src/components/ui/text'
import { Button } from '../../../../src/components/ui/button'
import { Skeleton } from '../../../../src/components/ui/skeleton'
import { getDocuments, approveChapter, type Document } from '../../../../src/services/chapter.service'

export default function ChapterReaderScreen() {
  const { id, idx } = useLocalSearchParams<{ id: string; idx: string }>()
  const chapterIndex = Number(idx)
  const [speaking, setSpeaking] = useState(false)
  const [approving, setApproving] = useState(false)
  const [error, setError] = useState('')

  const { data: documents, isLoading } = useQuery({
    queryKey: ['documents', id],
    queryFn: () => getDocuments(id!),
    enabled: !!id,
  })

  const chapter = (documents || []).find((doc) => {
    const meta = (doc.metadata || {}) as Record<string, any>
    return Number(meta.chapter_index ?? doc.order_index) === chapterIndex
  })

  const meta = (chapter?.metadata || {}) as Record<string, any>
  const status = String(meta.status || meta.chapter_status || 'draft').toLowerCase()
  const isApproved = status === 'approved'

  const toggleSpeech = useCallback(() => {
    if (speaking) {
      Speech.stop()
      setSpeaking(false)
    } else if (chapter?.content) {
      const cleanText = chapter.content.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
      Speech.speak(cleanText, {
        language: 'fr-FR',
        rate: 0.9,
        onDone: () => setSpeaking(false),
        onStopped: () => setSpeaking(false),
      })
      setSpeaking(true)
    }
  }, [speaking, chapter])

  const handleApprove = async () => {
    if (!chapter?.id) return
    try {
      setApproving(true)
      setError('')
      await approveChapter(chapter.id)
      router.back()
    } catch (err: any) {
      setError(err.message || 'Erreur')
    } finally {
      setApproving(false)
    }
  }

  if (isLoading) {
    return (
      <SafeAreaView className="flex-1 bg-canvas">
        <View className="p-5 gap-4">
          <Skeleton width="70%" height={28} />
          <Skeleton width="100%" height={200} variant="rect" />
        </View>
      </SafeAreaView>
    )
  }

  if (!chapter) {
    return (
      <SafeAreaView className="flex-1 bg-canvas items-center justify-center">
        <Text variant="caption">Chapitre introuvable</Text>
        <Button variant="ghost" onPress={() => router.back()} className="mt-4">
          Retour
        </Button>
      </SafeAreaView>
    )
  }

  const cleanContent = (chapter.content || '')
    .replace(/<[^>]+>/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim()

  return (
    <SafeAreaView className="flex-1 bg-shell" edges={['top']}>
      <View className="flex-row items-center justify-between px-5 pt-2 pb-3 border-b border-stone-200 bg-shell">
        <Pressable onPress={() => { Speech.stop(); router.back() }} className="flex-row items-center gap-2">
          <ArrowLeft size={20} color="#6a5746" />
          <Text variant="caption">Retour</Text>
        </Pressable>
        <View className="flex-row gap-2">
          <Pressable
            onPress={toggleSpeech}
            className="h-10 w-10 items-center justify-center rounded-full bg-brand-100"
            style={({ pressed }) => ({ opacity: pressed ? 0.7 : 1 })}
          >
            {speaking ? (
              <VolumeX size={18} color="#2f8578" />
            ) : (
              <Volume2 size={18} color="#2f8578" />
            )}
          </Pressable>
          {!isApproved && (
            <Pressable
              onPress={handleApprove}
              disabled={approving}
              className="h-10 w-10 items-center justify-center rounded-full bg-emerald-100"
              style={({ pressed }) => ({ opacity: approving ? 0.5 : pressed ? 0.7 : 1 })}
            >
              <Check size={18} color="#059669" />
            </Pressable>
          )}
        </View>
      </View>

      <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: 60 }}>
        <Text variant="h2" className="mb-1">
          {chapter.title || `Chapitre ${chapterIndex}`}
        </Text>
        <Text variant="caption" className="mb-6">
          {chapter.word_count.toLocaleString('fr-FR')} mots
          {isApproved ? ' — Approuve' : ''}
        </Text>

        {error ? (
          <View className="rounded-xl border border-red-200 bg-red-50 p-3 mb-4">
            <Text className="text-sm text-red-700">{error}</Text>
          </View>
        ) : null}

        <Text className="text-base leading-7 text-ink/90">
          {cleanContent || 'Aucun contenu.'}
        </Text>
      </ScrollView>
    </SafeAreaView>
  )
}
