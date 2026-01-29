'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import { getDocuments } from '@/lib/api-extended'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { Document } from '@/types'

export default function ChaptersPage() {
  const params = useParams()
  const projectId = params?.id as string
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const load = async () => {
      if (!projectId) return
      try {
        setLoading(true)
        const docs = await getDocuments(projectId)
        setDocuments(docs)
      } catch (err: any) {
        setError(err?.message || 'Erreur lors du chargement des chapitres.')
      } finally {
        setLoading(false)
      }
    }

    void load()
  }, [projectId])

  const chapters = documents
    .filter((doc) => doc.document_type === 'chapter')
    .map((doc) => {
      const meta = (doc.metadata || {}) as Record<string, any>
      const index = Number(meta.chapter_index ?? doc.order_index ?? 0)
      return {
        index,
        title: doc.title || `Chapitre ${index}`,
        wordCount: doc.word_count,
      }
    })
    .filter((chapter) => chapter.index > 0)
    .sort((a, b) => a.index - b.index)

  if (loading) {
    return <p className="text-sm text-ink/60">Chargement des chapitres...</p>
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        {error}
      </div>
    )
  }

  return (
    <Card variant="elevated">
      <CardHeader>
        <CardTitle>Chapitres du projet</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {chapters.length === 0 ? (
          <p className="text-sm text-ink/60">Aucun chapitre disponible pour le moment.</p>
        ) : (
          <div className="grid gap-3">
            {chapters.map((chapter) => (
              <Link
                key={chapter.index}
                href={`/projects/${projectId}/chapters/${chapter.index}`}
                className="rounded-xl border border-stone-200 bg-white p-4 transition hover:shadow-soft"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-semibold text-ink">{chapter.index}. {chapter.title}</p>
                    <p className="text-xs text-ink/60">{chapter.wordCount} mots</p>
                  </div>
                  <span className="text-xs text-brand-700">Ouvrir</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
