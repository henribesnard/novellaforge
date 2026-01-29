import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { projectService } from '@/services/project.service'

export const projectKeys = {
  all: ['projects'] as const,
  list: () => [...projectKeys.all, 'list'] as const,
  detail: (id: string) => [...projectKeys.all, id] as const,
  concept: (id: string) => [...projectKeys.all, id, 'concept'] as const,
  synopsis: (id: string) => [...projectKeys.all, id, 'synopsis'] as const,
  plan: (id: string) => [...projectKeys.all, id, 'plan'] as const,
}

export function useProjects() {
  return useQuery({
    queryKey: projectKeys.list(),
    queryFn: () => projectService.list(),
  })
}

export function useProject(id: string) {
  return useQuery({
    queryKey: projectKeys.detail(id),
    queryFn: () => projectService.get(id),
    enabled: !!id,
  })
}

export function useSynopsis(projectId: string) {
  return useQuery({
    queryKey: projectKeys.synopsis(projectId),
    queryFn: () => projectService.getSynopsis(projectId),
    enabled: !!projectId,
  })
}

export function usePlan(projectId: string) {
  return useQuery({
    queryKey: projectKeys.plan(projectId),
    queryFn: () => projectService.getPlan(projectId),
    enabled: !!projectId,
  })
}

export function useGenerateSynopsis(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (notes?: string) => projectService.generateSynopsis(projectId, notes),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: projectKeys.synopsis(projectId) })
      qc.invalidateQueries({ queryKey: projectKeys.detail(projectId) })
    },
  })
}

export function useGeneratePlan(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (params?: { chapterCount?: number; arcCount?: number }) =>
      projectService.generatePlan(projectId, params?.chapterCount, params?.arcCount),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: projectKeys.plan(projectId) })
      qc.invalidateQueries({ queryKey: projectKeys.detail(projectId) })
    },
  })
}

export function useDeleteProject() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, title }: { id: string; title: string }) =>
      projectService.delete(id, title),
    onSuccess: () => qc.invalidateQueries({ queryKey: projectKeys.list() }),
  })
}
