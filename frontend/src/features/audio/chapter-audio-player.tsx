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
    className={cn('h-4 w-4 text-ink/50 transition-transform', expanded && 'rotate-180')}
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
    <div className={cn('rounded-2xl border border-stone-200 bg-white p-4', className)}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <button
          type="button"
          onClick={handleToggleExpanded}
          className="flex items-center gap-3 rounded-lg px-2 py-1 text-left focus-visible:ring-2 focus-visible:ring-brand-500/40"
          aria-expanded={expanded}
        >
          <div>
            <p className="text-sm font-semibold text-ink">Ecouter le chapitre</p>
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
            <div className="rounded-xl border border-stone-200 bg-stone-50 p-3 text-sm text-ink/70">
              Aucun contenu a lire pour ce chapitre.
            </div>
          )}

          {!isSupported && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
              Votre navigateur ne supporte pas la lecture audio.
            </div>
          )}

          {state.error && (
            <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
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
            <div className="rounded-xl border border-stone-100 bg-stone-50 px-3 py-2 text-xs text-ink/60">
              Mot courant: <span className="font-semibold text-ink">{state.currentWord}</span>
            </div>
          )}

          <p className="text-xs text-ink/40">
            Raccourcis: Espace = lecture/pause, Fleches = avancer ou reculer, Echap = stop.
          </p>
        </div>
      )}
    </div>
  );
}
