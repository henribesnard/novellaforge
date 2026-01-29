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
      {projects.map((project) => (
        <ProjectCard
          key={project.id}
          project={project}
          onReload={onReload}
          onOpenProject={onOpenProject}
          onDeleteRequest={onDeleteRequest}
        />
      ))}
    </div>
  )
}
