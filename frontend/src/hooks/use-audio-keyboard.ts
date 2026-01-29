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
