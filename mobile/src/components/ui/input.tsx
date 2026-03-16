import { useState } from 'react'
import { View, Text, TextInput, type TextInputProps } from 'react-native'

interface InputProps extends TextInputProps {
  label?: string
  error?: string
}

export function Input({ label, error, ...props }: InputProps) {
  const [focused, setFocused] = useState(false)

  return (
    <View className="w-full">
      {label && (
        <Text className="mb-1 text-sm font-medium text-ink/70">{label}</Text>
      )}
      <TextInput
        className={`w-full rounded-xl border px-3 py-3 text-base text-ink bg-white/80 ${
          error
            ? 'border-red-500'
            : focused
              ? 'border-brand-500'
              : 'border-stone-300'
        }`}
        placeholderTextColor="#bca993"
        onFocus={(e) => {
          setFocused(true)
          props.onFocus?.(e)
        }}
        onBlur={(e) => {
          setFocused(false)
          props.onBlur?.(e)
        }}
        {...props}
      />
      {error && <Text className="mt-1 text-sm text-red-600">{error}</Text>}
    </View>
  )
}
