import { StatusBar } from 'expo-status-bar';
import { Text, View } from 'react-native';

export default function App() {
  return (
    <View className="flex-1 bg-white items-center justify-center">
      <Text className="text-lg font-bold text-gray-800">Welcome to NovellaForge Mobile!</Text>
      <StatusBar style="auto" />
    </View>
  );
}
