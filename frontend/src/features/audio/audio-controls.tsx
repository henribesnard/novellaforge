'use client'

import { Pause, Play, SkipBack, SkipForward, Square } from 'lucide-react';
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
          <SkipBack className="h-4 w-4" />
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
          {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
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
          <Square className="h-4 w-4" />
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
          <SkipForward className="h-4 w-4" />
          <span className="text-xs">+15s</span>
        </span>
      </Button>
    </div>
  );
}
