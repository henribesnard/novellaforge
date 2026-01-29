'use client'

import { useRouter } from 'next/navigation'
import { removeAuthToken } from '@/lib/api'
import { DashboardHeader } from '@/features/dashboard'

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()

  const handleLogout = () => {
    removeAuthToken()
    router.push('/')
  }

  return (
    <div className="min-h-screen bg-atlas">
      <DashboardHeader onLogout={handleLogout} />
      {children}
    </div>
  )
}
