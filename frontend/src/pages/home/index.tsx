import { useState, useEffect } from 'react'
import { View, Swiper, SwiperItem, Image, ScrollView, Input, Text } from '@tarojs/components'
import Taro, { useRouter, useShareAppMessage, useShareTimeline } from '@tarojs/taro'
import { productService } from '../../services/product'
import { specialZoneCoverService } from '../../services/special-zone-cover'
import { Product, Category, Brand, HomeBanner, SpecialZoneCover } from '../../types'
import { resolveLocalMediaUrl } from '../../utils/media'
import { Storage, CACHE_KEYS } from '../../utils/storage'
import ProductCard from '../../components/ProductCard'
import { withPrivacyCheck } from '../../components/withPrivacyCheck'
import './index.scss'

function Home() {
  const router = useRouter()
  const [searchValue, setSearchValue] = useState('')
  const [majorCategories, setMajorCategories] = useState<Category[]>([])
  const [brands, setBrands] = useState<Brand[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [banners, setBanners] = useState<HomeBanner[]>([])
  const [giftZoneCover, setGiftZoneCover] = useState<SpecialZoneCover | null>(null)
  const [designerZoneCover, setDesignerZoneCover] = useState<SpecialZoneCover | null>(null)
  const [bestSellerZoneCover, setBestSellerZoneCover] = useState<SpecialZoneCover | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const storeId = router.params?.store_id || router.params?.store
    loadBanners(storeId)
    loadSpecialZoneCovers(storeId)
    loadCategories(storeId)
    loadBrands(storeId)
    loadProducts(1, storeId)

    Taro.showShareMenu({
      withShareTicket: true
    })
  }, [])

  useShareAppMessage(() => ({
    title: '庆勋愉悦家',
    path: '/pages/home/index',
    ...(resolveLocalMediaUrl(banners[0]?.image_url) ? { imageUrl: resolveLocalMediaUrl(banners[0]?.image_url) } : {}),
  }))

  useShareTimeline(() => ({
    title: '庆勋愉悦家',
    ...(resolveLocalMediaUrl(banners[0]?.image_url) ? { imageUrl: resolveLocalMediaUrl(banners[0]?.image_url) } : {}),
  }))

  const loadBanners = async (storeId?: string, showRefreshing = false) => {
    if (showRefreshing) {
      setRefreshing(true)
    }
    try {
      const data = await productService.getHomeBanners(storeId ? { position: 'home', store: storeId } : 'home')
      setBanners(data)
    } catch (error) {
      // 静默失败，首页入口仍可用
    } finally {
      if (showRefreshing) {
        setRefreshing(false)
      }
    }
  }

  const loadSpecialZoneCovers = async (storeId?: string) => {
    try {
      const [gift, designer, bestSeller] = await Promise.all([
        specialZoneCoverService.getCovers({ type: 'gift', ...(storeId ? { store: storeId } : {}) }),
        specialZoneCoverService.getCovers({ type: 'designer', ...(storeId ? { store: storeId } : {}) }),
        specialZoneCoverService.getCovers({ type: 'best_seller', ...(storeId ? { store: storeId } : {}) }),
      ])
      setGiftZoneCover(gift[0] || null)
      setDesignerZoneCover(designer[0] || null)
      setBestSellerZoneCover(bestSeller[0] || null)
    } catch (error) {
      // 静默失败，保留专区入口兜底文案
    }
  }

  const loadCategories = async (storeId?: string) => {
    try {
      if (!storeId) {
        const cachedMajor = Storage.get<Category[]>(CACHE_KEYS.MAJOR_CATEGORIES)
        if (cachedMajor) {
          setMajorCategories(cachedMajor)
          return
        }
      }

      const data = await productService.getCategories({ level: 'major', ...(storeId ? { store: storeId } : {}) })
      setMajorCategories(data)
      if (!storeId) {
        Storage.set(CACHE_KEYS.MAJOR_CATEGORIES, data, 24 * 60 * 60 * 1000)
      }
    } catch (error) {
      // 静默失败
    }
  }

  const loadBrands = async (storeId?: string) => {
    try {
      if (!storeId) {
        const cached = Storage.get<Brand[]>(CACHE_KEYS.BRANDS)
        if (cached) {
          setBrands(cached)
          return
        }
      }

      const data = await productService.getBrands(storeId ? { store: storeId } : undefined)
      setBrands(data)
      if (!storeId) {
        Storage.set(CACHE_KEYS.BRANDS, data, 24 * 60 * 60 * 1000)
      }
    } catch (error) {
      // 静默失败
    }
  }

  const loadProducts = async (pageNum: number, storeId?: string) => {
    if (loading) return

    setLoading(true)
    try {
      const res = await productService.getProducts({
        page: pageNum,
        page_size: 20,
        ...(storeId ? { store: storeId } : {}),
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
    const storeId = router.params?.store_id || router.params?.store
    loadBanners(storeId, true)
    loadSpecialZoneCovers(storeId)
    loadProducts(1, storeId)
  }

  const onLoadMore = () => {
    if (hasMore && !loading) {
      const storeId = router.params?.store_id || router.params?.store
      loadProducts(page + 1, storeId)
    }
  }

  const handleSearch = () => {
    const keyword = searchValue.trim()
    if (!keyword) return
    Taro.navigateTo({ url: `/pages/search/index?keyword=${encodeURIComponent(keyword)}` })
  }

  const handleBannerClick = (banner: HomeBanner) => {
    if (banner.product_id) {
      Taro.navigateTo({ url: `/pages/product-detail/index?id=${banner.product_id}` })
    }
  }

  const goToBrandZone = () => {
    Taro.navigateTo({ url: '/pages/store-list/index' })
  }

  const goToActivityZone = () => {
    Taro.navigateTo({ url: '/pages/special-zone/index?mode=activity-list' })
  }

  const goToCategory = (category: string) => {
    Taro.switchTab({ url: '/pages/category/index' })
    Taro.eventCenter.trigger('selectCategory', category)
  }

  const goToBrand = (brand: string) => {
    Taro.navigateTo({ url: `/pages/brand/index?brand=${encodeURIComponent(brand)}` })
  }

  const goToSpecialZone = (type: 'gift' | 'designer' | 'best_seller', title: string) => {
    Taro.navigateTo({ url: `/pages/special-zone/index?type=${type}&title=${encodeURIComponent(title)}` })
  }

  const handleZoneClick = (type: 'gift' | 'designer' | 'best_seller') => {
    const titles = {
      gift: '礼品专区',
      designer: '设计师专区',
      best_seller: '爆品专区',
    }
    goToSpecialZone(type, titles[type])
  }

  const goToAllCategories = () => {
    Taro.switchTab({ url: '/pages/category/index' })
  }

  const goToAllBrands = () => {
    Taro.navigateTo({ url: '/pages/brand-list/index' })
  }

  return (
    <View className='home'>
      <View className='search-bar'>
        <View className='search-input'>
          <View className='search-icon'>🔍</View>
          <Input
            className='input'
            placeholder='搜索商品'
            value={searchValue}
            onInput={(e) => setSearchValue(e.detail.value)}
            onConfirm={handleSearch}
          />
        </View>
      </View>

      <ScrollView
        className='content'
        scrollY
        refresherEnabled
        refresherTriggered={refreshing || (loading && page === 1)}
        onRefresherRefresh={onRefresh}
        onScrollToLower={onLoadMore}
      >
        {banners.length > 0 && (
          <Swiper className='banner' autoplay circular indicatorDots>
            {banners.map(banner => (
              <SwiperItem key={banner.id} onClick={() => handleBannerClick(banner)}>
                <Image className='banner-image' src={resolveLocalMediaUrl(banner.image_url)} mode='aspectFill' />
              </SwiperItem>
            ))}
          </Swiper>
        )}

        <View className='entry-section'>
          <View className='entry-card brand-entry' onClick={goToBrandZone}>
            <View className='entry-label'>品牌专区</View>
            <View className='entry-desc'>合作品牌商品</View>
          </View>
          <View className='entry-card activity-entry' onClick={goToActivityZone}>
            <View className='entry-label'>活动专区</View>
            <View className='entry-desc'>平台活动精选</View>
          </View>
        </View>

        <View className='special-zones'>
          <View className='zone-item gift-zone' onClick={() => handleZoneClick('gift')}>
            {giftZoneCover?.image_url && (
              <Image className='zone-image' src={resolveLocalMediaUrl(giftZoneCover.image_url)} mode='aspectFill' />
            )}
            <View className='zone-content'>
              <View className='zone-title'>礼品专区</View>
              <View className='zone-subtitle'>礼赠精选</View>
            </View>
          </View>
          <View className='zone-item designer-zone' onClick={() => handleZoneClick('designer')}>
            {designerZoneCover?.image_url && (
              <Image className='zone-image' src={resolveLocalMediaUrl(designerZoneCover.image_url)} mode='aspectFill' />
            )}
            <View className='zone-content'>
              <View className='zone-title'>设计师专区</View>
              <View className='zone-subtitle'>场景灵感</View>
            </View>
          </View>
        </View>

        <View className='special-zones'>
          <View className='zone-item best-seller-zone' onClick={() => handleZoneClick('best_seller')}>
            {bestSellerZoneCover?.image_url && (
              <Image className='zone-image' src={resolveLocalMediaUrl(bestSellerZoneCover.image_url)} mode='aspectFill' />
            )}
            <View className='zone-content'>
              <View className='zone-title'>爆品专区</View>
              <View className='zone-subtitle'>热销好物</View>
            </View>
          </View>
        </View>

        {majorCategories.length > 0 && (
          <View className='category-nav'>
            <View className='section-header-row'>
              <View className='section-title'>品类专区</View>
              <View className='more-btn' onClick={goToAllCategories}>更多 {'>'}</View>
            </View>
            <View className='category-grid'>
              {majorCategories.map(cat => (
                <View key={cat.id} className='category-item' onClick={() => goToCategory(cat.name)}>
                  {cat.logo ? (
                    <Image className='category-icon-img' src={resolveLocalMediaUrl(cat.logo)} mode='aspectFill' />
                  ) : (
                    <View className='category-icon'>{cat.name.charAt(0)}</View>
                  )}
                  <View className='category-name'>{cat.name}</View>
                </View>
              ))}
            </View>
          </View>
        )}

        {brands.length > 0 && (
          <View className='brand-section'>
            <View className='section-header-row'>
              <View className='section-title'>品牌专区</View>
              <View className='more-btn' onClick={goToAllBrands}>更多 {'>'}</View>
            </View>
            <View className='brand-grid'>
              {brands.slice(0, 4).map(brand => (
                <View key={brand.id} className='brand-item' onClick={() => goToBrand(brand.name)}>
                  <Image className='brand-logo' src={resolveLocalMediaUrl(brand.logo)} mode='aspectFit' />
                  <View className='brand-name'>{brand.name}</View>
                </View>
              ))}
            </View>
          </View>
        )}

        <View className='product-section'>
          <View className='section-header'>
            <View className='section-title'>全部商品</View>
          </View>
          <View className='product-list'>
            {products.map(product => (
              <ProductCard key={product.id} product={product} />
            ))}
          </View>

          {loading && (
            <View className='loading-wrapper'>
              <View className='loading-spinner'></View>
              <Text className='loading-text'>加载中...</Text>
            </View>
          )}

          {!hasMore && products.length > 0 && (
            <View className='no-more'>
              <View className='no-more-line'></View>
              <Text className='no-more-text'>没有更多商品了</Text>
              <View className='no-more-line'></View>
            </View>
          )}

          {!loading && products.length === 0 && (
            <View className='empty-state'>
              <Text className='empty-icon'>📦</Text>
              <Text className='empty-text'>暂无商品</Text>
            </View>
          )}
        </View>
      </ScrollView>
    </View>
  )
}

export default withPrivacyCheck(Home)
