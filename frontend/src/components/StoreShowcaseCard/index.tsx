import { Image, Text, View } from '@tarojs/components'
import { Store } from '../../types'
import { resolveLocalMediaUrl } from '../../utils/media'
import AppIcon from '../AppIcon'
import './index.scss'

interface StoreShowcaseCardProps {
  store: Store
  className?: string
  onClick?: () => void
}

export default function StoreShowcaseCard({
  store,
  className = '',
  onClick,
}: StoreShowcaseCardProps) {
  const isChuangyi = /创艺|創藝|chuangyi/i.test(store.name)
  const coverImage = resolveLocalMediaUrl(store.cover_image || store.logo)
  const logoImage = resolveLocalMediaUrl(store.logo)
  const description = store.description || (
    isChuangyi
      ? '创艺精选生活馆，按空间灵感组织家电方案'
      : '精选合作品牌，浏览家电与生活方式方案'
  )

  return (
    <View
      className={`store-showcase-card ${isChuangyi ? 'store-showcase-card--chuangyi' : ''} ${className}`}
      onClick={onClick}
    >
      <View className='store-showcase-media'>
        {coverImage ? (
          <Image className='store-showcase-cover' src={coverImage} mode='aspectFill' />
        ) : (
          <View className='store-showcase-cover store-showcase-fallback'>
            <AppIcon name='store' tone='gold' />
          </View>
        )}
        <View className='store-showcase-shade' />
        <View className='store-showcase-badge'>{isChuangyi ? '创艺精选' : '品牌馆'}</View>
      </View>
      <View className='store-showcase-body'>
        <View className='store-showcase-head'>
          <View className={`store-showcase-logo-wrap ${logoImage ? '' : 'store-showcase-logo-wrap--icon'}`}>
            {logoImage ? (
              <Image className='store-showcase-logo' src={logoImage} mode='aspectFit' />
            ) : (
              <AppIcon name='store' tone='muted' />
            )}
          </View>
          <View className='store-showcase-title-block'>
            <Text className='store-showcase-kicker'>
              {isChuangyi ? 'CURATED HOME STUDIO' : 'PARTNER BRAND'}
            </Text>
            <Text className='store-showcase-title'>{store.name}</Text>
          </View>
        </View>
        <Text className='store-showcase-desc'>{description}</Text>
        <View className='store-showcase-footer'>
          <Text>{isChuangyi ? '查看创艺方案' : '进店浏览'}</Text>
          <Text className='store-showcase-arrow'>›</Text>
        </View>
      </View>
    </View>
  )
}
