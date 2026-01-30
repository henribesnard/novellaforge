/**
 * Utility functions for the frontend
 */

import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Merge Tailwind classes with clsx
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format date to French locale
 */
export function formatDate(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return new Intl.DateTimeFormat('fr-FR', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
  }).format(d);
}

/**
 * Format relative time in French
 */
export function formatRelativeTime(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - d.getTime()) / 1000);

  if (diffInSeconds < 60) return 'À l\'instant';
  if (diffInSeconds < 3600) return `Il y a ${Math.floor(diffInSeconds / 60)} min`;
  if (diffInSeconds < 86400) return `Il y a ${Math.floor(diffInSeconds / 3600)} h`;
  if (diffInSeconds < 604800) return `Il y a ${Math.floor(diffInSeconds / 86400)} j`;

  return formatDate(d);
}

/**
 * Format word count with separators
 */
export function formatWordCount(count: number): string {
  return new Intl.NumberFormat('fr-FR').format(count);
}

export function formatGenreLabel(genre?: string): string {
  const key = (genre || '').toLowerCase();
  const labels: Record<string, string> = {
    werewolf: 'loup-garou',
    billionaire: 'milliardaire',
    mafia: 'mafia',
    fantasy: 'fantasy',
    vengeance: 'vengeance',
    romance: 'romance',
    thriller: 'thriller',
    fiction: 'fiction',
    scifi: 'science-fiction',
    mystery: 'mystere',
    horror: 'horreur',
    historical: 'historique',
    other: 'autre',
  };
  return labels[key] || (genre || 'non defini');
}

/**
 * Calculate reading time (average 200 words per minute)
 */
export function calculateReadingTime(wordCount: number): string {
  const minutes = Math.ceil(wordCount / 200);
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}min` : `${hours}h`;
}
