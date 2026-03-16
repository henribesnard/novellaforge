/// <reference types="nativewind/types" />

import 'react-native'

declare module 'react-native' {
  interface ViewProps {
    className?: string
  }
  interface TextProps {
    className?: string
  }
  interface ImageProps {
    className?: string
  }
  interface TextInputProps {
    className?: string
  }
  interface PressableProps {
    className?: string
  }
  interface TouchableOpacityProps {
    className?: string
  }
  interface KeyboardAvoidingViewProps {
    className?: string
  }
}

declare module 'react-native-safe-area-context' {
  interface SafeAreaViewProps {
    className?: string
  }
}
