'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { getAuthToken } from '@/lib/api'

export default function Home() {
  const [isAuthed, setIsAuthed] = useState<boolean | null>(null)

  useEffect(() => {
    setIsAuthed(Boolean(getAuthToken()))
  }, [])

  const showExample = isAuthed === false
  const showAuthed = isAuthed === true

  return (
    <main className="min-h-screen bg-atlas text-ink">
      <div className="mx-auto flex min-h-screen max-w-6xl flex-col px-6 py-10 lg:py-16">
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-brand-700 text-white text-lg font-semibold">
              N
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-brand-700">NovellaForge Studio</p>
              <p className="text-sm text-ink/70">Atelier narratif autonome</p>
            </div>
          </div>
          {isAuthed !== null && (
            <div className="hidden items-center gap-3 sm:flex">
              {showAuthed ? (
                <>
                  <Link
                    href="/dashboard"
                    className="rounded-full border border-stone-300 px-4 py-2 text-sm text-ink/80 transition hover:bg-white/70"
                  >
                    Tableau de bord
                  </Link>
                  <Link
                    href="/dashboard?create=1"
                    className="rounded-full bg-brand-700 px-4 py-2 text-sm text-white shadow-soft transition hover:bg-brand-800"
                  >
                    Creer un projet
                  </Link>
                </>
              ) : (
                <>
                  <Link
                    href="/auth/login"
                    className="rounded-full border border-stone-300 px-4 py-2 text-sm text-ink/80 transition hover:bg-white/70"
                  >
                    Connexion
                  </Link>
                  <Link
                    href="/auth/register"
                    className="rounded-full bg-brand-700 px-4 py-2 text-sm text-white shadow-soft transition hover:bg-brand-800"
                  >
                    Commencer
                  </Link>
                </>
              )}
            </div>
          )}
        </header>

        <section className="mt-14 grid items-center gap-12 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-6">
            <span className="inline-flex w-fit items-center gap-2 rounded-full bg-white/70 px-3 py-1 text-xs font-semibold text-brand-700 ring-1 ring-brand-200">
              Pipeline editorial complet
            </span>
            <h1 className="font-serif text-4xl leading-tight md:text-5xl lg:text-6xl animate-rise">
              Ecrire un roman entier, chapitre par chapitre, sans perdre le contexte.
            </h1>
            <p className="text-lg text-ink/70 animate-rise" style={{ animationDelay: '120ms' }}>
              NovellaForge orchestre LangGraph, RAG et generation autonome pour produire une narration
              coherente, structuree et livrable en continu.
            </p>
            <div className="flex flex-col gap-3 sm:flex-row animate-rise" style={{ animationDelay: '200ms' }}>
              {showAuthed ? (
                <Link
                  href="/dashboard?create=1"
                  className="inline-flex items-center justify-center rounded-full bg-brand-700 px-6 py-3 text-sm font-medium text-white shadow-soft transition hover:bg-brand-800"
                >
                  Creer un projet
                </Link>
              ) : (
                <Link
                  href="/auth/register"
                  className="inline-flex items-center justify-center rounded-full bg-brand-700 px-6 py-3 text-sm font-medium text-white shadow-soft transition hover:bg-brand-800"
                >
                  Lancer un projet
                </Link>
              )}
              <Link
                href="/dashboard"
                className="inline-flex items-center justify-center rounded-full border border-stone-300 px-6 py-3 text-sm font-medium text-ink transition hover:bg-white/70"
              >
                Voir le tableau de bord
              </Link>
            </div>
            <div className="grid gap-4 pt-4 sm:grid-cols-2 animate-rise" style={{ animationDelay: '280ms' }}>
              <div className="rounded-2xl bg-white/80 p-4 ring-1 ring-stone-200">
                <p className="text-xs uppercase tracking-[0.2em] text-ink/60">Contexte</p>
                <p className="text-xl font-semibold text-ink">Collecte autonome</p>
              </div>
              <div className="rounded-2xl bg-white/80 p-4 ring-1 ring-stone-200">
                <p className="text-xs uppercase tracking-[0.2em] text-ink/60">RAG</p>
                <p className="text-xl font-semibold text-ink">Memoire vectorielle</p>
              </div>
            </div>
          </div>

          <div className="relative">
            {showExample && (
              <>
                <div className="glass-panel float-slow rounded-3xl p-8">
                  <div className="flex items-center justify-between text-xs uppercase tracking-[0.2em] text-brand-700">
                    <span>Exemple</span>
                    <span className="rounded-full bg-brand-100 px-2 py-1 text-[10px]">RAG demo</span>
                  </div>
                  <h3 className="mt-4 font-serif text-2xl text-ink">Roman de Ramon</h3>
                  <p className="text-sm text-ink/70">Scenario fictif - 10 chapitres</p>
                  <div className="mt-6 space-y-4">
                    {['Chapitre 1', 'Chapitre 2', 'Chapitre 3'].map((title, index) => (
                      <div key={title} className="space-y-2">
                        <div className="flex items-center justify-between text-sm text-ink/70">
                          <span>{title}</span>
                          <span>{120 + index * 12} mots</span>
                        </div>
                        <div className="h-2 w-full rounded-full bg-stone-200">
                          <div
                            className="h-2 rounded-full bg-brand-600"
                            style={{ width: `${70 + index * 8}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="absolute -bottom-6 -left-6 rounded-2xl bg-white/90 p-4 text-sm text-ink/80 shadow-soft ring-1 ring-stone-200">
                  Exemple: Ramon doit etre mentionne.
                </div>
              </>
            )}

            {showAuthed && (
              <div className="glass-panel rounded-3xl p-8">
                <div className="flex items-center justify-between text-xs uppercase tracking-[0.2em] text-brand-700">
                  <span>Espace connecte</span>
                  <span className="rounded-full bg-brand-100 px-2 py-1 text-[10px]">Compte actif</span>
                </div>
                <h3 className="mt-4 font-serif text-2xl text-ink">Demarrer un nouveau projet</h3>
                <p className="text-sm text-ink/70">
                  Lancez votre brief, vos contraintes et laissez NovellaForge orchestrer le flux.
                </p>
                <div className="mt-6 space-y-4 text-sm text-ink/70">
                  {[
                    'Definir le genre et la structure',
                    'Ajouter des notes et personnages',
                    'Generer le premier chapitre',
                  ].map((item) => (
                    <div key={item} className="flex items-center gap-3">
                      <div className="h-2 w-2 rounded-full bg-brand-600" />
                      <span>{item}</span>
                    </div>
                  ))}
                </div>
                <div className="mt-6 flex flex-col gap-3 sm:flex-row">
                  <Link
                    href="/dashboard?create=1"
                    className="inline-flex items-center justify-center rounded-full bg-brand-700 px-5 py-2.5 text-sm font-medium text-white shadow-soft transition hover:bg-brand-800"
                  >
                    Creer un projet
                  </Link>
                  <Link
                    href="/dashboard"
                    className="inline-flex items-center justify-center rounded-full border border-stone-300 px-5 py-2.5 text-sm font-medium text-ink transition hover:bg-white/70"
                  >
                    Ouvrir le tableau de bord
                  </Link>
                </div>
              </div>
            )}
          </div>
        </section>

        <section className="mt-16 grid gap-6 md:grid-cols-3">
          {[
            {
              title: 'Orchestration claire',
              body: 'Planification, ecriture et persistence enchaines sans friction.',
            },
            {
              title: 'Contexte toujours frais',
              body: 'Personnages, notes et chapitres synchronises en temps reel.',
            },
            {
              title: 'Qualite livrable',
              body: 'Structuration, contraintes et controle de longueur integres.',
            },
          ].map((item) => (
            <div
              key={item.title}
              className="rounded-2xl border border-stone-200 bg-white/80 p-6 shadow-soft"
            >
              <h3 className="font-serif text-xl text-ink">{item.title}</h3>
              <p className="mt-2 text-sm text-ink/70">{item.body}</p>
            </div>
          ))}
        </section>

        <footer className="mt-auto flex flex-col items-center gap-2 pt-12 text-xs text-ink/60">
          <p>NovellaForge Studio - pipeline d'ecriture autonome.</p>
          {showAuthed ? (
            <div className="flex gap-4">
              <Link href="/dashboard" className="hover:text-ink">Tableau de bord</Link>
              <Link href="/dashboard?create=1" className="hover:text-ink">Creer un projet</Link>
            </div>
          ) : (
            <div className="flex gap-4">
              <Link href="/auth/login" className="hover:text-ink">Connexion</Link>
              <Link href="/auth/register" className="hover:text-ink">Inscription</Link>
            </div>
          )}
        </footer>
      </div>
    </main>
  )
}
