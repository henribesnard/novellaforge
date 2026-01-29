'use client'

import { Pause, Play } from 'lucide-react';
import type { SpeechStatus } from '@/hooks/use-speech-synthesis';
import { cn } from '@/lib/utils';

export interface AudioPlayerMiniProps {
  status: SpeechStatus;
  progress: number;
  onToggle: () => void;
  disabled?: boolean;
}

export function AudioPlayerMini({ status, progress, onToggle, disabled = false }: AudioPlayerMiniProps) {
  const percent = Number.isFinite(progress) ? Math.round(progress * 100) : 0;

  return (
    <button
      type="button"
      onClick={onToggle}
      disabled={disabled}
      className={cn(
        'inline-flex items-center gap-2 rounded-full border border-stone-200 bg-white/80 px-3 py-1 text-xs text-ink/70',
        'transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-60'
      )}
      aria-label={status === 'playing' ? 'Mettre en pause' : 'Lancer la lecture'}
    >
      {status === 'playing' ? <Pause className="h-3 w-3" /> : <Play className="h-3 w-3" />}
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
