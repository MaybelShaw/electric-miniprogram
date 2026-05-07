import { View, Image, Text } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { Product } from '../../types'
import { formatPrice } from '../../utils/format'
import { resolveLocalMediaUrl } from '../../utils/media'
import './index.scss'

interface ProductCardProps {
  product: Product
}

export default function ProductCard({ product }: ProductCardProps) {
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
    <View className='product-card' onClick={goToDetail}>
      {/* 商品图片 */}
      <View className='product-image-wrapper'>
        {productImage ? (
          <Image
            className='product-image'
            src={productImage}
            mode='aspectFill'
          />
        ) : (
          <View className='product-image-placeholder'>暂无图片</View>
        )}
      </View>

      {/* 商品信息 */}
      <View className='product-info'>
        {/* 商品名称 */}
        <View className='product-name'>
          {tagText && <Text className='product-tag'>{tagText}</Text>}
          <Text>{product.name}</Text>
        </View>
        
        {/* 价格 */}
        <View className='product-bottom'>
          <View className='price-wrapper'>
            <Text className='currency'>¥</Text>
            <Text className='current-price'>{Number(sellingPrice)}</Text>
          </View>
        </View>
      </View>
    </View>
  )
}
