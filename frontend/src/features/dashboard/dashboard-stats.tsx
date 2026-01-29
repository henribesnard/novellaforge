import { Card } from '@/components/ui/card'
import { formatWordCount } from '@/lib/utils'
import type { Project } from '@/types'

interface DashboardStatsProps {
  projects: Project[]
}

export function DashboardStats({ projects }: DashboardStatsProps) {
  const totalWords = projects.reduce((sum, p) => sum + p.current_word_count, 0)
  const inProgress = projects.filter((p) => p.status === 'in_progress').length
  const completed = projects.filter((p) => p.status === 'completed').length

  const stats = [
    {
      label: 'Projets',
      value: projects.length,
      icon: (
        <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 7h6l2 2h10v10H3z" />
        </svg>
      ),
      color: 'bg-brand-100 text-brand-700',
    },
    {
      label: 'Mots ecrits',
      value: formatWordCount(totalWords),
      icon: (
        <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 7h16M4 12h10M4 17h7" />
        </svg>
      ),
      color: 'bg-accent-100 text-accent-700',
    },
    {
      label: 'En cours',
      value: inProgress,
      icon: (
        <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3" />
          <circle cx="12" cy="12" r="8" />
        </svg>
      ),
      color: 'bg-stone-200 text-ink',
    },
    {
      label: 'Termines',
      value: completed,
      icon: (
        <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      ),
      color: 'bg-emerald-100 text-emerald-700',
    },
  ]

  return (
    <Card variant="elevated" className="px-2 py-3">
      <div className="flex items-center divide-x divide-stone-200">
        {stats.map((stat) => (
          <div key={stat.label} className="flex flex-1 items-center gap-3 px-4">
            <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${stat.color}`}>
              {stat.icon}
            </div>
            <div className="min-w-0">
              <p className="text-[10px] uppercase tracking-[0.2em] text-ink/50">{stat.label}</p>
              <p className="text-lg font-semibold text-ink leading-tight">{stat.value}</p>
            </div>
          </div>
        ))}
      </div>
    </Card>
  )
}
