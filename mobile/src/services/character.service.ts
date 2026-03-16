import { api } from './api-client'

export interface Character {
  id: string
  name: string
  description?: string
  personality?: string
  backstory?: string
  character_metadata?: Record<string, any>
}

export async function getCharacters(projectId: string): Promise<Character[]> {
  const { data } = await api.get<Character[]>(`/characters/?project_id=${projectId}`)
  return data
}

export async function generateCharacters(projectId: string, precision?: string): Promise<Character[]> {
  const { data } = await api.post<Character[]>(`/characters/generate`, {
    project_id: projectId,
    precision: precision || 'principaux',
  })
  return data
}
