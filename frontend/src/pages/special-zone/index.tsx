import { useState, useEffect } from 'react'
import { View, Text, Image, Swiper, SwiperItem, ScrollView } from '@tarojs/components'
import Taro, { useRouter, useShareAppMessage, useShareTimeline } from '@tarojs/taro'
import { productService } from '../../services/product'
import { specialZoneService } from '../../services/special-zone'
import { caseService } from '../../services/case'
import { Product, Case, HomeBanner, LegacySpecialZoneType, SpecialZone as DynamicSpecialZone } from '../../types'
import ProductCard from '../../components/ProductCard'
import { resolveLocalMediaUrl } from '../../utils/media'
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
  const mode = router.params.mode || ''
  const isActivityListMode = mode === 'activity-list'
  const legacyType = (router.params.type || 'gift') as LegacySpecialZoneType
  const routeTitle = router.params.title || LEGACY_ZONE_TITLES[legacyType] || '专区'
  const routeZoneId = Number(router.params.zone_id || 0)
  const routeStoreId = router.params.store_id || router.params.store
  const zoneId = routeZoneId > 0 ? routeZoneId : undefined
  
  const [products, setProducts] = useState<Product[]>([])
  const [cases, setCases] = useState<Case[]>([])
  const [banners, setBanners] = useState<HomeBanner[]>([])
  const [activityZones, setActivityZones] = useState<DynamicSpecialZone[]>([])
  const [zone, setZone] = useState<DynamicSpecialZone | null>(null)
  const [pageTitle, setPageTitle] = useState(decodeURIComponent(routeTitle))
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  
  useEffect(() => {
    Taro.showShareMenu({
      withShareTicket: true
    })

    if (isActivityListMode) {
      const nextTitle = '活动专区'
      setPageTitle(nextTitle)
      setZone(null)
      setProducts([])
      setCases([])
      setBanners([])
      setPage(1)
      setHasMore(false)
      Taro.setNavigationBarTitle({ title: nextTitle })
      loadActivityZones()
      return
    }

    const nextTitle = zoneId ? '专区' : decodeURIComponent(routeTitle)
    setPageTitle(nextTitle)
    setActivityZones([])
    setZone(null)
    Taro.setNavigationBarTitle({ title: nextTitle })
    setProducts([])
    setPage(1)
    setHasMore(true)
    loadBanners(zoneId, legacyType, routeStoreId)
    loadProducts(1, zoneId, legacyType, routeStoreId)
    if (zoneId) {
      loadZone(zoneId)
      setCases([])
    } else if (legacyType === 'designer') {
      loadCases()
    } else {
      setCases([])
    }
  }, [isActivityListMode, zoneId, legacyType, routeTitle, routeStoreId])

  useShareAppMessage(() => ({
    title: pageTitle || '家电商城',
    path: isActivityListMode
      ? '/pages/special-zone/index?mode=activity-list'
      : zoneId
      ? `/pages/special-zone/index?zone_id=${zoneId}`
      : `/pages/special-zone/index?type=${encodeURIComponent(legacyType)}&title=${encodeURIComponent(pageTitle || '专区')}`,
  }))

  useShareTimeline(() => ({
    title: pageTitle || '家电商城',
    query: isActivityListMode
      ? 'mode=activity-list'
      : zoneId
      ? `zone_id=${zoneId}`
      : `type=${encodeURIComponent(legacyType)}&title=${encodeURIComponent(pageTitle || '专区')}`,
  }))

  const loadActivityZones = async () => {
    setLoading(true)
    try {
      const zones = await specialZoneService.getZones(routeStoreId)
      setActivityZones(zones.filter(item => item.kind === 'activity' || item.kind === 'promotion'))
    } catch (error) {
      Taro.showToast({ title: '加载活动失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }

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

  const loadBanners = async (
    currentZoneId?: number,
    currentType: LegacySpecialZoneType = legacyType,
    currentStoreId?: string
  ) => {
    try {
      const res = currentZoneId
        ? await productService.getHomeBanners({ special_zone: currentZoneId })
        : await productService.getHomeBanners(currentStoreId ? { position: currentType, store: currentStoreId } : currentType)
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
    currentType: LegacySpecialZoneType = legacyType,
    currentStoreId = routeStoreId
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
          ...(currentStoreId ? { store: currentStoreId } : {}),
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
    loadProducts(1, zoneId, legacyType, routeStoreId)
  }

  const onLoadMore = () => {
    if (hasMore && !loading) {
      loadProducts(page + 1, zoneId, legacyType, routeStoreId)
    }
  }

  const goToCaseDetail = (id: number) => {
    Taro.navigateTo({ url: `/pages/case-detail/index?id=${id}` })
  }

  const goToActivity = (item: DynamicSpecialZone) => {
    const storeId = item.store_id || item.store
    Taro.navigateTo({
      url: `/pages/special-zone/index?zone_id=${item.id}${storeId ? `&store_id=${storeId}` : ''}`,
    })
  }

  const handleBannerClick = (banner: HomeBanner) => {
    if (banner.product_id) {
      Taro.navigateTo({ url: `/pages/product-detail/index?id=${banner.product_id}` })
    }
  }

  if (isActivityListMode) {
    return (
      <View className='special-zone activity-list-zone'>
        <ScrollView className='content' scrollY>
          <View className='activity-list-header'>
            <View className='activity-list-title'>活动专区</View>
            <View className='activity-list-desc'>平台精选活动</View>
          </View>
          <View className='activity-list'>
            {activityZones.map(item => (
              <View key={item.id} className='activity-card' onClick={() => goToActivity(item)}>
                {item.cover_image ? (
                  <Image className='activity-image' src={resolveLocalMediaUrl(item.cover_image)} mode='aspectFill' />
                ) : (
                  <View className='activity-image placeholder'>{item.title.charAt(0)}</View>
                )}
                <View className='activity-content'>
                  <View className='activity-title'>{item.title}</View>
                  {!!item.subtitle && <View className='activity-subtitle'>{item.subtitle}</View>}
                </View>
              </View>
            ))}
          </View>
          {loading && <View className='loading-wrapper'>加载中...</View>}
          {!loading && activityZones.length === 0 && <View className='empty-state'>暂无活动</View>}
        </ScrollView>
      </View>
    )
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
        {zone && (
          <View className='zone-hero'>
            {zone.cover_image ? (
              <Image className='zone-hero-image' src={resolveLocalMediaUrl(zone.cover_image)} mode='aspectFill' />
            ) : null}
            <View className='zone-hero-copy'>
              <View className='zone-hero-title'>{zone.title}</View>
              {!!zone.subtitle && <View className='zone-hero-subtitle'>{zone.subtitle}</View>}
            </View>
          </View>
        )}

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
                    src={resolveLocalMediaUrl(banner.image_url)}
                    className='scene-image'
                    mode='aspectFill'
                  />
                </SwiperItem>
              ))}
            </Swiper>
          </View>
        )}

        {!zoneId && legacyType === 'designer' && cases.length > 0 && (
          <View className='case-display'>
            <View className='section-title'>精选案例</View>
            <ScrollView scrollX className='case-scroll'>
              {cases.map(item => (
                <View key={item.id} className='case-card' onClick={() => goToCaseDetail(item.id)}>
                  <Image src={resolveLocalMediaUrl(item.cover_image_url)} className='case-image' mode='aspectFill' />
                  <View className='case-title'>{item.title}</View>
                </View>
              ))}
            </ScrollView>
          </View>
        )}

        <View className='product-display'>
          {zoneId && <View className='section-title'>活动商品</View>}
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
