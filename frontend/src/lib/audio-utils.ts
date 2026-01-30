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
