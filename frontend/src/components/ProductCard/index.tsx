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
          src={product.main_images?.[0] || 'https://via.placeholder.com/330x330/F7F8FA/CCCCCC?text=No+Image'} 
          mode='aspectFill' 
        />
      </View>

      {/* 商品信息 */}
      <View className='product-info'>
        {/* 商品名称 */}
        <View className='product-name'>{product.name}</View>
        
        {/* 商品描述 */}
        {product.description && (
          <View className='product-desc'>{product.description}</View>
        )}

        {/* 价格和销量 */}
        <View className='product-bottom'>
          <View className='price-wrapper'>
            <Text className='current-price'>{Number(sellingPrice).toFixed(2)}</Text>
          </View>
          <View className='sales-info'>
            <Text className='sales-count'>已售 {product.sales_count}</Text>
          </View>
        </View>

        {/* 库存提示 */}
        {product.stock < 10 && product.stock > 0 && (
          <View className='stock-warning'>仅剩 {product.stock} 件</View>
        )}
        {product.stock === 0 && (
          <View className='stock-empty'>已售罄</View>
        )}
      </View>
    </View>
  )
}
