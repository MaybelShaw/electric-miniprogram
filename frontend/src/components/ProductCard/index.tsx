import { View, Image, Text } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { Product } from '../../types'
import { formatPrice } from '../../utils/format'
import './index.scss'

interface ProductCardProps {
  product: Product
}

export default function ProductCard({ product }: ProductCardProps) {
  // 跳转商品详情
  const goToDetail = () => {
    Taro.navigateTo({ url: `/pages/product-detail/index?id=${product.id}` })
  }

  const sellingPrice = product.discounted_price && product.discounted_price < parseFloat(product.price)
    ? product.discounted_price
    : parseFloat(product.price)

  return (
    <View className='product-card' onClick={goToDetail}>
      {/* 商品图片 */}
      <View className='product-image-wrapper'>
        <Image 
          className='product-image' 
          src={product.main_images?.[0] || 'https://via.placeholder.com/330x330/FFFFFF/CCCCCC?text=No+Image'} 
          mode='aspectFit' 
        />
      </View>

      {/* 商品信息 */}
      <View className='product-info'>
        {/* 商品名称 */}
        <View className='product-name'>{product.name}</View>
        
        {/* 价格 */}
        <View className='product-bottom'>
          <View className='price-wrapper'>
            <Text className='currency'>¥</Text>
            <Text className='current-price'>{Number(sellingPrice)}</Text>
            <Text className='price-unit'>/台</Text>
          </View>
        </View>
      </View>
    </View>
  )
}
