# Plan de Refonte Frontend - NovellaForge

**Version :** 1.0
**Date :** Janvier 2026
**Statut :** A implementer

---

## Table des Matieres

1. [Diagnostic de l'existant](#1-diagnostic-de-lexistant)
2. [Objectifs de la refonte](#2-objectifs-de-la-refonte)
3. [Architecture cible](#3-architecture-cible)
4. [Phase 0 : Fondations](#4-phase-0--fondations)
5. [Phase 1 : Couche API et state management](#5-phase-1--couche-api-et-state-management)
6. [Phase 2 : Decomposition du dashboard](#6-phase-2--decomposition-du-dashboard)
7. [Phase 3 : Pages et routing](#7-phase-3--pages-et-routing)
8. [Phase 4 : Integration TTS](#8-phase-4--integration-tts)
9. [Phase 5 : Editeur de chapitre](#9-phase-5--editeur-de-chapitre)
10. [Phase 6 : Tests](#10-phase-6--tests)
11. [Phase 7 : Nettoyage et polish](#11-phase-7--nettoyage-et-polish)
12. [Arborescence cible](#12-arborescence-cible)
13. [Checklist globale](#13-checklist-globale)

---

## 1. Diagnostic de l'existant

### 1.1 Problemes identifies

| Probleme | Severite | Detail |
|----------|----------|--------|
| Dashboard monolithique | Critique | `dashboard/new/page.tsx` = **1207 lignes**, `ProjectCard` = 789 lignes |
| Aucun state management | Eleve | 18+ `useState` dans un seul composant, prop drilling, pas de Zustand |
| API layer plat | Eleve | `api-extended.ts` = 524 lignes, pas de cache, pas d'intercepteurs |
| Dependances installees inutilisees | Moyen | Zustand, React Query, TipTap, React Hook Form, Zod, Lucide, Axios, Recharts = ~500KB de bundle mort |
| Pas de tests | Eleve | Aucun fichier test, aucune config (jest/vitest/playwright) |
| Logique metier dans les composants | Eleve | Calculs de statut, transformations de donnees, derivations dans le JSX |
| Pas de providers (layout) | Moyen | Pas de QueryClientProvider, pas de contexte auth, pas de theme provider |
| Icones en SVG inline dupliquees | Faible | `ChevronIcon` duplique dans dashboard et audio |
| TTS non commite | Eleve | 14 fichiers audio en working tree, aucun test |

### 1.2 Dependances actuelles

| Package | Installe | Utilise | Action |
|---------|----------|---------|--------|
| `next` | 15.0 | Oui | Garder |
| `react` | 18.3 | Oui | Garder |
| `@tanstack/react-query` | 5.56 | Non | **Activer** |
| `zustand` | 4.5 | Non | **Activer** |
| `react-hook-form` | 7.53 | Non | **Activer** |
| `zod` | 3.23 | Non | **Activer** |
| `@hookform/resolvers` | 3.9 | Non | **Activer** |
| `@tiptap/react` + extensions | 2.6 | Non | **Activer** |
| `lucide-react` | 0.441 | Non | **Activer** |
| `axios` | 1.7 | Non | **Supprimer** (fetch + react-query suffit) |
| `recharts` | 2.12 | Non | Garder (stats futures) |
| `next-auth` | 4.24 | Non | **Supprimer** (auth custom existante) |
| `date-fns` | 3.6 | Non | **Supprimer** (Intl.DateTimeFormat suffit) |
| `clsx` + `tailwind-merge` | - | Oui | Garder |

### 1.3 Metriques actuelles

```
Fichiers frontend totaux : ~35
Plus gros fichier : dashboard/new/page.tsx (1207 lignes)
Fichier API : api-extended.ts (524 lignes)
Composants UI reutilisables : 7
Hooks custom : 2 (audio uniquement)
Stores : 0
Tests : 0
```

---

## 2. Objectifs de la refonte

### 2.1 Objectifs techniques

1. **Aucun composant > 300 lignes** -- le dashboard doit etre decoupe en 15-20 composants
2. **State management global** via Zustand pour auth et UI state
3. **Server state** via React Query pour toutes les donnees API
4. **Formulaires** via React Hook Form + Zod pour toute saisie utilisateur
5. **Icones** via Lucide React partout (supprimer les SVG inline)
6. **Editeur riche** via TipTap pour l'edition de chapitres/synopsis
7. **Tests** avec Vitest + Testing Library + Playwright
8. **TTS integre** proprement dans l'architecture

### 2.2 Objectifs fonctionnels

- Le dashboard affiche la liste des projets avec stats
- Chaque projet se deplie pour voir le workflow (concept > synopsis > plan > chapitres)
- L'edition de chapitre se fait sur une page dediee avec TipTap + TTS
- La navigation est fluide et les etats sont preserves

### 2.3 Ce qui ne change pas

- Design system (couleurs ink/canvas/brand/accent, polices IBM Plex)
- Composants UI de base (Button, Card, Input, Dialog, Badge, Select, Textarea)
- Backend API (aucune modification)
- Audio hooks et composants (refactoring mineur seulement)

---

## 3. Architecture cible

### 3.1 Diagramme

```
app/layout.tsx
  +-- Providers (QueryClient, AuthContext)
  |
  +-- app/page.tsx                     Landing
  +-- app/auth/login/page.tsx          Login
  +-- app/auth/register/page.tsx       Register
  +-- app/dashboard/layout.tsx         Dashboard layout (header, sidebar)
  |     +-- app/dashboard/page.tsx     Liste des projets
  +-- app/projects/[id]/layout.tsx     Layout projet
        +-- app/projects/[id]/page.tsx            Vue d'ensemble projet
        +-- app/projects/[id]/chapters/page.tsx   Liste chapitres
        +-- app/projects/[id]/chapters/[idx]/page.tsx  Edition chapitre + TTS
        +-- app/projects/[id]/characters/page.tsx  Personnages
        +-- app/projects/[id]/chat/page.tsx        Chat IA
```

### 3.2 Couches

```
Pages (app/)
  |  Composent les features, zero logique metier
  v
Features (features/)
  |  Composants metier specifiques a un domaine
  |  Ex: ProjectCard, SynopsisEditor, ChapterGenerator, AudioPlayer
  v
Hooks (hooks/)
  |  React Query queries/mutations, logique metier reactive
  |  Ex: useProject, useChapters, useSpeechSynthesis
  v
Services (services/)
  |  Fonctions API pures, serialisation, transformation
  |  Ex: projectService, chapterService, authService
  v
Stores (stores/)
  |  Zustand pour l'etat global (auth, UI preferences)
  v
Types, Utils, UI Components
```

### 3.3 Conventions

| Convention | Regle |
|------------|-------|
| Fichier composant | `kebab-case.tsx` |
| Fichier hook | `use-xxx.ts` |
| Fichier service | `xxx.service.ts` |
| Fichier store | `xxx.store.ts` |
| Fichier test | `xxx.test.ts(x)` |
| Fichier schema (Zod) | `xxx.schema.ts` |
| Barrel exports | `index.ts` par dossier feature |
| Composant max | 300 lignes |
| Hook max | 200 lignes (sauf exceptions documentees) |

---

## 4. Phase 0 : Fondations

### 4.1 Nettoyage des dependances

**Fichier :** `package.json`

```
Supprimer :
- axios (fetch natif + react-query)
- next-auth (auth custom existante)
- date-fns (Intl.DateTimeFormat)

Ajouter (dev) :
- vitest
- @testing-library/react
- @testing-library/jest-dom
- @testing-library/user-event
- jsdom
- @playwright/test
- @vitejs/plugin-react
```

### 4.2 Configuration Vitest

**Fichier :** `frontend/vitest.config.ts`

```typescript
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    css: false,
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
    },
  },
})
```

**Fichier :** `frontend/src/test/setup.ts`

```typescript
import '@testing-library/jest-dom/vitest'
```

### 4.3 Providers

**Fichier :** `src/providers/index.tsx`

```typescript
'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState, type ReactNode } from 'react'

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      })
  )

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}
```

**Modification :** `src/app/layout.tsx`

```typescript
import { Providers } from '@/providers'

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body className={`${plexSans.variable} ${plexSerif.variable} font-sans`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
```

### 4.4 Store Auth (Zustand)

**Fichier :** `src/stores/auth.store.ts`

> **Correction SSR :** Ne pas lire `localStorage` pendant l'initialisation du module
> (provoque une erreur cote serveur). Utiliser un `useEffect` d'hydratation
> ou le middleware `persist` de Zustand. Ici on utilise l'approche simple
> avec hydratation manuelle dans le Provider.

```typescript
import { create } from 'zustand'

interface AuthState {
  token: string | null
  isAuthenticated: boolean
  _hydrated: boolean
  hydrate: () => void
  setToken: (token: string | null) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  isAuthenticated: false,
  _hydrated: false,
  hydrate: () => {
    const token = localStorage.getItem('auth_token')
    const valid = !!token && token !== 'undefined' && token !== 'null'
    set({
      token: valid ? token : null,
      isAuthenticated: valid,
      _hydrated: true,
    })
  },
  setToken: (token) => {
    if (token && token !== 'undefined' && token !== 'null') {
      localStorage.setItem('auth_token', token)
    } else {
      localStorage.removeItem('auth_token')
      token = null
    }
    set({ token, isAuthenticated: !!token })
  },
  logout: () => {
    localStorage.removeItem('auth_token')
    set({ token: null, isAuthenticated: false })
  },
}))
```

**Modification :** `src/providers/index.tsx` -- ajouter l'hydratation auth :

```typescript
import { useEffect } from 'react'
import { useAuthStore } from '@/stores/auth.store'

// Dans le composant Providers, ajouter :
export function Providers({ children }: { children: ReactNode }) {
  const hydrate = useAuthStore((s) => s.hydrate)
  useEffect(() => { hydrate() }, [hydrate])
  // ... QueryClientProvider etc.
}
```

### 4.5 Store UI (Zustand)

**Fichier :** `src/stores/ui.store.ts`

```typescript
import { create } from 'zustand'

interface UIState {
  sidebarOpen: boolean
  toggleSidebar: () => void
  expandedProjectId: string | null
  setExpandedProject: (id: string | null) => void
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: false,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  expandedProjectId: null,
  setExpandedProject: (id) => set({ expandedProjectId: id }),
}))
```

---

## 5. Phase 1 : Couche API et state management

### 5.1 Client API refactorise

**Fichier :** `src/services/api-client.ts`

Remplace `api.ts` et le wrapper `apiFetch` de `api-extended.ts`.

> **Differences cles avec l'actuel `apiFetch` a reproduire :**
> - `try/catch` autour de `fetch` pour les erreurs reseau
> - Gestion `204 No Content` et body vide
> - Support `FormData` (pas de `Content-Type` force)
> - Fonction `downloadFile` pour les exports blob
> - Types auth re-exportes depuis ce module

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8002/api/v1'

// Types auth (remplacement de lib/api.ts)
export interface LoginCredentials {
  email: string
  password: string
}

export interface RegisterData {
  email: string
  password: string
  full_name: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: { id: string; email: string; full_name: string }
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

function getToken(): string | null {
  if (typeof window === 'undefined') return null
  const token = localStorage.getItem('auth_token')
  if (!token || token === 'undefined' || token === 'null') {
    localStorage.removeItem('auth_token')
    return null
  }
  return token
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getToken()
  const isFormData = options?.body instanceof FormData

  const headers: HeadersInit = {
    // Ne PAS mettre Content-Type pour FormData (le navigateur le gere)
    ...(!isFormData && { 'Content-Type': 'application/json' }),
    ...(token && { Authorization: `Bearer ${token}` }),
    ...options?.headers,
  }

  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, { ...options, headers })
  } catch {
    throw new ApiError(0, "Impossible de contacter l'API. Verifiez que le backend tourne.")
  }

  if (!response.ok) {
    if (response.status === 401) {
      localStorage.removeItem('auth_token')
    }
    const body = await response.json().catch(() => ({ detail: 'Erreur reseau' }))
    throw new ApiError(response.status, body.detail || `Erreur ${response.status}`)
  }

  // Gestion 204 No Content
  if (response.status === 204) {
    return null as T
  }

  // Gestion body vide
  const text = await response.text()
  if (!text) {
    return null as T
  }

  return JSON.parse(text) as T
}

// Helper pour les telechargements (projet zip, document md)
function getDownloadFilename(disposition: string | null, fallback: string): string {
  if (!disposition) return fallback
  const match = disposition.match(/filename\*=UTF-8''([^;]+)|filename="?([^\\";]+)"?/i)
  const filename = match?.[1] || match?.[2]
  if (!filename) return fallback
  try { return decodeURIComponent(filename) } catch { return filename }
}

export async function downloadFile(
  path: string,
  fallbackName: string
): Promise<{ blob: Blob; filename: string }> {
  const token = getToken()
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { ...(token && { Authorization: `Bearer ${token}` }) },
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Download failed' }))
    if (response.status === 401) localStorage.removeItem('auth_token')
    throw new ApiError(response.status, error.detail || `Erreur ${response.status}`)
  }

  const blob = await response.blob()
  const filename = getDownloadFilename(response.headers.get('Content-Disposition'), fallbackName)
  return { blob, filename }
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: 'POST',
      body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
    }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'PUT', body: body ? JSON.stringify(body) : undefined }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
}
```

### 5.2 Services par domaine

Chaque domaine a son propre fichier service qui encapsule les appels API.

**Fichier :** `src/services/auth.service.ts`

```typescript
import { api } from './api-client'
import type { AuthResponse, LoginCredentials, RegisterData } from './api-client'

export const authService = {
  login: (credentials: LoginCredentials) =>
    api.post<AuthResponse>('/auth/login/json', credentials),
  register: (data: RegisterData) =>
    api.post<AuthResponse>('/auth/register', data),
}
```

**Fichier :** `src/services/project.service.ts`

> **Corrections vs version precedente :**
> - `list()` retourne `{ projects: Project[]; total: number }` (pas `Project[]`)
> - Trailing slash sur `/projects/` (conforme a l'API actuelle)
> - `acceptConcept` utilise `PUT /concept` (pas `POST /concept/accept`)
> - `acceptPlan` et `acceptSynopsis` utilisent `PUT` (pas `POST`)
> - `updatePlan` envoie `{ plan }` (pas `plan` directement)
> - `update` utilise `ProjectUpdate` (pas `Partial<Project>`)
> - Ajout de `generateConceptProposal`

```typescript
import { api, downloadFile } from './api-client'
import type {
  Project,
  ProjectCreate,
  ProjectUpdate,
  ConceptPayload,
  ConceptProposalResponse,
  ConceptResponse,
  SynopsisResponse,
  SynopsisUpdateRequest,
  PlanPayload,
  PlanResponse,
} from '@/types'

export const projectService = {
  list: (skip = 0, limit = 100) =>
    api.get<{ projects: Project[]; total: number }>(`/projects/?skip=${skip}&limit=${limit}`),
  get: (id: string) =>
    api.get<Project>(`/projects/${id}`),
  create: (data: ProjectCreate) =>
    api.post<Project>('/projects/', data),
  update: (id: string, data: ProjectUpdate) =>
    api.put<Project>(`/projects/${id}`, data),
  delete: (id: string, confirmTitle: string) =>
    api.post(`/projects/${id}/delete`, { confirm_title: confirmTitle }),
  download: (id: string) =>
    downloadFile(`/projects/${id}/download`, `project-${id}.zip`),

  // Concept
  getConcept: (id: string) =>
    api.get<ConceptResponse>(`/projects/${id}/concept`),
  generateConcept: (id: string, force = false) =>
    api.post<ConceptResponse>(`/projects/${id}/concept/generate`, { force }),
  generateConceptProposal: (genre: ProjectCreate['genre'], notes?: string) =>
    api.post<ConceptProposalResponse>('/projects/concept/proposal', { genre, notes }),
  acceptConcept: (id: string, concept: ConceptPayload) =>
    api.put<ConceptResponse>(`/projects/${id}/concept`, concept),

  // Synopsis
  getSynopsis: (id: string) =>
    api.get<SynopsisResponse>(`/projects/${id}/synopsis`),
  generateSynopsis: (id: string, notes?: string) =>
    api.post<SynopsisResponse>(`/projects/${id}/synopsis/generate`, { notes }),
  updateSynopsis: (id: string, payload: SynopsisUpdateRequest) =>
    api.put<SynopsisResponse>(`/projects/${id}/synopsis`, payload),
  acceptSynopsis: (id: string) =>
    api.put<SynopsisResponse>(`/projects/${id}/synopsis/accept`),

  // Plan
  getPlan: (id: string) =>
    api.get<PlanResponse>(`/projects/${id}/plan`),
  generatePlan: (id: string, chapterCount?: number, arcCount?: number) =>
    api.post<PlanResponse>(`/projects/${id}/plan/generate`, { chapter_count: chapterCount, arc_count: arcCount }),
  acceptPlan: (id: string) =>
    api.put<PlanResponse>(`/projects/${id}/plan/accept`),
  updatePlan: (id: string, plan: PlanPayload) =>
    api.put<PlanResponse>(`/projects/${id}/plan`, { plan }),
}
```

**Fichier :** `src/services/instruction.service.ts` *(nouveau -- absent de la version precedente)*

> Couvre les endpoints CRUD pour les consignes d'ecriture par projet.

```typescript
import { api } from './api-client'
import type { Instruction } from '@/types'

export const instructionService = {
  list: (projectId: string) =>
    api.get<{ instructions: Instruction[] }>(`/projects/${projectId}/instructions`),
  create: (projectId: string, data: Pick<Instruction, 'title' | 'detail'>) =>
    api.post<Instruction>(`/projects/${projectId}/instructions`, data),
  update: (projectId: string, instructionId: string, data: Partial<Pick<Instruction, 'title' | 'detail'>>) =>
    api.put<Instruction>(`/projects/${projectId}/instructions/${instructionId}`, data),
  delete: (projectId: string, instructionId: string) =>
    api.delete(`/projects/${projectId}/instructions/${instructionId}`),
}
```

**Fichier :** `src/services/document.service.ts` *(nouveau -- absent de la version precedente)*

> Couvre les endpoints documents, versions, commentaires, elements et generation.
> L'ancien `chapter.service.ts` ne couvrait que la pipeline d'ecriture.

```typescript
import { api, downloadFile } from './api-client'
import type { Document, DocumentVersion, DocumentComment } from '@/types'

export const documentService = {
  // CRUD documents
  list: (projectId: string) =>
    api.get<{ documents: Document[] }>(`/documents/?project_id=${projectId}`),
  get: (id: string) =>
    api.get<Document>(`/documents/${id}`),
  create: (data: Partial<Document>) =>
    api.post<Document>('/documents', data),
  update: (id: string, data: Partial<Document>) =>
    api.put<Document>(`/documents/${id}`, data),
  delete: (id: string) =>
    api.delete(`/documents/${id}`),
  download: (id: string) =>
    downloadFile(`/documents/${id}/download`, `document-${id}.md`),

  // Elements (creation structuree)
  createElement: (projectId: string, elementType: string, parentId?: string) =>
    api.post<Document>('/documents/elements', {
      project_id: projectId,
      element_type: elementType,
      parent_id: parentId || undefined,
    }),
  generateElement: (documentId: string, params?: {
    instructions?: string
    min_word_count?: number
    max_word_count?: number
    summary?: string
    source_version_id?: string
    comment_ids?: string[]
  }) =>
    api.post<Document>(`/documents/${documentId}/generate`, params),

  // Versions
  listVersions: (documentId: string) =>
    api.get<{ versions: DocumentVersion[] }>(`/documents/${documentId}/versions`),
  getVersion: (documentId: string, versionId: string) =>
    api.get<DocumentVersion>(`/documents/${documentId}/versions/${versionId}`),
  createVersion: (documentId: string, content: string, sourceVersionId?: string) =>
    api.post<Document>(`/documents/${documentId}/versions`, {
      content,
      source_version_id: sourceVersionId,
    }),

  // Commentaires
  listComments: (documentId: string) =>
    api.get<{ comments: DocumentComment[] }>(`/documents/${documentId}/comments`),
  createComment: (documentId: string, content: string, versionId?: string) =>
    api.post<DocumentComment>(`/documents/${documentId}/comments`, {
      content,
      version_id: versionId || undefined,
    }),
}
```

**Fichier :** `src/services/chapter.service.ts` *(corrige)*

> **Corrections :**
> - `ChapterGeneratePayload` defini en tant que type inline
> - Import et utilisation de `downloadFile` depuis `api-client`

```typescript
import { api, downloadFile } from './api-client'
import type { ChapterGenerationResponse, ChapterApprovalResponse } from '@/types'

export interface ChapterGeneratePayload {
  project_id: string
  chapter_id?: string
  chapter_index?: number
  instruction?: string
  rewrite_focus?: 'emotion' | 'tension' | 'action' | 'custom'
  target_word_count?: number
  use_rag?: boolean
  reindex_documents?: boolean
  create_document?: boolean
  auto_approve?: boolean
}

export const chapterService = {
  generate: (payload: ChapterGeneratePayload) =>
    api.post<ChapterGenerationResponse>('/writing/generate-chapter', payload),
  approve: (documentId: string) =>
    api.post<ChapterApprovalResponse>('/writing/approve-chapter', { document_id: documentId }),
}
```

> **Note :** Les operations CRUD sur les documents chapitres (list, get, update, delete, download)
> sont dans `document.service.ts`. `chapter.service.ts` ne couvre que la pipeline de generation.

**Fichier :** `src/services/character.service.ts` *(corrige)*

> **Corrections :**
> - `list()` retourne `{ characters: Character[] }` (pas `Character[]`)
> - Ajout de `generateMainCharacters`

```typescript
import { api } from './api-client'
import type { Character, CharacterCreate } from '@/types'

export const characterService = {
  list: (projectId: string) =>
    api.get<{ characters: Character[] }>(`/characters?project_id=${projectId}`),
  get: (id: string) =>
    api.get<Character>(`/characters/${id}`),
  create: (data: CharacterCreate) =>
    api.post<Character>('/characters', data),
  update: (id: string, data: Partial<Character>) =>
    api.put<Character>(`/characters/${id}`, data),
  delete: (id: string) =>
    api.delete(`/characters/${id}`),
  generateMainCharacters: (projectId: string, summary: string, precision?: string) =>
    api.post<{ characters: Character[] }>('/characters/auto', {
      project_id: projectId,
      summary,
      precision,
    }),
}
```

**Fichier :** `src/services/chat.service.ts` *(nouveau -- etait liste mais sans code)*

```typescript
import { api } from './api-client'
import type { ChatMessage } from '@/types'

export const chatService = {
  sendMessage: (message: string, projectId?: string) =>
    api.post<{ response: string; message_id: string }>('/chat/message', {
      message,
      project_id: projectId,
    }),
  getHistory: (projectId?: string, limit = 50) => {
    const query = projectId ? `?project_id=${projectId}&limit=${limit}` : `?limit=${limit}`
    return api.get<{ messages: ChatMessage[] }>(`/chat/history${query}`)
  },
}
```

**Fichier :** `src/services/upload.service.ts` *(nouveau -- absent de la version precedente)*

> Utilise `FormData` (pas de JSON) -- le `api-client` gere le Content-Type automatiquement.

```typescript
import { api } from './api-client'

export const uploadService = {
  uploadFile: (file: File, projectId: string) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('project_id', projectId)
    return api.post<{ document_id: string; message: string }>('/upload', formData)
  },
}
```

**Fichier :** `src/services/agent.service.ts` *(nouveau -- absent de la version precedente)*

```typescript
import { api } from './api-client'

export const agentService = {
  runAnalysis: (projectId: string, analysisType: string, data?: Record<string, any>) =>
    api.post<{ task_id: string }>('/agents/analyze', {
      project_id: projectId,
      analysis_type: analysisType,
      data,
    }),
  getAnalysisStatus: (taskId: string) =>
    api.get<any>(`/agents/analysis/${taskId}`),
}
```

### 5.3 React Query Hooks

**Fichier :** `src/hooks/use-projects.ts`

> **Corrections :**
> - `useProjects` : `data` est `{ projects: Project[]; total: number }` (pas `Project[]`)
> - Ajout hooks manquants : `useCreateProject`, `useUpdateProject`, `useConcept`,
>   `useGenerateConcept`, `useAcceptConcept`, `useAcceptSynopsis`, `useAcceptPlan`

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { projectService } from '@/services/project.service'
import type { ProjectCreate, ProjectUpdate, ConceptPayload } from '@/types'

export const projectKeys = {
  all: ['projects'] as const,
  list: () => [...projectKeys.all, 'list'] as const,
  detail: (id: string) => [...projectKeys.all, id] as const,
  concept: (id: string) => [...projectKeys.all, id, 'concept'] as const,
  synopsis: (id: string) => [...projectKeys.all, id, 'synopsis'] as const,
  plan: (id: string) => [...projectKeys.all, id, 'plan'] as const,
}

// Note : data est { projects: Project[]; total: number }, pas Project[]
export function useProjects() {
  return useQuery({
    queryKey: projectKeys.list(),
    queryFn: () => projectService.list(),
  })
}

export function useProject(id: string) {
  return useQuery({
    queryKey: projectKeys.detail(id),
    queryFn: () => projectService.get(id),
    enabled: !!id,
  })
}

export function useCreateProject() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ProjectCreate) => projectService.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: projectKeys.list() }),
  })
}

export function useUpdateProject(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ProjectUpdate) => projectService.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: projectKeys.detail(id) })
      qc.invalidateQueries({ queryKey: projectKeys.list() })
    },
  })
}

export function useDeleteProject() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, title }: { id: string; title: string }) =>
      projectService.delete(id, title),
    onSuccess: () => qc.invalidateQueries({ queryKey: projectKeys.list() }),
  })
}

// Concept
export function useConcept(projectId: string) {
  return useQuery({
    queryKey: projectKeys.concept(projectId),
    queryFn: () => projectService.getConcept(projectId),
    enabled: !!projectId,
  })
}

export function useGenerateConcept(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (force = false) => projectService.generateConcept(projectId, force),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: projectKeys.concept(projectId) })
      qc.invalidateQueries({ queryKey: projectKeys.detail(projectId) })
    },
  })
}

export function useAcceptConcept(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (concept: ConceptPayload) => projectService.acceptConcept(projectId, concept),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: projectKeys.concept(projectId) })
      qc.invalidateQueries({ queryKey: projectKeys.detail(projectId) })
    },
  })
}

// Synopsis
export function useSynopsis(projectId: string) {
  return useQuery({
    queryKey: projectKeys.synopsis(projectId),
    queryFn: () => projectService.getSynopsis(projectId),
    enabled: !!projectId,
  })
}

export function useGenerateSynopsis(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (notes?: string) => projectService.generateSynopsis(projectId, notes),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: projectKeys.synopsis(projectId) })
      qc.invalidateQueries({ queryKey: projectKeys.detail(projectId) })
    },
  })
}

export function useAcceptSynopsis(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => projectService.acceptSynopsis(projectId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: projectKeys.synopsis(projectId) })
      qc.invalidateQueries({ queryKey: projectKeys.detail(projectId) })
    },
  })
}

// Plan
export function usePlan(projectId: string) {
  return useQuery({
    queryKey: projectKeys.plan(projectId),
    queryFn: () => projectService.getPlan(projectId),
    enabled: !!projectId,
  })
}

export function useGeneratePlan(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (params?: { chapterCount?: number; arcCount?: number }) =>
      projectService.generatePlan(projectId, params?.chapterCount, params?.arcCount),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: projectKeys.plan(projectId) })
      qc.invalidateQueries({ queryKey: projectKeys.detail(projectId) })
    },
  })
}

export function useAcceptPlan(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => projectService.acceptPlan(projectId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: projectKeys.plan(projectId) })
      qc.invalidateQueries({ queryKey: projectKeys.detail(projectId) })
    },
  })
}
```

**Fichier :** `src/hooks/use-chapters.ts`

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { chapterService } from '@/services/chapter.service'
import { projectKeys } from './use-projects'

export const chapterKeys = {
  all: ['chapters'] as const,
  list: (projectId: string) => [...chapterKeys.all, 'list', projectId] as const,
  detail: (id: string) => [...chapterKeys.all, id] as const,
}

export function useChapters(projectId: string) {
  return useQuery({
    queryKey: chapterKeys.list(projectId),
    queryFn: () => chapterService.list(projectId),
    enabled: !!projectId,
  })
}

export function useGenerateChapter(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: chapterService.generate,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: chapterKeys.list(projectId) })
      qc.invalidateQueries({ queryKey: projectKeys.detail(projectId) })
    },
  })
}

export function useApproveChapter(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (documentId: string) => chapterService.approve(documentId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: chapterKeys.list(projectId) })
      qc.invalidateQueries({ queryKey: projectKeys.detail(projectId) })
    },
  })
}
```

---

## 6. Phase 2 : Decomposition du dashboard

### 6.1 Strategie de decoupage

Le `ProjectCard` actuel (789 lignes) est decoupe en composants feature :

```
ProjectCard (container ~120 lignes)
  +-- ProjectCardHeader        (~60 lignes)  Titre, badge statut, boutons
  +-- ProjectWorkflow           (~80 lignes)  Stepper concept > synopsis > plan
  +-- SynopsisSection           (~100 lignes) Affichage/edition synopsis
  +-- PlanSection               (~120 lignes) Vue du plan + badges audio
  +-- ChapterGeneratorSection   (~100 lignes) Selection chapitre + generation
  +-- ChapterPreviewSection     (~80 lignes)  Preview du chapitre genere
  +-- ChapterViewerSection      (~80 lignes)  Contenu du chapitre + TTS
  +-- ProjectActionsBar         (~60 lignes)  Download, delete
