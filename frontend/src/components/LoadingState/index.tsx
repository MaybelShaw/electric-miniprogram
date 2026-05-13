import { Text, View } from '@tarojs/components'
import './index.scss'

interface LoadingStateProps {
  text?: string
  className?: string
}

export default function LoadingState({ text = '加载中...', className = '' }: LoadingStateProps) {
  return (
    <View className={`loading-state ${className}`}>
      <View className='loading-state-spinner' />
      <Text className='loading-state-text'>{text}</Text>
    </View>
  )
}
