/**
 * Chat interface component for NovellaForge
 */

'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { sendChatMessage, getChatHistory } from '@/lib/api-extended'
import { getAuthToken, removeAuthToken } from '@/lib/api'
import type { ChatMessage } from '@/types'

interface ChatInterfaceProps {
  projectId?: string
  className?: string
}

export function ChatInterface({ projectId, className }: ChatInterfaceProps) {
  const router = useRouter()
  const [messages, setMessages] = React.useState<ChatMessage[]>([])
  const [input, setInput] = React.useState('')
  const [isLoading, setIsLoading] = React.useState(false)
  const [isLoadingHistory, setIsLoadingHistory] = React.useState(true)
  const [authRequired, setAuthRequired] = React.useState(false)
  const messagesEndRef = React.useRef<HTMLDivElement>(null)

  React.useEffect(() => {
    loadChatHistory()
  }, [projectId])

  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const loadChatHistory = async () => {
    const token = getAuthToken()
    if (!token) {
      setAuthRequired(true)
      setMessages([])
      setIsLoadingHistory(false)
      return
    }

    try {
      setAuthRequired(false)
      setIsLoadingHistory(true)
      const history = await getChatHistory(projectId)
      setMessages(history)
    } catch (error) {
      if (error instanceof Error && /not authenticated|validate credentials|401/i.test(error.message)) {
        removeAuthToken()
        setAuthRequired(true)
        setMessages([])
        return
      }
      console.error('Failed to load chat history:', error)
    } finally {
      setIsLoadingHistory(false)
    }
  }

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    const token = getAuthToken()
    if (!token) {
      setAuthRequired(true)
      return
    }
    if (!input.trim() || isLoading) return

    const userMessage = input.trim()
    setInput('')

    const userMsg: ChatMessage = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: userMessage,
      project_id: projectId,
      created_at: new Date().toISOString(),
    }

    setMessages((prev) => [...prev, userMsg])
    setIsLoading(true)

    try {
      const response = await sendChatMessage(userMessage, projectId)
      const assistantMsg: ChatMessage = {
        id: response.message_id,
        role: 'assistant',
        content: response.response,
        project_id: projectId,
        created_at: new Date().toISOString(),
      }

      setMessages((prev) => [...prev, assistantMsg])
    } catch (error) {
      if (error instanceof Error && /not authenticated|validate credentials|401/i.test(error.message)) {
        removeAuthToken()
        setAuthRequired(true)
        return
      }
      console.error('Failed to send message:', error)
      const errorMsg: ChatMessage = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: "Desole, une erreur s'est produite. Veuillez reessayer.",
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, errorMsg])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage(e as any)
    }
  }

  return (
    <div className={cn('flex h-full flex-col rounded-3xl border border-stone-200 bg-white/90 shadow-soft', className)}>
      <div className="flex items-center justify-between border-b border-stone-200 p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-brand-700 text-white font-semibold">
            N
          </div>
          <div>
            <h3 className="font-semibold text-ink">NovellaForge</h3>
            <p className="text-xs text-ink/60">Assistant d'ecriture</p>
          </div>
        </div>
        {projectId && <div className="text-xs text-ink/50">Contexte: projet actuel</div>}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {isLoadingHistory ? (
        <div className="flex h-full items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-700 mx-auto mb-2"></div>
            <p className="text-sm text-ink/60">Chargement de l'historique...</p>
          </div>
        </div>
        ) : authRequired ? (
          <div className="flex h-full items-center justify-center">
            <div className="text-center max-w-md">
              <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-100 text-brand-700">
                <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 1l3 4h4l-2 4 2 4h-4l-3 4-3-4H5l2-4-2-4h4l3-4z" />
                </svg>
              </div>
              <h3 className="font-serif text-lg text-ink mb-2">Connexion requise</h3>
              <p className="text-sm text-ink/60">
                Connectez-vous pour acceder a l'historique et utiliser le chat.
              </p>
              <Button variant="primary" className="mt-5" onClick={() => router.push('/auth/login')}>
                Se connecter
              </Button>
            </div>
          </div>
        ) : messages.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <div className="text-center max-w-md">
              <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-100 text-brand-700">
                <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
              </div>
              <h3 className="font-serif text-lg text-ink mb-2">Bienvenue dans votre atelier</h3>
              <p className="text-sm text-ink/60">
                Demandez une scene, un plan de chapitre ou un resume. NovellaForge
                s'appuie sur vos documents et vos contraintes.
              </p>
              <div className="mt-6 grid grid-cols-2 gap-2 text-xs text-left">
                {[
                  "Aide-moi a developper l'intrigue",
                  'Creons un personnage ensemble',
                  'Analyse mon chapitre',
                  'Suggestions de dialogue',
                ].map((prompt) => (
                  <button
                    key={prompt}
                    className="rounded-xl bg-white/80 p-2 text-ink/70 hover:text-ink hover:bg-white shadow-sm"
                    onClick={() => setInput(prompt)}
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <div key={message.id} className={cn('flex', message.role === 'user' ? 'justify-end' : 'justify-start')}>
              <div
                className={cn(
                  'max-w-[80%] rounded-2xl px-4 py-3 text-sm',
                  message.role === 'user'
                    ? 'bg-brand-700 text-white'
                    : 'bg-stone-100 text-ink'
                )}
              >
                <div className="whitespace-pre-wrap break-words">{message.content}</div>
              </div>
            </div>
          ))
        )}

        {isLoading && (
          <div className="flex justify-start">
            <div className="rounded-2xl bg-stone-100 px-4 py-3">
              <div className="flex space-x-2">
                <div className="h-2 w-2 rounded-full bg-ink/30 animate-bounce" style={{ animationDelay: '0ms' }}></div>
                <div className="h-2 w-2 rounded-full bg-ink/30 animate-bounce" style={{ animationDelay: '150ms' }}></div>
                <div className="h-2 w-2 rounded-full bg-ink/30 animate-bounce" style={{ animationDelay: '300ms' }}></div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="border-t border-stone-200 p-4">
        <form onSubmit={handleSendMessage} className="flex gap-2">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ecrivez votre message... (Entree pour envoyer)"
            className="flex-1 min-h-[60px] max-h-[200px] resize-none"
            disabled={isLoading || authRequired}
          />
          <Button
            type="submit"
            variant="primary"
            disabled={!input.trim() || isLoading || authRequired}
            className="self-end"
          >
            Envoyer
          </Button>
        </form>
      </div>
    </div>
  )
}
