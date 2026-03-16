import { Stack } from 'expo-router'

export default function ProjectLayout() {
  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: '#f7f2ea' },
        animation: 'slide_from_right',
      }}
    />
  )
}
