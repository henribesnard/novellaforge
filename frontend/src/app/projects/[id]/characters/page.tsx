'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { getCharacters } from '@/lib/api-extended'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { Character } from '@/types'

export default function CharactersPage() {
  const params = useParams()
  const projectId = params?.id as string
  const [characters, setCharacters] = useState<Character[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const load = async () => {
      if (!projectId) return
      try {
        setLoading(true)
        const data = await getCharacters(projectId)
        setCharacters(data)
      } catch (err: any) {
        setError(err?.message || 'Erreur lors du chargement des personnages.')
      } finally {
        setLoading(false)
      }
    }

    void load()
  }, [projectId])

  if (loading) {
    return <p className="text-sm text-ink/60">Chargement des personnages...</p>
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
        <CardTitle>Personnages</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {characters.length === 0 ? (
          <p className="text-sm text-ink/60">Aucun personnage trouve.</p>
        ) : (
          <div className="grid gap-3">
            {characters.map((character) => (
              <div key={character.id} className="rounded-xl border border-stone-200 bg-white p-4">
                <p className="text-sm font-semibold text-ink">{character.name}</p>
                {character.role && (
                  <p className="text-xs uppercase text-ink/40">{character.role}</p>
                )}
                {character.description && (
                  <p className="mt-2 text-sm text-ink/70">{character.description}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
