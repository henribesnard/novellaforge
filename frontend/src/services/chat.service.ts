import { api } from './api-client'
import type { ChatMessage } from '@/types'

export const chatService = {
  sendMessage: (message: string, projectId?: string) =>
    api.post<{ response: string; message_id: string }>('/chat/message', {
      message,
      project_id: projectId,
    }),
  getHistory: (projectId?: string, limit = 50) => {
    const query = projectId ? `?project_id=${projectId}&limit=${limit}` : `?limit=${limit}`
    return api.get<ChatMessage[]>(`/chat/history${query}`)
  },
}
