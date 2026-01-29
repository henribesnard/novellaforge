import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { chapterService, type ChapterGeneratePayload } from '@/services/chapter.service'
import { projectKeys } from './use-projects'

export const chapterKeys = {
  all: ['chapters'] as const,
  list: (projectId: string) => [...chapterKeys.all, 'list', projectId] as const,
  detail: (id: string) => [...chapterKeys.all, id] as const,
}

export function useChapters(projectId: string) {
  return useQuery({
    queryKey: chapterKeys.list(projectId),
    queryFn: () => chapterService.list(projectId),
    enabled: !!projectId,
  })
}

export function useGenerateChapter(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: ChapterGeneratePayload) => chapterService.generate(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: chapterKeys.list(projectId) })
      qc.invalidateQueries({ queryKey: projectKeys.detail(projectId) })
    },
  })
}

export function useApproveChapter(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (documentId: string) => chapterService.approve(documentId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: chapterKeys.list(projectId) })
      qc.invalidateQueries({ queryKey: projectKeys.detail(projectId) })
    },
  })
}
