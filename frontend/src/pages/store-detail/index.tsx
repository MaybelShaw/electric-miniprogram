import { useEffect, useMemo, useState } from 'react'
import { View, ScrollView, Image, Swiper, SwiperItem, Text } from '@tarojs/components'
import Taro, { useRouter, useShareAppMessage, useShareTimeline } from '@tarojs/taro'
import ProductCard from '../../components/ProductCard'
import PriceText from '../../components/PriceText'
import AppIcon from '../../components/AppIcon'
import { productService } from '../../services/product'
import { storeService } from '../../services/store'
import { Brand, Category, HomeBanner, Product, SpecialZone, Store } from '../../types'
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
  return '点击查看品牌和商品'
}

export default function StoreDetailPage() {
  const router = useRouter()
  const storeId = Number(router.params.id || router.params.store_id || 0)
  const initialCategoryId = Number(router.params.category_id || 0) || undefined

  const [store, setStore] = useState<Store | null>(null)
  const [banners, setBanners] = useState<HomeBanner[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [brands, setBrands] = useState<Brand[]>([])
  const [zones, setZones] = useState<SpecialZone[]>([])
  const [storeProducts, setStoreProducts] = useState<Product[]>([])
  const [featuredProducts, setFeaturedProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const [selectedCategoryId, setSelectedCategoryId] = useState<number | undefined>(initialCategoryId)
  const [selectedCategoryName, setSelectedCategoryName] = useState('')
  const [selectedBrandName, setSelectedBrandName] = useState('')

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

  const currentFocusLabel = selectedBrandName || selectedCategoryName || '全部商品'

  useEffect(() => {
    if (!storeId) {
      Taro.showToast({ title: '店铺不存在', icon: 'none' })
      return
    }

    loadStoreDetail(initialCategoryId)
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

  const loadStoreDetail = async (categoryId?: number) => {
    setLoading(true)
    try {
      const detail = await storeService.getStoreDetail(
        storeId,
        categoryId ? { category_id: categoryId } : undefined,
      )

      setStore(detail.store)
      setBanners(detail.banners || [])
      setCategories(detail.categories || [])
      setBrands(detail.brands || [])
      setZones(detail.special_zones || [])
      setStoreProducts(detail.products || [])
      setPage(1)
      setHasMore(!categoryId && (detail.products || []).length >= 20)
      setSelectedCategoryId(categoryId)
      setSelectedCategoryName(
        categoryId
          ? (detail.categories || []).find(category => category.id === categoryId)?.name || ''
          : '',
      )
      setSelectedBrandName('')
      Taro.setNavigationBarTitle({ title: detail.store.name })
    } catch {
      Taro.showToast({ title: '加载店铺失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }

  const loadBrandProducts = async (brandName: string, pageNum = 1) => {
    setLoading(true)
    try {
      const res = await productService.getProductsByBrand({
        brand: brandName,
        store: storeId,
        category_id: selectedCategoryId,
        page: pageNum,
        page_size: 20,
      })

      setStoreProducts(prev => (pageNum === 1 ? res.results : [...prev, ...res.results]))
      setPage(pageNum)
      setHasMore(res.has_next || false)
      setSelectedBrandName(brandName)
    } catch {
      Taro.showToast({ title: '加载品牌失败', icon: 'none' })
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
      setSelectedCategoryId(undefined)
      setSelectedCategoryName('')
      setSelectedBrandName('')
    } catch {
      Taro.showToast({ title: '加载商品失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }

  const resetFilters = async () => {
    if (loading) return
    await loadStoreDetail()
  }

  const loadMoreProducts = async () => {
    if (loading || !hasMore) return
    if (selectedCategoryId) return

    if (selectedBrandName) {
      await loadBrandProducts(selectedBrandName, page + 1)
      return
    }

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

    if (selectedCategoryId === category.id) {
      await resetFilters()
      return
    }

    await loadStoreDetail(category.id)
  }

  const handleBrandClick = async (brand: Brand) => {
    if (loading) return

    if (selectedBrandName === brand.name) {
      await loadStoreDetail(selectedCategoryId)
      return
    }

    await loadBrandProducts(brand.name)
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
                <Text className='section-title'>先选类别，再看品牌</Text>
              </View>
            </View>

            <ScrollView className='category-scroll' scrollX scrollWithAnimation>
              <View className='category-track'>
                {displayCategories.map((category) => {
                  const isActive = selectedCategoryId === category.id
                  return (
                    <View
                      key={category.id || category.name}
                      className={`category-card ${isActive ? 'active' : ''}`}
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
                      <Text className='category-copy'>{getCategoryCopy(category)}</Text>
                    </View>
                  )
                })}
              </View>
            </ScrollView>
          </View>
        )}

        {brands.length > 0 && (
          <View className='store-section'>
            <View className='section-header'>
              <View>
                <Text className='section-kicker'>品牌分类</Text>
                <Text className='section-title'>
                  {selectedCategoryName || selectedCategoryId ? '当前类别下的品牌' : '店铺品牌'}
                </Text>
              </View>
            </View>

            <ScrollView className='brand-scroll' scrollX scrollWithAnimation>
              <View className='brand-track'>
                {brands.map((brand) => {
                  const isActive = selectedBrandName === brand.name
                  return (
                    <View
                      key={brand.id || brand.name}
                      className={`brand-card ${isActive ? 'active' : ''}`}
                      onClick={() => handleBrandClick(brand)}
                    >
                      <View className='brand-media'>
                        {resolveLocalMediaUrl(brand.logo) ? (
                          <Image className='brand-image' src={resolveLocalMediaUrl(brand.logo)} mode='aspectFit' />
                        ) : (
                          <View className='brand-fallback'>
                            <AppIcon name='store' tone='muted' />
                          </View>
                        )}
                      </View>
                      <Text className='brand-name'>{brand.name}</Text>
                      <Text className='brand-copy'>{brand.description || '点击查看该品牌产品'}</Text>
                    </View>
                  )
                })}
              </View>
            </ScrollView>
          </View>
        )}

        {carouselSlides.length > 0 && (
          <View className='store-section'>
            <View className='section-header'>
              <View>
                <Text className='section-kicker'>产品大图</Text>
                <Text className='section-title'>展示价格和库存</Text>
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
                      <Text className='showcase-desc'>
                        {slide.product?.description || '点击查看详细产品介绍'}
                      </Text>
                      <View className='showcase-footer'>
                        {slide.product ? (
                          <>
                            <PriceText value={getSellingPrice(slide.product)} size='lg' />
                            <View className='stock-pill'>{getStockLabel(slide.product)}</View>
                          </>
                        ) : (
                          <View className='showcase-footnote'>点击进入详情</View>
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
                <Text className='section-kicker'>店铺专区</Text>
                <Text className='section-title'>活动和专题入口</Text>
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
              <Text className='status-text'>当前没有可展示的商品</Text>
            </View>
          )}
          {!loading && !hasMore && storeProducts.length > 0 && <View className='status-text'>没有更多商品了</View>}
        </View>
      </ScrollView>
    </View>
  )
}
