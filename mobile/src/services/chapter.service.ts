import { api } from './api-client'

export interface Document {
  id: string
  title: string
  content?: string
  document_type?: string
  order_index: number
  word_count: number
  created_at: string
  updated_at: string
  metadata?: Record<string, any>
}

export async function getDocuments(projectId: string): Promise<Document[]> {
  const { data } = await api.get<Document[]>(`/documents/?project_id=${projectId}`)
  return data
}

export async function getDocument(documentId: string): Promise<Document> {
  const { data } = await api.get<Document>(`/documents/${documentId}`)
  return data
}

export async function generateChapter(projectId: string, chapterIndex: number): Promise<any> {
  const { data } = await api.post('/writing/generate', {
    project_id: projectId,
    chapter_index: chapterIndex,
    create_document: true,
    auto_approve: true,
    use_rag: true,
  })
  return data
}

export async function approveChapter(documentId: string): Promise<any> {
  const { data } = await api.post(`/documents/${documentId}/approve`)
  return data
}
