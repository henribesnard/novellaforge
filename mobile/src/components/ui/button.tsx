import { Pressable, Text, ActivityIndicator, type PressableProps } from 'react-native'

type Variant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger'
type Size = 'sm' | 'md' | 'lg'

interface ButtonProps extends PressableProps {
  variant?: Variant
  size?: Size
  isLoading?: boolean
  children: React.ReactNode
}

const variantStyles: Record<Variant, { container: string; text: string }> = {
  primary: {
    container: 'bg-brand-700',
    text: 'text-white',
  },
  secondary: {
    container: 'bg-accent-600',
    text: 'text-white',
  },
  outline: {
    container: 'border border-stone-300 bg-transparent',
    text: 'text-ink',
  },
  ghost: {
    container: 'bg-transparent',
    text: 'text-ink/70',
  },
  danger: {
    container: 'bg-red-600',
    text: 'text-white',
  },
}

const sizeStyles: Record<Size, { container: string; text: string }> = {
  sm: { container: 'px-3 py-2', text: 'text-sm' },
  md: { container: 'px-5 py-3', text: 'text-base' },
  lg: { container: 'px-7 py-4', text: 'text-lg' },
}

export function Button({
  variant = 'primary',
  size = 'md',
  isLoading,
  disabled,
  children,
  ...props
}: ButtonProps) {
  const v = variantStyles[variant]
  const s = sizeStyles[size]

  return (
    <Pressable
      className={`flex-row items-center justify-center gap-2 rounded-full ${v.container} ${s.container} ${disabled || isLoading ? 'opacity-50' : ''}`}
      disabled={disabled || isLoading}
      style={({ pressed }) => ({ transform: [{ scale: pressed ? 0.95 : 1 }] })}
      {...props}
    >
      {isLoading && <ActivityIndicator size="small" color={variant === 'outline' || variant === 'ghost' ? '#1b1a17' : '#ffffff'} />}
      {typeof children === 'string' ? (
        <Text className={`font-medium ${v.text} ${s.text}`}>{children}</Text>
      ) : (
        children
      )}
    </Pressable>
  )
}
