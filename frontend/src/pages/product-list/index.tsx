import { useState, useEffect } from 'react'
import { View, ScrollView, Image, Text } from '@tarojs/components'
import Taro, { useRouter } from '@tarojs/taro'
import { productService } from '../../services/product'
import { Category, Product } from '../../types'
import { formatPrice } from '../../utils/format'
import './index.scss'

export default function ProductListPage() {
  const router = useRouter()
  const { majorId, minorId, itemId, title, brand } = router.params

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
  const [activeBrandName, setActiveBrandName] = useState<string>('')
  
  // Sort
  const [sortBy, setSortBy] = useState<'relevance' | 'sales' | 'price_asc' | 'price_desc'>('relevance')

  const handleSortClick = (type: 'relevance' | 'sales' | 'price') => {
    if (type === 'price') {
      if (sortBy === 'price_asc') {
        setSortBy('price_desc')
      } else {
        setSortBy('price_asc')
      }
    } else {
      setSortBy(type)
    }
  }

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
        setActiveBrandName('')
        loadProducts(item.name, null, 1)
      }
    } else if (brand) {
      const decodedBrand = decodeURIComponent(brand)
      setActiveBrandName(decodedBrand)
      setActiveCategoryName('')
      loadProducts(null, decodedBrand, 1)
    } else if (!majorId) {
      // If no majorId (All Products mode), reload when sortBy changes
      setActiveBrandName('')
      setActiveCategoryName('')
      loadProducts(null, null, 1)
    }
  }, [activeItemId, sortBy, items, majorId, brand])

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

  const loadProducts = async (categoryName: string | null, brandName: string | null, pageNum = 1) => {
    setLoading(true)
    try {
      let res;
      if (brandName) {
         res = await productService.getProductsByBrand({
           brand: brandName,
           sort_by: sortBy,
           page: pageNum,
           page_size: 20
         })
      } else if (categoryName) {
        res = await productService.getProductsByCategory({
          category: categoryName,
          sort_by: sortBy,
          page: pageNum,
          page_size: 20
        })
      } else {
        // Fetch all products
        res = await productService.getProducts({
          sort_by: sortBy === 'relevance' ? undefined : sortBy as any,
          page: pageNum,
          page_size: 20
        })
      }
      
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
    if (!loading && hasMore) {
      loadProducts(activeCategoryName || null, activeBrandName || null, page + 1)
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
        {minors.length > 0 && (
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
        )}

        {/* Right Content */}
        <View className='main-content'>
          {/* Top Items Bar */}
          {items.length > 0 && (
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
          )}
          
          {/* Sort Bar */}
          <View className='sort-bar'>
              <View 
                className={`sort-item ${sortBy === 'relevance' ? 'active' : ''}`} 
                onClick={() => handleSortClick('relevance')}
              >
                综合
              </View>
              <View 
                className={`sort-item ${sortBy === 'sales' ? 'active' : ''}`} 
                onClick={() => handleSortClick('sales')}
              >
                销量
              </View>
              <View 
                className={`sort-item ${sortBy.startsWith('price') ? 'active' : ''}`} 
                onClick={() => handleSortClick('price')}
              >
                价格
                {sortBy === 'price_asc' && <Text className='sort-arrow'>↑</Text>}
                {sortBy === 'price_desc' && <Text className='sort-arrow'>↓</Text>}
              </View>
          </View>

          {/* Product List */}
          <ScrollView className='products-scroll' scrollY onScrollToLower={onLoadMore}>
            {products.length > 0 ? (
              products.map(product => (
                <View key={product.id} className='product-card' onClick={() => handleProductClick(product.id)}>
                  <Image className='product-image' src={product.main_images[0] || ''} mode='aspectFill' />
                  <View className='product-info'>
                    <View className='name'>{product.name}</View>
                    <View className='meta-info'>
                      <Text className='brand'>品牌: {product.brand}</Text>
                    </View>
                    <View className='price-row'>
                      <View className='price-wrapper'>
                        <View className='price'>
                          {formatPrice(getSellingPrice(product))}
                        </View>
                        <Text className='sales'>  已售{product.sales_count}</Text>
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
