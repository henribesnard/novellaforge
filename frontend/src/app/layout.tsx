import type { Metadata } from 'next'
import { IBM_Plex_Sans, IBM_Plex_Serif } from 'next/font/google'
import { Providers } from '@/providers'
import './globals.css'

const plexSans = IBM_Plex_Sans({
  subsets: ['latin'],
  variable: '--font-sans',
  weight: ['400', '500', '600', '700'],
})
const plexSerif = IBM_Plex_Serif({
  subsets: ['latin'],
  variable: '--font-serif',
  weight: ['400', '500', '600', '700'],
})

export const metadata: Metadata = {
  title: "NovellaForge - Assistant intelligent d'ecriture",
  description: "Assistant IA pour l'ecriture long format",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="fr">
      <body className={`${plexSans.variable} ${plexSerif.variable} font-sans`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
