'use client'

import { cn } from '@/lib/utils';

export interface AudioProgressBarProps {
  progress: number;
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
