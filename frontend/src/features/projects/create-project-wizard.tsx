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
import { GENRE_SUGGESTIONS, NOVEL_SIZE_PRESETS, type ConceptPayload, type ProjectCreate } from '@/types'

interface CreateProjectWizardProps {
  open: boolean
  onClose: () => void
  onSuccess: (projectId: string) => void
}



export function CreateProjectWizard({ open, onClose, onSuccess }: CreateProjectWizardProps) {
  const [isGenerating, setIsGenerating] = React.useState(false)
  const [isCreating, setIsCreating] = React.useState(false)
  const [error, setError] = React.useState<string>('')
  const [step, setStep] = React.useState<'genre' | 'concept'>('genre')
  const [formData, setFormData] = React.useState<ProjectCreate>({
    genre: '',
    generation_mode: 'standard',
  })
  const [proposal, setProposal] = React.useState<ConceptPayload | null>(null)
  const [notes, setNotes] = React.useState('')

  const resetState = () => {
    setError('')
    setStep('genre')
    setFormData({ genre: '', generation_mode: 'standard' })
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
    const match = GENRE_SUGGESTIONS.find((option) => option.value === formData.genre)
    return match ? match.label : (formData.genre || 'Projet')
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
        target_word_count: formData.target_word_count,
        target_chapter_count: formData.target_chapter_count,
        target_chapter_length: formData.target_chapter_length,
        generation_mode: formData.generation_mode,
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

            <div>
              <Input
                label="Genre principal (ou saisie libre)"
                value={formData.genre || ''}
                onChange={(e) => setFormData({ ...formData, genre: e.target.value })}
                placeholder="Ex: Fantasy, Cyberpunk..."
                list="genre-suggestions"
              />
              <datalist id="genre-suggestions">
                {GENRE_SUGGESTIONS.map((g) => (
                  <option key={g.value} value={g.value}>
                    {g.label}
                  </option>
                ))}
              </datalist>
            </div>

            <Select
              label="Taille de l'œuvre"
              value={formData.target_word_count?.toString() || ''}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  target_word_count: e.target.value ? parseInt(e.target.value, 10) : undefined,
                })
              }
              options={NOVEL_SIZE_PRESETS}
            />

            <div className="grid grid-cols-2 gap-4">
              <Input
                label="Nombre de chapitres cible"
                type="number"
                value={formData.target_chapter_count?.toString() || ''}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    target_chapter_count: e.target.value ? parseInt(e.target.value, 10) : undefined,
                  })
                }
                placeholder="Ex: 30"
              />
              <Select
                label="Taille moyenne d'un chapitre"
                value={formData.target_chapter_length?.toString() || ''}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    target_chapter_length: e.target.value ? parseInt(e.target.value, 10) : undefined,
                  })
                }
                options={[
                  { value: '', label: 'Non défini' },
                  { value: '1500', label: 'Court (~1500 mots)' },
                  { value: '3000', label: 'Moyen (~3000 mots)' },
                  { value: '5000', label: 'Long (~5000 mots)' },
                ]}
              />
            </div>

            <Select
              label="Mode de création"
              value={formData.generation_mode || 'standard'}
              onChange={(e) => setFormData({ ...formData, generation_mode: e.target.value })}
              options={[
                { value: 'standard', label: 'Standard (Planification complète)' },
                { value: 'lazy', label: 'Lazy (Lecture continue)' },
              ]}
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
