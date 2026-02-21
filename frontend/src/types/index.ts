/**
 * TypeScript types for NovellaForge
 */

export enum ProjectStatus {
  DRAFT = 'draft',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
  ARCHIVED = 'archived',
}

export const GENRE_SUGGESTIONS = [
  { value: 'werewolf', label: 'Loup-garou' },
  { value: 'billionaire', label: 'Milliardaire' },
  { value: 'mafia', label: 'Mafia' },
  { value: 'fantasy', label: 'Fantasy' },
  { value: 'vengeance', label: 'Vengeance' },
  { value: 'romance', label: 'Romance' },
  { value: 'thriller', label: 'Thriller' },
  { value: 'scifi', label: 'Science-Fiction' },
  { value: 'mystery', label: 'Mystère' },
  { value: 'horror', label: 'Horreur' },
  { value: 'historical', label: 'Historique' },
];

export const NOVEL_SIZE_PRESETS = [
  { value: '', label: 'Non défini' },
  { value: '15000', label: 'Nouvelle (~15 000 mots)' },
  { value: '50000', label: 'Roman Court (~50 000 mots)' },
  { value: '80000', label: 'Roman Standard (~80 000 mots)' },
  { value: '120000', label: 'Roman Épique (~120 000 mots)' },
];

export interface User {
  id: string;
  email: string;
  full_name: string;
  created_at: string;
}

export interface Project {
  id: string;
  title: string;
  description?: string;
  genre?: string;
  status: ProjectStatus;
  target_word_count?: number;
  target_chapter_count?: number;
  target_chapter_length?: number;
  generation_mode: string;
  current_word_count: number;
  structure_template?: string;
  metadata: Record<string, any>;
  owner_id: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  genre: string;
  title?: string;
  description?: string;
  target_word_count?: number;
  target_chapter_count?: number;
  target_chapter_length?: number;
  generation_mode?: string;
  structure_template?: string;
}

export interface ProjectUpdate {
  title?: string;
  description?: string;
  genre?: string;
  status?: ProjectStatus;
  target_word_count?: number;
  target_chapter_count?: number;
  target_chapter_length?: number;
  current_word_count?: number;
  generation_mode?: string;
  structure_template?: string;
  metadata?: Record<string, any>;
}

export interface ConceptPayload {
  title?: string;
  premise: string;
  tone: string;
  tropes: string[];
  emotional_orientation: string;
}

export interface ConceptProposalResponse {
  status: string;
  concept: ConceptPayload;
  updated_at: string;
}

export interface ConceptResponse {
  project_id: string;
  status: string;
  concept: ConceptPayload;
  updated_at: string;
}

export interface SynopsisResponse {
  project_id: string;
  status: string;
  synopsis: string;
  updated_at: string;
}

export interface SynopsisUpdateRequest {
  synopsis: string;
}

export interface ArcPlan {
  id: string;
  title: string;
  summary: string;
  target_emotion: string;
  chapter_start: number;
  chapter_end: number;
}

export interface ChapterPlan {
  index: number;
  title: string;
  summary: string;
  emotional_stake: string;
  arc_id?: string;
  status?: string;
  cliffhanger_type?: string;
}

export interface PlanPayload {
  global_summary: string;
  arcs: ArcPlan[];
  chapters: ChapterPlan[];
}

export interface PlanResponse {
  project_id: string;
  status: string;
  plan: PlanPayload;
  updated_at: string;
}

export interface ChapterCritique {
  score: number;
  issues: string[];
  suggestions: string[];
  cliffhanger_ok: boolean;
  pacing_ok: boolean;
}

export interface ChapterGenerationResponse {
  success: boolean;
  chapter_title: string;
  plan?: Record<string, any>;
  content: string;
  word_count: number;
  document_id?: string;
  critique?: ChapterCritique;
  needs_review: boolean;
  continuity_alerts: string[];
  retrieved_chunks: string[];
}

export interface ChapterApprovalResponse {
  success: boolean;
  document_id: string;
  status: string;
  summary?: string;
}

export interface Document {
  id: string;
  title: string;
  content: string;
  document_type: 'chapter' | 'scene' | 'note' | 'outline';
  order_index: number;
  word_count: number;
  project_id: string;
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface DocumentVersion {
  id: string;
  version: string;
  created_at: string;
  word_count: number;
  min_word_count?: number;
  max_word_count?: number;
  summary?: string;
  instructions?: string;
  source_version_id?: string;
  source_version?: string;
  source_type?: string;
  source_comment_ids?: string[];
  content?: string;
  is_current?: boolean;
}

export interface DocumentComment {
  id: string;
  content: string;
  created_at: string;
  user_id: string;
  version_id?: string | null;
  applied_version_ids?: string[];
}

export interface Character {
  id: string;
  name: string;
  role?: 'protagonist' | 'antagonist' | 'supporting' | 'minor';
  description?: string;
  personality_traits?: string[];
  personality?: string;
  physical_description?: string;
  backstory?: string;
  goals?: string;
  relationships?: Record<string, string>;
  metadata: Record<string, any>;
  project_id: string;
  created_at: string;
  updated_at: string;
}

export interface CharacterCreate {
  name: string;
  project_id: string;
  description?: string;
  physical_description?: string;
  personality?: string;
  backstory?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  project_id?: string;
  metadata?: Record<string, any>;
  created_at: string;
}

export interface ChatSession {
  id: string;
  project_id?: string;
  title: string;
  messages: ChatMessage[];
  created_at: string;
  updated_at: string;
}

export interface AgentTask {
  id: string;
  agent_type: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  input_data: Record<string, any>;
  result?: Record<string, any>;
  error?: string;
  created_at: string;
  updated_at: string;
}

export interface Instruction {
  id: string;
  title: string;
  detail: string;
  created_at: string;
}
