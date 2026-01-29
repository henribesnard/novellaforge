'use client'

import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { useRouter } from 'next/navigation'
import {
  acceptPlan,
  acceptSynopsis,
  approveChapter,
  downloadDocument,
  downloadProject,
  generateChapter,
  generatePlan,
  generateSynopsis,
  getDocuments,
  getSynopsis,
  updateSynopsis,
} from '@/lib/api-extended'
import { AudioErrorBoundary } from '@/features/audio'
import { LazyChapterAudioPlayer } from '@/features/audio/lazy'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { getProgressPercent } from '@/lib/audio-storage'
import { cn, formatDate, formatGenreLabel, formatWordCount } from '@/lib/utils'
import { formatConceptStatus, getStatusColor, getStatusLabel } from '@/lib/project-helpers'
import type { ChapterGenerationResponse, Document, PlanPayload, Project } from '@/types'

export type ProjectCardProps = {
  project: Project
  onReload: () => Promise<void>
  onOpenProject: (projectId: string) => void
  onDeleteRequest: (project: Project) => void
}

const ChevronIcon = ({ expanded }: { expanded: boolean }) => (
  <svg
    aria-hidden="true"
    className={cn('h-4 w-4 text-ink/50 transition-transform', expanded && 'rotate-180')}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M6 9l6 6 6-6" />
  </svg>
)

const SpeakerIcon = ({ className }: { className?: string }) => {
  const hasTextColor = className?.includes('text-')
  return (
    <svg
      aria-hidden="true"
      className={cn('h-4 w-4', !hasTextColor && 'text-ink/60', className)}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M11 5L6 9H3v6h3l5 4V5z" />
      <path d="M15.5 8.5a4 4 0 010 7" />
      <path d="M18 6a7 7 0 010 12" />
    </svg>
  )
}

