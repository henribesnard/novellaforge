import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { characterService } from '@/services/character.service'
import type { Character } from '@/types'

export const characterKeys = {
  all: ['characters'] as const,
  list: (projectId: string) => [...characterKeys.all, 'list', projectId] as const,
  detail: (id: string) => [...characterKeys.all, id] as const,
}

export function useCharacters(projectId: string) {
  return useQuery({
    queryKey: characterKeys.list(projectId),
    queryFn: () => characterService.list(projectId),
    enabled: !!projectId,
  })
}

export function useCreateCharacter(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: characterService.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: characterKeys.list(projectId) })
    },
  })
}

export function useUpdateCharacter(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Character> }) =>
      characterService.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: characterKeys.list(projectId) })
    },
  })
}

export function useDeleteCharacter(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => characterService.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: characterKeys.list(projectId) })
    },
  })
}
