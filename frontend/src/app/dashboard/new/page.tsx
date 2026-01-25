/**
 * Modern dashboard with project management
 */

'use client'

import { Suspense, useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { getAuthToken, removeAuthToken } from '@/lib/api'
import {
  acceptPlan,
  deleteProject,
  downloadDocument,
  downloadProject,
  generateChapter,
  generatePlan,
  generateSynopsis,
  getDocuments,
  getProjects,
  getSynopsis,
  updateSynopsis,
  acceptSynopsis,
  approveChapter,
} from '@/lib/api-extended'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Select } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogContent,
  DialogFooter,
} from '@/components/ui/dialog'
import { CreateProjectWizard } from '@/components/projects/create-project-wizard'
import { formatDate, formatGenreLabel, formatWordCount } from '@/lib/utils'
import type { ChapterGenerationResponse, Document, PlanPayload, Project } from '@/types'

type ProjectCardProps = {
  project: Project
  onReload: () => Promise<void>
  onOpenProject: (projectId: string) => void
  onDeleteRequest: (project: Project) => void
}

const getStatusColor = (status: string) => {
  switch (status) {
    case 'draft':
      return 'default'
    case 'in_progress':
      return 'primary'
    case 'completed':
      return 'success'
    case 'archived':
      return 'warning'
    default:
      return 'default'
  }
}

const getStatusLabel = (status: string) => {
  switch (status) {
    case 'draft':
      return 'Brouillon'
    case 'in_progress':
      return 'En cours'
    case 'completed':
      return 'Termine'
    case 'archived':
      return 'Archive'
    case 'accepted':
      return 'Valide'
    default:
      return status
  }
}

const formatConceptStatus = (status?: string) => {
  if (!status) return 'non genere'
  if (status === 'accepted') return 'valide'
  if (status === 'draft') return 'brouillon'
  return status
}

