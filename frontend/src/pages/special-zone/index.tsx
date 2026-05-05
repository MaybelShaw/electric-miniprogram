import { useState, useEffect } from 'react'
import { View, Text, Image, Swiper, SwiperItem, ScrollView } from '@tarojs/components'
import Taro, { useRouter, useShareAppMessage, useShareTimeline } from '@tarojs/taro'
import { productService } from '../../services/product'
import { specialZoneService } from '../../services/special-zone'
import { caseService } from '../../services/case'
import { Product, Case, HomeBanner, LegacySpecialZoneType, SpecialZone as DynamicSpecialZone } from '../../types'
import ProductCard from '../../components/ProductCard'
import './index.scss'

const LEGACY_ZONE_TITLES: Record<LegacySpecialZoneType, string> = {
  gift: '礼品专区',
  designer: '设计师专区',
  best_seller: '爆品专区',
  promotion: '优惠专区',
}

const getLegacyProductParams = (type: LegacySpecialZoneType) => ({
  ...(type === 'gift' ? { show_in_gift_zone: true } : {}),
  ...(type === 'designer' ? { show_in_designer_zone: true } : {}),
  ...(type === 'best_seller' ? { show_in_best_seller_zone: true } : {}),
  ...(type === 'promotion' ? { show_in_promotion_zone: true } : {}),
})

export default function SpecialZone() {
  const router = useRouter()
  const legacyType = (router.params.type || 'gift') as LegacySpecialZoneType
  const routeTitle = router.params.title || LEGACY_ZONE_TITLES[legacyType] || '专区'
  const routeZoneId = Number(router.params.zone_id || 0)
  const zoneId = routeZoneId > 0 ? routeZoneId : undefined
  
  const [products, setProducts] = useState<Product[]>([])
  const [cases, setCases] = useState<Case[]>([])
  const [banners, setBanners] = useState<HomeBanner[]>([])
  const [zone, setZone] = useState<DynamicSpecialZone | null>(null)
  const [pageTitle, setPageTitle] = useState(decodeURIComponent(routeTitle))
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  
  useEffect(() => {
    // 确保显示分享菜单
    Taro.showShareMenu({
      withShareTicket: true
    })

    const nextTitle = zoneId ? '专区' : decodeURIComponent(routeTitle)
    setPageTitle(nextTitle)
    setZone(null)
    Taro.setNavigationBarTitle({ title: nextTitle })
    setProducts([])
    setPage(1)
    setHasMore(true)
    loadBanners(zoneId, legacyType)
    loadProducts(1, zoneId, legacyType)
    if (zoneId) {
      loadZone(zoneId)
      setCases([])
    } else if (legacyType === 'designer') {
      loadCases()
    } else {
      setCases([])
    }
  }, [zoneId, legacyType, routeTitle])

  useShareAppMessage(() => ({
    title: pageTitle || '家电商城',
    path: zoneId
      ? `/pages/special-zone/index?zone_id=${zoneId}`
      : `/pages/special-zone/index?type=${encodeURIComponent(legacyType)}&title=${encodeURIComponent(pageTitle || '专区')}`,
  }))

  useShareTimeline(() => ({
    title: pageTitle || '家电商城',
    query: zoneId
      ? `zone_id=${zoneId}`
      : `type=${encodeURIComponent(legacyType)}&title=${encodeURIComponent(pageTitle || '专区')}`,
  }))

  const loadZone = async (currentZoneId: number) => {
    try {
      const res = await specialZoneService.getZone(currentZoneId)
      setZone(res)
      setPageTitle(res.title)
      Taro.setNavigationBarTitle({ title: res.title })
    } catch (error) {
      console.error('Failed to load special zone:', error)
    }
  }

  const loadBanners = async (currentZoneId?: number, currentType: LegacySpecialZoneType = legacyType) => {
    try {
      const res = currentZoneId
        ? await productService.getHomeBanners({ special_zone: currentZoneId })
        : await productService.getHomeBanners(currentType)
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

  const loadProducts = async (
    pageNum = 1,
    currentZoneId = zoneId,
    currentType: LegacySpecialZoneType = legacyType
  ) => {
    if (loading) return
    setLoading(true)
    try {
      const params = { page: pageNum, page_size: 20 }
      const res = currentZoneId
        ? await specialZoneService.getZoneProducts(currentZoneId, params)
        : await productService.getProducts({
          ...params,
          ...getLegacyProductParams(currentType),
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
    loadProducts(1, zoneId, legacyType)
  }

  const onLoadMore = () => {
    if (hasMore && !loading) {
      loadProducts(page + 1, zoneId, legacyType)
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
    <View className={`special-zone ${zone ? 'dynamic-zone' : `${legacyType}-zone`}`}>
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
        {!zoneId && legacyType === 'designer' && cases.length > 0 && (
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
          {!zoneId && legacyType === 'designer' && <View className='section-title'>产品展示</View>}
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
