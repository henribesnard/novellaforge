'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import type { Editor } from '@tiptap/react'
import { getDocuments } from '@/lib/api-extended'
import { sanitizeForTTS } from '@/lib/tts-sanitizer'
import { AudioErrorBoundary } from '@/features/audio'
import { LazyChapterAudioPlayer } from '@/features/audio/lazy'
import { ChapterEditor } from '@/features/editor'
import { EditorToolbar } from '@/features/editor'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { Document } from '@/types'

export default function ChapterDetailPage() {
  const params = useParams()
  const projectId = params?.id as string
  const chapterIndex = Number(params?.idx)
  const [chapter, setChapter] = useState<Document | null>(null)
  const [editorContent, setEditorContent] = useState('')
  const [editorInstance, setEditorInstance] = useState<Editor | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const load = async () => {
      if (!projectId || !chapterIndex) return
      try {
        setLoading(true)
        const docs = await getDocuments(projectId)
        const match = docs.find((doc) => {
          const meta = (doc.metadata || {}) as Record<string, any>
          const indexValue = meta.chapter_index ?? doc.order_index
          return Number(indexValue) === chapterIndex
        }) || null
        setChapter(match)
        setEditorContent(match?.content || '')
        if (!match) {
          setError('Chapitre introuvable.')
        }
      } catch (err: any) {
        setError(err?.message || 'Erreur lors du chargement du chapitre.')
      } finally {
        setLoading(false)
      }
    }

    void load()
  }, [projectId, chapterIndex])

  if (loading) {
    return <p className="text-sm text-ink/60">Chargement du chapitre...</p>
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        {error}
      </div>
    )
  }

  if (!chapter) {
    return <p className="text-sm text-ink/60">Aucun chapitre selectionne.</p>
  }

  const ttsContent = sanitizeForTTS(editorContent)

  return (
    <div className="space-y-6">
      <Card variant="elevated">
        <CardHeader>
          <CardTitle>{chapter.title || `Chapitre ${chapterIndex}`}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <AudioErrorBoundary>
            <LazyChapterAudioPlayer
              chapterId={chapter.id}
              chapterTitle={chapter.title || `Chapitre ${chapterIndex}`}
              content={ttsContent}
              defaultExpanded={true}
            />
          </AudioErrorBoundary>

          <EditorToolbar editor={editorInstance} />
          <ChapterEditor
            content={editorContent}
            onChange={setEditorContent}
            onEditorReady={setEditorInstance}
          />
        </CardContent>
      </Card>
    </div>
  )
}
