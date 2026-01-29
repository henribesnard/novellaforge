import { create } from 'zustand'

interface UIState {
  sidebarOpen: boolean
  toggleSidebar: () => void
  expandedProjectId: string | null
  setExpandedProject: (id: string | null) => void
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: false,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  expandedProjectId: null,
  setExpandedProject: (id) => set({ expandedProjectId: id }),
}))
