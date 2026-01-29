'use client'

import dynamic from 'next/dynamic';

export const LazyChapterAudioPlayer = dynamic(
  () => import('./chapter-audio-player').then((mod) => mod.ChapterAudioPlayer),
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
    ssr: false,
  }
);
