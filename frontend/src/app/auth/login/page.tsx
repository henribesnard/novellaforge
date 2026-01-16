'use client'

import { useState, FormEvent } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { login, setAuthToken } from '@/lib/api'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const response = await login({ email, password })
      setAuthToken(response.access_token)
      router.push('/dashboard')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Une erreur est survenue')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-atlas">
      <div className="mx-auto flex min-h-screen max-w-6xl items-center px-6 py-12">
        <div className="grid w-full gap-12 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-6">
            <div className="inline-flex items-center gap-3 rounded-full bg-white/70 px-4 py-2 text-xs font-semibold uppercase tracking-[0.25em] text-brand-700">
              NovellaForge
            </div>
            <h1 className="font-serif text-4xl leading-tight text-ink md:text-5xl">
              Retrouvez votre atelier d'ecriture.
            </h1>
            <p className="text-base text-ink/70">
              Chaque session rehydrate le contexte, les contraintes et les documents
              pour reprendre la narration sans friction.
            </p>
            <div className="grid gap-4 sm:grid-cols-2">
              {[
                'Contexte autonome',
                'RAG vectoriel',
                'Planification des chapitres',
                'Generation guidee',
              ].map((item) => (
                <div key={item} className="flex items-center gap-3 rounded-2xl bg-white/80 p-4 ring-1 ring-stone-200">
                  <div className="h-9 w-9 rounded-full bg-brand-100 text-brand-700 flex items-center justify-center">
                    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <span className="text-sm font-medium text-ink">{item}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="glass-panel rounded-3xl p-8">
            <div className="mb-6">
              <h2 className="font-serif text-2xl text-ink">Connexion</h2>
              <p className="text-sm text-ink/60">Accedez a votre espace de creation.</p>
            </div>

            <form className="space-y-5" onSubmit={handleSubmit}>
              {error && (
                <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {error}
                </div>
              )}

              <Input
                id="email"
                name="email"
                type="email"
                label="Adresse email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={loading}
              />

              <Input
                id="password"
                name="password"
                type="password"
                label="Mot de passe"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading}
              />

              <Button type="submit" variant="primary" size="lg" isLoading={loading} className="w-full">
                {loading ? 'Connexion...' : 'Se connecter'}
              </Button>

              <p className="text-center text-sm text-ink/60">
                Pas encore de compte ?{' '}
                <Link href="/auth/register" className="font-medium text-brand-700 hover:text-brand-800">
                  Inscrivez-vous
                </Link>
              </p>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}
