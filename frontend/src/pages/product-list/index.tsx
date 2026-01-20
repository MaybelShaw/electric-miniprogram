import { useState, useEffect } from 'react'
import { View, ScrollView, Image, Text } from '@tarojs/components'
import Taro, { useRouter } from '@tarojs/taro'
import { productService } from '../../services/product'
import { Category, Product } from '../../types'
import { formatPrice } from '../../utils/format'
import './index.scss'

export default function ProductListPage() {
  const router = useRouter()
  const { majorId, minorId, itemId, title } = router.params

  // State
  const [minors, setMinors] = useState<Category[]>([])
  const [activeMinorId, setActiveMinorId] = useState<number | null>(null)
  
  const [items, setItems] = useState<Category[]>([])
  const [activeItemId, setActiveItemId] = useState<number | null>(null)
  
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const [activeCategoryName, setActiveCategoryName] = useState<string>('')
  
  // Sort
  const [sortBy, setSortBy] = useState<'relevance' | 'sales' | 'price_asc' | 'price_desc'>('relevance')

  // Load Minors on mount
  useEffect(() => {
    if (title) {
      Taro.setNavigationBarTitle({ title: decodeURIComponent(title) })
    }
    if (majorId) {
      loadMinors(Number(majorId))
    }
  }, [majorId])

  // Load Items when activeMinorId changes
  useEffect(() => {
    if (activeMinorId) {
      loadItems(activeMinorId)
    }
  }, [activeMinorId])

  // Load Products when activeItemId changes or sortBy changes
  useEffect(() => {
    if (activeItemId) {
      // Find item name for search
      const item = items.find(i => i.id === activeItemId)
      if (item) {
        setActiveCategoryName(item.name)
        loadProducts(item.name, 1)
      }
    }
  }, [activeItemId, sortBy, items])

  const loadMinors = async (pid: number) => {
    try {
      const data = await productService.getCategories({ parent_id: pid })
      setMinors(data)
      
      // Set default active minor
      if (minorId && data.find(m => m.id === Number(minorId))) {
        setActiveMinorId(Number(minorId))
      } else if (data.length > 0) {
        setActiveMinorId(data[0].id)
      }
    } catch (error) {
      console.error('Failed to load minor categories', error)
    }
  }

  const loadItems = async (pid: number) => {
    try {
      const data = await productService.getCategories({ parent_id: pid })
      setItems(data)
      
      // Set default active item
      // Only use router itemId if it matches the FIRST load and belongs to this minor
      // But here we simplify: if router itemId is present and in data, use it.
      // Note: router itemId is only valid for the specific minor it belongs to.
      // If user switches minor, router itemId is irrelevant.
      // So we need to check if this is the "initial" load or a user switch.
      // For simplicity: check if itemId exists in data.
      
      let targetId = data.length > 0 ? data[0].id : null
      
      if (itemId && data.find(i => i.id === Number(itemId))) {
         // Check if we should respect itemId (only if we are in the correct minor)
         // Since we don't strictly track "correct minor" for itemId from params,
         // we rely on the fact that if it exists in the list, it's valid.
         targetId = Number(itemId)
      }
      
      setActiveItemId(targetId)
      
    } catch (error) {
      console.error('Failed to load items', error)
    }
  }

  const loadProducts = async (categoryName: string, pageNum = 1) => {
    setLoading(true)
    try {
      const res = await productService.getProductsByCategory({
        category: categoryName,
        sort_by: sortBy,
        page: pageNum,
        page_size: 20
      })
      setProducts(prev => (pageNum === 1 ? res.results : [...prev, ...res.results]))
      setHasMore(res.has_next || false)
      setPage(pageNum)
    } catch (error) {
      console.error('Failed to load products', error)
    } finally {
      setLoading(false)
    }
  }

  const onLoadMore = () => {
    if (!loading && hasMore && activeCategoryName) {
      loadProducts(activeCategoryName, page + 1)
    }
  }
  
  const handleAddToCart = (e, product: Product) => {
      e.stopPropagation()
      Taro.showToast({ title: '已加入购物车', icon: 'success' })
      // TODO: Implement actual cart logic
  }
  
  const handleProductClick = (id: number) => {
      Taro.navigateTo({ url: `/pages/product-detail/index?id=${id}` })
  }

  const getSellingPrice = (product: Product) => {
    const basePrice = Number(product.display_price ?? product.price ?? 0)
    return product.discounted_price && Number(product.discounted_price) < basePrice
      ? Number(product.discounted_price)
      : basePrice
  }

  return (
    <View className='product-list-page'>
      <View className='content-container'>
        {/* Left Sidebar (Minors) */}
        <ScrollView className='sidebar' scrollY>
          {minors.map(minor => (
            <View
              key={minor.id}
              className={`sidebar-item ${activeMinorId === minor.id ? 'active' : ''}`}
              onClick={() => {
                  setActiveMinorId(minor.id)
                  // Reset itemId param effect so it doesn't stick when switching minors
                  // But we can't easily clear router params.
                  // The logic in loadItems handles it by defaulting to first item if itemId not found.
              }}
            >
              {minor.name}
            </View>
          ))}
        </ScrollView>

        {/* Right Content */}
        <View className='main-content'>
          {/* Top Items Bar */}
          <ScrollView className='items-scroll' scrollX>
            <View className='items-container'>
                {items.map(item => (
                <View
                    key={item.id}
                    className={`item-pill ${activeItemId === item.id ? 'active' : ''}`}
                    onClick={() => setActiveItemId(item.id)}
                >
                    {item.name}
                </View>
                ))}
            </View>
          </ScrollView>
          
          {/* Sort Bar */}
          <View className='sort-bar'>
              <View className={`sort-item ${sortBy === 'relevance' ? 'active' : ''}`} onClick={() => setSortBy('relevance')}>综合</View>
              <View className={`sort-item ${sortBy === 'sales' ? 'active' : ''}`} onClick={() => setSortBy('sales')}>销量</View>
              <View className={`sort-item ${sortBy === 'price_asc' ? 'active' : ''}`} onClick={() => setSortBy('price_asc')}>价格</View>
          </View>

          {/* Product List */}
          <ScrollView className='products-scroll' scrollY onScrollToLower={onLoadMore}>
            {products.length > 0 ? (
              products.map(product => (
                <View key={product.id} className='product-card' onClick={() => handleProductClick(product.id)}>
                  <Image className='product-image' src={product.main_images[0] || ''} mode='aspectFill' />
                  <View className='product-info'>
                    <View className='name'>{product.name}</View>
                    <View className='brand'>品牌: {product.brand}</View>
                    <View className='price-row'>
                      <View className='price'>
                        {formatPrice(getSellingPrice(product))}
                      </View>
                      <View className='action-btn' onClick={(e) => handleAddToCart(e, product)}>+</View>
                    </View>
                  </View>
                </View>
              ))
            ) : (
              !loading && <View className='empty-products'>暂无商品</View>
            )}
          </ScrollView>
        </View>
      </View>
      
      {/* Floating Cart Button */}
      <View className='cart-float-btn' onClick={() => Taro.switchTab({ url: '/pages/cart/index' })}>
          <View className='cart-icon'>🛒</View>
      </View>
    </View>
  )
}