```

### 6.2 Composants features a creer

**Dossier :** `src/features/projects/`

| Fichier | Responsabilite | Lignes max |
|---------|----------------|------------|
| `project-card.tsx` | Container, orchestre les sous-composants | 120 |
| `project-card-header.tsx` | Titre, genre, statut, date, collapse toggle | 60 |
| `project-workflow.tsx` | Indicateur d'avancement (concept > synopsis > plan) | 80 |
| `project-actions-bar.tsx` | Boutons download projet/chapitre, delete | 60 |
| `project-list.tsx` | Grille/liste de ProjectCard + stats globales | 80 |
| `create-project-wizard.tsx` | Deja existant (240 lignes, a garder) | 240 |
| `delete-project-dialog.tsx` | Dialog de confirmation de suppression | 60 |

**Dossier :** `src/features/synopsis/`

| Fichier | Responsabilite | Lignes max |
|---------|----------------|------------|
| `synopsis-section.tsx` | Affichage + edition + generation du synopsis | 100 |
| `synopsis-editor.tsx` | Textarea ou TipTap pour editer le synopsis | 80 |

**Dossier :** `src/features/plan/`

| Fichier | Responsabilite | Lignes max |
|---------|----------------|------------|
| `plan-section.tsx` | Conteneur plan avec toggle | 80 |
| `plan-chapter-list.tsx` | Liste des chapitres du plan avec badges | 100 |
| `plan-arc-list.tsx` | Liste des arcs narratifs | 60 |

**Dossier :** `src/features/chapters/`

| Fichier | Responsabilite | Lignes max |
|---------|----------------|------------|
| `chapter-generator.tsx` | Selecteur + bouton generer + loading | 100 |
| `chapter-preview.tsx` | Preview du chapitre genere (avant approbation) | 80 |
| `chapter-viewer.tsx` | Contenu du chapitre + TTS + download | 80 |
| `chapter-critique.tsx` | Affichage de la critique IA | 60 |
| `chapter-list.tsx` | Liste des chapitres generes | 80 |

**Dossier :** `src/features/audio/`

Les composants audio existants (`components/audio/`) sont deplaces ici.

| Fichier | Statut |
|---------|--------|
| `chapter-audio-player.tsx` | Existant, inchange |
| `audio-controls.tsx` | Existant, remplacer SVG inline par Lucide |
| `audio-progress-bar.tsx` | Existant, inchange |
| `audio-player-mini.tsx` | Existant, remplacer SVG inline par Lucide |
| `voice-selector.tsx` | Existant, inchange |
| `speed-control.tsx` | Existant, inchange |
| `audio-error-boundary.tsx` | Existant, inchange |
| `lazy.tsx` | Existant, inchange |

### 6.3 Logique metier a extraire

La logique suivante est actuellement dans `ProjectCard` et doit etre extraite :

**Fichier :** `src/hooks/use-project-workflow.ts`

```typescript
// Derive l'etat du workflow depuis les metadata du projet
export function useProjectWorkflow(project: Project) {
  const metadata = project.metadata || {}
  const conceptEntry = metadata.concept as Record<string, any> | undefined
  const conceptStatus = deriveConceptStatus(conceptEntry)

  const synopsisEntry = metadata.synopsis
  const synopsisText = deriveSynopsisText(synopsisEntry)

  const planEntry = metadata.plan as Record<string, any> | undefined
  const planPayload = derivePlanPayload(planEntry)
  const planStatus = planEntry?.status || 'draft'

  const canGeneratePlan = conceptStatus === 'accepted'
  const canGenerateChapter = !!planPayload && planStatus === 'accepted'

  return {
    conceptStatus,
    synopsisText,
    synopsisStatus: synopsisEntry?.status || 'draft',
    planPayload,
    planStatus,
    canGeneratePlan,
    canGenerateChapter,
  }
}
```

**Fichier :** `src/hooks/use-chapter-documents.ts`

```typescript
// Derive la liste des chapitres generes depuis les documents
export function useChapterDocuments(documents: Document[], planPayload?: PlanPayload) {
  // Logique extraite du dashboard : deduplication, tri, detection du prochain chapitre
  const generatedDocs = useMemo(() => deduplicateChapterDocs(documents), [documents])
  const generatedIndices = useMemo(() => generatedDocs.map(d => d.index), [generatedDocs])
  const nextChapter = useMemo(() => findNextChapter(planPayload, generatedIndices), [planPayload, generatedIndices])
  const chapterOptions = useMemo(() => buildChapterOptions(generatedDocs, nextChapter), [generatedDocs, nextChapter])

  return { generatedDocs, nextChapter, chapterOptions }
}
```

### 6.4 Helpers a extraire

**Fichier :** `src/lib/project-helpers.ts`

Extraire depuis le dashboard les fonctions utilitaires :

```typescript
export function getStatusColor(status: string): BadgeVariant
export function getStatusLabel(status: string): string
export function formatConceptStatus(status?: string): string
export function deduplicateChapterDocs(documents: Document[]): ChapterEntry[]
export function findNextChapter(plan: PlanPayload | undefined, generatedIndices: number[]): ChapterPlan | undefined
export function buildChapterOptions(docs: ChapterEntry[], next: ChapterPlan | undefined): SelectOption[]
export function triggerDownload(blob: Blob, filename: string): void
```

---

## 7. Phase 3 : Pages et routing

### 7.1 Dashboard refactorise

**Fichier :** `src/app/dashboard/page.tsx` (~60 lignes)

> **Corrections :**
> - `redirect()` est une fonction serveur (Next.js) -- ne marche pas dans `'use client'`
> - Utiliser `useRouter().replace()` dans un `useEffect` a la place
> - `data` de `useProjects()` est `{ projects, total }`, pas `Project[]`
> - Attendre l'hydratation du store auth avant de rediriger

```typescript
'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useProjects } from '@/hooks/use-projects'
import { useAuthStore } from '@/stores/auth.store'
import { ProjectList } from '@/features/projects/project-list'
import { DashboardHeader } from '@/features/dashboard/dashboard-header'
import { DashboardStats } from '@/features/dashboard/dashboard-stats'
import { CreateProjectWizard } from '@/features/projects/create-project-wizard'

