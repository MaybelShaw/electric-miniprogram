import { Image, View } from '@tarojs/components'
import './index.scss'

export type AppIconName =
  | 'search'
  | 'home'
  | 'cart'
  | 'service'
  | 'location'
  | 'message'
  | 'company'
  | 'credit'
  | 'order'
  | 'pay'
  | 'ship'
  | 'done'
  | 'refund'
  | 'package'
  | 'profile'
  | 'store'
  | 'close'
  | 'add'
  | 'minus'
  | 'empty'

interface AppIconProps {
  name: AppIconName
  className?: string
  tone?: 'default' | 'primary' | 'gold' | 'danger' | 'muted'
}

export default function AppIcon({ name, className = '', tone = 'default' }: AppIconProps) {
  return (
    <View className={`app-icon app-icon--${name} app-icon--${tone} ${className}`}>
      <Image
        className='app-icon-image'
        src={`/assets/icons/app/${tone}/${name}.png`}
        mode='aspectFit'
      />
    </View>
  )
}
