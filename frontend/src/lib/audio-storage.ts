/**
 * Local storage helpers for audio preferences and progress.
 */

import { clamp } from './audio-utils';

const PREFERENCES_KEY = 'novellaforge-audio-preferences';
const PROGRESS_KEY = 'novellaforge-audio-progress';

export interface AudioPreferences {
  voiceId?: string | null;
  rate?: number;
  pitch?: number;
  volume?: number;
}

export interface AudioProgressEntry {
  chapterId: string;
  position: number;
  progress: number;
  duration?: number;
  updatedAt: number;
  contentSignature: string;
}

type ProgressMap = Record<string, AudioProgressEntry>;

const isBrowser = () => typeof window !== 'undefined' && typeof window.localStorage !== 'undefined';

export function createContentSignature(text: string): string {
  const length = text.length;
  const head = text.slice(0, 48);
  const tail = text.slice(-48);
  return `${length}:${head}|${tail}`;
}

function loadJson<T>(key: string, fallback: T): T {
  if (!isBrowser()) return fallback;
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return fallback;
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

function saveJson<T>(key: string, value: T): void {
  if (!isBrowser()) return;
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Ignore storage write errors.
  }
}

export function loadAudioPreferences(): Required<AudioPreferences> {
  const stored = loadJson<AudioPreferences>(PREFERENCES_KEY, {});
  return {
    voiceId: stored.voiceId ?? null,
    rate: stored.rate ?? 1,
    pitch: stored.pitch ?? 1,
    volume: stored.volume ?? 1,
  };
}

export function saveAudioPreferences(preferences: AudioPreferences): void {
  const existing = loadJson<AudioPreferences>(PREFERENCES_KEY, {});
  saveJson(PREFERENCES_KEY, { ...existing, ...preferences });
}

function loadProgressMap(): ProgressMap {
  return loadJson<ProgressMap>(PROGRESS_KEY, {});
}

function saveProgressMap(map: ProgressMap): void {
  saveJson(PROGRESS_KEY, map);
}

export function saveAudioProgress(entry: AudioProgressEntry): void {
  if (!entry.chapterId) return;
  const map = loadProgressMap();
  map[entry.chapterId] = {
    ...entry,
    progress: clamp(entry.progress, 0, 1),
  };
  saveProgressMap(map);
}

export function getAudioProgress(chapterId: string, content: string): AudioProgressEntry | null {
  if (!chapterId) return null;
  const map = loadProgressMap();
  const entry = map[chapterId];
  if (!entry) return null;
  const signature = createContentSignature(content);
  if (signature !== entry.contentSignature) return null;
  return entry;
}

export function getProgressPercent(chapterId: string, content: string): number {
  const entry = getAudioProgress(chapterId, content);
  if (!entry) return 0;
  return Math.round(clamp(entry.progress, 0, 1) * 100);
}

export function clearAudioProgress(chapterId?: string): void {
  if (!isBrowser()) return;
  if (!chapterId) {
    saveProgressMap({});
    return;
  }
  const map = loadProgressMap();
  delete map[chapterId];
  saveProgressMap(map);
}
