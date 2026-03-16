import { View, Text } from 'react-native'

type Variant = 'default' | 'success' | 'warning' | 'danger' | 'brand'

interface BadgeProps {
  variant?: Variant
  children: string
}

const variantStyles: Record<Variant, { bg: string; text: string }> = {
  default: { bg: 'bg-stone-200', text: 'text-ink/70' },
  success: { bg: 'bg-emerald-100', text: 'text-emerald-700' },
  warning: { bg: 'bg-amber-100', text: 'text-amber-700' },
  danger: { bg: 'bg-red-100', text: 'text-red-700' },
  brand: { bg: 'bg-brand-100', text: 'text-brand-700' },
}

export function Badge({ variant = 'default', children }: BadgeProps) {
  const v = variantStyles[variant]
  return (
    <View className={`rounded-full px-2.5 py-1 ${v.bg}`}>
      <Text className={`text-xs font-medium ${v.text}`}>{children}</Text>
    </View>
  )
}
