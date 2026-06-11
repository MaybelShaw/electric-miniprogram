import { useEffect, useMemo, useState } from 'react'
import { View, ScrollView, Image, Swiper, SwiperItem, Text } from '@tarojs/components'
import Taro, { useRouter, useShareAppMessage, useShareTimeline } from '@tarojs/taro'
import ProductCard from '../../components/ProductCard'
import PriceText from '../../components/PriceText'
import AppIcon from '../../components/AppIcon'
import { productService } from '../../services/product'
import { storeService } from '../../services/store'
import { Category, HomeBanner, Product, SpecialZone, Store } from '../../types'
import { resolveLocalMediaUrl } from '../../utils/media'
import './index.scss'

interface DisplayCategory extends Partial<Category> {
  id?: number
  name: string
  logo?: string
}

interface ShowcaseSlide {
  id: string
  title: string
  imageUrl: string
  product?: Product
  banner?: HomeBanner
}

function getProductCover(product?: Product | null) {
  if (!product) return ''
  const raw = product.main_images?.[0] || product.detail_images?.[0] || (product as Product & { product_image_url?: string }).product_image_url
  return resolveLocalMediaUrl(raw)
}

function getSellingPrice(product?: Product | null) {
  if (!product) return 0
  const basePrice = Number(product.display_price ?? product.price ?? 0)
  const discountedPrice = Number(product.discounted_price ?? 0)
  if (Number.isFinite(discountedPrice) && discountedPrice > 0 && discountedPrice < basePrice) {
    return discountedPrice
  }
  return basePrice
}

function getStockLabel(product?: Product | null) {
  const stock = Number(product?.stock ?? 0)
  if (!Number.isFinite(stock) || stock < 0) {
    return '库存待同步'
  }
  return `库存 ${stock}`
}

function getCategoryCopy(category: DisplayCategory) {
  if (category.children?.length) {
    return `${category.children.length} 个子类`
  }
  return ''
}

