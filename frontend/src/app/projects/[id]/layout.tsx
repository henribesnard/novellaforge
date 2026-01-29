import Link from 'next/link'

export default async function ProjectLayout({
  children,
  params,
}: {
  children: React.ReactNode
  params: Promise<{ id: string }>
}) {
  const { id } = await params

  return (
    <div className="min-h-screen bg-atlas">
      <div className="border-b border-stone-200 bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <Link
              href="/dashboard"
              className="text-xs uppercase tracking-[0.25em] text-brand-700"
            >
              NovellaForge
            </Link>
            <span className="text-xs text-ink/50">/ Projet</span>
          </div>
          <Link
            href="/dashboard"
            className="text-sm text-ink/70 hover:text-ink"
          >
            Retour au dashboard
          </Link>
        </div>
      </div>

      <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8">
        <nav className="mb-6 flex flex-wrap gap-3 text-sm">
          <Link
            href={`/projects/${id}`}
            className="rounded-full border border-stone-200 bg-white px-4 py-1 text-ink/70 hover:text-ink"
          >
            Vue d'ensemble
          </Link>
          <Link
            href={`/projects/${id}/chapters`}
            className="rounded-full border border-stone-200 bg-white px-4 py-1 text-ink/70 hover:text-ink"
          >
            Chapitres
          </Link>
          <Link
            href={`/projects/${id}/characters`}
            className="rounded-full border border-stone-200 bg-white px-4 py-1 text-ink/70 hover:text-ink"
          >
            Personnages
          </Link>
          <Link
            href={`/projects/${id}/chat`}
            className="rounded-full border border-stone-200 bg-white px-4 py-1 text-ink/70 hover:text-ink"
          >
            Chat IA
          </Link>
        </nav>

        {children}
      </div>
    </div>
  )
}
