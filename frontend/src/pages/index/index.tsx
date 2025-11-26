import { View, Text } from '@tarojs/components'
import { useLoad } from '@tarojs/taro'
import './index.scss'

export default function Index () {
  useLoad(() => {
    // 页面加载完成
  })

  return (
    <View className='index'>
      <Text>Hello world!</Text>
    </View>
  )
}
