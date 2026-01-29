import { Button } from '@/components/ui/button'

interface DashboardHeaderProps {
  onLogout: () => void
}

export function DashboardHeader({ onLogout }: DashboardHeaderProps) {
  return (
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
        <Button variant="outline" onClick={onLogout}>
          Deconnexion
        </Button>
      </div>
    </header>
  )
}
