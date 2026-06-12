import { Text, View } from '@tarojs/components'
import Taro from '@tarojs/taro'
import AppIcon, { AppIconName } from '../AppIcon'
import './index.scss'

type StoreNavKey = 'home' | 'category' | 'profile'

interface StoreBottomNavProps {
  storeId: number | string
  active: StoreNavKey
  storeIsMain?: boolean
}

const navItems: Array<{ key: StoreNavKey; label: string; icon: AppIconName }> = [
  { key: 'home', label: '首页', icon: 'home' },
  { key: 'category', label: '分类', icon: 'package' },
  { key: 'profile', label: '我的', icon: 'profile' },
]

export default function StoreBottomNav({ storeId, active, storeIsMain }: StoreBottomNavProps) {
  const handleClick = (key: StoreNavKey) => {
    if (key === active) return

    if (key === 'home') {
      if (storeIsMain) {
        Taro.switchTab({ url: '/pages/home/index' })
        return
      }

      Taro.redirectTo({ url: `/pages/store-detail/index?id=${storeId}` })
      return
    }

    if (key === 'category') {
      Taro.redirectTo({ url: `/pages/store-categories/index?store_id=${storeId}` })
      return
    }

    Taro.redirectTo({ url: `/pages/store-profile/index?store_id=${storeId}` })
  }

  return (
    <View className='store-bottom-nav'>
      {navItems.map(item => {
        const isActive = item.key === active
        return (
          <View
            key={item.key}
            className={`store-bottom-nav__item ${isActive ? 'store-bottom-nav__item--active' : ''}`}
            onClick={() => handleClick(item.key)}
          >
            <AppIcon name={item.icon} tone={isActive ? 'primary' : 'muted'} />
            <Text className='store-bottom-nav__label'>{item.label}</Text>
          </View>
        )
      })}
    </View>
  )
}