export default function StoreDetailPage() {
  const router = useRouter()
  const storeId = Number(router.params.id || router.params.store_id || 0)

  const [store, setStore] = useState<Store | null>(null)
  const [banners, setBanners] = useState<HomeBanner[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [zones, setZones] = useState<SpecialZone[]>([])
  const [storeProducts, setStoreProducts] = useState<Product[]>([])
  const [featuredProducts, setFeaturedProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)

  const displayCategories = useMemo<DisplayCategory[]>(() => categories, [categories])

  const carouselSlides = useMemo<ShowcaseSlide[]>(() => {
    const productLookup = new Map<number, Product>()
    ;[...featuredProducts, ...storeProducts].forEach((product) => {
      productLookup.set(product.id, product)
    })

    const bannerSlides = banners.map((banner) => {
      const linkedProduct = banner.product_id ? productLookup.get(Number(banner.product_id)) : undefined
      return {
        id: `banner-${banner.id}`,
        title: banner.title || linkedProduct?.name || store?.name || '店铺轮播',
        imageUrl: resolveLocalMediaUrl(banner.image_url),
        product: linkedProduct,
        banner,
      }
    }).filter(slide => slide.imageUrl)

    const productSlides = (featuredProducts.length > 0 ? featuredProducts : storeProducts)
      .slice(0, 5)
      .map(product => ({
        id: `product-${product.id}`,
        title: product.name,
        imageUrl: getProductCover(product),
        product,
      }))
      .filter(slide => slide.imageUrl)

    return [...bannerSlides, ...productSlides].slice(0, 6)
  }, [banners, featuredProducts, storeProducts, store?.name])

  const currentFocusLabel = '全部商品'

  useEffect(() => {
    if (!storeId) {
      Taro.showToast({ title: '店铺不存在', icon: 'none' })
      return
    }

    loadStoreDetail()
    loadFeaturedProducts()
    Taro.showShareMenu({ withShareTicket: true })
  }, [storeId])

  useShareAppMessage(() => ({
    title: store?.name || '店铺首页',
    path: `/pages/store-detail/index?id=${storeId}`,
    ...(resolveLocalMediaUrl(store?.cover_image) ? { imageUrl: resolveLocalMediaUrl(store?.cover_image) } : {}),
  }))

  useShareTimeline(() => ({
    title: store?.name || '店铺首页',
    query: `id=${storeId}`,
    ...(resolveLocalMediaUrl(store?.cover_image) ? { imageUrl: resolveLocalMediaUrl(store?.cover_image) } : {}),
  }))

  const loadFeaturedProducts = async () => {
    try {
      const featuredResult = await productService.getProducts({ store: storeId, page: 1, page_size: 5, sort_by: 'sales' })
      setFeaturedProducts(featuredResult.results || [])
    } catch {
      setFeaturedProducts([])
    }
  }

  const loadStoreDetail = async () => {
    setLoading(true)
    try {
      const detail = await storeService.getStoreDetail(storeId)

      setStore(detail.store)
      setBanners(detail.banners || [])
      setCategories(detail.categories || [])
      setZones(detail.special_zones || [])
      setStoreProducts(detail.products || [])
      setPage(1)
      setHasMore((detail.products || []).length >= 20)
      Taro.setNavigationBarTitle({ title: detail.store.name })
    } catch {
      Taro.showToast({ title: '加载店铺失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }

  const loadGeneralProducts = async (pageNum = 1) => {
    setLoading(true)
    try {
      const res = await productService.getProducts({
        store: storeId,
        page: pageNum,
        page_size: 20,
      })

      setStoreProducts(prev => (pageNum === 1 ? res.results : [...prev, ...res.results]))
      setPage(pageNum)
      setHasMore(res.has_next || false)
    } catch {
      Taro.showToast({ title: '加载商品失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }

  const loadMoreProducts = async () => {
    if (loading || !hasMore) return
    await loadGeneralProducts(page + 1)
  }

  const goToZone = (zone: SpecialZone) => {
    Taro.navigateTo({ url: `/pages/special-zone/index?zone_id=${zone.id}&store_id=${storeId}` })
  }

  const goToProduct = (productId: number) => {
    Taro.navigateTo({ url: `/pages/product-detail/index?id=${productId}` })
  }

  const handleCategoryClick = async (category: DisplayCategory) => {
    if (loading || !category.id) return
    Taro.navigateTo({
      url: `/pages/store-category/index?store_id=${storeId}&category_id=${category.id}&category_name=${encodeURIComponent(category.name)}`,
    })
  }

  const handleBannerClick = (banner: HomeBanner) => {
    if (banner.product_id) {
      goToProduct(Number(banner.product_id))
      return
    }

    if (banner.special_zone_id) {
      Taro.navigateTo({ url: `/pages/special-zone/index?zone_id=${banner.special_zone_id}&store_id=${storeId}` })
    }
  }

  const handleShowcaseClick = (slide: ShowcaseSlide) => {
    if (slide.banner) {
      handleBannerClick(slide.banner)
      return
    }

    if (slide.product?.id) {
      goToProduct(slide.product.id)
    }
  }

  return (
    <View className='store-detail-page'>
      <ScrollView className='store-detail-scroll' scrollY onScrollToLower={loadMoreProducts}>
        {store && (
          <View className='store-hero'>
            <View className='store-hero-cover'>
              {resolveLocalMediaUrl(store.cover_image) ? (
                <Image className='store-hero-image' src={resolveLocalMediaUrl(store.cover_image)} mode='aspectFill' />
              ) : resolveLocalMediaUrl(featuredProducts[0]?.main_images?.[0]) ? (
                <Image className='store-hero-image' src={resolveLocalMediaUrl(featuredProducts[0]?.main_images?.[0])} mode='aspectFill' />
              ) : (
                <View className='store-hero-fallback'>
                  <View className='store-hero-fallback-mark'>{store.name.charAt(0)}</View>
                </View>
              )}
            </View>

            <View className='store-hero-panel'>
              <View className='store-brand-row'>
                <View className={`store-logo-wrap ${resolveLocalMediaUrl(store.logo) ? '' : 'store-logo-wrap--icon'}`}>
                  {resolveLocalMediaUrl(store.logo) ? (
                    <Image className='store-logo' src={resolveLocalMediaUrl(store.logo)} mode='aspectFit' />
                  ) : (
                    <View className='store-logo-fallback'>
                      <AppIcon name='store' tone='gold' />
                    </View>
                  )}
                </View>

                <View className='store-copy'>
                  <Text className='store-kicker'>店铺首页</Text>
                  <Text className='store-name'>{store.name}</Text>
                  {!!store.description && <Text className='store-description'>{store.description}</Text>}
                </View>
              </View>

              <View className='store-hero-meta'>
                {!!store.contact_phone && (
                  <View className='meta-pill'>
                    <AppIcon name='service' tone='primary' />
                    <Text>{store.contact_phone}</Text>
                  </View>
                )}
                {!!store.address && (
                  <View className='meta-pill'>
                    <AppIcon name='company' tone='primary' />
                    <Text>{store.address}</Text>
                  </View>
                )}
              </View>
            </View>
          </View>
        )}

        {displayCategories.length > 0 && (
          <View className='store-section'>
            <View className='section-header'>
              <View>
                <Text className='section-kicker'>产品类别</Text>
              </View>
            </View>

            <ScrollView className='category-scroll' scrollX scrollWithAnimation>
              <View className='category-track'>
                {displayCategories.map(category => (
                  <View
                    key={category.id || category.name}
                    className='category-card'
                    onClick={() => handleCategoryClick(category)}
                  >
                    <View className='category-media'>
                      {resolveLocalMediaUrl(category.logo) ? (
                        <Image className='category-image' src={resolveLocalMediaUrl(category.logo)} mode='aspectFit' />
                      ) : (
                        <View className='category-fallback'>{category.name.charAt(0)}</View>
                      )}
                    </View>
                    <Text className='category-name'>{category.name}</Text>
                    {getCategoryCopy(category) ? <Text className='category-copy'>{getCategoryCopy(category)}</Text> : null}
                  </View>
                ))}
              </View>
            </ScrollView>
          </View>
        )}

        {carouselSlides.length > 0 && (
          <View className='store-section'>
            <View className='section-header'>
              <View>
                <Text className='section-kicker'>推荐产品</Text>
              </View>
            </View>

            <Swiper className='showcase-swiper' autoplay circular indicatorDots>
              {carouselSlides.map((slide) => (
                <SwiperItem key={slide.id}>
                  <View className='showcase-card' onClick={() => handleShowcaseClick(slide)}>
                    <View className='showcase-media'>
                      <Image className='showcase-image' src={slide.imageUrl} mode='aspectFill' />
                      <View className='showcase-badge'>{slide.product ? '产品推荐' : '店铺轮播'}</View>
                    </View>
                    <View className='showcase-body'>
                      <Text className='showcase-title'>{slide.product?.name || slide.title}</Text>
                      {slide.product?.description ? <Text className='showcase-desc'>{slide.product.description}</Text> : null}
                      <View className='showcase-footer'>
                        {slide.product ? (
                          <>
                            <PriceText value={getSellingPrice(slide.product)} size='lg' />
                            <View className='stock-pill'>{getStockLabel(slide.product)}</View>
                          </>
                        ) : (
                          <View className='showcase-footnote'>{slide.title}</View>
                        )}
                      </View>
                    </View>
                  </View>
                </SwiperItem>
              ))}
            </Swiper>
          </View>
        )}

        {zones.length > 0 && (
          <View className='store-section'>
            <View className='section-header'>
              <View>
                <Text className='section-kicker'>店铺活动</Text>
              </View>
            </View>
            <View className='zone-grid'>
              {zones.map(zone => (
                <View key={zone.id} className='zone-card' onClick={() => goToZone(zone)}>
                  {resolveLocalMediaUrl(zone.cover_image) ? (
                    <Image className='zone-image' src={resolveLocalMediaUrl(zone.cover_image)} mode='aspectFill' />
                  ) : null}
                  <View className='zone-copy'>
                    <Text className='zone-title'>{zone.title}</Text>
                    {!!zone.subtitle && <Text className='zone-subtitle'>{zone.subtitle}</Text>}
                  </View>
                </View>
              ))}
            </View>
          </View>
        )}

        <View className='store-section product-section'>
          <View className='section-header'>
            <View>
              <Text className='section-kicker'>商品列表</Text>
              <Text className='section-title'>{currentFocusLabel}</Text>
            </View>
          </View>
          <View className='product-list'>
            {storeProducts.map(product => (
              <ProductCard key={product.id} product={product} />
            ))}
          </View>
          {loading && <View className='status-text'>加载中...</View>}
          {!loading && storeProducts.length === 0 && (
            <View className='empty-panel'>
              <Text className='status-text'>暂无商品</Text>
            </View>
          )}
          {!loading && !hasMore && storeProducts.length > 0 && <View className='status-text'>没有更多商品了</View>}
        </View>
      </ScrollView>
    </View>
  )
}