export default function DashboardPage() {
  const router = useRouter()
  const { isAuthenticated, _hydrated } = useAuthStore()
  const { data, isLoading, error } = useProjects()

  useEffect(() => {
    if (_hydrated && !isAuthenticated) {
      router.replace('/auth/login')
    }
  }, [_hydrated, isAuthenticated, router])

  if (!_hydrated || !isAuthenticated) return null

  const projects = data?.projects ?? []

  return (
    <div className="min-h-screen bg-canvas">
      <DashboardHeader />
      <main className="mx-auto max-w-5xl px-4 py-8 space-y-8">
        <DashboardStats projects={projects} />
        <CreateProjectWizard />
        <ProjectList
          projects={projects}
          isLoading={isLoading}
          error={error}
        />
      </main>
    </div>
  )
}
```

### 7.2 Dashboard layout

**Fichier :** `src/app/dashboard/layout.tsx`

```typescript
import { redirect } from 'next/navigation'

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  // Server-side auth check if needed
  return <>{children}</>
}
```

### 7.3 Page projet

**Fichier :** `src/app/projects/[id]/page.tsx` (~80 lignes)

Vue d'ensemble du projet avec :
- Editeur de concept (existant, a integrer)
- Synopsis section
- Plan section
- Raccourcis vers les chapitres

### 7.4 Page edition de chapitre

**Fichier :** `src/app/projects/[id]/chapters/[idx]/page.tsx` (~100 lignes)

Page dediee avec :
- Editeur TipTap pour le contenu
- Audio player TTS
- Infos critique IA
- Bouton approbation
- Navigation chapitre precedent/suivant

### 7.5 Page personnages

**Fichier :** `src/app/projects/[id]/characters/page.tsx` (~80 lignes)

Liste et edition des personnages avec formulaires React Hook Form.

### 7.6 Page chat

**Fichier :** `src/app/projects/[id]/chat/page.tsx` (~40 lignes)

Integre le `ChatInterface` existant.

---

## 8. Phase 4 : Integration TTS

### 8.1 Deplacements

```
AVANT                                    APRES
components/audio/*                  -->  features/audio/*
hooks/use-speech-synthesis.ts       -->  hooks/use-speech-synthesis.ts (inchange)
hooks/use-audio-keyboard.ts         -->  hooks/use-audio-keyboard.ts (inchange)
lib/audio-storage.ts                -->  lib/audio-storage.ts (inchange)
lib/audio-utils.ts                  -->  lib/audio-utils.ts (inchange)
```

### 8.2 Remplacement des icones SVG

Dans `audio-controls.tsx` et `audio-player-mini.tsx`, remplacer les SVG inline :

```typescript
// AVANT
const IconPlay = () => (
  <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    <path d="M8 5v14l11-7z" />
  </svg>
)

// APRES
import { Play, Pause, Square, SkipForward, SkipBack } from 'lucide-react'
// Utiliser directement <Play className="h-4 w-4" />
```

### 8.3 Integration dans la page chapitre

Le `ChapterAudioPlayer` est rendu dans la page d'edition de chapitre :

```typescript
// app/projects/[id]/chapters/[idx]/page.tsx
import { LazyChapterAudioPlayer } from '@/features/audio/lazy'
import { AudioErrorBoundary } from '@/features/audio'

// Dans le JSX :
{chapter?.content && (
  <AudioErrorBoundary>
    <LazyChapterAudioPlayer
      chapterId={chapter.id}
      chapterTitle={chapter.title}
      content={chapter.content}
    />
  </AudioErrorBoundary>
)}
```

### 8.4 Indicateurs audio dans le plan

Le badge de progression audio reste dans `plan-chapter-list.tsx` :

```typescript
import { getProgressPercent } from '@/lib/audio-storage'

// Pour chaque chapitre du plan :
const audioProgress = chapterDoc
  ? getProgressPercent(chapterDoc.id, chapterDoc.content || '')
  : 0
```

---

## 9. Phase 5 : Editeur de chapitre

### 9.1 Composant TipTap

**Fichier :** `src/features/editor/chapter-editor.tsx`

```typescript
'use client'

import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'

interface ChapterEditorProps {
  content: string
  onChange: (content: string) => void
  editable?: boolean
}

export function ChapterEditor({ content, onChange, editable = true }: ChapterEditorProps) {
  const editor = useEditor({
    extensions: [
      StarterKit,
      Placeholder.configure({ placeholder: 'Contenu du chapitre...' }),
    ],
    content,
    editable,
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML())
    },
  })

  return (
    <div className="prose prose-stone prose-sm max-w-none">
      <EditorContent editor={editor} />
    </div>
  )
}
```

### 9.2 Barre d'outils editeur

**Fichier :** `src/features/editor/editor-toolbar.tsx`

Barre de formatage (gras, italique, titres) utilisant l'API TipTap.

### 9.3 Layout page edition

La page d'edition de chapitre combine :
- Barre d'outils en haut
- Editeur TipTap au centre
- Audio player TTS en dessous
- Panneau critique IA sur le cote (desktop)

---

## 10. Phase 6 : Tests

### 10.1 Strategie de test

| Couche | Outil | Couverture cible |
|--------|-------|-----------------|
| Services API | Vitest | 100% des fonctions |
| Hooks React Query | Vitest + Testing Library | Queries et mutations |
| Hooks audio | Vitest + mock Web Speech API | Play, pause, seek, persistence |
| Composants UI | Vitest + Testing Library | Rendu, interactions |
| Features | Vitest + Testing Library | Integration composants + hooks |
| E2E | Playwright | Parcours critique (login > dashboard > generer chapitre) |

### 10.2 Tests unitaires services

**Fichier :** `src/services/__tests__/project.service.test.ts`

> **Corrections :**
> - URL attendue : `/projects/?skip=0&limit=100` (trailing slash, limit=100)
> - Response body : `{ projects: [], total: 0 }` (pas `[]`)

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { projectService } from '../project.service'

describe('projectService', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
    localStorage.setItem('auth_token', 'test-token')
  })

  it('list() sends GET /projects/', async () => {
    const mock = vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ projects: [], total: 0 }), { status: 200 })
    )
    const result = await projectService.list()
    expect(mock).toHaveBeenCalledWith(
      expect.stringContaining('/projects/?skip=0&limit=100'),
      expect.any(Object)
    )
    expect(result).toEqual({ projects: [], total: 0 })
  })
})
```

### 10.3 Tests hooks

**Fichier :** `src/hooks/__tests__/use-projects.test.ts`

> **Correction :** Le mock doit retourner `{ projects: [...], total: N }`
> et `data` est de type `{ projects, total }`, pas un array.

```typescript
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, vi } from 'vitest'
import { useProjects } from '../use-projects'
import type { ReactNode } from 'react'

const wrapper = ({ children }: { children: ReactNode }) => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe('useProjects', () => {
  it('fetches project list', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({ projects: [{ id: '1', title: 'Test' }], total: 1 }),
        { status: 200 }
      )
    )
    const { result } = renderHook(() => useProjects(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.projects).toHaveLength(1)
    expect(result.current.data?.total).toBe(1)
  })
})
```

### 10.4 Tests composants

**Fichier :** `src/features/projects/__tests__/project-card-header.test.tsx`

```typescript
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { ProjectCardHeader } from '../project-card-header'

describe('ProjectCardHeader', () => {
  it('displays project title and genre', () => {
    render(
      <ProjectCardHeader
        title="Mon Roman"
        genre="fantasy"
        status="in_progress"
        updatedAt="2025-01-01"
        expanded={false}
        onToggle={() => {}}
      />
    )
    expect(screen.getByText('Mon Roman')).toBeInTheDocument()
    expect(screen.getByText('fantasy')).toBeInTheDocument()
  })
})
```

### 10.5 Tests audio

**Fichier :** `src/lib/__tests__/audio-storage.test.ts`

```typescript
import { describe, it, expect, beforeEach } from 'vitest'
import {
  saveAudioProgress,
  getAudioProgress,
  clearAudioProgress,
  createContentSignature,
} from '../audio-storage'

describe('audio-storage', () => {
  beforeEach(() => localStorage.clear())

  it('saves and retrieves progress', () => {
    const content = 'Chapter content'
    saveAudioProgress({
      chapterId: 'c1',
      position: 50,
      progress: 0.5,
      duration: 60,
      updatedAt: Date.now(),
      contentSignature: createContentSignature(content),
    })
    const entry = getAudioProgress('c1', content)
    expect(entry?.progress).toBe(0.5)
  })

  it('returns null when content changed', () => {
    saveAudioProgress({
      chapterId: 'c1',
      position: 50,
      progress: 0.5,
      duration: 60,
      updatedAt: Date.now(),
      contentSignature: createContentSignature('old content'),
    })
    expect(getAudioProgress('c1', 'new content')).toBeNull()
  })
})
```

### 10.6 Tests E2E

**Fichier :** `e2e/dashboard.spec.ts`

```typescript
import { test, expect } from '@playwright/test'

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto('/auth/login')
    await page.fill('[name="email"]', 'test@example.com')
    await page.fill('[name="password"]', 'password123')
    await page.click('button[type="submit"]')
    await page.waitForURL('/dashboard')
  })

  test('displays project list', async ({ page }) => {
    await expect(page.locator('text=Mes Projets')).toBeVisible()
  })

  test('creates a new project', async ({ page }) => {
    await page.click('text=Nouveau projet')
    await page.selectOption('select', 'fantasy')
    await page.click('text=Generer un concept')
    await expect(page.locator('text=Concept genere')).toBeVisible({ timeout: 30000 })
  })
})
```

### 10.7 Scripts de test

**Ajout dans `package.json` :**

```json
{
  "scripts": {
    "test": "vitest",
    "test:run": "vitest run",
    "test:coverage": "vitest run --coverage",
    "test:e2e": "playwright test"
  }
}
```

---

## 11. Phase 7 : Nettoyage et polish

### 11.1 Fichiers a supprimer

| Fichier | Raison |
|---------|--------|
| `src/app/dashboard/new/page.tsx` | Remplace par les features decoupees |
| `src/app/dashboard/page.tsx` (wrapper) | Remplace par le nouveau dashboard |
| `src/lib/api.ts` | Remplace par `services/api-client.ts` + `stores/auth.store.ts` |
| `src/lib/api-extended.ts` | Remplace par `services/*.service.ts` |
| `src/components/audio/*` | Deplace vers `features/audio/` |
| `src/hooks/index.ts` | Remplace par imports directs |

### 11.2 Icones

Remplacer tous les SVG inline restants par Lucide React :
- `ChevronIcon` dans le dashboard -> `ChevronDown` de lucide-react
- Icones play/pause/stop -> `Play`, `Pause`, `Square` de lucide-react
- Icones skip -> `SkipForward`, `SkipBack` de lucide-react

### 11.3 Schemas Zod

**Fichier :** `src/schemas/project.schema.ts`

```typescript
import { z } from 'zod'

export const createProjectSchema = z.object({
  genre: z.enum(['werewolf', 'billionaire', 'mafia', 'fantasy', ...]),
  title: z.string().min(1).optional(),
  description: z.string().optional(),
})

export const conceptSchema = z.object({
  premise: z.string().min(10, 'La premise doit faire au moins 10 caracteres'),
  tone: z.string().min(1),
  tropes: z.array(z.string()),
  emotional_orientation: z.string().min(1),
})

export type CreateProjectInput = z.infer<typeof createProjectSchema>
export type ConceptInput = z.infer<typeof conceptSchema>
```

### 11.4 Formulaires React Hook Form

Convertir les formulaires existants :

- Login : `useForm` + `loginSchema`
- Register : `useForm` + `registerSchema`
- Create Project Wizard : `useForm` + `createProjectSchema`
- Concept Editor : `useForm` + `conceptSchema`
- Synopsis Editor : `useForm` + `synopsisSchema`

### 11.5 Suppression dependances mortes

```bash
npm uninstall axios next-auth date-fns
```

---

## 12. Arborescence cible

```
frontend/src/
+-- app/
|   +-- layout.tsx                              # Root layout + Providers
|   +-- page.tsx                                # Landing (existant)
|   +-- globals.css                             # Styles globaux (existant)
|   +-- auth/
|   |   +-- login/page.tsx                      # Login (refactorise avec RHF)
|   |   +-- register/page.tsx                   # Register (refactorise avec RHF)
|   +-- dashboard/
|   |   +-- layout.tsx                          # Dashboard layout
|   |   +-- page.tsx                            # Dashboard (60 lignes)
|   +-- projects/
|       +-- [id]/
|           +-- layout.tsx                      # Layout projet
|           +-- page.tsx                        # Vue d'ensemble projet
|           +-- chapters/
|           |   +-- page.tsx                    # Liste chapitres
|           |   +-- [idx]/page.tsx              # Edition chapitre + TTS
|           +-- characters/page.tsx             # Personnages
|           +-- chat/page.tsx                   # Chat IA
|
+-- features/
|   +-- dashboard/
|   |   +-- dashboard-header.tsx
|   |   +-- dashboard-stats.tsx
|   +-- projects/
|   |   +-- project-list.tsx
|   |   +-- project-card.tsx
|   |   +-- project-card-header.tsx
|   |   +-- project-workflow.tsx
|   |   +-- project-actions-bar.tsx
|   |   +-- create-project-wizard.tsx           # Existant, deplace
|   |   +-- delete-project-dialog.tsx
|   |   +-- index.ts
|   +-- synopsis/
|   |   +-- synopsis-section.tsx
|   |   +-- synopsis-editor.tsx
|   |   +-- index.ts
|   +-- plan/
|   |   +-- plan-section.tsx
|   |   +-- plan-chapter-list.tsx
|   |   +-- plan-arc-list.tsx
|   |   +-- index.ts
|   +-- chapters/
|   |   +-- chapter-generator.tsx
|   |   +-- chapter-preview.tsx
|   |   +-- chapter-viewer.tsx
|   |   +-- chapter-critique.tsx
|   |   +-- chapter-list.tsx
|   |   +-- index.ts
|   +-- audio/
|   |   +-- chapter-audio-player.tsx            # Existant
|   |   +-- audio-controls.tsx                  # Existant, icones Lucide
|   |   +-- audio-progress-bar.tsx              # Existant
|   |   +-- audio-player-mini.tsx               # Existant, icones Lucide
|   |   +-- voice-selector.tsx                  # Existant
|   |   +-- speed-control.tsx                   # Existant
|   |   +-- audio-error-boundary.tsx            # Existant
|   |   +-- lazy.tsx                            # Existant
|   |   +-- index.ts
|   +-- editor/
|   |   +-- chapter-editor.tsx                  # TipTap
|   |   +-- editor-toolbar.tsx
|   |   +-- index.ts
|   +-- chat/
|       +-- chat-interface.tsx                  # Existant, deplace
|       +-- index.ts
|
+-- hooks/
|   +-- use-projects.ts                         # React Query hooks projets/concept/synopsis/plan
|   +-- use-chapters.ts                         # React Query hooks pipeline ecriture
|   +-- use-characters.ts                       # React Query hooks personnages
|   +-- use-documents.ts                        # React Query hooks documents/versions/commentaires
|   +-- use-instructions.ts                     # React Query hooks consignes
|   +-- use-project-workflow.ts                 # Derivation etat workflow
|   +-- use-chapter-documents.ts                # Derivation documents chapitres
|   +-- use-speech-synthesis.ts                 # Existant
|   +-- use-audio-keyboard.ts                   # Existant
|
+-- services/
|   +-- api-client.ts                           # Client HTTP generique + downloadFile + types auth
|   +-- auth.service.ts                         # Endpoints auth
|   +-- project.service.ts                      # Endpoints projets/concept/synopsis/plan
|   +-- document.service.ts                     # CRUD documents, versions, commentaires, elements
|   +-- chapter.service.ts                      # Pipeline ecriture (generate/approve)
|   +-- character.service.ts                    # Endpoints personnages
|   +-- instruction.service.ts                  # CRUD consignes d'ecriture
|   +-- chat.service.ts                         # Endpoints chat
|   +-- upload.service.ts                       # Upload fichiers (FormData)
|   +-- agent.service.ts                        # Analyse IA
|
+-- stores/
|   +-- auth.store.ts                           # Zustand auth
|   +-- ui.store.ts                             # Zustand UI state
|
+-- schemas/
|   +-- auth.schema.ts                          # Zod login/register
|   +-- project.schema.ts                       # Zod concept/synopsis
|   +-- chapter.schema.ts                       # Zod generation params
|
+-- components/
|   +-- ui/
|       +-- button.tsx                          # Existant
|       +-- card.tsx                            # Existant
|       +-- input.tsx                           # Existant
|       +-- dialog.tsx                          # Existant
|       +-- badge.tsx                           # Existant
|       +-- select.tsx                          # Existant
|       +-- textarea.tsx                        # Existant
|       +-- skeleton.tsx                        # Nouveau
|       +-- spinner.tsx                         # Nouveau
|       +-- toast.tsx                           # Nouveau (notifications)
|
+-- lib/
|   +-- utils.ts                                # Existant
|   +-- project-helpers.ts                      # Helpers extraits du dashboard
|   +-- audio-storage.ts                        # Existant
|   +-- audio-utils.ts                          # Existant
|
+-- types/
|   +-- index.ts                                # Existant (inchange)
|
+-- test/
|   +-- setup.ts                                # Config Vitest
|   +-- test-utils.tsx                          # Wrapper QueryClient pour tests
|
+-- providers/
    +-- index.tsx                                # QueryClientProvider
```

---

## 13. Checklist globale

```
# Phase 0 : Fondations
- [ ] Supprimer axios, next-auth, date-fns
- [ ] Ajouter vitest, testing-library, playwright (devDependencies)
- [ ] Creer vitest.config.ts
- [ ] Creer src/test/setup.ts
- [ ] Creer src/providers/index.tsx (QueryClientProvider)
- [ ] Modifier app/layout.tsx pour utiliser Providers
- [ ] Creer stores/auth.store.ts (Zustand)
- [ ] Creer stores/ui.store.ts (Zustand)

# Phase 1 : Couche API
- [ ] Creer services/api-client.ts (avec downloadFile, types auth, gestion 204/empty body)
- [ ] Creer services/auth.service.ts
- [ ] Creer services/project.service.ts
- [ ] Creer services/document.service.ts (CRUD + versions + commentaires + elements)
- [ ] Creer services/chapter.service.ts (pipeline generate/approve uniquement)
- [ ] Creer services/character.service.ts (avec generateMainCharacters)
- [ ] Creer services/instruction.service.ts (CRUD consignes)
- [ ] Creer services/chat.service.ts
- [ ] Creer services/upload.service.ts (FormData)
- [ ] Creer services/agent.service.ts (analyse IA)
- [ ] Creer hooks/use-projects.ts (React Query -- avec tous les hooks concept/synopsis/plan)
- [ ] Creer hooks/use-chapters.ts (React Query)
- [ ] Creer hooks/use-characters.ts (React Query)
- [ ] Creer hooks/use-documents.ts (React Query -- versions/commentaires)
- [ ] Creer hooks/use-instructions.ts (React Query)
- [ ] Supprimer lib/api.ts et lib/api-extended.ts

# Phase 2 : Decomposition dashboard
- [ ] Creer lib/project-helpers.ts (fonctions extraites)
- [ ] Creer hooks/use-project-workflow.ts
- [ ] Creer hooks/use-chapter-documents.ts
- [ ] Creer features/dashboard/dashboard-header.tsx
- [ ] Creer features/dashboard/dashboard-stats.tsx
- [ ] Creer features/projects/project-list.tsx
- [ ] Creer features/projects/project-card.tsx (container)
- [ ] Creer features/projects/project-card-header.tsx
- [ ] Creer features/projects/project-workflow.tsx
- [ ] Creer features/projects/project-actions-bar.tsx
- [ ] Creer features/projects/delete-project-dialog.tsx
- [ ] Creer features/synopsis/synopsis-section.tsx
- [ ] Creer features/synopsis/synopsis-editor.tsx
- [ ] Creer features/plan/plan-section.tsx
- [ ] Creer features/plan/plan-chapter-list.tsx
- [ ] Creer features/plan/plan-arc-list.tsx
- [ ] Creer features/chapters/chapter-generator.tsx
- [ ] Creer features/chapters/chapter-preview.tsx
- [ ] Creer features/chapters/chapter-viewer.tsx
- [ ] Creer features/chapters/chapter-critique.tsx
- [ ] Creer features/chapters/chapter-list.tsx
- [ ] Deplacer create-project-wizard.tsx vers features/projects/
- [ ] Supprimer app/dashboard/new/page.tsx

# Phase 3 : Pages et routing
- [ ] Reecrire app/dashboard/page.tsx (compose les features)
- [ ] Creer app/dashboard/layout.tsx
- [ ] Refactoriser app/projects/[id]/page.tsx
- [ ] Creer app/projects/[id]/layout.tsx
- [ ] Creer app/projects/[id]/chapters/page.tsx
- [ ] Creer app/projects/[id]/chapters/[idx]/page.tsx
- [ ] Creer app/projects/[id]/characters/page.tsx
- [ ] Creer app/projects/[id]/chat/page.tsx

# Phase 4 : Integration TTS
- [ ] Deplacer components/audio/ vers features/audio/
- [ ] Remplacer SVG inline par Lucide dans audio-controls.tsx
- [ ] Remplacer SVG inline par Lucide dans audio-player-mini.tsx
- [ ] Integrer AudioPlayer dans la page chapitre
- [ ] Verifier les badges audio dans plan-chapter-list.tsx

# Phase 5 : Editeur de chapitre
- [ ] Creer features/editor/chapter-editor.tsx (TipTap)
- [ ] Creer features/editor/editor-toolbar.tsx
- [ ] Integrer l'editeur dans la page chapitre

# Phase 6 : Tests
- [ ] Tests services : api-client, project.service, chapter.service
- [ ] Tests hooks : use-projects, use-chapters
- [ ] Tests audio : audio-storage, audio-utils
- [ ] Tests composants : project-card-header, synopsis-section, plan-chapter-list
- [ ] Tests E2E : login, dashboard, generation chapitre
- [ ] Ajouter scripts test dans package.json

# Phase 7 : Nettoyage
- [ ] Creer schemas/auth.schema.ts (Zod)
- [ ] Creer schemas/project.schema.ts (Zod)
- [ ] Convertir login en React Hook Form
- [ ] Convertir register en React Hook Form
- [ ] Convertir create-project-wizard en React Hook Form
- [ ] Creer components/ui/skeleton.tsx
- [ ] Creer components/ui/spinner.tsx
- [ ] Supprimer les SVG inline restants (ChevronIcon)
- [ ] npm uninstall axios next-auth date-fns
- [ ] Verifier build TypeScript sans erreurs
- [ ] Verifier ESLint sans warnings
```

---

## Annexes

### A. Ordre de migration recommande

La migration se fait **incrementalement** -- chaque phase produit un frontend fonctionnel.

1. **Phase 0** d'abord : les providers et stores sont la fondation
2. **Phase 1** ensuite : la couche API est un prerequis pour tout le reste
3. **Phase 2** est la plus grosse : decouper le dashboard progressivement
4. **Phases 3-5** en parallele si plusieurs developpeurs
5. **Phase 6** peut commencer des la Phase 1 pour les tests services
6. **Phase 7** en continu, progressivement

### B. Risques identifies

| Risque | Mitigation |
|--------|------------|
| Regression lors du decoupage dashboard | Comparer visuellement avant/apres a chaque etape |
| Perte d'etat lors de la migration useState > React Query | Migrer un bloc a la fois, tester chaque bloc |
| Problemes de cache React Query | Definir des query keys hierarchiques coherentes |
| TipTap HTML vs texte brut pour le TTS | Le hook TTS devra stripper le HTML avant lecture |

### C. Metriques cibles post-refonte

| Metrique | Avant | Cible |
|----------|-------|-------|
| Plus gros fichier | 1207 lignes | < 300 lignes |
| Composants reutilisables | 7 | 25+ |
| Hooks custom | 2 | 10+ |
| Tests | 0 | 50+ |
| Dependances mortes | 6 | 0 |
| Stores | 0 | 2 |

---

*Document cree le 29 janvier 2026*
