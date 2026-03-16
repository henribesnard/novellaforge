import { Text as RNText, type TextProps as RNTextProps } from 'react-native'

type Variant = 'h1' | 'h2' | 'h3' | 'h4' | 'body' | 'caption' | 'label'

interface TextProps extends RNTextProps {
  variant?: Variant
}

const variantStyles: Record<Variant, string> = {
  h1: 'text-3xl font-bold text-ink',
  h2: 'text-2xl font-semibold text-ink',
  h3: 'text-xl font-semibold text-ink',
  h4: 'text-lg font-medium text-ink',
  body: 'text-base text-ink/80',
  caption: 'text-sm text-ink/60',
  label: 'text-xs uppercase tracking-widest text-ink/50',
}

export function Text({ variant = 'body', className = '', ...props }: TextProps) {
  return <RNText className={`${variantStyles[variant]} ${className}`} {...props} />
}
