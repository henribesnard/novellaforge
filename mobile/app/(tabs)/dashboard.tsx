import { useCallback } from 'react'
import { View, FlatList, Pressable, RefreshControl } from 'react-native'
import { router } from 'expo-router'
import { useQuery } from '@tanstack/react-query'
import { SafeAreaView } from 'react-native-safe-area-context'
import { LogOut } from 'lucide-react-native'
import { Text } from '../../src/components/ui/text'
import { Card } from '../../src/components/ui/card'
import { Badge } from '../../src/components/ui/badge'
import { Skeleton } from '../../src/components/ui/skeleton'
import { Fab } from '../../src/components/ui/fab'
import { useAuthStore } from '../../src/store/auth.store'
import { getProjects, type Project } from '../../src/services/project.service'
import { logout } from '../../src/services/auth.service'

function StatCard({ label, value, color }: { label: string; value: string | number; color: string }) {
  return (
    <View className={`flex-1 rounded-xl p-3 ${color}`}>
      <Text variant="label" className="text-[10px]">{label}</Text>
      <Text variant="h3" className="mt-1">{value}</Text>
    </View>
  )
}

function ProjectItem({ project }: { project: Project }) {
  return (
    <Pressable onPress={() => router.push(`/project/${project.id}`)}>
      <Card variant="elevated" className="p-4 mb-3">
        <View className="flex-row items-center justify-between">
          <View className="flex-1 mr-3">
            <Text variant="h4" numberOfLines={1}>{project.title}</Text>
            {project.description ? (
              <Text variant="caption" numberOfLines={1} className="mt-1">{project.description}</Text>
            ) : null}
          </View>
          <Badge variant={project.status === 'completed' ? 'success' : 'brand'}>
            {project.status === 'completed' ? 'Termine' : 'En cours'}
          </Badge>
        </View>
        <View className="flex-row items-center gap-4 mt-2">
          {project.genre ? (
            <Text variant="caption">{project.genre}</Text>
          ) : null}
          <Text variant="caption">{project.current_word_count.toLocaleString('fr-FR')} mots</Text>
        </View>
      </Card>
    </Pressable>
  )
}

export default function DashboardScreen() {
  const clearAuth = useAuthStore((s) => s.clear)
  const { data, isLoading, refetch, isRefetching } = useQuery({
    queryKey: ['projects'],
    queryFn: () => getProjects(),
  })

  const projects = data?.projects || []
  const totalWords = projects.reduce((sum, p) => sum + p.current_word_count, 0)
  const inProgress = projects.filter((p) => p.status === 'in_progress').length
  const completed = projects.filter((p) => p.status === 'completed').length

  const handleLogout = useCallback(async () => {
    await logout()
    await clearAuth()
    router.replace('/(auth)/login')
  }, [clearAuth])

  return (
    <SafeAreaView className="flex-1 bg-canvas" edges={['top']}>
      <View className="flex-row items-center justify-between px-5 pt-2 pb-4">
        <View className="flex-row items-center gap-3">
          <View className="h-10 w-10 items-center justify-center rounded-xl bg-brand-700">
            <Text className="text-lg font-bold text-white">N</Text>
          </View>
          <View>
            <Text variant="label" className="text-brand-700">NovellaForge</Text>
            <Text variant="caption">Tableau de bord</Text>
          </View>
        </View>
        <Pressable
          onPress={handleLogout}
          className="h-10 w-10 items-center justify-center rounded-full bg-stone-100"
          style={({ pressed }) => ({ opacity: pressed ? 0.6 : 1 })}
        >
          <LogOut size={18} color="#6a5746" />
        </Pressable>
      </View>

      {isLoading ? (
        <View className="px-5 gap-4">
          <View className="flex-row gap-3">
            {[0, 1, 2, 3].map((i) => (
              <View key={i} className="flex-1 rounded-xl bg-stone-100 p-3">
                <Skeleton width="60%" height={10} />
                <Skeleton width="40%" height={20} style={{ marginTop: 8 }} />
              </View>
            ))}
          </View>
          {[0, 1, 2].map((i) => (
            <View key={i} className="rounded-2xl bg-white border border-stone-100 p-4">
              <Skeleton width="70%" height={18} />
              <Skeleton width="50%" height={14} style={{ marginTop: 8 }} />
            </View>
          ))}
        </View>
      ) : (
        <FlatList
          data={projects}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => <ProjectItem project={item} />}
          contentContainerStyle={{ paddingHorizontal: 20, paddingBottom: 100 }}
          refreshControl={
            <RefreshControl
              refreshing={isRefetching}
              onRefresh={() => refetch()}
              tintColor="#2f8578"
            />
          }
          ListHeaderComponent={
            <View className="mb-6">
              <View className="flex-row gap-3 mb-6">
                <StatCard label="Projets" value={projects.length} color="bg-brand-100" />
                <StatCard label="Mots" value={totalWords.toLocaleString('fr-FR')} color="bg-accent-100" />
                <StatCard label="En cours" value={inProgress} color="bg-stone-100" />
                <StatCard label="Finis" value={completed} color="bg-emerald-100" />
              </View>
              <Text variant="h2">Mes projets</Text>
            </View>
          }
          ListEmptyComponent={
            <Card variant="outlined" className="p-8 items-center">
              <Text variant="h3">Aucun projet</Text>
              <Text variant="caption" className="mt-2 text-center">
                Creez votre premier projet pour commencer.
              </Text>
            </Card>
          }
        />
      )}

      <Fab onPress={() => router.push('/project/new')} />
    </SafeAreaView>
  )
}
