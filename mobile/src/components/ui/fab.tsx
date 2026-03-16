import { Pressable, type PressableProps } from 'react-native'
import { Plus } from 'lucide-react-native'

interface FabProps extends PressableProps {
  icon?: React.ReactNode
}

export function Fab({ icon, ...props }: FabProps) {
  return (
    <Pressable
      className="absolute bottom-6 right-6 h-14 w-14 items-center justify-center rounded-full bg-brand-700"
      style={({ pressed }) => ({
        transform: [{ scale: pressed ? 0.9 : 1 }],
        shadowColor: '#1b1a17',
        shadowOffset: { width: 0, height: 6 },
        shadowOpacity: 0.2,
        shadowRadius: 12,
        elevation: 6,
      })}
      {...props}
    >
      {icon || <Plus size={24} color="#ffffff" />}
    </Pressable>
  )
}
