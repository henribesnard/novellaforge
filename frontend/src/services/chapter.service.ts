import { api, downloadFile } from './api-client'
import type { ChapterApprovalResponse, ChapterGenerationResponse, Document } from '@/types'

export interface ChapterGeneratePayload {
  project_id: string
  chapter_id?: string
  chapter_index?: number
  instruction?: string
  rewrite_focus?: 'emotion' | 'tension' | 'action' | 'custom'
  target_word_count?: number
  use_rag?: boolean
  reindex_documents?: boolean
  create_document?: boolean
  auto_approve?: boolean
}

export const chapterService = {
  list: (projectId: string) =>
    api.get<Document[]>(`/documents?project_id=${projectId}`),
  get: (id: string) =>
    api.get<Document>(`/documents/${id}`),
  generate: (payload: ChapterGeneratePayload) =>
    api.post<ChapterGenerationResponse>('/writing/generate-chapter', payload),
  approve: (documentId: string) =>
    api.post<ChapterApprovalResponse>('/writing/approve-chapter', { document_id: documentId }),
  download: (id: string) =>
    downloadFile(`/documents/${id}/download`, `chapter-${id}.txt`),
}
