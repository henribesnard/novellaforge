import type { Project } from '@/types'
import { ProjectCard } from './project-card'

interface ProjectListProps {
  projects: Project[]
  onReload: () => Promise<void>
  onOpenProject: (projectId: string) => void
  onDeleteRequest: (project: Project) => void
}

export function ProjectList({ projects, onReload, onOpenProject, onDeleteRequest }: ProjectListProps) {
  return (
    <div className="space-y-6">
      {projects.map((project, i) => (
        <div
          key={project.id}
          className="animate-slideUp"
          style={{ animationDelay: `${i * 80}ms` }}
        >
          <ProjectCard
            project={project}
            onReload={onReload}
            onOpenProject={onOpenProject}
            onDeleteRequest={onDeleteRequest}
          />
        </div>
      ))}
    </div>
  )
}
