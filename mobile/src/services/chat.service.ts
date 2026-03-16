import { api } from './api-client'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export async function sendChatMessage(
  projectId: string,
  message: string,
  history: ChatMessage[]
): Promise<string> {
  const { data } = await api.post<{ response: string }>(`/projects/${projectId}/chat`, {
    message,
    history,
  })
  return data.response
}
