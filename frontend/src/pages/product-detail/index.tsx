import { useState, useEffect } from 'react'
import { View, Swiper, SwiperItem, Image, ScrollView, Text, Button } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { productService } from '../../services/product'
import { cartService } from '../../services/cart'
import { TokenManager } from '../../utils/request'
import { Product } from '../../types'
import { formatPrice } from '../../utils/format'
import './index.scss'

export default function ProductDetail() {
  const [product, setProduct] = useState<Product | null>(null)
  const [quantity, setQuantity] = useState(1)
  const [loading, setLoading] = useState(true)
  const [currentImageIndex, setCurrentImageIndex] = useState(0)
  const [showQuantityPopup, setShowQuantityPopup] = useState(false)
  const [actionType, setActionType] = useState<'cart' | 'buy'>('cart')

  useEffect(() => {
    const instance = Taro.getCurrentInstance()
    const id = instance.router?.params?.id
    if (id) {
      loadProduct(Number(id))
    }
  }, [])

  const loadProduct = async (id: number) => {
    setLoading(true)
    try {
      const data = await productService.getProductDetail(id)
      setProduct(data)
    } catch (error) {
      Taro.showToast({ title: '加载失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }



  const handleShowQuantityPopup = (type: 'cart' | 'buy') => {
    if (!TokenManager.getAccessToken()) {
      Taro.showToast({ title: '请先登录', icon: 'none' })
      return
    }

    if (!product) return

    setActionType(type)
    setQuantity(1) // 重置数量为1
    setShowQuantityPopup(true)
  }

  const handleConfirmAction = async () => {
    if (!product) return

    if (actionType === 'cart') {
      try {
        await cartService.addItem(product.id, quantity)
        setShowQuantityPopup(false)
        Taro.showToast({ title: '已加入购物车', icon: 'success' })
      } catch (error) {
        Taro.showToast({ title: '添加失败', icon: 'none' })
      }
    } else {
      setShowQuantityPopup(false)
      Taro.navigateTo({
        url: `/pages/order-confirm/index?productId=${product.id}&quantity=${quantity}`
      })
    }
  }



  const handleQuantityChange = (delta: number) => {
    const newQuantity = quantity + delta
    if (newQuantity < 1) return
    if (product && newQuantity > product.stock) {
      Taro.showToast({ title: '库存不足', icon: 'none' })
      return
    }
    setQuantity(newQuantity)
  }

  const handleImagePreview = (index: number, isDetailImage = false) => {
    if (!product) return
    
    const images = isDetailImage ? product.detail_images : product.main_images
    if (!images || images.length === 0) return
    
    Taro.previewImage({
      urls: images,
      current: images[index]
    })
  }

  const handleSwiperChange = (e: any) => {
    setCurrentImageIndex(e.detail.current)
  }

  if (loading) {
    return (
      <View className='product-detail loading-container'>
        <View className='loading-text'>加载中...</View>
      </View>
    )
  }

  if (!product) {
    return (
      <View className='product-detail error-container'>
        <View className='error-text'>商品不存在</View>
        <Button className='back-btn' onClick={() => Taro.navigateBack()}>
          返回
        </Button>
      </View>
    )
  }

  return (
    <View className='product-detail'>
      <ScrollView className='content' scrollY>
        {/* 商品主图 */}
        <View className='image-container'>
          <Swiper 
            className='image-swiper' 
            indicatorDots={false}
            circular
            onChange={handleSwiperChange}
          >
            {product.main_images.map((img, index) => (
              <SwiperItem key={index}>
                <Image 
                  className='product-image' 
                  src={img} 
                  mode='aspectFill'
                  onClick={() => handleImagePreview(index)}
                />
              </SwiperItem>
            ))}
          </Swiper>
          {product.main_images.length > 1 && (
            <View className='image-indicator'>
              {currentImageIndex + 1} / {product.main_images.length}
            </View>
          )}
        </View>

        {/* 商品信息 */}
        <View className='product-info'>
          <View className='product-name'>{product.name}</View>
          {product.description && (
            <View className='product-desc'>{product.description}</View>
          )}
          <View className='product-price-row'>
            <View className='price-wrapper'>
              <Text className='price-label'>¥</Text>
              <Text className='price'>
                 {(product.discounted_price && product.discounted_price < parseFloat(product.price)
                   ? product.discounted_price
                   : parseFloat(product.price)).toFixed(2)}
               </Text>
            </View>
            <View className='sales-info'>
              <Text className='sales'>销量 {product.sales_count}</Text>
            </View>
          </View>
          <View className='product-meta'>
            <View className='meta-item'>
              <Text className='meta-label'>品牌</Text>
              <Text className='meta-value'>{product.brand}</Text>
            </View>
            <View className='meta-item'>
              <Text className='meta-label'>分类</Text>
              <Text className='meta-value'>{product.category}</Text>
            </View>
          </View>
        </View>

        {/* 规格选择 */}
        {product.specifications && Object.keys(product.specifications).length > 0 && (
          <View className='specs-section'>
            <View className='section-title'>商品规格</View>
            <View className='specs-list'>
              {Object.entries(product.specifications).map(([key, value]) => (
                <View key={key} className='spec-item'>
                  <Text className='spec-label'>{key}</Text>
                  <Text className='spec-value'>{String(value)}</Text>
                </View>
              ))}
            </View>
          </View>
        )}

        {/* 商品详情 */}
        {/* 商品详情 */}
        <View className='detail-section'>
          <View className='section-title'>
            <View className='title-line' />
            <Text className='title-text'>商品详情</Text>
            <View className='title-line' />
          </View>
          
          {product.detail_images && product.detail_images.length > 0 ? (
            <View className='detail-images'>
              {product.detail_images.map((img, index) => (
                <View key={index} className='detail-image-wrapper'>
                  <Image 
                    className='detail-image' 
                    src={img} 
                    mode='widthFix'
                    lazyLoad
                    onClick={() => handleImagePreview(index, true)}
                  />
                </View>
              ))}
              <View className='detail-end'>
                <View className='end-line' />
                <Text className='end-text'>已经到底啦</Text>
                <View className='end-line' />
              </View>
            </View>
          ) : (
            <View className='no-detail'>
              <View className='no-detail-icon'>📦</View>
              <View className='no-detail-text'>暂无详细信息</View>
              <View className='no-detail-tip'>商品详情图片正在准备中</View>
            </View>
          )}
        </View>
      </ScrollView>

      {/* 底部操作栏 */}
      <View className='footer-bar'>
        <View className='footer-left'>
          <View className='icon-btn' onClick={() => Taro.switchTab({ url: '/pages/home/index' })}>
            <View className='icon-wrapper'>
              <Text className='icon'>🏠</Text>
            </View>
            <Text className='icon-text'>首页</Text>
          </View>

          <View className='icon-btn' onClick={() => Taro.switchTab({ url: '/pages/cart/index' })}>
            <View className='icon-wrapper'>
              <Text className='icon'>🛒</Text>
            </View>
            <Text className='icon-text'>购物车</Text>
          </View>
        </View>
        <View className='footer-right'>
          <View 
            className={`action-btn cart-btn ${product.stock === 0 ? 'disabled' : ''}`}
            onClick={() => product.stock > 0 && handleShowQuantityPopup('cart')}
          >
            加入购物车
          </View>
          <View 
            className={`action-btn buy-btn ${product.stock === 0 ? 'disabled' : ''}`}
            onClick={() => product.stock > 0 && handleShowQuantityPopup('buy')}
          >
            {product.stock === 0 ? '已售罄' : '立即购买'}
          </View>
        </View>
      </View>

      {/* 数量选择弹窗 */}
      {showQuantityPopup && (
        <View className='quantity-popup-overlay' onClick={() => setShowQuantityPopup(false)}>
          <View className='quantity-popup' onClick={(e) => e.stopPropagation()}>
            <View className='popup-header'>
              <View className='popup-product-info'>
                <Image className='popup-product-image' src={product.main_images[0]} mode='aspectFill' />
                <View className='popup-product-details'>
                  <View className='popup-product-name'>{product.name}</View>
                  <View className='popup-product-price'>¥{product.price}</View>
                  <View className='popup-stock-text'>库存 {product.stock} 件</View>
                </View>
              </View>
              <View className='popup-close' onClick={() => setShowQuantityPopup(false)}>✕</View>
            </View>

            <View className='popup-quantity-section'>
              <Text className='popup-section-title'>购买数量</Text>
              <View className='popup-quantity-control'>
                <View 
                  className={`popup-btn minus ${quantity <= 1 ? 'disabled' : ''}`}
                  onClick={() => handleQuantityChange(-1)}
                >
                  -
                </View>
                <View className='popup-quantity'>{quantity}</View>
                <View 
                  className={`popup-btn plus ${quantity >= product.stock ? 'disabled' : ''}`}
                  onClick={() => handleQuantityChange(1)}
                >
                  +
                </View>
              </View>
            </View>

            <View className='popup-footer'>
              <Button className='popup-confirm-btn' onClick={handleConfirmAction}>
                {actionType === 'cart' ? '加入购物车' : '立即购买'}
              </Button>
            </View>
          </View>
        </View>
      )}
    </View>
  )
}
