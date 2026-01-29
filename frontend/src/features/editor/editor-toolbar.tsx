'use client'

import { Bold, Heading2, Italic, List, ListOrdered } from 'lucide-react'
import type { Editor } from '@tiptap/react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface EditorToolbarProps {
  editor: Editor | null
}

export function EditorToolbar({ editor }: EditorToolbarProps) {
  if (!editor) return null

  const toggleHeading = () => editor.chain().focus().toggleHeading({ level: 2 }).run()
  const toggleBold = () => editor.chain().focus().toggleBold().run()
  const toggleItalic = () => editor.chain().focus().toggleItalic().run()
  const toggleBullet = () => editor.chain().focus().toggleBulletList().run()
  const toggleOrdered = () => editor.chain().focus().toggleOrderedList().run()

  return (
    <div className="flex flex-wrap gap-2 rounded-2xl border border-stone-200 bg-white/80 p-2">
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={toggleHeading}
        className={cn(editor.isActive('heading', { level: 2 }) && 'bg-stone-100')}
      >
        <Heading2 className="h-4 w-4" />
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={toggleBold}
        className={cn(editor.isActive('bold') && 'bg-stone-100')}
      >
        <Bold className="h-4 w-4" />
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={toggleItalic}
        className={cn(editor.isActive('italic') && 'bg-stone-100')}
      >
        <Italic className="h-4 w-4" />
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={toggleBullet}
        className={cn(editor.isActive('bulletList') && 'bg-stone-100')}
      >
        <List className="h-4 w-4" />
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={toggleOrdered}
        className={cn(editor.isActive('orderedList') && 'bg-stone-100')}
      >
        <ListOrdered className="h-4 w-4" />
      </Button>
    </div>
  )
}
