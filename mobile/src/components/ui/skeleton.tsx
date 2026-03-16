import { useEffect, useRef } from 'react'
import { Animated, type StyleProp, type ViewStyle } from 'react-native'

interface SkeletonProps {
  width?: number | string
  height?: number
  variant?: 'text' | 'circle' | 'rect'
  style?: StyleProp<ViewStyle>
}

export function Skeleton({ width, height = 16, variant = 'text', style }: SkeletonProps) {
  const opacity = useRef(new Animated.Value(0.3)).current

  useEffect(() => {
    const animation = Animated.loop(
      Animated.sequence([
        Animated.timing(opacity, { toValue: 0.7, duration: 800, useNativeDriver: true }),
        Animated.timing(opacity, { toValue: 0.3, duration: 800, useNativeDriver: true }),
      ])
    )
    animation.start()
    return () => animation.stop()
  }, [opacity])

  const borderRadius = variant === 'circle' ? 999 : variant === 'rect' ? 12 : 6

  return (
    <Animated.View
      style={[
        { width: width as number, height, borderRadius, backgroundColor: '#e3d8c9' },
        { opacity },
        style,
      ]}
    />
  )
}
