import { View, FlatList, Pressable, RefreshControl, Alert } from 'react-native'
import { router } from 'expo-router'
import { useQuery } from '@tanstack/react-query'
import { SafeAreaView } from 'react-native-safe-area-context'
import { Text } from '../../src/components/ui/text'
import { Card } from '../../src/components/ui/card'
import { Badge } from '../../src/components/ui/badge'
import { Fab } from '../../src/components/ui/fab'
import { Skeleton } from '../../src/components/ui/skeleton'
import { getProjects, type Project } from '../../src/services/project.service'

function ProjectRow({ project }: { project: Project }) {
  return (
    <Pressable onPress={() => router.push(`/project/${project.id}`)}>
      <Card variant="elevated" className="p-4 mb-3">
        <View className="flex-row items-start justify-between">
          <View className="flex-1 mr-3">
            <Text variant="h4" numberOfLines={1}>{project.title}</Text>
            {project.description ? (
              <Text variant="caption" numberOfLines={2} className="mt-1">{project.description}</Text>
            ) : null}
            <View className="flex-row items-center gap-3 mt-2">
              {project.genre ? (
                <Badge variant="brand">{project.genre}</Badge>
              ) : null}
              <Text variant="caption">
                {project.current_word_count.toLocaleString('fr-FR')} mots
              </Text>
            </View>
          </View>
          <Badge variant={project.status === 'completed' ? 'success' : 'default'}>
            {project.status === 'completed' ? 'Termine' : project.status === 'in_progress' ? 'En cours' : project.status}
          </Badge>
        </View>
      </Card>
    </Pressable>
  )
}

export default function ProjectsScreen() {
  const { data, isLoading, refetch, isRefetching } = useQuery({
    queryKey: ['projects'],
    queryFn: () => getProjects(),
  })

  const projects = data?.projects || []

  return (
    <SafeAreaView className="flex-1 bg-canvas" edges={['top']}>
      <View className="px-5 pt-2 pb-4">
        <Text variant="h2">Projets</Text>
        <Text variant="caption">{projects.length} projet{projects.length !== 1 ? 's' : ''}</Text>
      </View>

      {isLoading ? (
        <View className="px-5 gap-3">
          {[0, 1, 2, 3].map((i) => (
            <View key={i} className="rounded-2xl bg-white border border-stone-100 p-4">
              <Skeleton width="70%" height={18} />
              <Skeleton width="40%" height={14} style={{ marginTop: 8 }} />
              <Skeleton width="30%" height={12} style={{ marginTop: 8 }} />
            </View>
          ))}
        </View>
      ) : (
        <FlatList
          data={projects}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => <ProjectRow project={item} />}
          contentContainerStyle={{ paddingHorizontal: 20, paddingBottom: 100 }}
          refreshControl={
            <RefreshControl
              refreshing={isRefetching}
              onRefresh={() => refetch()}
              tintColor="#2f8578"
            />
          }
          ListEmptyComponent={
            <Card variant="outlined" className="p-8 items-center">
              <Text variant="h3">Aucun projet</Text>
              <Text variant="caption" className="mt-2 text-center">
                Appuyez sur + pour creer votre premier projet.
              </Text>
            </Card>
          }
        />
      )}

      <Fab onPress={() => router.push('/project/new')} />
    </SafeAreaView>
  )
}
