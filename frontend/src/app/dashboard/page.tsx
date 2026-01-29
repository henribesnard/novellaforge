/**
 * Modern dashboard with project management
 */

'use client'

import { Suspense, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { getAuthToken, removeAuthToken } from '@/lib/api'
import { deleteProject, getProjects } from '@/lib/api-extended'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogContent,
  DialogFooter,
} from '@/components/ui/dialog'
import { DashboardStats } from '@/features/dashboard'
import { CreateProjectWizard, ProjectList } from '@/features/projects'
import type { Project } from '@/types'

function DashboardContent() {
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
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 animate-spin rounded-full border-b-2 border-brand-700"></div>
          <p className="mt-4 text-ink/60">Chargement...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <DashboardStats projects={projects} />

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
          <ProjectList
            projects={projects}
            onReload={() => loadProjects(true)}
            onOpenProject={(projectId) => router.push(`/projects/${projectId}`)}
            onDeleteRequest={handleOpenDelete}
          />
        )}
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

export default function DashboardPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <div className="text-center">
            <div className="mx-auto h-12 w-12 animate-spin rounded-full border-b-2 border-brand-700"></div>
            <p className="mt-4 text-ink/60">Chargement...</p>
          </div>
        </div>
      }
    >
      <DashboardContent />
    </Suspense>
  )
}
