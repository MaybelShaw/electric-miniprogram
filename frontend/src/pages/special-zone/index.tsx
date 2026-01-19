import { useState, useEffect } from 'react'
import { View, Text, Image, Swiper, SwiperItem, ScrollView } from '@tarojs/components'
import Taro, { useRouter, useShareAppMessage, useShareTimeline } from '@tarojs/taro'
import { productService } from '../../services/product'
import { caseService } from '../../services/case'
import { Product, Case, HomeBanner } from '../../types'
import ProductCard from '../../components/ProductCard'
import './index.scss'

export default function SpecialZone() {
  const router = useRouter()
  const { type = 'gift', title = '专区' } = router.params
  
  const [products, setProducts] = useState<Product[]>([])
  const [cases, setCases] = useState<Case[]>([])
  const [banners, setBanners] = useState<HomeBanner[]>([])
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  
  useEffect(() => {
    Taro.setNavigationBarTitle({ title: decodeURIComponent(title) })
    setProducts([])
    setPage(1)
    setHasMore(true)
    loadBanners()
    loadProducts(1)
    if (type === 'designer') {
      loadCases()
    } else {
      setCases([])
    }
  }, [type])

  useShareAppMessage(() => ({
    title: decodeURIComponent(title || '家电商城'),
    path: '/pages/home/index',
  }))

  useShareTimeline(() => ({
    title: decodeURIComponent(title || '家电商城'),
    query: `type=${encodeURIComponent(type || 'gift')}&title=${encodeURIComponent(title || '专区')}`,
  }))

  const loadBanners = async () => {
    try {
        const res = await productService.getHomeBanners(type as 'gift' | 'designer')
        setBanners(res)
    } catch (error) {
        console.error('Failed to load banners:', error)
    }
  }

  const loadCases = async () => {
    try {
      const res = await caseService.getCases({ page: 1, page_size: 10 })
      setCases(res.results)
    } catch (error) {
      console.error('Failed to load cases:', error)
    }
  }

  const loadProducts = async (pageNum = 1) => {
    if (loading) return
    setLoading(true)
    try {
      const res = await productService.getProducts({
        page: pageNum,
        page_size: 20,
        ...(type === 'gift' ? { show_in_gift_zone: true } : {}),
        ...(type === 'designer' ? { show_in_designer_zone: true } : {}),
      })
      setProducts(prev => (pageNum === 1 ? res.results : [...prev, ...res.results]))
      setHasMore(res.has_next || false)
      setPage(pageNum)
    } catch (error) {
      Taro.showToast({ title: '加载商品失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }

  const onRefresh = () => {
    loadProducts(1)
  }

  const onLoadMore = () => {
    if (hasMore && !loading) {
      loadProducts(page + 1)
    }
  }

  const goToCaseDetail = (id: number) => {
    Taro.navigateTo({ url: `/pages/case-detail/index?id=${id}` })
  }

  const handleBannerClick = (banner: HomeBanner) => {
    if (banner.product_id) {
      Taro.navigateTo({ url: `/pages/product-detail/index?id=${banner.product_id}` })
    }
  }

  return (
    <View className='special-zone'>
      <ScrollView
        className='content'
        scrollY
        refresherEnabled
        refresherTriggered={loading && page === 1}
        onRefresherRefresh={onRefresh}
        onScrollToLower={onLoadMore}
      >
        {/* 场景展示 */}
        {banners.length > 0 && (
          <View className='scene-display'>
              <View className='section-title'>场景展示</View>
              <Swiper
              className='scene-swiper'
              circular
              indicatorDots
              autoplay
              >
              {banners.map((banner) => (
                  <SwiperItem key={banner.id} onClick={() => handleBannerClick(banner)}>
                  <Image 
                      src={banner.image_url} 
                      className='scene-image' 
                      mode='aspectFill' 
                  />
                  </SwiperItem>
              ))}
              </Swiper>
          </View>
        )}

        {/* 案例展示 */}
        {type === 'designer' && cases.length > 0 && (
          <View className='case-display'>
            <View className='section-title'>精选案例</View>
            <ScrollView scrollX className='case-scroll'>
              {cases.map(item => (
                <View key={item.id} className='case-card' onClick={() => goToCaseDetail(item.id)}>
                  <Image src={item.cover_image_url || ''} className='case-image' mode='aspectFill' />
                  <View className='case-title'>{item.title}</View>
                </View>
              ))}
            </ScrollView>
          </View>
        )}

        {/* 产品展示 */}
        <View className='product-display'>
          <View className='section-title'>产品展示</View>
          <View className='product-list'>
            {products.map(product => (
              <ProductCard
                key={product.id}
                product={product}
              />
            ))}
          </View>
          
          {loading && (
            <View className='loading-wrapper'>
              <Text>加载中...</Text>
            </View>
          )}
          
          {!loading && products.length === 0 && (
            <View className='empty-state'>
              <Text>暂无相关商品</Text>
            </View>
          )}
        </View>
      </ScrollView>
    </View>
  )
}
