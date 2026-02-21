/**
 * Extended API client for projects, documents, characters, and chat
 */

import { getAuthToken, removeAuthToken } from './api';
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
  ChapterGenerationResponse,
  ChapterApprovalResponse,
  Document,
  Character,
  CharacterCreate,
  ChatMessage,
  Instruction,
  DocumentVersion,
  DocumentComment,
} from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8002/api/v1';

/**
 * Helper to get auth headers
 */
function getAuthHeaders(): HeadersInit {
  const token = getAuthToken();
  return {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
  };
}

function getDownloadFilename(disposition: string | null, fallback: string): string {
  if (!disposition) return fallback;
  const match = disposition.match(/filename\*=UTF-8''([^;]+)|filename="?([^\";]+)"?/i);
  const filename = match?.[1] || match?.[2];
  if (!filename) return fallback;
  try {
    return decodeURIComponent(filename);
  } catch {
    return filename;
  }
}

async function downloadFile(path: string, fallbackName: string): Promise<{ blob: Blob; filename: string }> {
  const token = getAuthToken();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      ...(token && { Authorization: `Bearer ${token}` }),
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Download failed' }));
    if (response.status === 401) {
      removeAuthToken();
      throw new Error(error.detail || 'Not authenticated');
    }
    throw new Error(error.detail || `HTTP error! status: ${response.status}`);
  }

  const blob = await response.blob();
  const filename = getDownloadFilename(response.headers.get('Content-Disposition'), fallbackName);
  return { blob, filename };
}

/**
 * Generic fetch wrapper with error handling
 */