const ChevronIcon = ({ expanded }: { expanded: boolean }) => (
  <svg
    aria-hidden="true"
    className={`h-4 w-4 text-ink/50 transition-transform ${expanded ? 'rotate-180' : ''}`}
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

function ProjectCard({ project, onReload, onOpenProject, onDeleteRequest }: ProjectCardProps) {
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
    // Only update index if we don't have one or if pendingIndex changed significantly
    if (pendingIndex && !chapterIndex) {
      setChapterIndex(String(pendingIndex))
    }

    // Do NOT reset documents here. They are loaded independently and should persist.
    // setDocuments([]) 

    // Only reset detailed views, but keep main context
    setChapterPreview(null)
    setChapterView(null)
    setShowChapter(false)
    setShowPlan(false)
    setShowSynopsis(Boolean(initialSynopsisText))
    setActionError('')

    // Reset all loading states when project changes
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
                    {planPayload.chapters.map((chapter) => (
                      <div key={chapter.index} className="rounded-lg border border-stone-100 bg-white p-2">
                        <div className="flex items-center justify-between">
                          <span>{chapter.index}. {chapter.title}</span>
                          <span className="uppercase text-ink/40">{chapter.status || 'planned'}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.2em] text-ink/50">Chapitres</p>
            <Select
              label="Numero du chapitre"
              value={chapterIndex}
              onChange={(event) => {
                setChapterIndex(event.target.value)
                // Reset chapter display states when changing selection
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
              <Button
                variant="ghost"
                onClick={handleViewChapter}
                isLoading={chapterViewLoading}
                disabled={!planPayload || (!selectedChapterDoc && chapterOptions.length === 0)}
              >
                {showChapter ? 'Masquer le chapitre' : 'Consulter le chapitre'}
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
            {showChapter && chapterPreview && (
              <div className="rounded-2xl border border-stone-200 bg-white p-3">
                <div className="flex items-center justify-between text-xs text-ink/60">
                  <span>{chapterPreview.chapter_title}</span>
                  <span>{chapterPreview.word_count} mots</span>
                </div>
                <div className="mt-2 whitespace-pre-wrap text-sm text-ink/80">
                  {chapterPreview.content}
                </div>
              </div>
            )}
            {showChapter && chapterView && (
              <div className="rounded-2xl border border-stone-200 bg-white p-3">
                <div className="flex items-center justify-between text-xs text-ink/60">
                  <span>{chapterView.title}</span>
                  <span>{chapterView.word_count} mots</span>
                </div>
                <div className="mt-2 whitespace-pre-wrap text-sm text-ink/80">
                  {chapterView.content}
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

function ModernDashboardContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [loading, setLoading] = useState(true)
  const [projects, setProjects] = useState<Project[]>([])
  const [showCreateWizard, setShowCreateWizard] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<Project | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState('')
  const [deleteError, setDeleteError] = useState('')
  const [deleteLoading, setDeleteLoading] = useState(false)

  useEffect(() => {
    const token = getAuthToken()
    if (!token) {
      router.push('/auth/login')
    } else {
      loadProjects()
    }
  }, [router])

  useEffect(() => {
    if (searchParams.get('create') === '1') {
      setShowCreateWizard(true)
    }
  }, [searchParams])

  const loadProjects = async (silent = false) => {
    try {
      if (!silent) {
        setLoading(true)
      }
      const result = await getProjects()
      setProjects(result.projects)
    } catch (error) {
      if (error instanceof Error && /validate credentials|not authenticated|401/i.test(error.message)) {
        removeAuthToken()
        router.push('/auth/login')
        return
      }
      console.error('Failed to load projects:', error)
    } finally {
      if (!silent) {
        setLoading(false)
      }
    }
  }

  const handleLogout = () => {
    removeAuthToken()
    router.push('/')
  }

  const handleProjectCreated = (projectId: string) => {
    loadProjects(true)
    router.push(`/projects/${projectId}`)
  }

  const handleOpenDelete = (project: Project) => {
    setDeleteTarget(project)
    setDeleteConfirm('')
    setDeleteError('')
  }

  const handleCloseDelete = () => {
    setDeleteTarget(null)
    setDeleteConfirm('')
    setDeleteError('')
    setDeleteLoading(false)
  }

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return
    const trimmed = deleteConfirm.trim()
    if (trimmed !== deleteTarget.title) {
      setDeleteError('Le nom du projet ne correspond pas.')
      return
    }
    try {
      setDeleteLoading(true)
      setDeleteError('')
      await deleteProject(deleteTarget.id, trimmed)
      await loadProjects(true)
      handleCloseDelete()
    } catch (error: any) {
      setDeleteError(error?.message || 'Erreur lors de la suppression du projet.')
    } finally {
      setDeleteLoading(false)
    }
  }

  const deleteMatch = deleteTarget ? deleteConfirm.trim() === deleteTarget.title : false

  if (loading) {
    return (
      <div className="min-h-screen bg-atlas flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-700 mx-auto"></div>
          <p className="mt-4 text-ink/60">Chargement...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-atlas">
      <header className="sticky top-0 z-20 border-b border-stone-200 bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-brand-700 text-white text-lg font-semibold">
              N
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.25em] text-brand-700">NovellaForge</p>
              <p className="text-xs text-ink/60">Assistant d'ecriture litteraire</p>
            </div>
          </div>
          <Button variant="outline" onClick={handleLogout}>
            Deconnexion
          </Button>
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 gap-6 md:grid-cols-4">
          <Card variant="elevated">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-ink/60">Projets</p>
                  <p className="text-3xl font-semibold text-ink">{projects.length}</p>
                </div>
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-100 text-brand-700">
                  <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 7h6l2 2h10v10H3z" />
                  </svg>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card variant="elevated">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-ink/60">Mots ecrits</p>
                  <p className="text-3xl font-semibold text-ink">
                    {formatWordCount(projects.reduce((sum, p) => sum + p.current_word_count, 0))}
                  </p>
                </div>
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-accent-100 text-accent-700">
                  <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4 7h16M4 12h10M4 17h7" />
                  </svg>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card variant="elevated">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-ink/60">En cours</p>
                  <p className="text-3xl font-semibold text-ink">
                    {projects.filter((p) => p.status === 'in_progress').length}
                  </p>
                </div>
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-stone-200 text-ink">
                  <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3" />
                    <circle cx="12" cy="12" r="8" />
                  </svg>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card variant="elevated">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-ink/60">Termines</p>
                  <p className="text-3xl font-semibold text-ink">
                    {projects.filter((p) => p.status === 'completed').length}
                  </p>
                </div>
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-700">
                  <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="mt-10 space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="font-serif text-2xl text-ink">Mes projets</h2>
            <Button variant="primary" onClick={() => setShowCreateWizard(true)}>
              Nouveau projet
            </Button>
          </div>

          {projects.length === 0 ? (
            <Card variant="outlined" className="p-10 text-center">
              <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-100 text-brand-700">
                <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 5v14M5 12h14" />
                </svg>
              </div>
              <h3 className="font-serif text-xl text-ink">Aucun projet pour le moment</h3>
              <p className="mt-2 text-sm text-ink/60">
                Creez votre premier projet et commencez a ecrire avec NovellaForge.
              </p>
              <Button variant="primary" className="mt-6" onClick={() => setShowCreateWizard(true)}>
                Creer mon premier projet
              </Button>
            </Card>
          ) : (
            <div className="space-y-6">
              {projects.map((project) => (
                <ProjectCard
                  key={project.id}
                  project={project}
                  onReload={() => loadProjects(true)}
                  onOpenProject={(projectId) => router.push(`/projects/${projectId}`)}
                  onDeleteRequest={handleOpenDelete}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      <CreateProjectWizard
        open={showCreateWizard}
        onClose={() => setShowCreateWizard(false)}
        onSuccess={handleProjectCreated}
      />

      <Dialog open={!!deleteTarget} onClose={handleCloseDelete} size="sm">
        <DialogHeader>
          <DialogTitle>Supprimer le projet</DialogTitle>
          <DialogDescription>
            Cette action est definitive. Tapez le nom exact du projet pour confirmer.
          </DialogDescription>
        </DialogHeader>
        <DialogContent className="space-y-4">
          <Input
            label="Nom du projet"
            value={deleteConfirm}
            onChange={(event) => setDeleteConfirm(event.target.value)}
            placeholder={deleteTarget?.title || 'Nom du projet'}
          />
          {deleteTarget && (
            <p className="text-xs text-ink/60">Nom attendu: {deleteTarget.title}</p>
          )}
          {deleteError && (
            <div className="rounded-2xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              {deleteError}
            </div>
          )}
        </DialogContent>
        <DialogFooter>
          <Button variant="ghost" onClick={handleCloseDelete}>
            Annuler
          </Button>
          <Button
            variant="danger"
            onClick={handleConfirmDelete}
            isLoading={deleteLoading}
            disabled={!deleteMatch}
          >
            Supprimer
          </Button>
        </DialogFooter>
      </Dialog>
    </div>
  )
}

// Wrapper with Suspense for useSearchParams (required by Next.js 15)
export default function ModernDashboardPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-atlas flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-700 mx-auto"></div>
            <p className="mt-4 text-ink/60">Chargement...</p>
          </div>
        </div>
      }
    >
      <ModernDashboardContent />
    </Suspense>
  )
}
