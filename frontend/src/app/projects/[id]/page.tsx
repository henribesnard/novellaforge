/**
 * Project detail page for NovellaForge
 */

'use client'

import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { getAuthToken } from '@/lib/api'
import {
  getProject,
  getConcept,
  generateConcept,
  acceptConcept,
} from '@/lib/api-extended'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { formatDate, formatGenreLabel, formatWordCount } from '@/lib/utils'
import type {
  Project,
  ConceptPayload,
} from '@/types'

export default function ProjectDetailPage() {
  const router = useRouter()
  const params = useParams()
  const projectId = params?.id as string

  const [project, setProject] = useState<Project | null>(null)
  const [concept, setConcept] = useState<ConceptPayload | null>(null)
  const [conceptStatus, setConceptStatus] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>('')

  const formatConceptStatus = (status?: string) => {
    if (!status) return ''
    if (status === 'accepted') return 'valide'
    if (status === 'draft') return 'brouillon'
    return status
  }

  const normalizeConcept = (raw: Partial<ConceptPayload> | null, fallbackTitle: string) => ({
    title: raw?.title || fallbackTitle,
    premise: raw?.premise || '',
    tone: raw?.tone || '',
    tropes: Array.isArray(raw?.tropes) ? raw?.tropes : [],
    emotional_orientation: raw?.emotional_orientation || '',
  })

  const buildConcept = (patch: Partial<ConceptPayload>) => ({
    title: concept?.title || project?.title || '',
    premise: concept?.premise || '',
    tone: concept?.tone || '',
    tropes: concept?.tropes || [],
    emotional_orientation: concept?.emotional_orientation || '',
    ...patch,
  })

  useEffect(() => {
    if (!getAuthToken()) {
      router.push('/auth/login')
      return
    }
    if (!projectId) {
      return
    }
    loadAll()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId])

  const loadAll = async () => {
    try {
      setLoading(true)
      setError('')
      const projectData = await getProject(projectId)
      setProject(projectData)
      const metadata = projectData.metadata || {}
      const conceptEntry = metadata.concept as Record<string, any> | undefined
      const fallbackConcept = conceptEntry?.data ?? (conceptEntry?.premise ? conceptEntry : null)
      const fallbackStatus = conceptEntry?.status as string | undefined
      if (fallbackConcept) {
        setConcept(normalizeConcept(fallbackConcept, projectData.title))
        setConceptStatus(fallbackStatus || 'draft')
      }

      if (metadata.concept) {
        try {
          const conceptResponse = await getConcept(projectId)
          setConcept(conceptResponse.concept)
          setConceptStatus(conceptResponse.status)
        } catch {
          if (!fallbackConcept) {
            setConcept(null)
            setConceptStatus('')
          }
        }
      } else {
        setConcept(null)
        setConceptStatus('')
      }

    } catch (err: any) {
      setError(err.message || 'Erreur lors du chargement du projet')
      setProject(null)
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateConcept = async () => {
    try {
      setError('')
      const response = await generateConcept(projectId, true)
      setConcept(response.concept)
      setConceptStatus(response.status)
    } catch (err: any) {
      setError(err.message || 'Erreur lors de la generation du concept')
    }
  }

  const handleAcceptConcept = async () => {
    if (!concept) return
    try {
      setError('')
      const response = await acceptConcept(projectId, concept)
      setConcept(response.concept)
      setConceptStatus(response.status)
      router.push('/dashboard/new')
    } catch (err: any) {
      setError(err.message || 'Erreur lors de la validation du concept')
    }
  }

  if (loading) {
    return (
      <div className="p-10 text-center text-sm text-ink/60">Chargement...</div>
    )
  }

  if (!project) {
    return (
      <div className="p-10 text-center text-sm text-ink/60">Projet introuvable</div>
    )
  }

  return (
    <div className="space-y-8 p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex flex-col gap-2">
          <h1 className="text-2xl font-semibold text-ink">{project.title}</h1>
          <p className="text-sm text-ink/60">
            Genre: {formatGenreLabel(project.genre)} | {formatWordCount(project.current_word_count)} mots | Cree le{' '}
            {formatDate(project.created_at)}
          </p>
        </div>
        <Button variant="outline" onClick={() => router.push('/dashboard/new')}>
          Retour au dashboard
        </Button>
      </div>

      {error && (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Concept central</CardTitle>
          <CardDescription>Premisse, ton et tropes alignes sur la serialisation pay-to-read.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Button variant="primary" onClick={handleGenerateConcept}>Generer un concept</Button>
            <Button variant="ghost" onClick={handleAcceptConcept} disabled={!concept}>Valider le concept</Button>
            {conceptStatus && (
              <span className="text-xs uppercase tracking-[0.2em] text-brand-600">
                {formatConceptStatus(conceptStatus)}
              </span>
            )}
          </div>

          <Input
            label="Titre propose"
            value={concept?.title || ''}
            onChange={(e) => setConcept(buildConcept({ title: e.target.value }))}
            placeholder="Titre du projet"
          />

          <Input
            label="Premisse"
            value={concept?.premise || ''}
            onChange={(e) => setConcept(buildConcept({ premise: e.target.value }))}
            placeholder="Une heroine est liee a une meute interdite..."
          />

          <Input
            label="Ton"
            value={concept?.tone || ''}
            onChange={(e) => setConcept(buildConcept({ tone: e.target.value }))}
            placeholder="Emotionnel, tendu, addictif"
          />

          <Input
            label="Orientation emotionnelle"
            value={concept?.emotional_orientation || ''}
            onChange={(e) => setConcept(buildConcept({ emotional_orientation: e.target.value }))}
            placeholder="Passion, vengeance, tension"
          />

          <Textarea
            label="Tropes (separes par des virgules)"
            value={concept?.tropes?.join(', ') || ''}
            onChange={(e) => setConcept(buildConcept({
              tropes: e.target.value.split(',').map((item) => item.trim()).filter(Boolean),
            }))}
            rows={3}
          />
        </CardContent>
      </Card>
    </div>
  )
}
