'use client'

import { useState, FormEvent } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { register, setAuthToken } from '@/lib/api'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'

export default function RegisterPage() {
  const router = useRouter()
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    full_name: '',
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    })
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')

    if (formData.password !== formData.confirmPassword) {
      setError('Les mots de passe ne correspondent pas')
      return
    }

    if (formData.password.length < 8) {
      setError('Le mot de passe doit contenir au moins 8 caracteres')
      return
    }

    setLoading(true)

    try {
      const response = await register({
        email: formData.email,
        password: formData.password,
        full_name: formData.full_name,
      })
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
        <div className="grid w-full gap-12 lg:grid-cols-[0.95fr_1.05fr]">
          <div className="glass-panel rounded-3xl p-8">
            <div className="mb-6">
              <h2 className="font-serif text-2xl text-ink">Creer un compte</h2>
              <p className="text-sm text-ink/60">
                Lancez votre premier projet et testez le pipeline complet.
              </p>
            </div>

            <form className="space-y-5" onSubmit={handleSubmit}>
              {error && (
                <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {error}
                </div>
              )}

              <Input
                id="full_name"
                name="full_name"
                type="text"
                label="Nom complet"
                required
                value={formData.full_name}
                onChange={handleChange}
                disabled={loading}
              />

              <Input
                id="email"
                name="email"
                type="email"
                label="Adresse email"
                autoComplete="email"
                required
                value={formData.email}
                onChange={handleChange}
                disabled={loading}
              />

              <Input
                id="password"
                name="password"
                type="password"
                label="Mot de passe"
                autoComplete="new-password"
                required
                value={formData.password}
                onChange={handleChange}
                disabled={loading}
              />

              <Input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                label="Confirmer le mot de passe"
                autoComplete="new-password"
                required
                value={formData.confirmPassword}
                onChange={handleChange}
                disabled={loading}
              />

              <Button type="submit" variant="primary" size="lg" isLoading={loading} className="w-full">
                {loading ? 'Inscription...' : "S'inscrire"}
              </Button>

              <p className="text-center text-sm text-ink/60">
                Deja un compte ?{' '}
                <Link href="/auth/login" className="font-medium text-brand-700 hover:text-brand-800">
                  Connectez-vous
                </Link>
              </p>
            </form>
          </div>

          <div className="space-y-6">
            <div className="inline-flex items-center gap-3 rounded-full bg-white/70 px-4 py-2 text-xs font-semibold uppercase tracking-[0.25em] text-brand-700">
              Lancement
            </div>
            <h1 className="font-serif text-4xl leading-tight text-ink md:text-5xl">
              Donnez un cadre solide a votre roman.
            </h1>
            <p className="text-base text-ink/70">
              NovellaForge structure le contexte, alimente le RAG et genere chaque chapitre
              avec des contraintes explicites.
            </p>
            <div className="space-y-4">
              {[
                { title: 'Plan structurant', body: 'Definissez vos objectifs et vos contraintes.' },
                { title: 'Execution autonome', body: 'Generation par chapitre, contexte recalcule.' },
                { title: 'Qualite suivie', body: 'Longueur, structure et mentions verifiees.' },
              ].map((item) => (
                <div key={item.title} className="rounded-2xl border border-stone-200 bg-white/80 p-5">
                  <h3 className="font-serif text-lg text-ink">{item.title}</h3>
                  <p className="text-sm text-ink/70">{item.body}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
