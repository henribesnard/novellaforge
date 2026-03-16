import { View, type ViewProps } from 'react-native'

type Variant = 'default' | 'outlined' | 'elevated'

interface CardProps extends ViewProps {
  variant?: Variant
}

const variantStyles: Record<Variant, string> = {
  default: 'bg-white/80 border border-stone-200',
  outlined: 'bg-transparent border border-stone-300',
  elevated: 'bg-white border border-stone-100',
}

export function Card({ variant = 'default', className = '', ...props }: CardProps) {
  return (
    <View
      className={`rounded-2xl ${variantStyles[variant]} ${className}`}
      style={{
        shadowColor: '#1b1a17',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.08,
        shadowRadius: 12,
        elevation: 3,
      }}
      {...props}
    />
  )
}
