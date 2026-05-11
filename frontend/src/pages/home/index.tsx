import { useState, useEffect } from 'react'
import { View, Swiper, SwiperItem, Image, ScrollView, Input, Text } from '@tarojs/components'
import Taro, { useRouter, useShareAppMessage, useShareTimeline } from '@tarojs/taro'
import { productService } from '../../services/product'
import { specialZoneCoverService } from '../../services/special-zone-cover'
import { specialZoneService } from '../../services/special-zone'
import { storeService } from '../../services/store'
import { Product, Category, HomeBanner, HomeStoreCard, SpecialZoneCover, Store } from '../../types'
import { resolveLocalMediaUrl } from '../../utils/media'
import { Storage, CACHE_KEYS } from '../../utils/storage'
import ProductCard from '../../components/ProductCard'
import { withPrivacyCheck } from '../../components/withPrivacyCheck'
import './index.scss'

function Home() {
  const router = useRouter()
  const [searchValue, setSearchValue] = useState('')
  const [majorCategories, setMajorCategories] = useState<Category[]>([])
  const [partnerStores, setPartnerStores] = useState<Store[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [homeStoreCards, setHomeStoreCards] = useState<HomeStoreCard[]>([])
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
    loadPartnerStores()
    loadHomeStoreCards(storeId)
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

  const loadPartnerStores = async () => {
    try {
      const data = await storeService.getPartnerStores({ page: 1, page_size: 8 })
      setPartnerStores(data.results || [])
    } catch (error) {
      // 静默失败
    }
  }

  const loadHomeStoreCards = async (storeId?: string) => {
    try {
      const data = await specialZoneService.getHomeStoreCards(storeId ? { store: storeId } : undefined)
      setHomeStoreCards(data)
    } catch (error) {
      setHomeStoreCards([])
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
    loadHomeStoreCards(storeId)
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

  const goToStore = (store: Store) => {
    Taro.navigateTo({ url: `/pages/store-detail/index?id=${store.id}` })
  }

  const goToCardStore = (card: HomeStoreCard, categoryId?: number) => {
    Taro.navigateTo({
      url: `/pages/store-detail/index?id=${card.store}${categoryId ? `&category_id=${categoryId}` : ''}`,
    })
  }

  const goToCardProduct = (product: Product) => {
    if (!product.is_active) {
      Taro.showModal({ title: '商品已下架', content: '该商品已下架，请联系管理员更新', showCancel: false })
      return
    }
    Taro.navigateTo({ url: `/pages/product-detail/index?id=${product.id}` })
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
    Taro.navigateTo({ url: '/pages/store-list/index' })
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

        {homeStoreCards.map(card => (
          <View key={card.id} className='home-store-card'>
            <View className='home-store-card-header' onClick={() => goToCardStore(card)}>
              <View className='home-store-card-title'>{card.title}</View>
              {!!card.subtitle && <View className='home-store-card-subtitle'>{card.subtitle}</View>}
            </View>
            {card.main_product && (
              <View className='home-store-main-product' onClick={() => goToCardProduct(card.main_product as Product)}>
                <Image className='home-store-main-image' src={resolveLocalMediaUrl(card.main_product.main_images?.[0])} mode='aspectFill' />
                <View className='home-store-main-name'>{card.main_product.name}</View>
              </View>
            )}
            <View className='home-store-secondary-grid'>
              {(card.secondary_products || []).map(product => (
                <View key={product.id} className='home-store-secondary-product' onClick={() => goToCardProduct(product)}>
                  <Image className='home-store-secondary-image' src={resolveLocalMediaUrl(product.main_images?.[0])} mode='aspectFill' />
                  <View className='home-store-secondary-name'>{product.name}</View>
                </View>
              ))}
            </View>
            <View className='home-store-category-row'>
              {(card.categories || []).map(category => (
                <View key={category.id} className='home-store-category-pill' onClick={() => goToCardStore(card, category.id)}>
                  {category.name}
                </View>
              ))}
            </View>
          </View>
        ))}

        {false && <View className='special-zones'>
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
        </View>}

        {false && <View className='special-zones'>
          <View className='zone-item best-seller-zone' onClick={() => handleZoneClick('best_seller')}>
            {bestSellerZoneCover?.image_url && (
              <Image className='zone-image' src={resolveLocalMediaUrl(bestSellerZoneCover.image_url)} mode='aspectFill' />
            )}
            <View className='zone-content'>
              <View className='zone-title'>爆品专区</View>
              <View className='zone-subtitle'>热销好物</View>
            </View>
          </View>
        </View>}

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

        {partnerStores.length > 0 && (
          <View className='brand-section'>
            <View className='section-header-row'>
              <View className='section-title'>品牌专区</View>
              <View className='more-btn' onClick={goToAllBrands}>更多 {'>'}</View>
            </View>
            <View className='brand-grid'>
              {partnerStores.slice(0, 4).map(store => (
                <View key={store.id} className='brand-item' onClick={() => goToStore(store)}>
                  {store.logo ? (
                    <Image className='brand-logo' src={resolveLocalMediaUrl(store.logo)} mode='aspectFit' />
                  ) : (
                    <View className='brand-logo brand-logo-placeholder'>{store.name.charAt(0)}</View>
                  )}
                  <View className='brand-name'>{store.name}</View>
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
