import { useState, useEffect } from 'react'
import { View, Swiper, SwiperItem, Image, ScrollView, Text, Button } from '@tarojs/components'
import Taro, { useShareAppMessage, useShareTimeline, useRouter } from '@tarojs/taro'
import { productService } from '../../services/product'
import { cartService } from '../../services/cart'
import { TokenManager } from '../../utils/request'
import { resolveLocalMediaUrl } from '../../utils/media'
import { Product, ProductSKU } from '../../types'
import AppIcon from '../../components/AppIcon'
import BottomActionBar from '../../components/BottomActionBar'
import EmptyState from '../../components/EmptyState'
import ProductCard from '../../components/ProductCard'
import QuantityStepper from '../../components/QuantityStepper'
import { requireTransactionAuth, TransactionAction } from '../../utils/auth-guard'
import './index.scss'

export default function ProductDetail() {
  const router = useRouter()
  const routeProductId = Number(router.params.id || 0) || undefined
  const [product, setProduct] = useState<Product | null>(null)
  const [quantity, setQuantity] = useState(1)
  const [loading, setLoading] = useState(true)
  const [currentImageIndex, setCurrentImageIndex] = useState(0)
  const [showQuantityPopup, setShowQuantityPopup] = useState(false)
  const [actionType, setActionType] = useState<'cart' | 'buy'>('cart')
  const [selectedSpecs, setSelectedSpecs] = useState<Record<string, string>>({})
  const [currentSku, setCurrentSku] = useState<ProductSKU | null>(null)
  const [relatedProducts, setRelatedProducts] = useState<Product[]>([])
  const [relatedLoading, setRelatedLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('product')
  const [scrollIntoView, setScrollIntoView] = useState('')
  const [navOpacity, setNavOpacity] = useState(0)
  const [hasAutoResumed, setHasAutoResumed] = useState(false)
  const isDisplayOnlyProduct = product?.store_type === 'partner'

  useEffect(() => {
    // 确保显示分享菜单
    Taro.showShareMenu({
      withShareTicket: true
    })

    const id = router.params.id
    if (id) {
      loadProduct(Number(id))
    }
  }, [])

  useShareAppMessage(() => {
    const productId = product?.id || routeProductId
    if (!productId) {
      return {
        title: '家电商城',
        path: '/pages/home/index',
      }
    }
    const imageUrl = resolveLocalMediaUrl(product?.main_images?.[0])
    return {
      title: product?.name || '商品详情',
      path: `/pages/product-detail/index?id=${productId}`,
      ...(imageUrl ? { imageUrl } : {}),
    }
  })

  useShareTimeline(() => {
    const productId = product?.id || routeProductId
    if (!productId) {
      return {
        title: '家电商城',
      }
    }
    const imageUrl = resolveLocalMediaUrl(product?.main_images?.[0])
    return {
      title: product?.name || '商品详情',
      query: `id=${productId}`,
      ...(imageUrl ? { imageUrl } : {}),
    }
  })

  useEffect(() => {
    if (!product) return
    const stock = currentSku ? currentSku.stock : (product.total_stock ?? product.stock)
    if (stock > 0 && quantity > stock) {
      setQuantity(stock)
    }
  }, [currentSku, product])

  useEffect(() => {
    if (product?.id) {
      loadRelatedProducts(product.id, product.category_id, product.category)
    }
  }, [product?.id, product?.category_id, product?.category])

  useEffect(() => {
    if (!product || hasAutoResumed) return
    if (!TokenManager.getAccessToken()) return

    const intent = router.params?.auth_action || router.params?.intent
    if (intent !== 'buy' && intent !== 'cart') return
    if (product.store_type === 'partner') return

    setHasAutoResumed(true)
    handleShowQuantityPopup(intent as TransactionAction)
  }, [router.params?.auth_action, router.params?.intent, hasAutoResumed, product])

  const loadProduct = async (id: number) => {
    setLoading(true)
    try {
      const data = await productService.getProductDetail(id)
      setProduct(data)
      initSpecs(data)
    } catch (error) {
      Taro.showToast({ title: '加载失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }

  const loadRelatedProducts = async (id: number, categoryId?: number, categoryName?: string) => {
    setRelatedLoading(true)
    try {
      let items: Product[] = []
      
      if (categoryName) {
        const res = await productService.getProductsByCategory({
          category: categoryName,
          page_size: 20
        })
        items = res.results || []
      } else if (categoryId) {
        items = await productService.getRecommendations({
          type: 'category',
          category_id: categoryId,
          limit: 20
        })
      } else {
        items = await productService.getRelatedProducts(id, 20)
      }
      
      setRelatedProducts(items.filter((item) => item.id !== id))
    } catch (error) {
      console.error(error)
      setRelatedProducts([])
    } finally {
      setRelatedLoading(false)
    }
  }

  const findSkuBySpecs = (specs: Record<string, string>, skus?: ProductSKU[] | null) => {
    if (!skus || skus.length === 0) return null
    return skus.find((sku) => {
      const skuSpecs = sku.specs || {}
      return Object.keys(specs).every((key) => skuSpecs[key] === specs[key])
    }) || null
  }

  const initSpecs = (p: Product) => {
    if (!p) return
    if (p.skus && p.skus.length > 0) {
      const defaults: Record<string, string> = {}
      if (p.spec_options) {
        Object.entries(p.spec_options).forEach(([key, values]) => {
          if (Array.isArray(values) && values.length === 1) {
            defaults[key] = values[0]
          }
        })
      }
      const matched = findSkuBySpecs(defaults, p.skus) || p.skus[0]
      setSelectedSpecs(defaults)
      setCurrentSku(matched || null)
    } else {
      setSelectedSpecs({})
      setCurrentSku(null)
    }
  }

  const handleSelectSpec = (name: string, value: string) => {
    if (!product) return
    const next = { ...selectedSpecs, [name]: value }
    setSelectedSpecs(next)
    const matched = findSkuBySpecs(next, product.skus)
    setCurrentSku(matched || null)
    setQuantity(1)
  }

  const getAvailableStock = () => {
    if (!product) return 0
    if (currentSku) return currentSku.stock
    return product.total_stock ?? product.stock
  }



  const handleShowQuantityPopup = async (type: TransactionAction) => {
    const loggedIn = await requireTransactionAuth(type)
    if (!loggedIn) {
      return
    }

    if (!product) return
    if (isDisplayOnlyProduct) {
      Taro.showToast({ title: '该店铺商品仅展示', icon: 'none' })
      return
    }

    setActionType(type)
    setQuantity(1) // 重置数量为1
    setShowQuantityPopup(true)
  }

  const handleConfirmAction = async () => {
    if (!product) return

    if (product.skus && product.skus.length > 0 && !currentSku) {
      Taro.showToast({ title: '请选择规格', icon: 'none' })
      return
    }

    if (actionType === 'cart') {
      try {
        await cartService.addItem(product.id, quantity, currentSku?.id)
        setShowQuantityPopup(false)
        Taro.showToast({ title: '已加入购物车', icon: 'success' })
      } catch (error) {
        Taro.showToast({ title: '添加失败', icon: 'none' })
      }
    } else {
      setShowQuantityPopup(false)
      Taro.navigateTo({
        url: `/pages/order-confirm/index?productId=${product.id}&quantity=${quantity}${currentSku ? `&skuId=${currentSku.id}` : ''}`
      })
    }
  }



  const handleImagePreview = (index: number, isDetailImage = false) => {
    if (!product) return
    
    const images = (isDetailImage ? product.detail_images : product.main_images)
      ?.map(resolveLocalMediaUrl)
      .filter(Boolean)
    if (!images || images.length === 0) return
    
    Taro.previewImage({
      urls: images,
      current: images[index] || images[0]
    })
  }

  const getAttachmentName = (attachment: NonNullable<Product['product_attachments']>[number]) => {
    const explicitName = attachment.name?.trim()
    if (explicitName) return explicitName
    const originalName = attachment.original_name?.trim()
    if (originalName) return originalName
    const rawName = (attachment.url || '').split('?')[0].split('/').pop()
    if (!rawName) return 'PDF附件'
    try {
      return decodeURIComponent(rawName)
    } catch (error) {
      return rawName
    }
  }

  const handleOpenAttachment = async (attachment: NonNullable<Product['product_attachments']>[number]) => {
    const url = resolveLocalMediaUrl(attachment.url)
    if (!url) {
      Taro.showToast({ title: '附件地址无效', icon: 'none' })
      return
    }

    Taro.showLoading({ title: '下载中...' })
    try {
      const res = await Taro.downloadFile({ url })
      Taro.hideLoading()
      if (res.statusCode !== 200) {
        Taro.showToast({ title: '下载失败', icon: 'none' })
        return
      }
      Taro.openDocument({
        filePath: res.tempFilePath,
        fileType: 'pdf',
        fail: () => Taro.showToast({ title: '无法打开PDF', icon: 'none' }),
      })
    } catch (error) {
      Taro.hideLoading()
      Taro.showToast({ title: '下载失败', icon: 'none' })
    }
  }

  const handleSwiperChange = (e: any) => {
    setCurrentImageIndex(e.detail.current)
  }

  const handleTabClick = (tab: string) => {
    setActiveTab(tab)
    setScrollIntoView(`${tab}-anchor`)
  }

  const handleScroll = (e: any) => {
    const scrollTop = e.detail.scrollTop
    const threshold = 100 // Pixel threshold for full opacity
    let opacity = 0
    if (scrollTop > 0) {
      opacity = Math.min(scrollTop / threshold, 1)
    }
    setNavOpacity(opacity)
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

  const availableStock = getAvailableStock()
  
  // 计算基础价格（原价/市场价）
  // 对于经销商，display_price 已经是经销价，所以不能用它作为“原价”来计算 hasDiscount
  // 应该使用 originalPrice (市场价) 或 price (零售价) 作为基准
  const productBasePrice = Number(product.originalPrice || product.price || 0)
  const skuBasePrice = currentSku ? Number(currentSku.price || 0) : productBasePrice
  const currentBasePrice = currentSku ? skuBasePrice : productBasePrice

  // 计算最终价格（折扣价/经销价）
  // 优先级：discounted_price (活动价) > display_price (用户价/经销价) > price (零售价)
  const getFinalPrice = (item: Product | ProductSKU) => {
    if (item.discounted_price && Number(item.discounted_price) > 0) {
      return Number(item.discounted_price)
    }
    // display_price 对于经销商已经是经销价
    if (item.display_price && Number(item.display_price) > 0) {
      return Number(item.display_price)
    }
    // Product 有 dealer_price 字段，作为额外的 fallback (虽然 display_price 应该已经涵盖)
    if ('dealer_price' in item && item.dealer_price && Number(item.dealer_price) > 0) {
      return Number(item.dealer_price)
    }
    return Number(item.price || 0)
  }

  const productFinalPrice = getFinalPrice(product)
  const skuFinalPrice = currentSku ? getFinalPrice(currentSku) : productFinalPrice

  const displayPrice = currentSku ? skuFinalPrice : productFinalPrice
  // 只有当最终展示价格小于原价时，才显示划线价
  const hasDiscount = displayPrice < currentBasePrice
  const priceTier = product.dealer_price ? '经销价' : hasDiscount ? '活动价' : '零售价'

  const selectedSpecText = currentSku?.specs ? Object.values(currentSku.specs).join(' / ') : ''

  return (
    <View className='product-detail'>
      <View className={`nav-bar ${navOpacity > 0.8 ? 'visible' : ''}`}>
        {['product', 'detail', 'recommend'].map((tab) => (
          <View
            key={tab}
            className={`nav-item ${activeTab === tab ? 'active' : ''}`}
            onClick={() => handleTabClick(tab)}
          >
            {tab === 'product' ? '商品' : tab === 'detail' ? '详情' : '推荐'}
          </View>
        ))}
      </View>
      <ScrollView 
        className='content' 
        scrollY
        scrollIntoView={scrollIntoView}
        scrollWithAnimation
        onScroll={handleScroll}
      >
        <View id='product-anchor'>
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
                  src={resolveLocalMediaUrl(img)}
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
              <Text className='price-badge'>{priceTier}</Text>
              <Text className='price-label'>¥</Text>
              <Text className='price'>
                 {Number(displayPrice || 0).toFixed(2)}
               </Text>
               {hasDiscount && (
                 <Text className='original-price'>
                   ¥{Number(currentBasePrice || 0).toFixed(2)}
                 </Text>
               )}
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

        <View className='service-strip'>
          <View className='service-item'>
            <AppIcon name='done' tone='muted' className='service-icon' />
            <Text className='service-text'>正品保障</Text>
          </View>
          <View className='service-item'>
            <AppIcon name='ship' tone='muted' className='service-icon' />
            <Text className='service-text'>配送安装</Text>
          </View>
          <View className='service-item'>
            <AppIcon name='service' tone='muted' className='service-icon' />
            <Text className='service-text'>售后无忧</Text>
          </View>
        </View>

        {/* 规格选择 */}
        {product.spec_options && Object.keys(product.spec_options).length > 0 && (
          <View className='specs-section'>
            <View className='section-title'>选择规格</View>
            <View className='spec-options'>
              {Object.entries(product.spec_options).map(([key, values]) => (
                <View key={key} className='spec-option-row'>
                  <Text className='spec-label'>{key}</Text>
                  <View className='spec-values'>
                    {values.map((val) => (
                      <View
                        key={val}
                        className={`spec-chip ${selectedSpecs[key] === val ? 'active' : ''}`}
                        onClick={() => handleSelectSpec(key, val)}
                      >
                        {val}
                      </View>
                    ))}
                  </View>
                </View>
              ))}
              {selectedSpecText ? (
                <View className='selected-spec-text'>已选：{selectedSpecText}</View>
              ) : null}
            </View>
          </View>
        )}

        {/* 商品规格参数 */}
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

        {product.product_attachments && product.product_attachments.length > 0 && (
          <View className='attachments-section'>
            <View className='section-title'>资料下载</View>
            <View className='attachment-list'>
              {product.product_attachments.map((attachment, index) => (
                <View
                  key={`${attachment.url}-${index}`}
                  className='attachment-item'
                  onClick={() => handleOpenAttachment(attachment)}
                >
                  <View className='attachment-badge'>PDF</View>
                  <Text className='attachment-name'>{getAttachmentName(attachment)}</Text>
                  <Text className='attachment-action'>下载</Text>
                </View>
              ))}
            </View>
          </View>
        )}

        </View>

        {/* 商品详情 */}
        <View id='detail-anchor' className='detail-section'>
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
                    src={resolveLocalMediaUrl(img)}
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
            <EmptyState title='暂无详细信息' description='商品详情图片正在准备中' icon='package' />
          )}
        </View>

        {/* 猜你喜欢 */}
        <View id='recommend-anchor' className='recommend-section'>
          <View className='recommend-header'>
            <View className='recommend-title'>
              <View className='dot' />
              <Text className='title-text'>猜你喜欢</Text>
            </View>
          </View>

          {relatedLoading ? (
            <View className='recommend-placeholder'>推荐加载中...</View>
          ) : relatedProducts.length > 0 ? (
            <ScrollView className='recommend-scroll' scrollX>
              <View className='recommend-row'>
                {relatedProducts.map((item) => (
                  <View key={item.id} className='recommend-card'>
                    <ProductCard product={item} variant='compact' />
                  </View>
                ))}
              </View>
            </ScrollView>
          ) : (
            <View className='recommend-placeholder'>暂无同类推荐</View>
          )}
        </View>
      </ScrollView>

      {/* 底部操作栏 */}
      <BottomActionBar className='detail-action-bar'>
        <View className='footer-left'>
          <View className='icon-btn' onClick={() => Taro.switchTab({ url: '/pages/home/index' })}>
            <View className='icon-wrapper'>
              <AppIcon name='home' tone='muted' />
            </View>
            <Text className='icon-text'>首页</Text>
          </View>

          <View className='icon-btn contact-btn' onClick={() => {
            const supportStoreId = product?.store_id || product?.store
            Taro.navigateTo({ url: `/pages/support-chat/index${supportStoreId ? `?store_id=${supportStoreId}` : ''}` })
          }}>
            <View className='icon-wrapper'>
              <AppIcon name='service' tone='muted' />
            </View>
            <Text className='icon-text'>客服</Text>
          </View>

          <View className='icon-btn' onClick={() => Taro.switchTab({ url: '/pages/cart/index' })}>
            <View className='icon-wrapper'>
              <AppIcon name='cart' tone='muted' />
            </View>
            <Text className='icon-text'>购物车</Text>
          </View>
        </View>
        <View className='footer-right'>
          {isDisplayOnlyProduct ? (
            <View className='action-btn buy-btn disabled'>
              仅展示
            </View>
          ) : (
            <>
              <View
                className={`action-btn cart-btn ${availableStock === 0 ? 'disabled' : ''}`}
                onClick={() => availableStock > 0 && handleShowQuantityPopup('cart')}
              >
                加入购物车
              </View>
              <View
                className={`action-btn buy-btn ${availableStock === 0 ? 'disabled' : ''}`}
                onClick={() => availableStock > 0 && handleShowQuantityPopup('buy')}
              >
                {availableStock === 0 ? '已售罄' : '立即购买'}
              </View>
            </>
          )}
        </View>
      </BottomActionBar>

      {/* 数量选择弹窗 */}
      {showQuantityPopup && (
        <View className='quantity-popup-overlay' onClick={() => setShowQuantityPopup(false)}>
          <View className='quantity-popup' onClick={(e) => e.stopPropagation()}>
            <View className='popup-header'>
              <View className='popup-product-info'>
                <Image className='popup-product-image' src={resolveLocalMediaUrl(currentSku?.image || product.main_images[0])} mode='aspectFill' />
                <View className='popup-product-details'>
                  <View className='popup-product-name'>{product.name}</View>
                  <View className='popup-product-price-row'>
                    <View className='popup-product-price'>¥{Number(displayPrice || 0).toFixed(2)}</View>
                    {hasDiscount && (
                      <View className='popup-original-price'>¥{Number(currentBasePrice || 0).toFixed(2)}</View>
                    )}
                  </View>
                  {selectedSpecText && <View className='popup-spec-text'>{selectedSpecText}</View>}
                  <View className='popup-stock-text'>库存 {availableStock} 件</View>
                </View>
              </View>
              <View className='popup-close' onClick={() => setShowQuantityPopup(false)}>
                <AppIcon name='close' tone='muted' />
              </View>
            </View>

            <View className='popup-quantity-section'>
              <Text className='popup-section-title'>购买数量</Text>
              <QuantityStepper value={quantity} max={availableStock || undefined} onChange={setQuantity} />
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
