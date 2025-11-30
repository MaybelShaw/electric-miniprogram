import { View, Image, Text } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { Product } from '../../types'
import { formatPrice } from '../../utils/format'
import './index.scss'

interface ProductCardProps {
  product: Product
}

export default function ProductCard({ product }: ProductCardProps) {
  // 计算折扣百分比
  const getDiscountPercent = () => {
    if (!product.discounted_price || product.discounted_price >= parseFloat(product.price)) {
      return null
    }
    const percent = Math.round((1 - product.discounted_price / parseFloat(product.price)) * 100)
    return percent > 0 ? percent : null
  }

  const discountPercent = getDiscountPercent()

  // 跳转商品详情
  const goToDetail = () => {
    Taro.navigateTo({ url: `/pages/product-detail/index?id=${product.id}` })
  }

  return (
    <View className='product-card' onClick={goToDetail}>
      {/* 商品图片 */}
      <View className='product-image-wrapper'>
        <Image 
          className='product-image' 
          src={product.main_images?.[0] || 'https://via.placeholder.com/330x330/F7F8FA/CCCCCC?text=No+Image'} 
          mode='aspectFill' 
        />
        
        {/* 折扣标签 */}
        {discountPercent && (
          <View className='discount-badge'>
            <Text className='discount-text'>{discountPercent}% OFF</Text>
          </View>
        )}
        
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
            {discountPercent ? (
              <>
                <Text className='current-price'>{Number(product.discounted_price).toFixed(2)}</Text>
                <Text className='original-price'>{formatPrice(product.price)}</Text>
              </>
            ) : (
              <Text className='current-price'>{Number(product.price).toFixed(2)}</Text>
            )}
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
