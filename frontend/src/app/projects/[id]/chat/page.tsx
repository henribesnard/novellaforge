'use client'

import { useParams } from 'next/navigation'
import { ChatInterface } from '@/features/chat'

export default function ProjectChatPage() {
  const params = useParams()
  const projectId = params?.id as string

  return (
    <div className="h-[calc(100vh-220px)]">
      <ChatInterface projectId={projectId} className="h-full" />
    </div>
  )
}
