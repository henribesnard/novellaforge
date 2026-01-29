import { api } from './api-client'
import type { Character, CharacterCreate } from '@/types'

export const characterService = {
  list: (projectId: string) =>
    api.get<Character[]>(`/characters?project_id=${projectId}`),
  get: (id: string) =>
    api.get<Character>(`/characters/${id}`),
  create: (data: CharacterCreate) =>
    api.post<Character>('/characters', data),
  update: (id: string, data: Partial<Character>) =>
    api.put<Character>(`/characters/${id}`, data),
  delete: (id: string) =>
    api.delete<void>(`/characters/${id}`),
}
