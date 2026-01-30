export const getStatusColor = (status: string) => {
  switch (status) {
    case 'draft':
      return 'default'
    case 'in_progress':
      return 'primary'
    case 'completed':
      return 'success'
    case 'archived':
      return 'warning'
    default:
      return 'default'
  }
}

export const getStatusLabel = (status: string) => {
  switch (status) {
    case 'draft':
      return 'Brouillon'
    case 'in_progress':
      return 'En cours'
    case 'completed':
      return 'Termine'
    case 'archived':
      return 'Archive'
    case 'accepted':
      return 'Valide'
    default:
      return status
  }
}

export const formatConceptStatus = (status?: string) => {
  if (!status) return 'non genere'
  if (status === 'accepted') return 'valide'
  if (status === 'draft') return 'brouillon'
  return status
}
