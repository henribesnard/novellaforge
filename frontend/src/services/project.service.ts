import { api, downloadFile } from './api-client'
import type { ConceptPayload, PlanPayload, Project, ProjectCreate, SynopsisResponse, PlanResponse, ConceptResponse } from '@/types'

export const projectService = {
  list: (skip = 0, limit = 50) =>
    api.get<Project[]>(`/projects?skip=${skip}&limit=${limit}`),
  get: (id: string) =>
    api.get<Project>(`/projects/${id}`),
  create: (data: ProjectCreate) =>
    api.post<Project>('/projects', data),
  update: (id: string, data: Partial<Project>) =>
    api.put<Project>(`/projects/${id}`, data),
  delete: (id: string, confirmTitle: string) =>
    api.post<void>(`/projects/${id}/delete`, { confirm_title: confirmTitle }),
  download: (id: string) =>
    downloadFile(`/projects/${id}/download`, `project-${id}.zip`),

  getConcept: (id: string) =>
    api.get<ConceptResponse>(`/projects/${id}/concept`),
  generateConcept: (id: string, force = false) =>
    api.post<ConceptResponse>(`/projects/${id}/concept/generate`, { force }),
  acceptConcept: (id: string, concept: ConceptPayload) =>
    api.put<ConceptResponse>(`/projects/${id}/concept`, concept),

  getSynopsis: (id: string) =>
    api.get<SynopsisResponse>(`/projects/${id}/synopsis`),
  generateSynopsis: (id: string, notes?: string) =>
    api.post<SynopsisResponse>(`/projects/${id}/synopsis/generate`, { notes }),
  updateSynopsis: (id: string, synopsis: string) =>
    api.put<SynopsisResponse>(`/projects/${id}/synopsis`, { synopsis }),
  acceptSynopsis: (id: string) =>
    api.put<SynopsisResponse>(`/projects/${id}/synopsis/accept`),

  getPlan: (id: string) =>
    api.get<PlanResponse>(`/projects/${id}/plan`),
  generatePlan: (id: string, chapterCount?: number, arcCount?: number) =>
    api.post<PlanResponse>(`/projects/${id}/plan/generate`, { chapter_count: chapterCount, arc_count: arcCount }),
  acceptPlan: (id: string) =>
    api.put<PlanResponse>(`/projects/${id}/plan/accept`),
  updatePlan: (id: string, plan: PlanPayload) =>
    api.put<PlanResponse>(`/projects/${id}/plan`, { plan }),
}