async function apiFetch<T>(url: string, options?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${url}`, {
      ...options,
      headers: {
        ...getAuthHeaders(),
        ...options?.headers,
      },
    });
  } catch {
    throw new Error("Impossible de contacter l'API. Verifiez que le backend tourne.");
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'An error occurred' }));
    if (response.status === 401) {
      removeAuthToken();
      throw new Error(error.detail || 'Not authenticated');
    }
    throw new Error(error.detail || `HTTP error! status: ${response.status}`);
  }

  if (response.status === 204) {
    return null as T;
  }

  const text = await response.text();
  if (!text) {
    return null as T;
  }

  return JSON.parse(text) as T;
}

// ============================================================================
// PROJECTS
// ============================================================================

export async function getProjects(skip = 0, limit = 100): Promise<{ projects: Project[]; total: number }> {
  return apiFetch(`/projects/?skip=${skip}&limit=${limit}`);
}

export async function getProject(id: string): Promise<Project> {
  return apiFetch(`/projects/${id}`);
}

export async function createProject(data: ProjectCreate): Promise<Project> {
  return apiFetch('/projects/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateProject(id: string, data: ProjectUpdate): Promise<Project> {
  return apiFetch(`/projects/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteProject(id: string, confirmTitle: string): Promise<void> {
  await apiFetch(`/projects/${id}/delete`, {
    method: 'POST',
    body: JSON.stringify({ confirm_title: confirmTitle }),
  });
}

export async function getConcept(projectId: string): Promise<ConceptResponse> {
  return apiFetch(`/projects/${projectId}/concept`);
}

export async function generateConceptProposal(
  genre: ProjectCreate['genre'],
  notes?: string
): Promise<ConceptProposalResponse> {
  return apiFetch('/projects/concept/proposal', {
    method: 'POST',
    body: JSON.stringify({ genre, notes }),
  });
}

export async function generateConcept(projectId: string, force = false): Promise<ConceptResponse> {
  return apiFetch(`/projects/${projectId}/concept/generate`, {
    method: 'POST',
    body: JSON.stringify({ force }),
  });
}

export async function acceptConcept(projectId: string, concept: ConceptPayload): Promise<ConceptResponse> {
  return apiFetch(`/projects/${projectId}/concept`, {
    method: 'PUT',
    body: JSON.stringify(concept),
  });
}

export async function getPlan(projectId: string): Promise<PlanResponse> {
  return apiFetch(`/projects/${projectId}/plan`);
}

export async function generatePlan(projectId: string, chapterCount?: number, arcCount?: number): Promise<PlanResponse> {
  return apiFetch(`/projects/${projectId}/plan/generate`, {
    method: 'POST',
    body: JSON.stringify({ chapter_count: chapterCount, arc_count: arcCount }),
  });
}

export async function acceptPlan(projectId: string): Promise<PlanResponse> {
  return apiFetch(`/projects/${projectId}/plan/accept`, {
    method: 'PUT',
  });
}

export async function updatePlan(projectId: string, plan: PlanPayload): Promise<PlanResponse> {
  return apiFetch(`/projects/${projectId}/plan`, {
    method: 'PUT',
    body: JSON.stringify({ plan }),
  });
}

export async function getSynopsis(projectId: string): Promise<SynopsisResponse> {
  return apiFetch(`/projects/${projectId}/synopsis`);
}

export async function generateSynopsis(projectId: string, notes?: string): Promise<SynopsisResponse> {
  return apiFetch(`/projects/${projectId}/synopsis/generate`, {
    method: 'POST',
    body: JSON.stringify({ notes }),
  });
}

export async function updateSynopsis(projectId: string, payload: SynopsisUpdateRequest): Promise<SynopsisResponse> {
  return apiFetch(`/projects/${projectId}/synopsis`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function acceptSynopsis(projectId: string): Promise<SynopsisResponse> {
  return apiFetch(`/projects/${projectId}/synopsis/accept`, {
    method: 'PUT',
  });
}

export async function listInstructions(projectId: string): Promise<Instruction[]> {
  const response = await apiFetch<{ instructions: Instruction[] }>(`/projects/${projectId}/instructions`);
  return Array.isArray(response) ? response : response.instructions ?? [];
}

export async function createInstruction(
  projectId: string,
  data: Pick<Instruction, 'title' | 'detail'>
): Promise<Instruction> {
  return apiFetch(`/projects/${projectId}/instructions`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateInstruction(
  projectId: string,
  instructionId: string,
  data: Partial<Pick<Instruction, 'title' | 'detail'>>
): Promise<Instruction> {
  return apiFetch(`/projects/${projectId}/instructions/${instructionId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteInstruction(projectId: string, instructionId: string): Promise<void> {
  await apiFetch(`/projects/${projectId}/instructions/${instructionId}`, { method: 'DELETE' });
}

// ============================================================================
// DOCUMENTS
// ============================================================================

export async function getDocuments(projectId: string): Promise<Document[]> {
  const response = await apiFetch<{ documents: Document[] }>(`/documents/?project_id=${projectId}`);
  return Array.isArray(response) ? response : response.documents ?? [];
}

export async function getDocument(id: string): Promise<Document> {
  return apiFetch(`/documents/${id}`);
}

export async function createDocument(data: Partial<Document>): Promise<Document> {
  return apiFetch('/documents', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateDocument(id: string, data: Partial<Document>): Promise<Document> {
  return apiFetch(`/documents/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteDocument(id: string): Promise<void> {
  await apiFetch(`/documents/${id}`, { method: 'DELETE' });
}

export async function createElement(
  projectId: string,
  elementType: string,
  parentId?: string
): Promise<Document> {
  return apiFetch('/documents/elements', {
    method: 'POST',
    body: JSON.stringify({
      project_id: projectId,
      element_type: elementType,
      parent_id: parentId || undefined,
    }),
  });
}

export async function generateElement(
  documentId: string,
  instructions?: string,
  minWordCount?: number,
  maxWordCount?: number,
  summary?: string,
  sourceVersionId?: string,
  commentIds?: string[]
): Promise<Document> {
  return apiFetch(`/documents/${documentId}/generate`, {
    method: 'POST',
    body: JSON.stringify({
      instructions,
      min_word_count: minWordCount,
      max_word_count: maxWordCount,
      summary,
      source_version_id: sourceVersionId,
      comment_ids: Array.isArray(commentIds) ? commentIds : undefined,
    }),
  });
}

export async function listDocumentVersions(documentId: string): Promise<DocumentVersion[]> {
  const response = await apiFetch<{ versions: DocumentVersion[] }>(`/documents/${documentId}/versions`);
  return Array.isArray(response) ? response : response.versions ?? [];
}

export async function getDocumentVersion(documentId: string, versionId: string): Promise<DocumentVersion> {
  return apiFetch(`/documents/${documentId}/versions/${versionId}`);
}

export async function createDocumentVersion(
  documentId: string,
  content: string,
  sourceVersionId?: string
): Promise<Document> {
  return apiFetch(`/documents/${documentId}/versions`, {
    method: 'POST',
    body: JSON.stringify({
      content,
      source_version_id: sourceVersionId,
    }),
  });
}

export async function listDocumentComments(documentId: string): Promise<DocumentComment[]> {
  const response = await apiFetch<{ comments: DocumentComment[] }>(`/documents/${documentId}/comments`);
  return Array.isArray(response) ? response : response.comments ?? [];
}

export async function createDocumentComment(
  documentId: string,
  content: string,
  versionId?: string
): Promise<DocumentComment> {
  return apiFetch(`/documents/${documentId}/comments`, {
    method: 'POST',
    body: JSON.stringify({
      content,
      version_id: versionId || undefined,
    }),
  });
}

// ============================================================================
// WRITING PIPELINE
// ============================================================================

export async function generateChapter(payload: {
  project_id: string;
  chapter_id?: string;
  chapter_index?: number;
  instruction?: string;
  rewrite_focus?: 'emotion' | 'tension' | 'action' | 'custom';
  target_word_count?: number;
  use_rag?: boolean;
  reindex_documents?: boolean;
  create_document?: boolean;
  auto_approve?: boolean;
}): Promise<ChapterGenerationResponse> {
  return apiFetch('/writing/generate-chapter', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function approveChapter(documentId: string): Promise<ChapterApprovalResponse> {
  return apiFetch('/writing/approve-chapter', {
    method: 'POST',
    body: JSON.stringify({ document_id: documentId }),
  });
}

// ============================================================================
// CHARACTERS
// ============================================================================

export async function getCharacters(projectId: string): Promise<Character[]> {
  const response = await apiFetch<{ characters: Character[] }>(`/characters?project_id=${projectId}`);
  return Array.isArray(response) ? response : response.characters ?? [];
}

export async function getCharacter(id: string): Promise<Character> {
  return apiFetch(`/characters/${id}`);
}

export async function createCharacter(data: CharacterCreate): Promise<Character> {
  return apiFetch('/characters', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateCharacter(id: string, data: Partial<Character>): Promise<Character> {
  return apiFetch(`/characters/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteCharacter(id: string): Promise<void> {
  await apiFetch(`/characters/${id}`, { method: 'DELETE' });
}

export async function generateMainCharacters(
  projectId: string,
  summary: string,
  precision?: string
): Promise<Character[]> {
  const response = await apiFetch<{ characters: Character[] }>(`/characters/auto`, {
    method: 'POST',
    body: JSON.stringify({
      project_id: projectId,
      summary,
      precision,
    }),
  });
  return Array.isArray(response) ? response : response.characters ?? [];
}

// ============================================================================
// CHAT
// ============================================================================

export async function sendChatMessage(
  message: string,
  projectId?: string
): Promise<{ response: string; message_id: string }> {
  return apiFetch('/chat/message', {
    method: 'POST',
    body: JSON.stringify({
      message,
      project_id: projectId,
    }),
  });
}

export async function getChatHistory(projectId?: string, limit = 50): Promise<ChatMessage[]> {
  const query = projectId ? `?project_id=${projectId}&limit=${limit}` : `?limit=${limit}`;
  const response = await apiFetch<{ messages: ChatMessage[] }>(`/chat/history${query}`);
  return Array.isArray(response) ? response : response.messages ?? [];
}

// ============================================================================
// FILE UPLOAD
// ============================================================================

export async function uploadFile(file: File, projectId: string): Promise<{ document_id: string; message: string }> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('project_id', projectId);

  const token = getAuthToken();
  const response = await fetch(`${API_BASE_URL}/upload`, {
    method: 'POST',
    headers: {
      ...(token && { Authorization: `Bearer ${token}` }),
    },
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
    if (response.status === 401) {
      removeAuthToken();
      throw new Error(error.detail || 'Not authenticated');
    }
    throw new Error(error.detail);
  }

  return response.json();
}

// ============================================================================
// AI AGENTS
// ============================================================================

export async function runAnalysis(
  projectId: string,
  analysisType: string,
  data?: Record<string, any>
): Promise<{ task_id: string }> {
  return apiFetch('/agents/analyze', {
    method: 'POST',
    body: JSON.stringify({
      project_id: projectId,
      analysis_type: analysisType,
      data,
    }),
  });
}

export async function getAnalysisStatus(taskId: string): Promise<any> {
  return apiFetch(`/agents/analysis/${taskId}`);
}

// ============================================================================
// DOWNLOADS
// ============================================================================

export async function downloadDocument(documentId: string): Promise<{ blob: Blob; filename: string }> {
  return downloadFile(`/documents/${documentId}/download`, `document-${documentId}.md`);
}

export async function downloadProject(projectId: string): Promise<{ blob: Blob; filename: string }> {
  return downloadFile(`/projects/${projectId}/download`, `project-${projectId}.zip`);
}

export async function lazyGenerateNext(
  projectId: string,
  instruction?: string,
  targetWordCount?: number
): Promise<{
  success: boolean;
  chapter_title: string;
  content: string;
  word_count: number;
  document_id: string;
}> {
  return apiFetch('/writing/lazy-generate-next', {
    method: 'POST',
    body: JSON.stringify({
      project_id: projectId,
      instruction,
      target_word_count: targetWordCount,
    }),
  });
}

/**
 * Stream lazy chapter generation via WebSocket.
 * Returns a close function to disconnect.
 */
export function lazyGenerateNextWs(
  projectId: string,
  options: {
    instruction?: string;
    targetWordCount?: number;
    onStatus?: (message: string) => void;
    onChunk?: (content: string, beatIndex: number) => void;
    onComplete?: (data: {
      chapter_title: string;
      content: string;
      document_id: string;
      word_count: number;
    }) => void;
    onError?: (message: string) => void;
  }
): () => void {
  const token = getAuthToken();
  if (!token) {
    options.onError?.('Not authenticated');
    return () => { };
  }

  const wsBase = (process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8002/api/v1')
    .replace(/^http/, 'ws');
  const ws = new WebSocket(`${wsBase}/writing/ws/lazy-generate/${projectId}`);

  ws.onopen = () => {
    ws.send(
      JSON.stringify({
        token,
        instruction: options.instruction,
        target_word_count: options.targetWordCount,
      })
    );
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      switch (data.type) {
        case 'status':
          options.onStatus?.(data.message);
          break;
        case 'chunk':
          options.onChunk?.(data.content, data.beat_index);
          break;
        case 'complete':
          options.onComplete?.({
            chapter_title: data.chapter_title,
            content: data.content,
            document_id: data.document_id,
            word_count: data.word_count,
          });
          break;
        case 'error':
          options.onError?.(data.message);
          break;
      }
    } catch {
      // Ignore parse errors
    }
  };

  ws.onerror = () => {
    options.onError?.('WebSocket connection error');
  };

  ws.onclose = () => {
    // Closed
  };

  return () => {
    if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
      ws.close();
    }
  };
}

