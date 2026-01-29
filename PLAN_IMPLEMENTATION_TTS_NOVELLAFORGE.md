# Plan d'Implementation - Lecture Audio des Chapitres

## NovellaForge - Text-to-Speech Feature

**Version:** 1.1 (mise a jour post-implementation)
**Date:** Janvier 2025
**Statut:** Implemente

---

## Table des Matieres

1. [Vue d'Ensemble](#1-vue-densemble)
2. [Architecture Technique](#2-architecture-technique)
3. [Prerequis](#3-prerequis)
4. [Structure des Fichiers](#4-structure-des-fichiers)
5. [Phase 1 : Infrastructure de Base](#5-phase-1--infrastructure-de-base)
6. [Phase 2 : Hook de Synthese Vocale](#6-phase-2--hook-de-synthese-vocale)
7. [Phase 3 : Composants UI](#7-phase-3--composants-ui)
8. [Phase 4 : Integration Dashboard](#8-phase-4--integration-dashboard)
9. [Phase 5 : Optimisations UX](#9-phase-5--optimisations-ux)
10. [Phase 6 : Tests](#10-phase-6--tests)
11. [Phase 7 : Deploiement Production](#11-phase-7--deploiement-production)
12. [Evolutions Futures](#12-evolutions-futures)
13. [Checklist de Lancement](#13-checklist-de-lancement)

---

## 1. Vue d'Ensemble

### 1.1 Objectif

Permettre aux utilisateurs d'ecouter leurs chapitres generes avec :
- Choix de la voix et de la vitesse de lecture
- Controles de lecture (play/pause/stop/seek)
- Sauvegarde automatique de la progression
- Reprise la ou l'utilisateur s'est arrete

### 1.2 Fonctionnalites Cles

| Fonctionnalite | Priorite | Statut |
|----------------|----------|--------|
| Lecture/Pause/Stop | P0 | Fait |
| Choix de la voix | P0 | Fait |
| Choix de la vitesse | P0 | Fait |
| Barre de progression | P0 | Fait |
| Sauvegarde position | P0 | Fait |
| Navigation +/-15s | P1 | Fait |
| Mot courant affiche | P1 | Fait |
| Raccourcis clavier | P2 | Fait |
| Lazy loading | P2 | Fait |
| Error boundary | P2 | Fait |
| Mini player replie | P2 | Fait |

### 1.3 Criteres de Succes

- [x] Temps de demarrage lecture < 500ms
- [x] Position sauvegardee avec signature de contenu
- [x] Compatible Chrome, Safari, Firefox, Edge
- [x] Zero regression sur les fonctionnalites existantes

---

## 2. Architecture Technique

### 2.1 Diagramme d'Architecture

```
+---------------------------------------------------------------------------+
|                           FRONTEND (Next.js)                              |
+---------------------------------------------------------------------------+
|                                                                           |
|  +-------------------------------------------------------------------+   |
|  |                    Page Dashboard / Projet                         |   |
|  |  +-------------------------------------------------------------+  |   |
|  |  |    AudioErrorBoundary > LazyChapterAudioPlayer               |  |   |
|  |  |                                                              |  |   |
|  |  |   +-------------+  +--------------+  +-----------------+    |  |   |
|  |  |   |AudioControls|  |ProgressBar   |  |AudioPlayerMini  |    |  |   |
|  |  |   +-------------+  +--------------+  +-----------------+    |  |   |
|  |  |                                                              |  |   |
|  |  |   +--------------+  +--------------+                         |  |   |
|  |  |   |VoiceSelector |  |SpeedControl  |                         |  |   |
|  |  |   +--------------+  +--------------+                         |  |   |
|  |  +-------------------------------------------------------------+  |   |
|  +-------------------------------------------------------------------+   |
|                              |                                            |
|                              v                                            |
|  +-------------------------------------------------------------------+   |
|  |                    useSpeechSynthesis Hook                          |   |
|  |  - Gestion Web Speech API                                          |   |
|  |  - Etat de lecture (play/pause/position)                           |   |
|  |  - Gestion des voix disponibles                                    |   |
|  |  - Persistance automatique de la progression                       |   |
|  +-------------------------------------------------------------------+   |
|                              |                                            |
|                              v                                            |
|  +-------------------------------------------------------------------+   |
|  |                    Audio Storage (localStorage)                    |   |
|  |  - Progression par chapitre (avec contentSignature)                |   |
|  |  - Preferences utilisateur (voix, vitesse, pitch, volume)         |   |
|  +-------------------------------------------------------------------+   |
|                                                                           |
+---------------------------------------------------------------------------+
```

### 2.2 Flux de Donnees

```
+----------+     +---------------+     +--------------------+
|  User    |---->| AudioPlayer   |---->| useSpeechSynthesis |
|  Action  |     | Component     |     | Hook               |
+----------+     +---------------+     +--------------------+
                                              |
                        +---------------------+---------------------+
                        v                     v                     v
              +-----------------+  +-----------------+  +-----------------+
              | Web Speech API  |  | localStorage    |  | React State     |
              | (speechSynthesis)|  | (persistence)   |  | (UI updates)    |
              +-----------------+  +-----------------+  +-----------------+
```

### 2.3 Technologies Utilisees

| Composant | Technologie | Justification |
|-----------|-------------|---------------|
| TTS Engine | Web Speech API | Natif, gratuit, performant |
| State Management | React Hooks + Refs | Leger, pas de dependance externe |
| Persistence | localStorage | Simple, synchrone, fiable |
| UI Components | Tailwind CSS | Coherent avec le projet existant |
| Icons | SVG inline | Pas de dependance supplementaire |
| Lazy Loading | next/dynamic | SSR-safe, skeleton loading |

---

## 3. Prerequis

### 3.1 Environnement de Developpement

```bash
# Versions requises
node >= 18.0.0
npm >= 9.0.0 ou yarn >= 1.22.0
next >= 15.0.0
react >= 18.0.0
typescript >= 5.0.0
```

### 3.2 Navigateurs Supportes

| Navigateur | Version Min | Support Web Speech API |
|------------|-------------|------------------------|
| Chrome | 33+ | Complet |
| Safari | 14.1+ | Complet |
| Firefox | 49+ | Complet |
| Edge | 79+ | Complet |
| Opera | 21+ | Complet |
| iOS Safari | 14.5+ | Partiel (limite) |
| Android Chrome | 33+ | Complet |

---

## 4. Structure des Fichiers

### 4.1 Arborescence Implementee

```
frontend/src/
+-- components/
|   +-- audio/
|   |   +-- index.ts                      # Exports publics
|   |   +-- chapter-audio-player.tsx      # Composant principal
|   |   +-- audio-controls.tsx            # Boutons de controle
|   |   +-- audio-progress-bar.tsx        # Barre de progression
|   |   +-- voice-selector.tsx            # Selecteur de voix
|   |   +-- speed-control.tsx             # Controle de vitesse
|   |   +-- audio-player-mini.tsx         # Version compacte (header replie)
|   |   +-- audio-error-boundary.tsx      # Error boundary React
|   |   +-- lazy.tsx                      # Chargement dynamique (SSR-safe)
|   +-- ui/
|       +-- ... (existant)
+-- hooks/
|   +-- index.ts                          # Exports publics
|   +-- use-speech-synthesis.ts           # Hook principal TTS
|   +-- use-audio-keyboard.ts             # Raccourcis clavier
+-- lib/
|   +-- audio-storage.ts                  # Persistence localStorage
|   +-- audio-utils.ts                    # Utilitaires audio
|   +-- ... (existant)
+-- app/
    +-- dashboard/
        +-- new/
            +-- page.tsx                  # Integration (modifie)
```

> **Note :** Les types TypeScript sont definis directement dans les fichiers qui les utilisent
> (hook, storage, composants) plutot que dans un fichier `types/audio.ts` centralise.

---

## 5. Phase 1 : Infrastructure de Base

### 5.1 Utilitaires Audio

**Fichier :** `src/lib/audio-utils.ts`

```typescript
/**
 * Audio utility helpers for speech synthesis.
 */

const BASE_WPM = 180;

export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

export function countWords(text: string): number {
  const matches = text.trim().match(/\S+/g);
  return matches ? matches.length : 0;
}

export function estimateDurationSeconds(text: string, rate: number): number {
  const words = countWords(text);
  if (!words) return 0;
  const safeRate = rate > 0 ? rate : 1;
  return (words / (BASE_WPM * safeRate)) * 60;
}

export type WordData = {
  words: string[];
  offsets: number[];
};

export function buildWordData(text: string): WordData {
  const words: string[] = [];
  const offsets: number[] = [];
  const regex = /\S+/g;
  let match: RegExpExecArray | null;
  while ((match = regex.exec(text)) !== null) {
    words.push(match[0]);
    offsets.push(match.index);
  }
  return { words, offsets };
}

export function getWordIndexFromCharIndex(offsets: number[], charIndex: number): number {
  if (offsets.length === 0) return 0;
  let low = 0;
  let high = offsets.length - 1;
  while (low <= high) {
    const mid = Math.floor((low + high) / 2);
    if (offsets[mid] <= charIndex) {
      low = mid + 1;
    } else {
      high = mid - 1;
    }
  }
  return clamp(low - 1, 0, offsets.length - 1);
}

export function getCharIndexFromWordIndex(offsets: number[], wordIndex: number): number {
  if (offsets.length === 0) return 0;
  const clamped = clamp(wordIndex, 0, offsets.length - 1);
  return offsets[clamped] ?? 0;
}
```

**Points cles :**
- Estimation de duree basee sur 180 mots/minute (standard lecture a voix haute)
- `buildWordData` construit un index mot/offset pour le suivi en temps reel
- `getWordIndexFromCharIndex` utilise une recherche binaire pour les performances
- `clamp` utilise partout pour securiser les bornes

### 5.2 Module de Stockage

**Fichier :** `src/lib/audio-storage.ts`

```typescript
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
  progress: number;           // 0-1
  duration?: number;
  updatedAt: number;
  contentSignature: string;   // Detecte si le contenu a change
}

type ProgressMap = Record<string, AudioProgressEntry>;

const isBrowser = () =>
  typeof window !== 'undefined' && typeof window.localStorage !== 'undefined';

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

export function getAudioProgress(
  chapterId: string,
  content: string
): AudioProgressEntry | null {
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
```

**Points cles :**
- `contentSignature` : hash leger (longueur + 48 premiers/derniers caracteres) pour
  detecter si le texte du chapitre a ete modifie depuis la derniere sauvegarde
- Progression stockee sur 0-1 (pas 0-100)
- Persistance throttled a 1500ms dans le hook (voir Phase 2)
- Pas de gestion d'historique ni de statistiques (YAGNI)

---

## 6. Phase 2 : Hook de Synthese Vocale

### 6.1 Hook Principal

**Fichier :** `src/hooks/use-speech-synthesis.ts`

```typescript
'use client'

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  buildWordData,
  clamp,
  estimateDurationSeconds,
  getCharIndexFromWordIndex,
  getWordIndexFromCharIndex,
} from '@/lib/audio-utils';
import {
  createContentSignature,
  getAudioProgress,
  loadAudioPreferences,
  saveAudioPreferences,
  saveAudioProgress,
} from '@/lib/audio-storage';

export type SpeechStatus = 'idle' | 'playing' | 'paused' | 'stopped' | 'error';

export interface SpeechState {
  status: SpeechStatus;
  currentPosition: number;      // Index caractere dans le texte
  progress: number;              // 0-1
  currentTime: number;           // Secondes ecoulees (estime)
  duration: number;              // Duree totale estimee (secondes)
  currentWord: string;           // Mot en cours de lecture
  error: string | null;
}

export interface SpeechConfig {
  rate: number;                  // 0.5-2.5
  pitch: number;
  volume: number;
  voiceId: string | null;
}

export interface SpeechVoice {
  id: string;
  name: string;
  lang: string;
  localService: boolean;
  default: boolean;
}

export interface UseSpeechSynthesisOptions {
  chapterId: string;
  text: string;
}

const initialState: SpeechState = {
  status: 'idle',
  currentPosition: 0,
  progress: 0,
  currentTime: 0,
  duration: 0,
  currentWord: '',
  error: null,
};

export function useSpeechSynthesis({ chapterId, text }: UseSpeechSynthesisOptions) {
  // --- State ---
  const [state, setState] = useState<SpeechState>(initialState);
  const [config, setConfig] = useState<SpeechConfig>(() => {
    const prefs = loadAudioPreferences();
    return {
      rate: prefs.rate ?? 1,
      pitch: prefs.pitch ?? 1,
      volume: prefs.volume ?? 1,
      voiceId: prefs.voiceId ?? null,
    };
  });
  const [voices, setVoices] = useState<SpeechVoice[]>([]);
  const [isSupported, setIsSupported] = useState(false);
  const [isReady, setIsReady] = useState(false);

  // --- Refs pour eviter les closures perimees ---
  const synthRef = useRef<SpeechSynthesis | null>(null);
  const browserVoicesRef = useRef<SpeechSynthesisVoice[]>([]);
  const stateRef = useRef(state);
  const configRef = useRef(config);
  const chapterIdRef = useRef(chapterId);
  const textRef = useRef(text ?? '');
  const wordDataRef = useRef(buildWordData(text ?? ''));
  const contentSignatureRef = useRef(createContentSignature(text ?? ''));
  const utteranceIdRef = useRef(0);
  const currentUtteranceIdRef = useRef<number | null>(null);
  const cancelledUtterancesRef = useRef<Set<number>>(new Set());
  const hasBoundaryUpdatesRef = useRef(false);
  const progressTimerRef = useRef<number | null>(null);
  const playbackStartRef = useRef<number | null>(null);
  const lastPersistRef = useRef(0);

  // Synchroniser les refs
  useEffect(() => { stateRef.current = state; }, [state]);
  useEffect(() => {
    configRef.current = config;
    saveAudioPreferences(config);
  }, [config]);

  // --- Chargement des voix ---
  const loadVoices = useCallback(() => {
    const synth = synthRef.current;
    if (!synth) return;
    const list = synth.getVoices() || [];
    browserVoicesRef.current = list;
    const mapped = list.map((voice) => ({
      id: voice.voiceURI || voice.name,
      name: voice.name,
      lang: voice.lang,
      localService: voice.localService,
      default: voice.default,
    }));
    setVoices(mapped);
    setIsReady(mapped.length > 0);
  }, []);

  // --- Initialisation ---
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const supported =
      'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window;
    setIsSupported(supported);
    if (!supported) return;
    synthRef.current = window.speechSynthesis;
    loadVoices();
    const handleVoicesChanged = () => loadVoices();
    window.speechSynthesis.onvoiceschanged = handleVoicesChanged;
    return () => {
      if (window.speechSynthesis.onvoiceschanged === handleVoicesChanged) {
        window.speechSynthesis.onvoiceschanged = null;
      }
    };
  }, [loadVoices]);

  // Selection automatique de la voix par defaut
  useEffect(() => {
    if (!voices.length) return;
    const currentVoice = configRef.current.voiceId;
    const hasVoice =
      currentVoice && voices.some((voice) => voice.id === currentVoice);
    if (hasVoice) return;
    const preferred = voices.find((voice) => voice.default) ?? voices[0];
    if (!preferred) return;
    setConfig((prev) => ({ ...prev, voiceId: preferred.id }));
  }, [voices]);

  // --- Timer de progression (fallback quand onboundary n'est pas supporte) ---
  const stopProgressTimer = useCallback(() => {
    if (progressTimerRef.current !== null) {
      window.clearInterval(progressTimerRef.current);
      progressTimerRef.current = null;
    }
  }, []);

  const updateStateFromPosition = useCallback((position: number) => {
    const fullText = textRef.current;
    const safePosition = clamp(position, 0, fullText.length || 0);
    const progress = fullText.length ? safePosition / fullText.length : 0;
    const duration = stateRef.current.duration;
    const currentTime = duration ? progress * duration : 0;
    const wordData = wordDataRef.current;
    const wordIndex = getWordIndexFromCharIndex(wordData.offsets, safePosition);
    const currentWord = wordData.words[wordIndex] ?? '';
    setState((prev) => ({
      ...prev,
      currentPosition: safePosition,
      progress,
      currentTime,
      currentWord,
      error: null,
    }));
  }, []);

  const persistProgress = useCallback((position: number, progress: number) => {
    const now = Date.now();
    if (progress < 0.98 && now - lastPersistRef.current < 1500) return;
    lastPersistRef.current = now;
    const chapter = chapterIdRef.current;
    if (!chapter) return;
    saveAudioProgress({
      chapterId: chapter,
      position,
      progress,
      duration: stateRef.current.duration,
      updatedAt: now,
      contentSignature: contentSignatureRef.current,
    });
  }, []);

  const startProgressTimer = useCallback(
    (startProgress: number, durationOverride?: number) => {
      stopProgressTimer();
      hasBoundaryUpdatesRef.current = false;
      const duration = durationOverride ?? stateRef.current.duration;
      if (!duration) return;
      playbackStartRef.current =
        Date.now() - startProgress * duration * 1000;
      progressTimerRef.current = window.setInterval(() => {
        if (stateRef.current.status !== 'playing') return;
        if (hasBoundaryUpdatesRef.current) return;
        const startTime = playbackStartRef.current;
        if (!startTime) return;
        const elapsed = (Date.now() - startTime) / 1000;
        const progress = clamp(duration ? elapsed / duration : 0, 0, 1);
        const position = Math.round(progress * textRef.current.length);
        updateStateFromPosition(position);
        persistProgress(position, progress);
        if (progress >= 1) {
          stopProgressTimer();
        }
      }, 700);
    },
    [persistProgress, stopProgressTimer, updateStateFromPosition]
  );

  // --- Gestion des utterances ---
  const cancelCurrentUtterance = useCallback(() => {
    const synth = synthRef.current;
    if (!synth) return;
    const currentId = currentUtteranceIdRef.current;
    if (currentId !== null) {
      cancelledUtterancesRef.current.add(currentId);
    }
    synth.cancel();
  }, []);

  const startUtteranceFrom = useCallback(
    (startPosition: number) => {
      const synth = synthRef.current;
      const fullText = textRef.current;
      if (!synth || !fullText) {
        setState((prev) => ({
          ...prev,
          status: 'error',
          error: 'Lecture audio indisponible.',
        }));
        return;
      }

      let safePosition = clamp(startPosition, 0, fullText.length || 0);
      if (fullText.length && safePosition >= fullText.length) {
        safePosition = 0;
      }
      const startProgress = fullText.length
        ? safePosition / fullText.length
        : 0;

      cancelCurrentUtterance();

      const utteranceId = ++utteranceIdRef.current;
      currentUtteranceIdRef.current = utteranceId;

      const utterance = new SpeechSynthesisUtterance(
        fullText.slice(safePosition)
      );
      const currentConfig = configRef.current;
      utterance.rate = currentConfig.rate;
      utterance.pitch = currentConfig.pitch;
      utterance.volume = currentConfig.volume;

      if (currentConfig.voiceId) {
        const voice = browserVoicesRef.current.find(
          (item) =>
            (item.voiceURI || item.name) === currentConfig.voiceId
        );
        if (voice) {
          utterance.voice = voice;
        }
      }

      utterance.onboundary = (event: SpeechSynthesisEvent) => {
        if (typeof event.charIndex !== 'number') return;
        hasBoundaryUpdatesRef.current = true;
        const absoluteIndex = safePosition + event.charIndex;
        updateStateFromPosition(absoluteIndex);
        const progress = fullText.length
          ? absoluteIndex / fullText.length
          : 0;
        persistProgress(absoluteIndex, progress);
      };

      utterance.onend = () => {
        if (cancelledUtterancesRef.current.has(utteranceId)) {
          cancelledUtterancesRef.current.delete(utteranceId);
          return;
        }
        stopProgressTimer();
        updateStateFromPosition(fullText.length);
        persistProgress(fullText.length, 1);
        setState((prev) => ({ ...prev, status: 'idle' }));
      };

      utterance.onerror = (event: SpeechSynthesisErrorEvent) => {
        if (cancelledUtterancesRef.current.has(utteranceId)) {
          cancelledUtterancesRef.current.delete(utteranceId);
          return;
        }
        stopProgressTimer();
        setState((prev) => ({
          ...prev,
          status: 'error',
          error: event.error || 'Erreur de synthese vocale.',
        }));
      };

      const duration = estimateDurationSeconds(fullText, currentConfig.rate);
      setState((prev) => ({
        ...prev,
        status: 'playing',
        currentPosition: safePosition,
        progress: startProgress,
        currentTime: duration ? startProgress * duration : 0,
        duration,
        error: null,
      }));

      synth.speak(utterance);
      startProgressTimer(startProgress, duration);
    },
    [
      cancelCurrentUtterance,
      persistProgress,
      startProgressTimer,
      stopProgressTimer,
      updateStateFromPosition,
    ]
  );

  // --- Actions publiques ---

  const seekToPosition = useCallback(
    (position: number) => {
      const fullText = textRef.current;
      if (!fullText) return;
      const safePosition = clamp(position, 0, fullText.length);
      updateStateFromPosition(safePosition);
      const progress = fullText.length
        ? safePosition / fullText.length
        : 0;
      persistProgress(safePosition, progress);
      if (stateRef.current.status === 'playing') {
        startUtteranceFrom(safePosition);
      } else if (stateRef.current.status === 'paused') {
        cancelCurrentUtterance();
        stopProgressTimer();
        setState((prev) => ({ ...prev, status: 'idle' }));
      }
    },
    [
      cancelCurrentUtterance,
      persistProgress,
      startUtteranceFrom,
      stopProgressTimer,
      updateStateFromPosition,
    ]
  );

  const play = useCallback(() => {
    if (!isSupported) return;
    if (stateRef.current.status === 'paused') {
      const synth = synthRef.current;
      if (synth) {
        synth.resume();
        setState((prev) => ({
          ...prev,
          status: 'playing',
          error: null,
        }));
        startProgressTimer(stateRef.current.progress);
      }
      return;
    }
    if (stateRef.current.status === 'playing') return;
    startUtteranceFrom(stateRef.current.currentPosition || 0);
  }, [isSupported, startProgressTimer, startUtteranceFrom]);

  const pause = useCallback(() => {
    const synth = synthRef.current;
    if (!synth || stateRef.current.status !== 'playing') return;
    synth.pause();
    stopProgressTimer();
    setState((prev) => ({ ...prev, status: 'paused' }));
    persistProgress(
      stateRef.current.currentPosition,
      stateRef.current.progress
    );
  }, [persistProgress, stopProgressTimer]);

  const resume = useCallback(() => {
    const synth = synthRef.current;
    if (!synth || stateRef.current.status !== 'paused') return;
    synth.resume();
    setState((prev) => ({ ...prev, status: 'playing', error: null }));
    startProgressTimer(stateRef.current.progress);
  }, [startProgressTimer]);

  const stop = useCallback(() => {
    cancelCurrentUtterance();
    stopProgressTimer();
    setState((prev) => ({ ...prev, status: 'idle' }));
    persistProgress(
      stateRef.current.currentPosition,
      stateRef.current.progress
    );
  }, [cancelCurrentUtterance, persistProgress, stopProgressTimer]);

  const seekToPercent = useCallback(
    (percent: number) => {
      const fullText = textRef.current;
      if (!fullText) return;
      const safePercent = clamp(percent, 0, 1);
      seekToPosition(Math.round(fullText.length * safePercent));
    },
    [seekToPosition]
  );

  const skipBySeconds = useCallback(
    (seconds: number) => {
      const fullText = textRef.current;
      const wordData = wordDataRef.current;
      if (!fullText || !wordData.words.length) return;
      const duration = stateRef.current.duration;
      const wordsPerSecond =
        duration > 0 ? wordData.words.length / duration : 3;
      const deltaWords = Math.round(seconds * wordsPerSecond);
      const currentWordIndex = getWordIndexFromCharIndex(
        wordData.offsets,
        stateRef.current.currentPosition
      );
      const targetWordIndex = clamp(
        currentWordIndex + deltaWords,
        0,
        wordData.words.length - 1
      );
      const targetPosition = getCharIndexFromWordIndex(
        wordData.offsets,
        targetWordIndex
      );
      seekToPosition(targetPosition);
    },
    [seekToPosition]
  );

  const skipForward = useCallback(
    (seconds = 15) => skipBySeconds(seconds),
    [skipBySeconds]
  );

  const skipBackward = useCallback(
    (seconds = 15) => skipBySeconds(-seconds),
    [skipBySeconds]
  );

  const setRate = useCallback(
    (rate: number) => {
      const safeRate = clamp(rate, 0.5, 2.5);
      setConfig((prev) => ({ ...prev, rate: safeRate }));
      const duration = estimateDurationSeconds(textRef.current, safeRate);
      setState((prev) => ({
        ...prev,
        duration,
        currentTime: duration ? prev.progress * duration : 0,
      }));
      if (stateRef.current.status === 'playing') {
        startUtteranceFrom(stateRef.current.currentPosition);
      }
    },
    [startUtteranceFrom]
  );

  const setVoice = useCallback(
    (voiceId: string | null) => {
      setConfig((prev) => ({ ...prev, voiceId }));
      if (stateRef.current.status === 'playing') {
        startUtteranceFrom(stateRef.current.currentPosition);
      }
    },
    [startUtteranceFrom]
  );

  // --- Effet de synchronisation texte/chapitre ---
  useEffect(() => {
    chapterIdRef.current = chapterId;
    textRef.current = text ?? '';
    wordDataRef.current = buildWordData(textRef.current);
    contentSignatureRef.current = createContentSignature(textRef.current);
    const duration = estimateDurationSeconds(
      textRef.current,
      configRef.current.rate
    );
    const saved = getAudioProgress(chapterId, textRef.current);
    const position = saved?.position ?? 0;
    const progress = textRef.current.length
      ? position / textRef.current.length
      : 0;
    const currentTime = duration ? progress * duration : 0;
    const wordIndex = getWordIndexFromCharIndex(
      wordDataRef.current.offsets,
      position
    );
    const currentWord = wordDataRef.current.words[wordIndex] ?? '';
    cancelCurrentUtterance();
    stopProgressTimer();
    setState((prev) => ({
      ...prev,
      status: 'idle',
      currentPosition: position,
      progress,
      currentTime,
      duration,
      currentWord,
      error: null,
    }));
  }, [chapterId, text, cancelCurrentUtterance, stopProgressTimer]);

  // Cleanup
  useEffect(
    () => () => {
      cancelCurrentUtterance();
      stopProgressTimer();
    },
    [cancelCurrentUtterance, stopProgressTimer]
  );

  return {
    state,
    config,
    voices,
    isSupported,
    isReady,
    play,
    pause,
    resume,
    stop,
    setRate,
    setVoice,
    seekToPercent,
    skipForward,
    skipBackward,
  };
}
```

**Points cles de l'implementation :**
- Le hook recoit `{ chapterId, text }` en props -- le texte n'est pas passe a `play()`
- `play()` sans arguments : reprend depuis la position courante ou sauvegardee
- Systeme d'`utteranceId` pour ignorer les events des utterances annulees
- Double strategie de suivi de progression :
  1. `onboundary` (precis, mot par mot) quand le navigateur le supporte
  2. Timer fallback a 700ms base sur le temps ecoule
- Persistance throttled a 1500ms sauf fin de chapitre (progress >= 0.98)
- Quand `chapterId` ou `text` change, la lecture s'arrete et la position sauvegardee est restauree

### 6.2 Hook pour Raccourcis Clavier

**Fichier :** `src/hooks/use-audio-keyboard.ts`

```typescript
'use client'

import { useEffect } from 'react';

export interface AudioKeyboardOptions {
  enabled: boolean;
  onPlayPause?: () => void;
  onStop?: () => void;
  onSkipForward?: () => void;
  onSkipBackward?: () => void;
}

const isEditableTarget = (target: EventTarget | null) => {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName.toLowerCase();
  if (['input', 'textarea', 'select'].includes(tag)) return true;
  if (target.isContentEditable) return true;
  return false;
};

export function useAudioKeyboard({
  enabled,
  onPlayPause,
  onStop,
  onSkipForward,
  onSkipBackward,
}: AudioKeyboardOptions) {
  useEffect(() => {
    if (!enabled) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (isEditableTarget(event.target)) return;

      switch (event.key) {
        case ' ':
        case 'Spacebar':
          event.preventDefault();
          onPlayPause?.();
          break;
        case 'ArrowRight':
          event.preventDefault();
          onSkipForward?.();
          break;
        case 'ArrowLeft':
          event.preventDefault();
          onSkipBackward?.();
          break;
        case 'Escape':
          onStop?.();
          break;
        default:
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [enabled, onPlayPause, onSkipBackward, onSkipForward, onStop]);
}
```

**Raccourcis supportes :**

| Touche | Action |
|--------|--------|
| Espace | Play / Pause |
| Fleche droite | Avancer +15s |
| Fleche gauche | Reculer -15s |
| Echap | Stop |

Les raccourcis sont desactives quand un champ de saisie est focus (`input`, `textarea`, `contentEditable`).

### 6.3 Index des Exports

**Fichier :** `src/hooks/index.ts`

```typescript
export * from './use-audio-keyboard';
export * from './use-speech-synthesis';
```

---

## 7. Phase 3 : Composants UI

### 7.1 Composant de Controles

**Fichier :** `src/components/audio/audio-controls.tsx`

```typescript
'use client'

import type { SpeechStatus } from '@/hooks/use-speech-synthesis';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export interface AudioControlsProps {
  status: SpeechStatus;
  onPlay: () => void;
  onPause: () => void;
  onStop: () => void;
  onSkipForward: () => void;
  onSkipBackward: () => void;
  disabled?: boolean;
}

const IconPlay = () => (
  <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    <path d="M8 5v14l11-7z" />
  </svg>
);

const IconPause = () => (
  <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    <path d="M6 5h4v14H6zM14 5h4v14h-4z" />
  </svg>
);

const IconStop = () => (
  <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    <path d="M6 6h12v12H6z" />
  </svg>
);

const IconForward = () => (
  <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    <path d="M4 4v16l8-8-8-8zm8 0v16l8-8-8-8z" />
  </svg>
);

const IconBackward = () => (
  <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    <path d="M20 4v16l-8-8 8-8zm-8 0v16l-8-8 8-8z" />
  </svg>
);

export function AudioControls({
  status,
  onPlay,
  onPause,
  onStop,
  onSkipForward,
  onSkipBackward,
  disabled = false,
}: AudioControlsProps) {
  const isPlaying = status === 'playing';
  const isPaused = status === 'paused';

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button
        variant="ghost"
        size="sm"
        onClick={onSkipBackward}
        disabled={disabled}
        aria-label="Reculer de 15 secondes"
      >
        <span className="flex items-center gap-1">
          <IconBackward />
          <span className="text-xs">-15s</span>
        </span>
      </Button>

      <Button
        variant="primary"
        size="sm"
        onClick={isPlaying ? onPause : onPlay}
        disabled={disabled}
        aria-label={isPlaying ? 'Pause' : 'Lecture'}
        className={cn('min-w-[120px]', disabled && 'opacity-60')}
      >
        <span className="flex items-center gap-2">
          {isPlaying ? <IconPause /> : <IconPlay />}
          <span className="text-sm">
            {isPlaying ? 'Pause' : isPaused ? 'Reprendre' : 'Lire'}
          </span>
        </span>
      </Button>

      <Button
        variant="ghost"
        size="sm"
        onClick={onStop}
        disabled={disabled}
        aria-label="Arreter"
      >
        <span className="flex items-center gap-1">
          <IconStop />
          <span className="text-xs">Stop</span>
        </span>
      </Button>

      <Button
        variant="ghost"
        size="sm"
        onClick={onSkipForward}
        disabled={disabled}
        aria-label="Avancer de 15 secondes"
      >
        <span className="flex items-center gap-1">
          <IconForward />
          <span className="text-xs">+15s</span>
        </span>
      </Button>
    </div>
  );
}
```

### 7.2 Barre de Progression

**Fichier :** `src/components/audio/audio-progress-bar.tsx`

```typescript
'use client'

import { cn } from '@/lib/utils';

export interface AudioProgressBarProps {
  progress: number;           // 0-1
  currentTime: number;
  duration: number;
  onSeek?: (percent: number) => void;
  disabled?: boolean;
}

const formatTime = (value: number) => {
  if (!Number.isFinite(value) || value <= 0) return '0:00';
  const minutes = Math.floor(value / 60);
  const seconds = Math.floor(value % 60);
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
};

export function AudioProgressBar({
  progress,
  currentTime,
  duration,
  onSeek,
  disabled = false,
}: AudioProgressBarProps) {
  const percent = Number.isFinite(progress) ? Math.round(progress * 100) : 0;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs text-ink/60">
        <span>{formatTime(currentTime)}</span>
        <span>{formatTime(duration)}</span>
      </div>
      <div className="relative">
        <input
          type="range"
          min={0}
          max={100}
          step={1}
          value={percent}
          onChange={(event) => onSeek?.(Number(event.target.value) / 100)}
          disabled={disabled}
          className={cn(
            'w-full accent-brand-600',
            'disabled:cursor-not-allowed disabled:opacity-50'
          )}
          aria-label="Progression audio"
        />
        <div className="mt-1 text-xs text-ink/50">{percent}%</div>
      </div>
    </div>
  );
}
```

**Note :** Utilise un `<input type="range">` natif pour la simplicite et l'accessibilite.
Le `onSeek` recoit une valeur 0-1 (conversion depuis 0-100 du range).

### 7.3 Selecteur de Voix

**Fichier :** `src/components/audio/voice-selector.tsx`

```typescript
'use client'

import { Select } from '@/components/ui/select';
import type { SpeechVoice } from '@/hooks/use-speech-synthesis';

export interface VoiceSelectorProps {
  voices: SpeechVoice[];
  value: string | null;
  onChange: (value: string | null) => void;
  disabled?: boolean;
}

export function VoiceSelector({
  voices,
  value,
  onChange,
  disabled = false,
}: VoiceSelectorProps) {
  const options = voices.map((voice) => ({
    value: voice.id,
    label: `${voice.name} (${voice.lang})${voice.default ? ' *' : ''}`,
  }));

  return (
    <Select
      label="Voix"
      options={
        options.length
          ? options
          : [{ value: '', label: 'Voix indisponibles' }]
      }
      value={value ?? ''}
      onChange={(event) => onChange(event.target.value || null)}
      disabled={disabled || !options.length}
    />
  );
}
```

**Note :** Affiche toutes les voix du systeme (pas de filtre francais uniquement)
pour laisser le choix a l'utilisateur.

### 7.4 Controle de Vitesse

**Fichier :** `src/components/audio/speed-control.tsx`

```typescript
'use client'

import { Select } from '@/components/ui/select';

export interface SpeedControlProps {
  rate: number;
  onChange: (rate: number) => void;
  disabled?: boolean;
}

const SPEED_OPTIONS = [0.75, 1, 1.25, 1.5, 2];

export function SpeedControl({
  rate,
  onChange,
  disabled = false,
}: SpeedControlProps) {
  const options = SPEED_OPTIONS.map((value) => ({
    value: String(value),
    label: `${value}x`,
  }));

  return (
    <Select
      label="Vitesse"
      options={options}
      value={String(rate)}
      onChange={(event) => onChange(Number(event.target.value))}
      disabled={disabled}
    />
  );
}
```

### 7.5 Mini Player

**Fichier :** `src/components/audio/audio-player-mini.tsx`

```typescript
'use client'

import type { SpeechStatus } from '@/hooks/use-speech-synthesis';
import { cn } from '@/lib/utils';

export interface AudioPlayerMiniProps {
  status: SpeechStatus;
  progress: number;           // 0-1
  onToggle: () => void;
  disabled?: boolean;
}

const IconPlay = () => (
  <svg className="h-3 w-3" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    <path d="M8 5v14l11-7z" />
  </svg>
);

const IconPause = () => (
  <svg className="h-3 w-3" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    <path d="M6 5h4v14H6zM14 5h4v14h-4z" />
  </svg>
);

export function AudioPlayerMini({
  status,
  progress,
  onToggle,
  disabled = false,
}: AudioPlayerMiniProps) {
  const percent = Number.isFinite(progress) ? Math.round(progress * 100) : 0;

  return (
    <button
      type="button"
      onClick={onToggle}
      disabled={disabled}
      className={cn(
        'inline-flex items-center gap-2 rounded-full border border-stone-200',
        'bg-white/80 px-3 py-1 text-xs text-ink/70',
        'transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-60'
      )}
      aria-label={
        status === 'playing' ? 'Mettre en pause' : 'Lancer la lecture'
      }
    >
      {status === 'playing' ? <IconPause /> : <IconPlay />}
      <span>{status === 'playing' ? 'Lecture' : 'Audio'}</span>
      <span className="h-1 w-16 overflow-hidden rounded-full bg-stone-200">
        <span
          className="block h-full bg-brand-500"
          style={{ width: `${percent}%` }}
        />
      </span>
    </button>
  );
}
```

### 7.6 Composant Principal

**Fichier :** `src/components/audio/chapter-audio-player.tsx`

```typescript
'use client'

import { useCallback, useMemo, useState } from 'react';
import { cn } from '@/lib/utils';
import { useAudioKeyboard } from '@/hooks/use-audio-keyboard';
import { useSpeechSynthesis } from '@/hooks/use-speech-synthesis';
import { AudioControls } from './audio-controls';
import { AudioProgressBar } from './audio-progress-bar';
import { AudioPlayerMini } from './audio-player-mini';
import { SpeedControl } from './speed-control';
import { VoiceSelector } from './voice-selector';

export interface ChapterAudioPlayerProps {
  chapterId: string;
  chapterTitle: string;
  content: string;
  defaultExpanded?: boolean;
  className?: string;
}

const ChevronIcon = ({ expanded }: { expanded: boolean }) => (
  <svg
    aria-hidden="true"
    className={cn(
      'h-4 w-4 text-ink/50 transition-transform',
      expanded && 'rotate-180'
    )}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M6 9l6 6 6-6" />
  </svg>
);

export function ChapterAudioPlayer({
  chapterId,
  chapterTitle,
  content,
  defaultExpanded = false,
  className,
}: ChapterAudioPlayerProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const hasContent = Boolean(content && content.trim().length > 0);

  const {
    state,
    config,
    voices,
    isSupported,
    isReady,
    play,
    pause,
    resume,
    stop,
    setRate,
    setVoice,
    seekToPercent,
    skipForward,
    skipBackward,
  } = useSpeechSynthesis({ chapterId, text: content ?? '' });

  const handlePlayPause = useCallback(() => {
    if (!hasContent || !isSupported) return;
    if (state.status === 'playing') {
      pause();
      return;
    }
    if (state.status === 'paused') {
      resume();
      return;
    }
    play();
  }, [hasContent, isSupported, pause, play, resume, state.status]);

  const handleToggleExpanded = useCallback(() => {
    setExpanded((prev) => !prev);
  }, []);

  const statusLabel = useMemo(() => {
    if (!isSupported) return 'Navigateur non compatible';
    switch (state.status) {
      case 'playing':
        return 'Lecture en cours';
      case 'paused':
        return 'Lecture en pause';
      case 'error':
        return 'Erreur audio';
      default:
        return 'Pret a lire';
    }
  }, [isSupported, state.status]);

  useAudioKeyboard({
    enabled: expanded && isSupported && hasContent,
    onPlayPause: handlePlayPause,
    onStop: stop,
    onSkipForward: skipForward,
    onSkipBackward: skipBackward,
  });

  const controlsDisabled = !isSupported || !hasContent;

  return (
    <div
      className={cn(
        'rounded-2xl border border-stone-200 bg-white p-4',
        className
      )}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <button
          type="button"
          onClick={handleToggleExpanded}
          className="flex items-center gap-3 rounded-lg px-2 py-1 text-left
                     focus-visible:ring-2 focus-visible:ring-brand-500/40"
          aria-expanded={expanded}
        >
          <div>
            <p className="text-sm font-semibold text-ink">
              Ecouter le chapitre
            </p>
            <p className="text-xs text-ink/60">{chapterTitle}</p>
          </div>
          <ChevronIcon expanded={expanded} />
        </button>

        <div className="flex items-center gap-3">
          <span className="text-xs text-ink/60">{statusLabel}</span>
          <AudioPlayerMini
            status={state.status}
            progress={state.progress}
            onToggle={handlePlayPause}
            disabled={controlsDisabled}
          />
        </div>
      </div>

      {expanded && (
        <div className="mt-4 space-y-4">
          {!hasContent && (
            <div className="rounded-xl border border-stone-200 bg-stone-50
                            p-3 text-sm text-ink/70">
              Aucun contenu a lire pour ce chapitre.
            </div>
          )}

          {!isSupported && (
            <div className="rounded-xl border border-amber-200 bg-amber-50
                            p-3 text-sm text-amber-800">
              Votre navigateur ne supporte pas la lecture audio.
            </div>
          )}

          {state.error && (
            <div className="rounded-xl border border-red-200 bg-red-50
                            p-3 text-sm text-red-700">
              {state.error}
            </div>
          )}

          <AudioControls
            status={state.status}
            onPlay={play}
            onPause={pause}
            onStop={stop}
            onSkipForward={skipForward}
            onSkipBackward={skipBackward}
            disabled={controlsDisabled}
          />

          <AudioProgressBar
            progress={state.progress}
            currentTime={state.currentTime}
            duration={state.duration}
            onSeek={seekToPercent}
            disabled={controlsDisabled}
          />

          <div className="grid gap-3 md:grid-cols-2">
            <VoiceSelector
              voices={voices}
              value={config.voiceId}
              onChange={setVoice}
              disabled={controlsDisabled || !isReady}
            />
            <SpeedControl
              rate={config.rate}
              onChange={setRate}
              disabled={controlsDisabled}
            />
          </div>

          {state.currentWord && (
            <div className="rounded-xl border border-stone-100 bg-stone-50
                            px-3 py-2 text-xs text-ink/60">
              Mot courant:{' '}
              <span className="font-semibold text-ink">
                {state.currentWord}
              </span>
            </div>
          )}

          <p className="text-xs text-ink/40">
            Raccourcis: Espace = lecture/pause, Fleches = avancer ou reculer,
            Echap = stop.
          </p>
        </div>
      )}
    </div>
  );
}
```

### 7.7 Index des Exports

**Fichier :** `src/components/audio/index.ts`

```typescript
export * from './audio-controls';
export * from './audio-error-boundary';
export * from './audio-player-mini';
export * from './audio-progress-bar';
export * from './chapter-audio-player';
export * from './speed-control';
export * from './voice-selector';
```

---

## 8. Phase 4 : Integration Dashboard

### 8.1 Lazy Loading du Composant

**Fichier :** `src/components/audio/lazy.tsx`

```typescript
'use client'

import dynamic from 'next/dynamic';

export const LazyChapterAudioPlayer = dynamic(
  () =>
    import('./chapter-audio-player').then((mod) => mod.ChapterAudioPlayer),
  {
    loading: () => (
      <div className="rounded-2xl border border-stone-200 bg-stone-50 p-4 animate-pulse">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-full bg-stone-200" />
          <div className="space-y-2">
            <div className="h-4 w-32 rounded bg-stone-200" />
            <div className="h-3 w-24 rounded bg-stone-200" />
          </div>
        </div>
      </div>
    ),
    ssr: false, // Web Speech API n'existe pas cote serveur
  }
);
```

### 8.2 Error Boundary

**Fichier :** `src/components/audio/audio-error-boundary.tsx`

```typescript
'use client'

import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class AudioErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('[AudioPlayer] Error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-center">
            <p className="text-sm text-red-700">
              Une erreur est survenue avec le lecteur audio.
            </p>
            <button
              className="mt-2 text-xs text-red-600 underline"
              onClick={() => this.setState({ hasError: false })}
              type="button"
            >
              Reessayer
            </button>
          </div>
        )
      );
    }

    return this.props.children;
  }
}
```

### 8.3 Integration dans le Dashboard

**Fichier :** `src/app/dashboard/new/page.tsx` (modifications)

```typescript
// Imports ajoutes
import { AudioErrorBoundary } from '@/components/audio';
import { LazyChapterAudioPlayer } from '@/components/audio/lazy';
import { getProgressPercent } from '@/lib/audio-storage';

// Dans la section d'affichage du chapitre :
{showChapter && activeChapterContent && (
  <AudioErrorBoundary>
    <LazyChapterAudioPlayer
      chapterId={activeChapterId}
      chapterTitle={activeChapterTitle}
      content={activeChapterContent}
      className="mb-3"
    />
  </AudioErrorBoundary>
)}

// Dans la liste des chapitres du plan, indicateur de progression audio :
{audioProgress > 0 && (
  <span className={cn(
    'text-xs px-2 py-0.5 rounded-full',
    audioProgress >= 95
      ? 'bg-green-50 text-green-700'   // "Audio OK"
      : 'bg-brand-50 text-brand-700'   // "Audio XX%"
  )}>
    {audioProgress >= 95 ? 'Audio OK' : `Audio ${Math.round(audioProgress)}%`}
  </span>
)}
```

---

## 9. Phase 5 : Optimisations UX

### 9.1 Decisions de simplification

Plusieurs fonctionnalites prevues initialement ont ete volontairement omises
pour garder l'implementation legere :

| Fonctionnalite ecartee | Raison |
|------------------------|--------|
| `types/audio.ts` centralise | Types colocates avec le code qui les utilise |
| Filtre voix francaises | L'utilisateur choisit lui-meme sa voix |
| `prepareTextForSpeech` (nettoyage texte) | Complexite non justifiee |
| `splitTextIntoSegments` (decoupe) | Web Speech API gere les longs textes |
| Historique de lecture | YAGNI -- pas de besoin identifie |
| Statistiques d'ecoute | YAGNI -- pas de besoin identifie |
| Export/Import des donnees | YAGNI -- pas de besoin identifie |
| Nettoyage automatique des anciennes progressions | YAGNI |
| Volume/Speed/Mute via clavier | Controles UI suffisants |
| Multi-tailles (sm/md/lg) sur AudioControls | Une seule taille suffit |
| Slider custom avec drag/hover/tooltip | `<input type="range">` natif plus accessible |

### 9.2 Ameliorations implementees

- **Lazy loading** avec `next/dynamic` et `ssr: false`
- **Skeleton loading** pendant le chargement du composant
- **Error boundary** avec bouton "Reessayer"
- **Mini player** visible quand le player est replie
- **Content signature** pour invalider la progression si le texte change
- **Utterance ID tracking** pour eviter les race conditions
- **Double strategie de progression** (onboundary + timer fallback)

---

## 10. Phase 6 : Tests

### 10.1 Tests Unitaires

```typescript
// __tests__/lib/audio-utils.test.ts

import {
  clamp,
  countWords,
  estimateDurationSeconds,
  buildWordData,
  getWordIndexFromCharIndex,
  getCharIndexFromWordIndex,
} from '@/lib/audio-utils';

describe('audio-utils', () => {
  describe('clamp', () => {
    it('should clamp values within range', () => {
      expect(clamp(5, 0, 10)).toBe(5);
      expect(clamp(-1, 0, 10)).toBe(0);
      expect(clamp(15, 0, 10)).toBe(10);
    });
  });

  describe('countWords', () => {
    it('should count words correctly', () => {
      expect(countWords('Hello world')).toBe(2);
      expect(countWords('  ')).toBe(0);
      expect(countWords('One')).toBe(1);
    });
  });

  describe('estimateDurationSeconds', () => {
    it('should estimate based on 180 WPM', () => {
      const text = Array(180).fill('word').join(' '); // 180 words
      expect(estimateDurationSeconds(text, 1)).toBeCloseTo(60);
    });

    it('should adjust for rate', () => {
      const text = Array(180).fill('word').join(' ');
      expect(estimateDurationSeconds(text, 2)).toBeCloseTo(30);
    });
  });

  describe('buildWordData', () => {
    it('should build word data with offsets', () => {
      const data = buildWordData('Hello world test');
      expect(data.words).toEqual(['Hello', 'world', 'test']);
      expect(data.offsets).toEqual([0, 6, 12]);
    });
  });

  describe('getWordIndexFromCharIndex', () => {
    it('should find word index via binary search', () => {
      const offsets = [0, 6, 12];
      expect(getWordIndexFromCharIndex(offsets, 0)).toBe(0);
      expect(getWordIndexFromCharIndex(offsets, 7)).toBe(1);
      expect(getWordIndexFromCharIndex(offsets, 12)).toBe(2);
    });
  });
});
```

### 10.2 Tests du Module de Stockage

```typescript
// __tests__/lib/audio-storage.test.ts

import {
  saveAudioProgress,
  getAudioProgress,
  clearAudioProgress,
  getProgressPercent,
  createContentSignature,
  saveAudioPreferences,
  loadAudioPreferences,
} from '@/lib/audio-storage';

describe('Audio Storage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('Progress', () => {
    const content = 'Some chapter content here';
    const mockEntry = {
      chapterId: 'chapter-1',
      position: 10,
      progress: 0.5,
      duration: 60,
      updatedAt: Date.now(),
      contentSignature: createContentSignature(content),
    };

    it('should save and retrieve progress', () => {
      saveAudioProgress(mockEntry);
      const retrieved = getAudioProgress('chapter-1', content);
      expect(retrieved).toMatchObject({
        chapterId: 'chapter-1',
        position: 10,
        progress: 0.5,
      });
    });

    it('should return null for non-existent chapter', () => {
      expect(getAudioProgress('non-existent', content)).toBeNull();
    });

    it('should return null if content changed', () => {
      saveAudioProgress(mockEntry);
      expect(getAudioProgress('chapter-1', 'Different content')).toBeNull();
    });

    it('should clear progress', () => {
      saveAudioProgress(mockEntry);
      clearAudioProgress('chapter-1');
      expect(getAudioProgress('chapter-1', content)).toBeNull();
    });

    it('should return progress percent', () => {
      saveAudioProgress(mockEntry);
      expect(getProgressPercent('chapter-1', content)).toBe(50);
    });
  });

  describe('Preferences', () => {
    it('should save and retrieve preferences', () => {
      saveAudioPreferences({ rate: 1.5 });
      const prefs = loadAudioPreferences();
      expect(prefs.rate).toBe(1.5);
    });

    it('should return defaults when empty', () => {
      const prefs = loadAudioPreferences();
      expect(prefs.rate).toBe(1);
      expect(prefs.voiceId).toBeNull();
    });
  });
});
```

### 10.3 Tests de Composants

```typescript
// __tests__/components/audio/chapter-audio-player.test.tsx

import { render, screen, fireEvent } from '@testing-library/react';
import { ChapterAudioPlayer } from '@/components/audio';

// Mock du hook
jest.mock('@/hooks/use-speech-synthesis', () => ({
  useSpeechSynthesis: () => ({
    state: {
      status: 'idle',
      currentPosition: 0,
      progress: 0,
      currentTime: 0,
      duration: 60,
      currentWord: '',
      error: null,
    },
    config: { rate: 1.0, pitch: 1.0, volume: 1.0, voiceId: null },
    voices: [
      { id: 'fr-1', name: 'French', lang: 'fr-FR', localService: false, default: true },
    ],
    isSupported: true,
    isReady: true,
    play: jest.fn(),
    pause: jest.fn(),
    resume: jest.fn(),
    stop: jest.fn(),
    setRate: jest.fn(),
    setVoice: jest.fn(),
    seekToPercent: jest.fn(),
    skipForward: jest.fn(),
    skipBackward: jest.fn(),
  }),
}));

describe('ChapterAudioPlayer', () => {
  const defaultProps = {
    chapterId: 'test-chapter',
    chapterTitle: 'Test Chapter',
    content: 'This is test content for the chapter.',
  };

  it('should render correctly', () => {
    render(<ChapterAudioPlayer {...defaultProps} />);
    expect(screen.getByText('Ecouter le chapitre')).toBeInTheDocument();
    expect(screen.getByText('Test Chapter')).toBeInTheDocument();
  });

  it('should expand when clicked', () => {
    render(<ChapterAudioPlayer {...defaultProps} />);
    const header = screen.getByRole('button', { name: /ecouter/i });
    fireEvent.click(header);
    expect(screen.getByText('Voix')).toBeInTheDocument();
    expect(screen.getByText('Vitesse')).toBeInTheDocument();
  });

  it('should show keyboard shortcuts hint when expanded', () => {
    render(<ChapterAudioPlayer {...defaultProps} defaultExpanded />);
    expect(screen.getByText(/Raccourcis/)).toBeInTheDocument();
  });
});
```

---

## 11. Phase 7 : Deploiement Production

### 11.1 Checklist Pre-Deploiement

```
## Code
- [x] Pas d'erreurs TypeScript
- [x] Code review effectuee

## Performance
- [x] Lazy loading configure (ssr: false)
- [x] Pas de memory leaks (cleanup des timers et utterances)

## Compatibilite
- [x] Fallback pour navigateurs non supportes
- [x] SSR-safe (typeof window checks)

## Accessibilite
- [x] Navigation clavier fonctionnelle
- [x] Labels ARIA corrects
- [x] Input range natif pour la progression

## Securite
- [x] Pas de donnees sensibles dans localStorage
```

### 11.2 Configuration Docker

```
Pas de modification necessaire au Dockerfile.
La fonctionnalite est 100% frontend (Web Speech API).
```

---

## 12. Evolutions Futures

### 12.1 Roadmap

| Version | Fonctionnalite | Priorite |
|---------|----------------|----------|
| v1.1 | Nettoyage automatique des anciennes progressions | P2 |
| v1.2 | Lecture continue multi-chapitres | P1 |
| v1.3 | Slider custom avec hover tooltip | P2 |
| v2.0 | Voix premium (ElevenLabs) via backend | P1 |
| v2.1 | Export MP3 | P2 |
| v2.2 | Synchronisation cloud des preferences | P3 |

### 12.2 Integration Voix Premium (Architecture)

```typescript
// Backend: app/api/v1/endpoints/tts.py
@router.post("/generate")
async def generate_premium_audio(
    request: TTSRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Generate audio using ElevenLabs API"""
    audio_bytes = await elevenlabs_service.generate(
        text=request.text,
        voice_id=request.voice_id,
    )
    return StreamingResponse(
        io.BytesIO(audio_bytes),
        media_type="audio/mpeg",
    )

// Frontend: hook utilisant HTMLAudioElement au lieu de Web Speech API
export function usePremiumSpeech() {
  const audioRef = useRef<HTMLAudioElement>(null)

  const playPremium = async (text: string, voiceId: string) => {
    const response = await fetch('/api/v1/tts/generate', {
      method: 'POST',
      body: JSON.stringify({ text, voice_id: voiceId }),
    })
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    if (audioRef.current) {
      audioRef.current.src = url
      audioRef.current.play()
    }
  }

  return { audioRef, playPremium }
}
```

---

## 13. Checklist de Lancement

```
# Checklist de Lancement - Audio Feature

## Phase 1 : Infrastructure
- [x] Structure des fichiers creee
- [x] Module audio-utils.ts implemente
- [x] Module audio-storage.ts implemente
- [x] Persistence via contentSignature

## Phase 2 : Hook Principal
- [x] Hook useSpeechSynthesis implemente
- [x] Hook useAudioKeyboard implemente
- [x] Gestion des utterance IDs (race conditions)
- [x] Double strategie de progression (onboundary + timer)
- [x] Auto-persistance throttled a 1500ms

## Phase 3 : Composants UI
- [x] AudioControls (play/pause/stop/skip)
- [x] AudioProgressBar (input range natif)
- [x] VoiceSelector (toutes les voix)
- [x] SpeedControl (0.75x a 2x)
- [x] AudioPlayerMini (header replie)
- [x] ChapterAudioPlayer (composant principal)

## Phase 4 : Integration
- [x] LazyChapterAudioPlayer (dynamic import, ssr: false)
- [x] AudioErrorBoundary
- [x] Integration dans dashboard/new/page.tsx
- [x] Badge de progression audio dans la liste des chapitres

## Phase 5 : Optimisations
- [x] Lazy loading avec skeleton
- [x] Error boundary avec retry
- [x] Cleanup automatique des timers et utterances
```

---

## Annexes

### A. Types exportes (reference rapide)

| Type | Fichier source | Description |
|------|---------------|-------------|
| `SpeechStatus` | `use-speech-synthesis.ts` | `'idle' \| 'playing' \| 'paused' \| 'stopped' \| 'error'` |
| `SpeechState` | `use-speech-synthesis.ts` | Etat complet de lecture |
| `SpeechConfig` | `use-speech-synthesis.ts` | Configuration (rate, pitch, volume, voiceId) |
| `SpeechVoice` | `use-speech-synthesis.ts` | Voix disponible |
| `AudioPreferences` | `audio-storage.ts` | Preferences persistees |
| `AudioProgressEntry` | `audio-storage.ts` | Progression persistee par chapitre |
| `WordData` | `audio-utils.ts` | Index mots/offsets pour le suivi |

### B. Valeurs cles

| Constante | Valeur | Usage |
|-----------|--------|-------|
| `BASE_WPM` | 180 | Estimation de duree (mots/minute) |
| Timer fallback | 700ms | Interval de mise a jour quand onboundary absent |
| Persist throttle | 1500ms | Frequence min de sauvegarde localStorage |
| Speed range | 0.75 - 2.0 | Presets proposes (hook accepte 0.5-2.5) |
| Content signature | head 48 + tail 48 | Detection de changement de contenu |

### C. Ressources

- [Web Speech API Documentation](https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API)
- [Can I Use - Speech Synthesis](https://caniuse.com/speech-synthesis)

---

*Document cree le 29 janvier 2025*
*Derniere mise a jour : 29 janvier 2026 (v1.1 - alignement avec l'implementation reelle)*
