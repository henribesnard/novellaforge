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
  currentPosition: number;
  progress: number;
  currentTime: number;
  duration: number;
  currentWord: string;
  error: string | null;
}

export interface SpeechConfig {
  rate: number;
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

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  useEffect(() => {
    configRef.current = config;
    saveAudioPreferences(config);
  }, [config]);

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

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const supported = 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window;
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

  useEffect(() => {
    if (!voices.length) return;
    const currentVoice = configRef.current.voiceId;
    const hasVoice = currentVoice && voices.some((voice) => voice.id === currentVoice);
    if (hasVoice) return;
    const preferred = voices.find((voice) => voice.default) ?? voices[0];
    if (!preferred) return;
    setConfig((prev) => ({ ...prev, voiceId: preferred.id }));
  }, [voices]);

  const stopProgressTimer = useCallback(() => {
    if (progressTimerRef.current !== null) {
      window.clearInterval(progressTimerRef.current);
      progressTimerRef.current = null;
    }
  }, []);

  const updateStateFromPosition = useCallback((position: number) => {
    const fullText = textRef.current;
    const safePosition = clamp(position, 0, fullText.length ? fullText.length : 0);
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

  const startProgressTimer = useCallback((startProgress: number, durationOverride?: number) => {
    stopProgressTimer();
    hasBoundaryUpdatesRef.current = false;
    const duration = durationOverride ?? stateRef.current.duration;
    if (!duration) return;
    playbackStartRef.current = Date.now() - startProgress * duration * 1000;
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
  }, [persistProgress, stopProgressTimer, updateStateFromPosition]);

  const cancelCurrentUtterance = useCallback(() => {
    const synth = synthRef.current;
    if (!synth) return;
    const currentId = currentUtteranceIdRef.current;
    if (currentId !== null) {
      cancelledUtterancesRef.current.add(currentId);
    }
    synth.cancel();
  }, []);

  const startUtteranceFrom = useCallback((startPosition: number) => {
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

    let safePosition = clamp(startPosition, 0, fullText.length ? fullText.length : 0);
    if (fullText.length && safePosition >= fullText.length) {
      safePosition = 0;
    }
    const startProgress = fullText.length ? safePosition / fullText.length : 0;

    cancelCurrentUtterance();

    const utteranceId = ++utteranceIdRef.current;
    currentUtteranceIdRef.current = utteranceId;

    const utterance = new SpeechSynthesisUtterance(fullText.slice(safePosition));
    const currentConfig = configRef.current;
    utterance.rate = currentConfig.rate;
    utterance.pitch = currentConfig.pitch;
    utterance.volume = currentConfig.volume;

    if (currentConfig.voiceId) {
      const voice = browserVoicesRef.current.find(
        (item) => (item.voiceURI || item.name) === currentConfig.voiceId
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
      const progress = fullText.length ? absoluteIndex / fullText.length : 0;
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
      setState((prev) => ({
        ...prev,
        status: 'idle',
      }));
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
  }, [cancelCurrentUtterance, persistProgress, startProgressTimer, stopProgressTimer, updateStateFromPosition]);

  const seekToPosition = useCallback((position: number) => {
    const fullText = textRef.current;
    if (!fullText) return;
    const safePosition = clamp(position, 0, fullText.length);
    updateStateFromPosition(safePosition);
    const progress = fullText.length ? safePosition / fullText.length : 0;
    persistProgress(safePosition, progress);
    if (stateRef.current.status === 'playing') {
      startUtteranceFrom(safePosition);
    } else if (stateRef.current.status === 'paused') {
      cancelCurrentUtterance();
      stopProgressTimer();
      setState((prev) => ({ ...prev, status: 'idle' }));
    }
  }, [cancelCurrentUtterance, persistProgress, startUtteranceFrom, stopProgressTimer, updateStateFromPosition]);

  const play = useCallback(() => {
    if (!isSupported) return;
    if (stateRef.current.status === 'paused') {
      const synth = synthRef.current;
      if (synth) {
        synth.resume();
        setState((prev) => ({ ...prev, status: 'playing', error: null }));
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
    persistProgress(stateRef.current.currentPosition, stateRef.current.progress);
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
    persistProgress(stateRef.current.currentPosition, stateRef.current.progress);
  }, [cancelCurrentUtterance, persistProgress, stopProgressTimer]);

  const seekToPercent = useCallback((percent: number) => {
    const fullText = textRef.current;
    if (!fullText) return;
    const safePercent = clamp(percent, 0, 1);
    seekToPosition(Math.round(fullText.length * safePercent));
  }, [seekToPosition]);

  const skipBySeconds = useCallback((seconds: number) => {
    const fullText = textRef.current;
    const wordData = wordDataRef.current;
    if (!fullText || !wordData.words.length) return;
    const duration = stateRef.current.duration;
    const wordsPerSecond = duration > 0 ? wordData.words.length / duration : 3;
    const deltaWords = Math.round(seconds * wordsPerSecond);
    const currentWordIndex = getWordIndexFromCharIndex(wordData.offsets, stateRef.current.currentPosition);
    const targetWordIndex = clamp(currentWordIndex + deltaWords, 0, wordData.words.length - 1);
    const targetPosition = getCharIndexFromWordIndex(wordData.offsets, targetWordIndex);
    seekToPosition(targetPosition);
  }, [seekToPosition]);

  const skipForward = useCallback((seconds = 15) => {
    skipBySeconds(seconds);
  }, [skipBySeconds]);

  const skipBackward = useCallback((seconds = 15) => {
    skipBySeconds(-seconds);
  }, [skipBySeconds]);

  const setRate = useCallback((rate: number) => {
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
  }, [startUtteranceFrom]);

  const setVoice = useCallback((voiceId: string | null) => {
    setConfig((prev) => ({ ...prev, voiceId }));
    if (stateRef.current.status === 'playing') {
      startUtteranceFrom(stateRef.current.currentPosition);
    }
  }, [startUtteranceFrom]);

  useEffect(() => {
    chapterIdRef.current = chapterId;
    textRef.current = text ?? '';
    wordDataRef.current = buildWordData(textRef.current);
    contentSignatureRef.current = createContentSignature(textRef.current);
    const duration = estimateDurationSeconds(textRef.current, configRef.current.rate);
    const saved = getAudioProgress(chapterId, textRef.current);
    const position = saved?.position ?? 0;
    const progress = textRef.current.length ? position / textRef.current.length : 0;
    const currentTime = duration ? progress * duration : 0;
    const wordIndex = getWordIndexFromCharIndex(wordDataRef.current.offsets, position);
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

  useEffect(() => () => {
    cancelCurrentUtterance();
    stopProgressTimer();
  }, [cancelCurrentUtterance, stopProgressTimer]);

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
