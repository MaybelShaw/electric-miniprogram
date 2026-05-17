import { View, Image, Text } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { Product } from '../../types'
import { resolveLocalMediaUrl } from '../../utils/media'
import AppIcon from '../AppIcon'
import PriceText from '../PriceText'
import './index.scss'

interface ProductCardProps {
  product: Product
  variant?: 'grid' | 'list' | 'compact'
  onAddCart?: (product: Product, event: any) => void
}

export default function ProductCard({ product, variant = 'grid', onAddCart }: ProductCardProps) {
  // 跳转商品详情
  const goToDetail = () => {
    Taro.navigateTo({ url: `/pages/product-detail/index?id=${product.id}` })
  }

  const basePrice = Number(product.display_price ?? product.price ?? 0)
  const sellingPrice = product.discounted_price && Number(product.discounted_price) < basePrice
    ? Number(product.discounted_price)
    : basePrice

  const getTagText = (tag?: string) => {
    switch (tag) {
      case 'brand_direct': return '品牌直发'
      case 'source_factory': return '源头厂家'
      default: return null
    }
  }

  const tagText = getTagText(product.tag)
  const productImage = resolveLocalMediaUrl(product.main_images?.[0])

  return (
    <View className={`product-card product-card--${variant}`} onClick={goToDetail}>
      <View className='product-image-wrapper'>
        {productImage ? (
          <Image
            className='product-image'
            src={productImage}
            mode='aspectFill'
          />
        ) : (
          <View className='product-image-placeholder'>
            <AppIcon name='package' tone='muted' />
            <Text>暂无图片</Text>
          </View>
        )}
      </View>

      <View className='product-info'>
        {(product.brand || tagText) ? (
          <View className='product-meta-row'>
            {product.brand ? <Text className='product-brand'>{product.brand}</Text> : null}
            {tagText ? <Text className='product-tag'>{tagText}</Text> : null}
          </View>
        ) : null}
        <View className='product-name'>
          <Text>{product.name}</Text>
        </View>

        <View className='product-bottom'>
          <PriceText value={sellingPrice} size={variant === 'compact' ? 'sm' : 'md'} />
          {onAddCart ? (
            <View className='product-add-btn' onClick={(event) => onAddCart(product, event)}>
              <AppIcon name='add' tone='primary' />
            </View>
          ) : null}
        </View>
      </View>
    </View>
  )
}
