import { useState, useRef, useCallback } from 'react'
import {
  View,
  FlatList,
  TextInput,
  Pressable,
  KeyboardAvoidingView,
  Platform,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { Send } from 'lucide-react-native'
import { useQuery } from '@tanstack/react-query'
import { Text } from '../../src/components/ui/text'
import { Card } from '../../src/components/ui/card'
import { sendChatMessage, type ChatMessage } from '../../src/services/chat.service'
import { getProjects } from '../../src/services/project.service'

export default function ChatScreen() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const flatListRef = useRef<FlatList>(null)

  const { data } = useQuery({ queryKey: ['projects'], queryFn: () => getProjects() })
  const firstProject = data?.projects?.[0]

  const handleSend = useCallback(async () => {
    const text = input.trim()
    if (!text || sending) return
    if (!firstProject) return

    const userMsg: ChatMessage = { role: 'user', content: text }
    setMessages((prev) => [...prev, userMsg])
    setInput('')

    try {
      setSending(true)
      const response = await sendChatMessage(firstProject.id, text, [...messages, userMsg])
      setMessages((prev) => [...prev, { role: 'assistant', content: response }])
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Erreur: ${err.message}` },
      ])
    } finally {
      setSending(false)
    }
  }, [input, sending, firstProject, messages])

  return (
    <SafeAreaView className="flex-1 bg-canvas" edges={['top']}>
      <View className="px-5 pt-2 pb-4 border-b border-stone-200">
        <Text variant="h2">Chat IA</Text>
        <Text variant="caption">
          {firstProject ? firstProject.title : 'Aucun projet selectionne'}
        </Text>
      </View>

      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        className="flex-1"
        keyboardVerticalOffset={90}
      >
        <FlatList
          ref={flatListRef}
          data={messages}
          keyExtractor={(_, i) => String(i)}
          renderItem={({ item }) => (
            <View
              className={`mb-3 max-w-[85%] ${
                item.role === 'user' ? 'self-end' : 'self-start'
              }`}
            >
              <View
                className={`rounded-2xl px-4 py-3 ${
                  item.role === 'user'
                    ? 'bg-brand-700 rounded-br-md'
                    : 'bg-stone-100 rounded-bl-md'
                }`}
              >
                <Text
                  className={`text-base ${
                    item.role === 'user' ? 'text-white' : 'text-ink'
                  }`}
                >
                  {item.content}
                </Text>
              </View>
            </View>
          )}
          contentContainerStyle={{ padding: 20, flexGrow: 1, justifyContent: 'flex-end' }}
          onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: true })}
          ListEmptyComponent={
            <View className="flex-1 items-center justify-center">
              <Text variant="caption" className="text-center">
                Posez une question sur votre projet.{'\n'}L'IA utilisera le contexte de votre roman.
              </Text>
            </View>
          }
        />

        <View className="flex-row items-end gap-2 px-4 pb-4 pt-2 border-t border-stone-200 bg-shell">
          <TextInput
            className="flex-1 rounded-xl border border-stone-300 bg-white/80 px-4 py-3 text-base text-ink"
            placeholder="Votre message..."
            placeholderTextColor="#bca993"
            value={input}
            onChangeText={setInput}
            multiline
            maxLength={2000}
            editable={!sending}
          />
          <Pressable
            onPress={handleSend}
            disabled={!input.trim() || sending}
            className="h-12 w-12 items-center justify-center rounded-full bg-brand-700"
            style={({ pressed }) => ({
              opacity: !input.trim() || sending ? 0.5 : pressed ? 0.7 : 1,
              transform: [{ scale: pressed ? 0.9 : 1 }],
            })}
          >
            <Send size={20} color="#ffffff" />
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  )
}
