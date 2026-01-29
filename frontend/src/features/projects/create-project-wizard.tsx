/**
 * Wizard for creating a new NovellaForge project
 */

'use client'

import * as React from 'react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { acceptConcept, createProject, generateConceptProposal } from '@/lib/api-extended'
import { Genre, type ConceptPayload, type ProjectCreate } from '@/types'

interface CreateProjectWizardProps {
  open: boolean
  onClose: () => void
  onSuccess: (projectId: string) => void
}

const GENRE_OPTIONS = [
  { value: '', label: 'Selectionnez un genre principal' },
  { value: Genre.WEREWOLF, label: 'Loup-garou' },
  { value: Genre.BILLIONAIRE, label: 'Milliardaire' },
  { value: Genre.MAFIA, label: 'Mafia' },
  { value: Genre.FANTASY, label: 'Fantasy' },
  { value: Genre.VENGEANCE, label: 'Vengeance' },
  { value: Genre.ROMANCE, label: 'Romance' },
  { value: Genre.THRILLER, label: 'Thriller' },
  { value: Genre.OTHER, label: 'Autre' },
]

export function CreateProjectWizard({ open, onClose, onSuccess }: CreateProjectWizardProps) {
  const [isGenerating, setIsGenerating] = React.useState(false)
  const [isCreating, setIsCreating] = React.useState(false)
  const [error, setError] = React.useState<string>('')
  const [step, setStep] = React.useState<'genre' | 'concept'>('genre')
  const [formData, setFormData] = React.useState<ProjectCreate>({
    genre: '' as Genre,
  })
  const [proposal, setProposal] = React.useState<ConceptPayload | null>(null)
  const [notes, setNotes] = React.useState('')

  const resetState = () => {
    setError('')
    setStep('genre')
    setFormData({ genre: '' as Genre })
    setProposal(null)
    setNotes('')
    setIsGenerating(false)
    setIsCreating(false)
  }

  const handleClose = () => {
    resetState()
    onClose()
  }

  const updateProposal = (patch: Partial<ConceptPayload>) => {
    const current = proposal || {
      title: '',
      premise: '',
      tone: '',
      tropes: [],
      emotional_orientation: '',
    }
    setProposal({ ...current, ...patch })
  }

  const getGenreLabel = () => {
    const match = GENRE_OPTIONS.find((option) => option.value === formData.genre)
    return match?.label || 'Projet'
  }

  const handleGenerateProposal = async () => {
    if (!formData.genre) {
      setError('Veuillez choisir un genre')
      return
    }

    setIsGenerating(true)
    setError('')

    try {
      const response = await generateConceptProposal(formData.genre, notes || undefined)
      setProposal(response.concept)
      setStep('concept')
    } catch (err: any) {
      setError(err.message || 'Erreur lors de la generation du concept')
    } finally {
      setIsGenerating(false)
    }
  }

  const handleCreateProject = async () => {
    if (!formData.genre || !proposal) {
      setError('Veuillez generer un concept avant de continuer')
      return
    }

    setIsCreating(true)
    setError('')

    try {
      const title = proposal.title?.trim() || `Projet ${getGenreLabel()} sans titre`
      const project = await createProject({
        genre: formData.genre,
        title,
        description: proposal.premise || undefined,
      })
      await acceptConcept(project.id, proposal)
      onSuccess(project.id)
      handleClose()
    } catch (err: any) {
      setError(err.message || 'Erreur lors de la creation du projet')
    } finally {
      setIsCreating(false)
    }
  }

  return (
    <Dialog open={open} onClose={handleClose} size="lg">
      <DialogHeader>
        <DialogTitle>Creer un nouveau projet</DialogTitle>
      </DialogHeader>

      <DialogContent>
        {step === 'genre' ? (
          <div className="space-y-6">
            <div className="rounded-2xl border border-brand-200 bg-brand-50 p-4 text-sm text-brand-800">
              Choisissez un genre principal. NovellaForge proposera automatiquement le titre, la premisse,
              le ton, l'orientation emotionnelle et les tropes.
            </div>

            <Select
              label="Genre principal"
              value={formData.genre || ''}
              onChange={(e) => setFormData({ ...formData, genre: e.target.value as Genre })}
              options={GENRE_OPTIONS}
            />

            {error && (
              <div className="rounded-2xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                {error}
              </div>
            )}

            <div className="flex justify-end">
              <Button variant="primary" onClick={handleGenerateProposal} isLoading={isGenerating}>
                Generer une proposition
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-5">
            <div className="rounded-2xl border border-stone-200 bg-stone-50 p-4 text-sm text-ink/70">
              Ajustez la proposition si besoin, puis validez pour creer le projet.
            </div>

            <Input
              label="Titre propose"
              value={proposal?.title || ''}
              onChange={(e) => updateProposal({ title: e.target.value })}
              placeholder="Titre de projet"
            />

            <Input
              label="Premisse"
              value={proposal?.premise || ''}
              onChange={(e) => updateProposal({ premise: e.target.value })}
              placeholder="Une heroine est liee a une meute interdite..."
            />

            <Input
              label="Ton"
              value={proposal?.tone || ''}
              onChange={(e) => updateProposal({ tone: e.target.value })}
              placeholder="Emotionnel, tendu, addictif"
            />

            <Input
              label="Orientation emotionnelle"
              value={proposal?.emotional_orientation || ''}
              onChange={(e) => updateProposal({ emotional_orientation: e.target.value })}
              placeholder="Passion, vengeance, tension"
            />

            <Textarea
              label="Tropes (separes par des virgules)"
              value={proposal?.tropes?.join(', ') || ''}
              onChange={(e) =>
                updateProposal({
                  tropes: e.target.value
                    .split(',')
                    .map((item) => item.trim())
                    .filter(Boolean),
                })
              }
              rows={3}
            />

            <Textarea
              label="Vos propositions pour une nouvelle version"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              placeholder="Ajoutez des precisions pour regenerer une nouvelle proposition."
            />

            {error && (
              <div className="rounded-2xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                {error}
              </div>
            )}

            <div className="flex flex-wrap justify-between gap-2">
              <Button variant="ghost" onClick={() => setStep('genre')}>
                Retour
              </Button>
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" onClick={handleGenerateProposal} isLoading={isGenerating}>
                  Regenerer
                </Button>
                <Button
                  variant="primary"
                  onClick={handleCreateProject}
                  isLoading={isCreating}
                  disabled={!proposal}
                >
                  Creer le projet
                </Button>
              </div>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