const triggerDownload = (blob: Blob, filename: string) => {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

const getPreviewText = (content: string, wordLimit = 200) => {
  const cleaned = content
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
  if (!cleaned) {
    return ''
  }
  const words = cleaned.split(' ')
  if (words.length <= wordLimit) {
    return cleaned
  }
  return `${words.slice(0, wordLimit).join(' ')}...`
}

export function ProjectCard({ project, onReload, onOpenProject, onDeleteRequest }: ProjectCardProps) {
  const router = useRouter()
  const metadata = (project.metadata as Record<string, any>) || {}
  const conceptEntry = metadata.concept as Record<string, any> | undefined
  const conceptStatusRaw = conceptEntry?.status as string | undefined
  const conceptHasData = !!conceptEntry?.data || !!conceptEntry?.premise
  const conceptStatus = conceptStatusRaw || (conceptHasData ? 'draft' : undefined)
  const synopsisRaw = metadata.synopsis as any
  const synopsisEntry = typeof synopsisRaw === 'string'
    ? { text: synopsisRaw }
    : synopsisRaw && typeof synopsisRaw === 'object'
      ? { text: synopsisRaw.text ?? synopsisRaw.synopsis, status: synopsisRaw.status }
      : undefined
  const initialSynopsisText = synopsisEntry?.text ? String(synopsisEntry.text) : ''
  const planEntry = metadata.plan as Record<string, any> | undefined
  const planPayload = (planEntry?.data as PlanPayload) ?? (planEntry?.chapters ? (planEntry as PlanPayload) : undefined)
  const planStatus = (planEntry?.status as string) || 'draft'
  const canGeneratePlan = conceptStatus === 'accepted'
  const canGenerateChapter = !!planPayload && planStatus === 'accepted'
  const [showChapter, setShowChapter] = useState(false)
  const [chapterApproveLoading, setChapterApproveLoading] = useState(false)
  const [synopsisLoading, setSynopsisLoading] = useState(false)
  const [planLoading, setPlanLoading] = useState(false)
  const [chapterGenerateLoading, setChapterGenerateLoading] = useState(false)
  const [chapterViewLoading, setChapterViewLoading] = useState(false)
  const [projectDownloadLoading, setProjectDownloadLoading] = useState(false)
  const [chapterDownloadLoading, setChapterDownloadLoading] = useState(false)
  const [isCollapsed, setIsCollapsed] = useState(true)
  const [actionError, setActionError] = useState('')
  const [chapterIndex, setChapterIndex] = useState<string>('')
  const [chapterPreview, setChapterPreview] = useState<ChapterGenerationResponse | null>(null)
  const [chapterView, setChapterView] = useState<Document | null>(null)
  const [documents, setDocuments] = useState<Document[]>([])
  const [showPlan, setShowPlan] = useState(false)
  const [showSynopsis, setShowSynopsis] = useState(false)
  const [synopsisText, setSynopsisText] = useState<string>(initialSynopsisText)
  const [synopsisFetchAttempted, setSynopsisFetchAttempted] = useState(false)
  const [synopsisStatus, setSynopsisStatus] = useState<string>(synopsisEntry?.status || 'draft')
  const skipResetRef = useRef<string | null>(null)
  const generatedDocs = Array.from(
    documents
      .map((doc) => {
        const meta = (doc.metadata || {}) as Record<string, any>
        const idx = Number(meta.chapter_index ?? doc.order_index ?? 0)
        if (!idx) {
          return null
        }
        const status = String(meta.status || meta.chapter_status || 'draft').toLowerCase()
        const updatedAt = Date.parse(doc.updated_at || doc.created_at || '')
        return {
          index: idx,
          title: doc.title || `Chapitre ${idx}`,
          status,
          updatedAt: Number.isNaN(updatedAt) ? 0 : updatedAt,
          doc,
        }
      })
      .filter(Boolean)
      .reduce((acc, entry) => {
        if (!entry) {
          return acc
        }
        const current = acc.get(entry.index)
        if (!current) {
          acc.set(entry.index, entry)
          return acc
        }
        const currentApproved = current.status === 'approved'
        const entryApproved = entry.status === 'approved'
        if (entryApproved && !currentApproved) {
          acc.set(entry.index, entry)
          return acc
        }
        if (entryApproved === currentApproved && entry.updatedAt > current.updatedAt) {
          acc.set(entry.index, entry)
        }
        return acc
      }, new Map<number, {
        index: number
        title: string
        status: string
        updatedAt: number
        doc: Document
      }>())
      .values()
  )
  const generatedIndices = generatedDocs.map((d) => d.index)
  const nextPlanChapter = (planPayload?.chapters || [])
    .sort((a, b) => Number(a.index) - Number(b.index))
    .find((c) => !generatedIndices.includes(Number(c.index || 0)))
  const chapterOptions = [
    ...generatedDocs
      .sort((a, b) => a.index - b.index)
      .map((c) => ({ value: String(c.index), label: `${c.index}. ${c.title}` })),
    ...(nextPlanChapter
      ? [
        {
          value: String(nextPlanChapter.index),
          label: `${nextPlanChapter.index}. ${nextPlanChapter.title || `Chapitre ${nextPlanChapter.index}`} (a generer)`,
        },
      ]
      : []),
  ]
  const pendingIndex = planPayload?.chapters?.find((chapter) => chapter.status !== 'approved')?.index

  useEffect(() => {
    if (skipResetRef.current === project.id) {
      skipResetRef.current = null
      return
    }
    if (pendingIndex && !chapterIndex) {
      setChapterIndex(String(pendingIndex))
    }

    setChapterPreview(null)
    setChapterView(null)
    setShowChapter(false)
    setShowPlan(false)
    setShowSynopsis(Boolean(initialSynopsisText))
    setActionError('')

    setSynopsisLoading(false)
    setPlanLoading(false)
    setChapterGenerateLoading(false)
    setChapterViewLoading(false)
    setChapterApproveLoading(false)
    setProjectDownloadLoading(false)
    setChapterDownloadLoading(false)
    setSynopsisText(initialSynopsisText)
    setSynopsisFetchAttempted(false)
    setSynopsisStatus(synopsisEntry?.status || 'draft')
  }, [project.id, pendingIndex, planStatus, initialSynopsisText])

  useEffect(() => {
    if (!synopsisEntry || initialSynopsisText || synopsisFetchAttempted) {
      return
    }
    const run = async () => {
      await fetchSynopsis()
    }
    void run()
  }, [synopsisEntry, initialSynopsisText, synopsisFetchAttempted, project.id])

  const loadDocuments = async () => {
    try {
      const docs = await getDocuments(project.id)
      setDocuments(docs)
      return docs
    } catch (error: any) {
      console.error('Failed to load documents:', error)
      setActionError(error?.message || 'Erreur lors du chargement des documents.')
      return []
    }
  }

  useEffect(() => {
    void loadDocuments()
  }, [project.id])

  const fetchSynopsis = async (force = false) => {
    if (!force && synopsisFetchAttempted) {
      return
    }
    try {
      setSynopsisLoading(true)
      setActionError('')
      const response = await getSynopsis(project.id)
      if (response?.synopsis) {
        setSynopsisText(response.synopsis)
        setSynopsisStatus(response.status || synopsisStatus)
      }
    } catch (error: any) {
      setActionError(error?.message || 'Synopsis non disponible.')
    } finally {
      setSynopsisLoading(false)
      setSynopsisFetchAttempted(true)
    }
  }

  const handleGenerateSynopsis = async () => {
    if (conceptStatus !== 'accepted') {
      setActionError('Validez le concept avant de generer le synopsis.')
      return
    }
    try {
      setSynopsisLoading(true)
      setActionError('')
      const response = await generateSynopsis(project.id)
      if (response?.synopsis) {
        setSynopsisText(response.synopsis)
        setSynopsisStatus(response.status || 'draft')
      }
      setSynopsisFetchAttempted(true)
      await onReload()
      setShowSynopsis(true)
    } catch (error: any) {
      setActionError(error?.message || 'Erreur lors de la generation du synopsis.')
    } finally {
      setSynopsisLoading(false)
    }
  }

  const handleGeneratePlan = async () => {
    if (!canGeneratePlan) {
      setActionError('Validez le concept avant de generer le plan.')
      return
    }
    try {
      setPlanLoading(true)
      setActionError('')
      await generatePlan(project.id)
      await onReload()
      setShowPlan(true)
    } catch (error: any) {
      setActionError(error?.message || 'Erreur lors de la generation du plan.')
    } finally {
      setPlanLoading(false)
    }
  }

  const toggleCollapsed = () => {
    setIsCollapsed((prev) => !prev)
  }

  const handleCollapseKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      toggleCollapsed()
    }
  }

  const handleTitleKeyDown = (event: KeyboardEvent<HTMLHeadingElement>) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      toggleCollapsed()
    }
  }

  const handleDownloadProject = async () => {
    try {
      setProjectDownloadLoading(true)
      setActionError('')
      const { blob, filename } = await downloadProject(project.id)
      triggerDownload(blob, filename)
    } catch (error: any) {
      setActionError(error?.message || 'Erreur lors du telechargement du projet.')
    } finally {
      setProjectDownloadLoading(false)
    }
  }

  const handleOpenChapterList = () => {
    router.push(`/projects/${project.id}/chapters`)
  }

  const handleOpenChapterDetail = () => {
    const chapterNumber = Number(chapterIndex)
    if (!chapterNumber) {
      setActionError('Choisissez un numero de chapitre.')
      return
    }
    if (!selectedChapterDoc) {
      setActionError('Ce chapitre n\'est pas encore genere.')
      return
    }
    router.push(`/projects/${project.id}/chapters/${chapterNumber}`)
  }

  const handleToggleSynopsis = async () => {
    if (showSynopsis) {
      setShowSynopsis(false)
      return
    }
    if (!synopsisText) {
      await fetchSynopsis(true)
    }
    setShowSynopsis(true)
  }

  const handleSaveSynopsis = async () => {
    if (!synopsisText) {
      setActionError('Ajoutez un synopsis avant de sauvegarder.')
      return
    }
    try {
      setSynopsisLoading(true)
      setActionError('')
      const response = await updateSynopsis(project.id, { synopsis: synopsisText })
      if (response?.synopsis) {
        setSynopsisText(response.synopsis)
        setSynopsisStatus(response.status || synopsisStatus)
      }
      setSynopsisFetchAttempted(true)
      await onReload()
    } catch (error: any) {
      setActionError(error?.message || 'Erreur lors de la sauvegarde du synopsis.')
    } finally {
      setSynopsisLoading(false)
    }
  }

  const handleAcceptSynopsis = async () => {
    if (!synopsisText) {
      setActionError('Aucun synopsis a valider.')
      return
    }
    try {
      setSynopsisLoading(true)
      setActionError('')
      const response = await acceptSynopsis(project.id)
      if (response?.synopsis) {
        setSynopsisText(response.synopsis)
        setSynopsisStatus(response.status || 'accepted')
      } else {
        setSynopsisStatus('accepted')
      }
      setSynopsisFetchAttempted(true)
      await onReload()
    } catch (error: any) {
      setActionError(error?.message || 'Erreur lors de la validation du synopsis.')
    } finally {
      setSynopsisLoading(false)
    }
  }

  const handleAcceptPlan = async () => {
    if (!planPayload) {
      setActionError('Le plan narratif n\'est pas encore genere.')
      return
    }
    try {
      setPlanLoading(true)
      setActionError('')
      await acceptPlan(project.id)
      await onReload()
    } catch (error: any) {
      setActionError(error?.message || 'Erreur lors de la validation du plan.')
    } finally {
      setPlanLoading(false)
    }
  }

  const handleGenerateChapter = async () => {
    if (!canGenerateChapter) {
      setActionError('Validez le plan avant de generer un chapitre.')
      return
    }
    const chapterNumber = Number(chapterIndex)
    if (!chapterNumber) {
      setActionError('Choisissez un numero de chapitre.')
      return
    }
    try {
      setChapterGenerateLoading(true)
      setActionError('')
      const response = await generateChapter({
        project_id: project.id,
        chapter_index: chapterNumber,
        create_document: true,
        auto_approve: true,
        use_rag: true,
      })
      setChapterPreview(response)
      setChapterView(null)
      setShowChapter(true)
      setChapterIndex(String(chapterNumber))
      await loadDocuments()
      skipResetRef.current = project.id
      await onReload()
    } catch (error: any) {
      setActionError(error?.message || 'Erreur lors de la generation du chapitre.')
    } finally {
      setChapterGenerateLoading(false)
    }
  }

  const handleViewChapter = async () => {
    if (showChapter) {
      setShowChapter(false)
      return
    }
    const chapterNumber = Number(chapterIndex)
    if (!chapterNumber) {
      setActionError('Choisissez un numero de chapitre.')
      return
    }
    try {
      setChapterViewLoading(true)
      setActionError('')
      const docs = documents.length > 0 ? documents : await loadDocuments()
      const chapterDoc = docs.find((doc) => {
        const docMetadata = (doc.metadata || {}) as Record<string, any>
        const indexValue = docMetadata.chapter_index ?? doc.order_index
        return Number(indexValue) === chapterNumber
      }) || null
      setChapterView(chapterDoc)
      setChapterPreview(null)
      setShowChapter(true)
      if (!chapterDoc) {
        setActionError('Ce chapitre n\'est pas encore genere.')
        setShowChapter(false)
      }
    } catch (error: any) {
      setActionError(error?.message || 'Erreur lors du chargement du chapitre.')
    } finally {
      setChapterViewLoading(false)
    }
  }

  const handleDownloadChapter = async () => {
    if (!selectedChapterDoc?.id) {
      setActionError('Choisissez un chapitre a telecharger.')
      return
    }
    try {
      setChapterDownloadLoading(true)
      setActionError('')
      const { blob, filename } = await downloadDocument(selectedChapterDoc.id)
      triggerDownload(blob, filename)
    } catch (error: any) {
      setActionError(error?.message || 'Erreur lors du telechargement du chapitre.')
    } finally {
      setChapterDownloadLoading(false)
    }
  }

  const handleApproveChapter = async () => {
    const chapterNumber = Number(chapterIndex)
    if (!chapterNumber) {
      setActionError('Choisissez un numero de chapitre.')
      return
    }
    const currentDoc = generatedDocs.find((d) => d.index === chapterNumber)?.doc
    if (!currentDoc?.id) {
      setActionError('Ce chapitre n\'est pas encore genere.')
      return
    }
    try {
      setChapterApproveLoading(true)
      setActionError('')
      await approveChapter(currentDoc.id)
      await loadDocuments()
      await onReload()
    } catch (error: any) {
      setActionError(error?.message || 'Erreur lors de la validation du chapitre.')
    } finally {
      setChapterApproveLoading(false)
    }
  }

  const selectedChapterDoc = generatedDocs.find((d) => d.index === Number(chapterIndex))?.doc || null
  const selectedChapterStatus = (() => {
    const meta = (selectedChapterDoc?.metadata || {}) as Record<string, any>
    return (meta.status || meta.chapter_status || '').toLowerCase()
  })()
  const planChapterStatus = (planPayload?.chapters || []).find(
    (c) => Number(c.index) === Number(chapterIndex)
  )?.status?.toLowerCase()
  const isChapterApproved = selectedChapterStatus === 'approved' || planChapterStatus === 'approved'
  const activeChapterContent = chapterView?.content ?? chapterPreview?.content ?? ''
  const activeChapterTitle = chapterPreview?.chapter_title
    ?? chapterView?.title
    ?? (chapterIndex ? `Chapitre ${chapterIndex}` : 'Chapitre')
  const activeChapterId = chapterView?.id
    ?? chapterPreview?.document_id
    ?? (chapterIndex ? `${project.id}-chapter-${chapterIndex}` : project.id)
  const previewMeta = chapterPreview
    ? {
      title: chapterPreview.chapter_title || activeChapterTitle,
      wordCount: chapterPreview.word_count,
      content: chapterPreview.content ?? '',
    }
    : chapterView
      ? {
        title: chapterView.title || activeChapterTitle,
        wordCount: chapterView.word_count,
        content: chapterView.content ?? '',
      }
      : null
  const previewText = previewMeta ? getPreviewText(previewMeta.content) : ''

  if (isCollapsed) {
    return (
      <Card
        variant="elevated"
        hoverable
        role="button"
        tabIndex={0}
        aria-expanded="false"
        onClick={toggleCollapsed}
        onKeyDown={handleCollapseKeyDown}
        className="focus-visible:ring-2 focus-visible:ring-brand-500/40"
      >
        <CardHeader className="py-5">
          <div className="flex items-center justify-between gap-3">
            <CardTitle className="text-xl text-ink">{project.title}</CardTitle>
            <ChevronIcon expanded={false} />
          </div>
        </CardHeader>
      </Card>
    )
  }

  return (
    <Card variant="elevated">
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <CardTitle
              className="text-xl cursor-pointer rounded-lg px-1 -mx-1 focus-visible:ring-2 focus-visible:ring-brand-500/40 inline-flex items-center gap-2"
              role="button"
              tabIndex={0}
              aria-expanded="true"
              onClick={toggleCollapsed}
              onKeyDown={handleTitleKeyDown}
            >
              {project.title}
              <ChevronIcon expanded />
            </CardTitle>
            {project.description && (
              <CardDescription className="mt-2 line-clamp-2">
                {project.description}
              </CardDescription>
            )}
          </div>
          <div className="flex flex-col items-end gap-2">
            <Badge variant={getStatusColor(project.status)}>
              {getStatusLabel(project.status)}
            </Badge>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onDeleteRequest(project)}
            >
              Supprimer
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4 text-sm text-ink/60">
          <div className="flex flex-wrap items-center gap-4">
            {project.genre && (
              <span className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-accent-500" />
                {formatGenreLabel(project.genre)}
              </span>
            )}
            <span className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-brand-500" />
              {formatWordCount(project.current_word_count)} mots
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span>{formatDate(project.updated_at)}</span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onOpenProject(project.id)}
            >
              Consulter le concept
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleOpenChapterList}
              disabled={documents.length === 0}
            >
              Voir les chapitres
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleDownloadProject}
              isLoading={projectDownloadLoading}
            >
              Telecharger le projet
            </Button>
          </div>
        </div>

        <div className="rounded-2xl border border-stone-200 bg-stone-50/80 p-4 space-y-4">
          <div className="space-y-1">
            <p className="text-xs uppercase tracking-[0.2em] text-ink/50">Pilotage du projet</p>
            <div className="flex flex-wrap items-center gap-2 text-xs text-ink/60">
              <span>Concept: {formatConceptStatus(conceptStatus)}</span>
              <span>Plan: {planPayload ? planStatus : 'non genere'}</span>
              <span>Synopsis: {synopsisText ? (synopsisStatus || 'genere') : 'non genere'}</span>
            </div>
          </div>

          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.2em] text-ink/50">Synopsis</p>
            <div className="flex flex-wrap gap-2">
              {synopsisStatus !== 'accepted' && (
                <>
                  <Button variant="outline" onClick={handleGenerateSynopsis} isLoading={synopsisLoading}>
                    Generer le synopsis
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={handleSaveSynopsis}
                    isLoading={synopsisLoading}
                    disabled={!synopsisText}
                  >
                    Enregistrer le synopsis
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={handleAcceptSynopsis}
                    isLoading={synopsisLoading}
                    disabled={!synopsisText || synopsisStatus === 'accepted'}
                  >
                    Valider le synopsis
                  </Button>
                </>
              )}
              <Button
                variant="ghost"
                onClick={handleToggleSynopsis}
              >
                {showSynopsis ? 'Masquer le synopsis' : 'Consulter le synopsis'}
              </Button>
            </div>
            {showSynopsis && synopsisText && (
              <Textarea
                label="Synopsis"
                value={synopsisText}
                onChange={(event) => setSynopsisText(event.target.value)}
                rows={6}
                readOnly={synopsisStatus === 'accepted'}
              />
            )}
          </div>

          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.2em] text-ink/50">Plan narratif</p>
            <div className="flex flex-wrap gap-2">
              {planStatus !== 'accepted' && (
                <>
                  <Button
                    variant="outline"
                    onClick={handleGeneratePlan}
                    isLoading={planLoading}
                    disabled={!canGeneratePlan}
                  >
                    Generer le plan narratif
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={handleAcceptPlan}
                    isLoading={planLoading}
                    disabled={!planPayload || planStatus === 'accepted'}
                  >
                    Valider le plan
                  </Button>
                </>
              )}
              <Button
                variant="ghost"
                onClick={() => setShowPlan((prev) => !prev)}
                disabled={!planPayload}
              >
                {showPlan ? 'Masquer le plan' : 'Consulter le plan'}
              </Button>
            </div>
            {showPlan && planPayload && (
              <div className="space-y-3">
                <Textarea
                  label="Synopsis global"
                  value={planPayload.global_summary}
                  readOnly
                  rows={4}
                />
                <div className="rounded-2xl border border-stone-200 bg-stone-50 p-3">
                  <p className="text-sm font-semibold text-ink">Arcs narratifs</p>
                  <div className="mt-2 space-y-2 text-sm text-ink/70">
                    {planPayload.arcs.map((arc) => (
                      <div key={arc.id} className="rounded-xl border border-stone-100 bg-white p-3">
                        <p className="font-semibold text-ink">{arc.title}</p>
                        <p>{arc.summary}</p>
                        <p className="text-xs text-ink/50">Emotion: {arc.target_emotion}</p>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="rounded-2xl border border-stone-200 bg-stone-50 p-3">
                  <p className="text-sm font-semibold text-ink">Chapitres</p>
                  <div className="mt-2 grid gap-2 text-xs text-ink/70">
                    {planPayload.chapters.map((chapter) => {
                      const chapterDoc = documents.find((doc) => {
                        const meta = (doc.metadata || {}) as Record<string, any>
                        return Number(meta.chapter_index ?? doc.order_index) === chapter.index
                      })

                      const audioProgress = chapterDoc?.id
                        ? getProgressPercent(chapterDoc.id, chapterDoc.content || '')
                        : 0

                      return (
                        <div key={chapter.index} className="rounded-lg border border-stone-100 bg-white p-2">
                          <div className="flex items-center justify-between">
                            <span>{chapter.index}. {chapter.title}</span>
                            <div className="flex items-center gap-2">
                              {chapterDoc && (
                                <button
                                  type="button"
                                  onClick={() => router.push(`/projects/${project.id}/chapters/${chapter.index}`)}
                                  className="rounded-full border border-stone-200 bg-white p-1 text-ink/60 transition hover:text-ink"
                                  aria-label={`Lire et ecouter le chapitre ${chapter.index}`}
                                  title="Lire et ecouter"
                                >
                                  <SpeakerIcon className="h-3.5 w-3.5" />
                                </button>
                              )}
                              {audioProgress > 0 && (
                                <span
                                  className={cn(
                                    'rounded-full px-2 py-0.5 text-xs',
                                    audioProgress >= 95
                                      ? 'bg-emerald-50 text-emerald-700'
                                      : 'bg-brand-50 text-brand-700'
                                  )}
                                >
                                  Audio {audioProgress >= 95 ? 'OK' : `${Math.round(audioProgress)}%`}
                                </span>
                              )}
                              <span className="uppercase text-ink/40">{chapter.status || 'planned'}</span>
                            </div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.2em] text-ink/50">Chapitres</p>
            <p className="text-xs text-ink/50">
              Selectionnez un chapitre pour le lire et l'ecouter avec la synthese vocale.
            </p>
            <Select
              label="Numero du chapitre"
              value={chapterIndex}
              onChange={(event) => {
                setChapterIndex(event.target.value)
                setChapterPreview(null)
                setChapterView(null)
                setShowChapter(false)
              }}
              options={[{ value: '', label: 'Choisir un chapitre' }, ...chapterOptions]}
            />
            <div className="flex flex-wrap gap-2">
              {!isChapterApproved && (
                <Button
                  variant="outline"
                  onClick={handleGenerateChapter}
                  isLoading={chapterGenerateLoading}
                  disabled={!canGenerateChapter}
                >
                  Generer le chapitre
                </Button>
              )}
              {selectedChapterDoc && (
                <Button
                  variant="primary"
                  onClick={handleOpenChapterDetail}
                >
                  <SpeakerIcon className="h-4 w-4 text-white" />
                  Lire & Ecouter
                </Button>
              )}
              <Button
                variant="ghost"
                onClick={handleViewChapter}
                isLoading={chapterViewLoading}
                disabled={!planPayload || (!selectedChapterDoc && chapterOptions.length === 0)}
              >
                {showChapter ? 'Masquer l\'apercu' : 'Apercu rapide'}
              </Button>
              <Button
                variant="ghost"
                onClick={handleDownloadChapter}
                isLoading={chapterDownloadLoading}
                disabled={!selectedChapterDoc}
              >
                Telecharger le chapitre
              </Button>
              {selectedChapterDoc && !isChapterApproved && (
                <Button
                  variant="ghost"
                  onClick={handleApproveChapter}
                  isLoading={chapterApproveLoading}
                >
                  Valider le chapitre
                </Button>
              )}
            </div>
            {showChapter && activeChapterContent && (
              <AudioErrorBoundary>
                <LazyChapterAudioPlayer
                  chapterId={activeChapterId}
                  chapterTitle={activeChapterTitle}
                  content={activeChapterContent}
                  defaultExpanded={true}
                  className="mb-3"
                />
              </AudioErrorBoundary>
            )}
            {showChapter && previewMeta && (
              <div className="rounded-2xl border border-stone-200 bg-white p-3">
                <div className="flex items-center justify-between text-xs text-ink/60">
                  <span>{previewMeta.title}</span>
                  {typeof previewMeta.wordCount === 'number' && (
                    <span>{previewMeta.wordCount} mots</span>
                  )}
                </div>
                <div className="mt-2 text-sm text-ink/80">
                  {previewText || 'Aucun contenu a afficher.'}
                </div>
                <div className="mt-3 flex items-center justify-between text-xs text-ink/50">
                  <span>Apercu limite a 200 mots.</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleOpenChapterDetail}
                    disabled={!selectedChapterDoc}
                  >
                    Lire la suite
                  </Button>
                </div>
              </div>
            )}
          </div>

          {actionError && (
            <div className="rounded-2xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              {actionError}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
