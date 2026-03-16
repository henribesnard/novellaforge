import { View, ScrollView, Pressable, RefreshControl } from 'react-native'
import { router, useLocalSearchParams } from 'expo-router'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { SafeAreaView } from 'react-native-safe-area-context'
import { ArrowLeft, BookOpen, Users, MessageCircle } from 'lucide-react-native'
import { Text } from '../../../src/components/ui/text'
import { Card } from '../../../src/components/ui/card'
import { Badge } from '../../../src/components/ui/badge'
import { Button } from '../../../src/components/ui/button'
import { Skeleton } from '../../../src/components/ui/skeleton'
import { getProject, generateConcept, acceptConcept, generatePlan, acceptPlan } from '../../../src/services/project.service'
import { useState } from 'react'

export default function ProjectDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const queryClient = useQueryClient()
  const [actionLoading, setActionLoading] = useState('')
  const [error, setError] = useState('')

  const { data: project, isLoading, refetch, isRefetching } = useQuery({
    queryKey: ['project', id],
    queryFn: () => getProject(id!),
    enabled: !!id,
  })

  const metadata = (project?.metadata || {}) as Record<string, any>
  const conceptEntry = metadata.concept as Record<string, any> | undefined
  const conceptStatus = conceptEntry?.status || (conceptEntry?.data || conceptEntry?.premise ? 'draft' : undefined)
  const planEntry = metadata.plan as Record<string, any> | undefined
  const planStatus = planEntry?.status || 'none'

  const handleAction = async (action: string, fn: () => Promise<any>) => {
    try {
      setActionLoading(action)
      setError('')
      await fn()
      await refetch()
      queryClient.invalidateQueries({ queryKey: ['projects'] })
    } catch (err: any) {
      setError(err.message || 'Erreur')
    } finally {
      setActionLoading('')
    }
  }

  if (isLoading) {
    return (
      <SafeAreaView className="flex-1 bg-canvas">
        <View className="p-5 gap-4">
          <Skeleton width="60%" height={28} />
          <Skeleton width="40%" height={16} />
          <View className="mt-4 gap-3">
            <Skeleton variant="rect" height={100} />
            <Skeleton variant="rect" height={100} />
          </View>
        </View>
      </SafeAreaView>
    )
  }

  if (!project) {
    return (
      <SafeAreaView className="flex-1 bg-canvas items-center justify-center">
        <Text variant="caption">Projet introuvable</Text>
      </SafeAreaView>
    )
  }

  return (
    <SafeAreaView className="flex-1 bg-canvas" edges={['top']}>
      <ScrollView
        contentContainerStyle={{ padding: 20 }}
        refreshControl={
          <RefreshControl refreshing={isRefetching} onRefresh={() => refetch()} tintColor="#2f8578" />
        }
      >
        <Pressable onPress={() => router.back()} className="flex-row items-center gap-2 mb-4">
          <ArrowLeft size={20} color="#6a5746" />
          <Text variant="caption">Retour</Text>
        </Pressable>

        <View className="mb-6">
          <Text variant="h1">{project.title}</Text>
          <View className="flex-row items-center gap-3 mt-2">
            {project.genre ? <Badge variant="brand">{project.genre}</Badge> : null}
            <Text variant="caption">{project.current_word_count.toLocaleString('fr-FR')} mots</Text>
            <Badge variant={project.status === 'completed' ? 'success' : 'default'}>
              {project.status === 'completed' ? 'Termine' : 'En cours'}
            </Badge>
          </View>
        </View>

        {error ? (
          <View className="rounded-xl border border-red-200 bg-red-50 p-3 mb-4">
            <Text className="text-sm text-red-700">{error}</Text>
          </View>
        ) : null}

        {/* Concept */}
        <Card className="p-4 mb-4">
          <View className="flex-row items-center justify-between mb-3">
            <Text variant="h4">Concept</Text>
            {conceptStatus ? (
              <Badge variant={conceptStatus === 'accepted' ? 'success' : 'warning'}>
                {conceptStatus === 'accepted' ? 'Valide' : 'Brouillon'}
              </Badge>
            ) : null}
          </View>
          <View className="flex-row flex-wrap gap-2">
            <Button
              variant="primary"
              size="sm"
              isLoading={actionLoading === 'concept'}
              onPress={() => handleAction('concept', () => generateConcept(id!))}
            >
              Generer
            </Button>
            {conceptStatus && conceptStatus !== 'accepted' && (
              <Button
                variant="outline"
                size="sm"
                isLoading={actionLoading === 'acceptConcept'}
                onPress={() => handleAction('acceptConcept', () => acceptConcept(id!, conceptEntry?.data || conceptEntry))}
              >
                Valider
              </Button>
            )}
          </View>
        </Card>

        {/* Plan */}
        <Card className="p-4 mb-4">
          <View className="flex-row items-center justify-between mb-3">
            <Text variant="h4">Plan narratif</Text>
            {planStatus !== 'none' ? (
              <Badge variant={planStatus === 'accepted' ? 'success' : 'warning'}>
                {planStatus === 'accepted' ? 'Valide' : 'Brouillon'}
              </Badge>
            ) : null}
          </View>
          <View className="flex-row flex-wrap gap-2">
            <Button
              variant="primary"
              size="sm"
              isLoading={actionLoading === 'plan'}
              disabled={conceptStatus !== 'accepted'}
              onPress={() => handleAction('plan', () => generatePlan(id!))}
            >
              Generer le plan
            </Button>
            {planEntry && planStatus !== 'accepted' && (
              <Button
                variant="outline"
                size="sm"
                isLoading={actionLoading === 'acceptPlan'}
                onPress={() => handleAction('acceptPlan', () => acceptPlan(id!))}
              >
                Valider
              </Button>
            )}
          </View>
        </Card>

        {/* Quick actions */}
        <View className="gap-3">
          <Pressable
            className="flex-row items-center gap-3 rounded-2xl bg-white/80 border border-stone-200 p-4"
            onPress={() => router.push(`/project/${id}/chapters`)}
            style={({ pressed }) => ({ opacity: pressed ? 0.7 : 1 })}
          >
            <BookOpen size={20} color="#2f8578" />
            <Text variant="body" className="flex-1">Chapitres</Text>
            <ArrowLeft size={16} color="#bca993" style={{ transform: [{ rotate: '180deg' }] }} />
          </Pressable>

          <Pressable
            className="flex-row items-center gap-3 rounded-2xl bg-white/80 border border-stone-200 p-4"
            onPress={() => router.push(`/project/${id}/characters`)}
            style={({ pressed }) => ({ opacity: pressed ? 0.7 : 1 })}
          >
            <Users size={20} color="#2f8578" />
            <Text variant="body" className="flex-1">Personnages</Text>
            <ArrowLeft size={16} color="#bca993" style={{ transform: [{ rotate: '180deg' }] }} />
          </Pressable>

          <Pressable
            className="flex-row items-center gap-3 rounded-2xl bg-white/80 border border-stone-200 p-4"
            onPress={() => router.push('/(tabs)/chat')}
            style={({ pressed }) => ({ opacity: pressed ? 0.7 : 1 })}
          >
            <MessageCircle size={20} color="#2f8578" />
            <Text variant="body" className="flex-1">Chat IA</Text>
            <ArrowLeft size={16} color="#bca993" style={{ transform: [{ rotate: '180deg' }] }} />
          </Pressable>
        </View>
      </ScrollView>
    </SafeAreaView>
  )
}
