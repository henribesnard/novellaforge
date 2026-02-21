'use client'

import * as React from 'react'
import { useParams, useRouter } from 'next/navigation'
import { getDocuments, lazyGenerateNextWs } from '@/lib/api-extended'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Document } from '@/types'

export function ReaderMode() {
    const params = useParams()
    const router = useRouter()
    const projectId = params.id as string

    const [chapters, setChapters] = React.useState<Document[]>([])
    const [isLoading, setIsLoading] = React.useState(true)
    const [isGenerating, setIsGenerating] = React.useState(false)
    const [instruction, setInstruction] = React.useState('')
    const [error, setError] = React.useState('')
    const [statusMessage, setStatusMessage] = React.useState('')
    const [streamingText, setStreamingText] = React.useState('')
    const [streamingTitle, setStreamingTitle] = React.useState('')

    const closeWsRef = React.useRef<(() => void) | null>(null)
    const streamingRef = React.useRef<HTMLDivElement>(null)

    const loadChapters = React.useCallback(async () => {
        try {
            setIsLoading(true)
            const docs = await getDocuments(projectId)
            const chaps = docs
                .filter((d) => d.document_type === 'chapter')
                .sort((a, b) => a.order_index - b.order_index)
            setChapters(chaps)
        } catch (err: any) {
            setError(err.message || 'Erreur lors du chargement des chapitres')
        } finally {
            setIsLoading(false)
        }
    }, [projectId])

    React.useEffect(() => {
        loadChapters()
    }, [loadChapters])

    // Cleanup WebSocket on unmount
    React.useEffect(() => {
        return () => {
            closeWsRef.current?.()
        }
    }, [])

    const handleGenerateNext = () => {
        setIsGenerating(true)
        setError('')
        setStatusMessage('')
        setStreamingText('')
        setStreamingTitle('')

        const close = lazyGenerateNextWs(projectId, {
            instruction: instruction || undefined,
            onStatus: (message) => {
                setStatusMessage(message)
            },
            onChunk: (content, _beatIndex) => {
                setStreamingText((prev) => (prev ? prev + '\n\n' + content : content))
                // Scroll to streaming content
                setTimeout(() => {
                    streamingRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
                }, 100)
            },
            onComplete: async (data) => {
                setStreamingTitle(data.chapter_title)
                setStreamingText('')
                setStatusMessage('')
                setInstruction('')
                setIsGenerating(false)
                closeWsRef.current = null
                // Reload all chapters to include the new one
                await loadChapters()
                // Scroll to the bottom
                setTimeout(() => {
                    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })
                }, 200)
            },
            onError: (message) => {
                setError(message)
                setIsGenerating(false)
                setStatusMessage('')
                setStreamingText('')
                closeWsRef.current = null
            },
        })

        closeWsRef.current = close
    }

    if (isLoading) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-stone-50">
                <p className="text-lg text-ink/70">Chargement de l'histoire...</p>
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-stone-50 pb-20">
            {/* Header */}
            <div className="sticky top-0 z-10 flex items-center justify-between border-b border-stone-200 bg-white/80 px-6 py-4 backdrop-blur-md">
                <h1 className="text-xl font-serif text-ink">Mode Lecture Continue</h1>
                <Button variant="outline" onClick={() => router.push(`/projects/${projectId}`)}>
                    Retour au Dashboard
                </Button>
            </div>

            {/* Reader Content */}
            <div className="mx-auto max-w-3xl p-6">
                {chapters.length === 0 && !isGenerating ? (
                    <div className="my-10 text-center">
                        <h2 className="text-2xl font-serif text-ink mb-4">L'histoire n'a pas encore commencé.</h2>
                        <p className="text-ink/60 mb-8">Lancez la première génération pour commencer à lire.</p>
                    </div>
                ) : (
                    <div className="space-y-12">
                        {chapters.map((chapter) => (
                            <div key={chapter.id} className="prose prose-stone max-w-none prose-lg">
                                <h2 className="font-serif text-center font-semibold text-3xl mb-8 tracking-tight">{chapter.title}</h2>
                                <div
                                    className="font-serif leading-relaxed text-ink/90 whitespace-pre-wrap"
                                    dangerouslySetInnerHTML={{ __html: chapter.content }}
                                />
                                <div className="mt-8 flex items-center justify-center">
                                    <div className="h-px w-24 bg-stone-300"></div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {/* Streaming content (live generation) */}
                {isGenerating && (
                    <div ref={streamingRef} className="mt-12 animate-fade-in">
                        {streamingTitle && (
                            <h2 className="font-serif text-center font-semibold text-3xl mb-8 tracking-tight text-ink/70">
                                {streamingTitle}
                            </h2>
                        )}

                        {statusMessage && !streamingText && (
                            <div className="flex items-center justify-center gap-3 py-8">
                                <div className="h-5 w-5 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
                                <p className="text-ink/60 text-lg font-serif italic">{statusMessage}</p>
                            </div>
                        )}

                        {streamingText && (
                            <div className="prose prose-stone max-w-none prose-lg">
                                <div className="font-serif leading-relaxed text-ink/70 whitespace-pre-wrap">
                                    {streamingText}
                                </div>
                                <div className="mt-4 flex items-center gap-2 text-sm text-ink/40">
                                    <div className="h-3 w-3 animate-pulse rounded-full bg-brand-400" />
                                    {statusMessage || 'Écriture en cours...'}
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {/* Action Panel */}
                <div className="mt-16 rounded-xl border border-stone-200 bg-white p-6 shadow-sm">
                    <h3 className="mb-4 text-lg font-medium text-ink">Que doit-il se passer ensuite ?</h3>

                    {error && (
                        <div className="mb-4 rounded-lg bg-red-50 p-4 text-sm text-red-800">
                            {error}
                        </div>
                    )}

                    <div className="space-y-4">
                        <Input
                            placeholder="Ex: Le héros découvre un passage secret... (Optionnel)"
                            value={instruction}
                            onChange={(e) => setInstruction(e.target.value)}
                            className="w-full text-base"
                            disabled={isGenerating}
                        />

                        <Button
                            variant="primary"
                            className="w-full py-6 text-lg"
                            disabled={isGenerating}
                            onClick={handleGenerateNext}
                            isLoading={isGenerating}
                        >
                            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                            </svg>
                            Générer la suite
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    )
}
