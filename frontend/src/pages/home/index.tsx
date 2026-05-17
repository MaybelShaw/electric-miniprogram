import { useState, useEffect } from 'react'
import { View, Swiper, SwiperItem, Image, ScrollView, Text } from '@tarojs/components'
import Taro, { useRouter, useShareAppMessage, useShareTimeline } from '@tarojs/taro'
import { productService } from '../../services/product'
import { specialZoneCoverService } from '../../services/special-zone-cover'
import { specialZoneService } from '../../services/special-zone'
import { storeService } from '../../services/store'
import { Product, HomeBanner, HomeStoreCard, SpecialZoneCover, Store } from '../../types'
import { resolveLocalMediaUrl } from '../../utils/media'
import AppIcon from '../../components/AppIcon'
import EmptyState from '../../components/EmptyState'
import LoadingState from '../../components/LoadingState'
import ProductCard from '../../components/ProductCard'
import SearchBar from '../../components/SearchBar'
import SectionHeader from '../../components/SectionHeader'
import StoreShowcaseCard from '../../components/StoreShowcaseCard'
import { withPrivacyCheck } from '../../components/withPrivacyCheck'
import './index.scss'

function Home() {
  const router = useRouter()
  const [searchValue, setSearchValue] = useState('')
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
      <View className='home-topbar'>
        <SearchBar
          value={searchValue}
          onInput={setSearchValue}
          onConfirm={handleSearch}
        />
      </View>

      <ScrollView
        className='content'
        scrollY
        refresherEnabled
        refresherTriggered={refreshing || (loading && page === 1)}
        onRefresherRefresh={onRefresh}
        onScrollToLower={onLoadMore}
      >
        <View className='home-hero'>
          {banners.length > 0 ? (
            <Swiper className='hero-swiper' autoplay circular indicatorDots>
              {banners.map(banner => (
                <SwiperItem key={banner.id} onClick={() => handleBannerClick(banner)}>
                  <Image className='hero-image' src={resolveLocalMediaUrl(banner.image_url)} mode='aspectFill' />
                </SwiperItem>
              ))}
            </Swiper>
          ) : (
            <View className='hero-fallback'>
              <View className='hero-fallback-line' />
            </View>
          )}
          <View className='hero-copy'>
            <Text className='hero-kicker'>QINGXUN HOME</Text>
            <View className='hero-title'>庆勋愉悦家</View>
            <View className='hero-subtitle'>精选品牌家电与生活方式方案</View>
          </View>
        </View>

        <View className='home-actions'>
          <View className='home-action' onClick={goToActivityZone}>
            <AppIcon name='package' tone='muted' className='action-icon' />
            <View className='action-title'>活动展区</View>
            <View className='action-desc'>限时组合</View>
          </View>
          <View className='home-action' onClick={goToBrandZone}>
            <AppIcon name='store' tone='gold' className='action-icon' />
            <View className='action-title'>品牌馆</View>
            <View className='action-desc'>合作品牌精选</View>
          </View>
          <View className='home-action' onClick={goToAllCategories}>
            <AppIcon name='search' tone='muted' className='action-icon' />
            <View className='action-title'>全品类</View>
            <View className='action-desc'>按功能选购</View>
          </View>
        </View>

        <View className='curation-section'>
          <SectionHeader title='灵感专区' subtitle='按礼赠、设计与热销场景快速进入' />
          <View className='curation-list'>
            <View className='curation-item curation-item--primary' onClick={() => handleZoneClick('designer')}>
              <View className='curation-visual'>
                <AppIcon name='search' tone='muted' className='curation-icon' />
              </View>
              <View className='curation-copy'>
                <Text className='curation-label'>DESIGN</Text>
                <View className='curation-title'>设计师专区</View>
                <View className='curation-desc'>场景灵感与搭配方案</View>
              </View>
              <Text className='curation-arrow'>›</Text>
            </View>
            <View className='curation-item' onClick={() => handleZoneClick('gift')}>
              <View className='curation-visual'>
                <AppIcon name='package' tone='gold' className='curation-icon' />
              </View>
              <View className='curation-copy'>
                <Text className='curation-label'>GIFT</Text>
                <View className='curation-title'>礼品专区</View>
                <View className='curation-desc'>签单礼品与客户伴手礼</View>
              </View>
              <Text className='curation-arrow'>›</Text>
            </View>
            <View className='curation-item' onClick={() => handleZoneClick('best_seller')}>
              <View className='curation-visual'>
                <AppIcon name='store' tone='muted' className='curation-icon' />
              </View>
              <View className='curation-copy'>
                <Text className='curation-label'>BEST</Text>
                <View className='curation-title'>爆品专区</View>
                <View className='curation-desc'>近期热销与高频采购</View>
              </View>
              <Text className='curation-arrow'>›</Text>
            </View>
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
            <ScrollView className='home-store-category-scroll' scrollX>
              <View className='home-store-category-row'>
                {(card.categories || []).map((category, index) => {
                  const categoryImage = category.logo
                    || card.secondary_products?.[index]?.main_images?.[0]
                    || card.main_product?.main_images?.[0]

                  return (
                    <View key={category.id} className='home-store-category-card' onClick={() => goToCardStore(card, category.id)}>
                      {categoryImage ? (
                        <Image className='home-store-category-image' src={resolveLocalMediaUrl(categoryImage)} mode='aspectFill' />
                      ) : (
                        <View className='home-store-category-placeholder'>
                          <AppIcon name='package' tone='muted' />
                        </View>
                      )}
                      <View className='home-store-category-name'>{category.name}</View>
                    </View>
                  )
                })}
              </View>
            </ScrollView>
          </View>
        ))}

        {partnerStores.length > 0 && (
          <View className='brand-section'>
            <View className='section-header-row'>
              <SectionHeader title='品牌专区' actionText='更多' onAction={goToAllBrands} />
            </View>
            <ScrollView className='brand-showcase-scroll' scrollX>
              <View className='brand-showcase-row'>
                {partnerStores.slice(0, 8).map(store => (
                  <StoreShowcaseCard
                    key={store.id}
                    store={store}
                    className='brand-showcase-card-home'
                    onClick={() => goToStore(store)}
                  />
                ))}
              </View>
            </ScrollView>
          </View>
        )}

        <View className='product-section'>
          <View className='section-header'>
            <SectionHeader title='全部商品' subtitle='精选家电与生活方式好物' centered />
          </View>
          <View className='product-list'>
            {products.map(product => (
              <ProductCard key={product.id} product={product} />
            ))}
          </View>

          {loading && (
            <LoadingState text='加载中...' />
          )}

          {!hasMore && products.length > 0 && (
            <View className='no-more'>
              <View className='no-more-line'></View>
              <Text className='no-more-text'>没有更多商品了</Text>
              <View className='no-more-line'></View>
            </View>
          )}

          {!loading && products.length === 0 && (
            <EmptyState title='暂无商品' icon='package' />
          )}
        </View>
      </ScrollView>
    </View>
  )
}

export default withPrivacyCheck(Home)
