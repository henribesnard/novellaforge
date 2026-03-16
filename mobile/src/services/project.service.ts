import { api } from './api-client'

export interface Project {
  id: string
  title: string
  description?: string
  genre?: string
  status: string
  current_word_count: number
  target_word_count?: number
  structure_template?: string
  created_at: string
  updated_at: string
  metadata?: Record<string, any>
}

interface ProjectsResponse {
  projects: Project[]
  total: number
}

export async function getProjects(): Promise<ProjectsResponse> {
  const { data } = await api.get<ProjectsResponse>('/projects/')
  return data
}

export async function getProject(id: string): Promise<Project> {
  const { data } = await api.get<Project>(`/projects/${id}`)
  return data
}

export async function createProject(payload: {
  title: string
  genre?: string
  description?: string
  notes?: string
}): Promise<Project> {
  const { data } = await api.post<Project>('/projects/', payload)
  return data
}

export async function generateConcept(projectId: string): Promise<any> {
  const { data } = await api.post(`/projects/${projectId}/concept/generate`, { regenerate: true })
  return data
}

export async function acceptConcept(projectId: string, concept: any): Promise<any> {
  const { data } = await api.post(`/projects/${projectId}/concept/accept`, concept)
  return data
}

export async function generateSynopsis(projectId: string): Promise<any> {
  const { data } = await api.post(`/projects/${projectId}/synopsis/generate`)
  return data
}

export async function generatePlan(projectId: string): Promise<any> {
  const { data } = await api.post(`/projects/${projectId}/plan/generate`)
  return data
}

export async function acceptPlan(projectId: string): Promise<any> {
  const { data } = await api.post(`/projects/${projectId}/plan/accept`)
  return data
}
