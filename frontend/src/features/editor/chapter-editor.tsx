'use client'

import { useEffect } from 'react'
import { type Editor, useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'

interface ChapterEditorProps {
  content: string
  onChange: (content: string) => void
  editable?: boolean
  onEditorReady?: (editor: Editor | null) => void
}

export function ChapterEditor({ content, onChange, editable = true, onEditorReady }: ChapterEditorProps) {
  const editor = useEditor({
    extensions: [
      StarterKit,
      Placeholder.configure({ placeholder: 'Contenu du chapitre...' }),
    ],
    content,
    editable,
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML())
    },
  })

  useEffect(() => {
    if (!editor) return
    if (content !== editor.getHTML()) {
      editor.commands.setContent(content, false)
    }
  }, [content, editor])

  useEffect(() => {
    onEditorReady?.(editor)
  }, [editor, onEditorReady])

  return (
    <div className="prose prose-stone prose-sm max-w-none">
      <EditorContent editor={editor} />
    </div>
  )
}
