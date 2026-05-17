import { useEffect, useMemo, useState } from 'react'
import { View, ScrollView, Image, Swiper, SwiperItem, Text, Video } from '@tarojs/components'
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

interface DisplayBrand extends Partial<Brand> {
  id?: number
  name: string
  logo?: string
  description?: string
}

interface ShowcaseSlide {
  id: string
  title: string
  imageUrl: string
  product?: Product
  banner?: HomeBanner
}

interface ArrivalCard {
  id: string
  product: Product
  imageUrl: string
  videoUrl?: string
}

const CHUANGYI_CATEGORY_ORDER = ['卫浴', '防水', '电器', '瓷砖', '乳胶漆', '水管', '开关']

const CHUANGYI_AUDIENCE = ['材料部', '设计师', '工程部', '零售客户']

const CATEGORY_COPY: Record<string, string> = {
  卫浴: '洁具 / 五金 / 空间配套',
  防水: '基材 / 防护 / 施工方案',
  电器: '开关 / 插座 / 机电配套',
  瓷砖: '空间铺贴 / 花色组合',
  乳胶漆: '墙面 / 色彩 / 施工维护',
  水管: '管路 / 连接 / 隐蔽工程',
  开关: '开关面板 / 统一配套',
}

function isChuangyiStore(store?: Store | null) {
  return !!store?.name && /创艺|創藝|chuangyi/i.test(store.name)
}

function getProductCover(product?: Product | null) {
  if (!product) return ''
  const raw = product.main_images?.[0] || product.detail_images?.[0] || (product as Product & { product_image_url?: string }).product_image_url
  return resolveLocalMediaUrl(raw)
}

function getProductVideo(product?: Product | null) {
  if (!product) return ''
  const extended = product as Product & {
    video_url?: string
    video?: string
    videoUrl?: string
  }
  const raw = extended.video_url || extended.video || extended.videoUrl || product.specifications?.video_url || product.specifications?.video || product.specifications?.videoUrl
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
  return stock > 0 ? `库存 ${stock}` : '库存 0'
}

function getCategoryCopy(name: string) {
  return CATEGORY_COPY[name] || '创艺精选分类'
}

function dedupeBrandsFromProducts(products: Product[]) {
  const map = new Map<string, DisplayBrand>()
  products.forEach((product) => {
    if (!product.brand || map.has(product.brand)) return
    map.set(product.brand, {
      name: product.brand,
      description: '',
      logo: '',
    })
  })
  return Array.from(map.values())
}

export default function StoreDetailPage() {
  const router = useRouter()
  const storeId = Number(router.params.id || router.params.store_id || 0)
  const initialCategoryId = Number(router.params.category_id || 0) || undefined

  const [store, setStore] = useState<Store | null>(null)
  const [banners, setBanners] = useState<HomeBanner[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [zones, setZones] = useState<SpecialZone[]>([])
  const [storeProducts, setStoreProducts] = useState<Product[]>([])
  const [featuredProducts, setFeaturedProducts] = useState<Product[]>([])
  const [newArrivalProducts, setNewArrivalProducts] = useState<Product[]>([])
  const [brands, setBrands] = useState<Brand[]>([])
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const [selectedCategoryId, setSelectedCategoryId] = useState<number | undefined>(initialCategoryId)
  const [selectedCategoryName, setSelectedCategoryName] = useState('')
  const [selectedBrandName, setSelectedBrandName] = useState('')

  const storeIsChuangyi = useMemo(() => isChuangyiStore(store), [store])

  const displayCategories = useMemo<DisplayCategory[]>(() => {
    if (!storeIsChuangyi) {
      return categories
    }

    const categoryMap = new Map<string, DisplayCategory>()
    categories.forEach((category) => {
      if (category.name) {
        categoryMap.set(category.name, category)
      }
    })

    const orderedCategories: DisplayCategory[] = CHUANGYI_CATEGORY_ORDER.map((name, index) => (
      categoryMap.get(name) || {
        name,
        order: index,
        logo: '',
      }
    ))

    categories.forEach((category) => {
      if (!category.name) return
      if (CHUANGYI_CATEGORY_ORDER.includes(category.name)) return
      if (orderedCategories.some(item => item.name === category.name)) return
      orderedCategories.push(category)
    })

    return orderedCategories
  }, [categories, storeIsChuangyi])

  const displayBrands = useMemo<DisplayBrand[]>(() => {
    const baseBrands = brands.length > 0 ? brands : dedupeBrandsFromProducts(storeProducts)

    if (!selectedCategoryId && !selectedCategoryName && !selectedBrandName) {
      return baseBrands
    }

    const availableBrandNames = new Set(storeProducts.map(product => product.brand).filter(Boolean))
    const filteredBrands = baseBrands.filter(brand => availableBrandNames.has(brand.name))
    return filteredBrands.length > 0 ? filteredBrands : baseBrands
  }, [brands, storeProducts, selectedBrandName, selectedCategoryId, selectedCategoryName])

  const carouselSlides = useMemo<ShowcaseSlide[]>(() => {
    const productLookup = new Map<number, Product>()
    ;[...featuredProducts, ...storeProducts].forEach((product) => {
      productLookup.set(product.id, product)
    })

    const bannerSlides = banners.map((banner) => {
      const linkedProduct = banner.product_id ? productLookup.get(banner.product_id) : undefined
      return {
        id: `banner-${banner.id}`,
        title: banner.title || linkedProduct?.name || store?.name || '品牌馆',
        imageUrl: resolveLocalMediaUrl(banner.image_url),
        product: linkedProduct,
        banner,
      }
    })

    const productSlides = (featuredProducts.length > 0 ? featuredProducts : storeProducts)
      .slice(0, 5)
      .map(product => ({
        id: `product-${product.id}`,
        title: product.name,
        imageUrl: getProductCover(product),
        product,
      }))

    if (bannerSlides.length > 0) {
      const mergedSlides = [...bannerSlides]
      productSlides.forEach((slide) => {
        if (!slide.product || mergedSlides.some(item => item.product?.id === slide.product?.id)) return
        mergedSlides.push(slide)
      })
      return mergedSlides.slice(0, 6)
    }

    return productSlides
  }, [banners, featuredProducts, storeProducts, store?.name])

  const arrivalCards = useMemo<ArrivalCard[]>(() => (
    newArrivalProducts.slice(0, 6).map(product => ({
      id: `arrival-${product.id}`,
      product,
      imageUrl: getProductCover(product),
      videoUrl: getProductVideo(product),
    }))
  ), [newArrivalProducts])

  const currentFocusLabel = selectedBrandName || selectedCategoryName || '全部商品'

  useEffect(() => {
    if (!storeId) {
      Taro.showToast({ title: '店铺不存在', icon: 'none' })
      return
    }

    loadStoreDetail(initialCategoryId)
    loadSupportingData()
    Taro.showShareMenu({ withShareTicket: true })
  }, [storeId])

  useShareAppMessage(() => ({
    title: store?.name || '合作方店铺',
    path: `/pages/store-detail/index?id=${storeId}`,
    ...(resolveLocalMediaUrl(store?.cover_image) ? { imageUrl: resolveLocalMediaUrl(store?.cover_image) } : {}),
  }))

  useShareTimeline(() => ({
    title: store?.name || '合作方店铺',
    query: `id=${storeId}`,
    ...(resolveLocalMediaUrl(store?.cover_image) ? { imageUrl: resolveLocalMediaUrl(store?.cover_image) } : {}),
  }))

  const loadSupportingData = async () => {
    try {
      const [brandResult, featuredResult, arrivalResult] = await Promise.allSettled([
        productService.getBrands({ store: storeId }),
        productService.getProducts({ store: storeId, page: 1, page_size: 5, sort_by: 'sales' }),
        productService.getProducts({ store: storeId, page: 1, page_size: 8, sort_by: 'created' }),
      ])

      if (brandResult.status === 'fulfilled') {
        setBrands(brandResult.value || [])
      }
      if (featuredResult.status === 'fulfilled') {
        setFeaturedProducts(featuredResult.value.results || [])
      }
      if (arrivalResult.status === 'fulfilled') {
        setNewArrivalProducts(arrivalResult.value.results || [])
      }
    } catch (error) {
      // 保留现有主内容，不让辅助数据影响浏览
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
    } catch (error) {
      Taro.showToast({ title: '加载店铺失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }

  const loadCategoryProductsByName = async (categoryName: string, pageNum = 1) => {
    setLoading(true)
    try {
      const res = await productService.getProductsByCategory({
        category: categoryName,
        store: storeId,
        page: pageNum,
        page_size: 20,
      })

      setStoreProducts(prev => (pageNum === 1 ? res.results : [...prev, ...res.results]))
      setPage(pageNum)
      setHasMore(res.has_next || false)
      setSelectedCategoryId(undefined)
      setSelectedCategoryName(categoryName)
      setSelectedBrandName('')
    } catch (error) {
      Taro.showToast({ title: '加载分类失败', icon: 'none' })
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
        page: pageNum,
        page_size: 20,
      })

      setStoreProducts(prev => (pageNum === 1 ? res.results : [...prev, ...res.results]))
      setPage(pageNum)
      setHasMore(res.has_next || false)
      setSelectedCategoryId(undefined)
      setSelectedCategoryName('')
      setSelectedBrandName(brandName)
    } catch (error) {
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
    } catch (error) {
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

    if (selectedCategoryName) {
      await loadCategoryProductsByName(selectedCategoryName, page + 1)
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
    if (loading) return

    const isActiveById = !!category.id && selectedCategoryId === category.id
    const isActiveByName = !category.id && selectedCategoryName === category.name
    if (isActiveById || isActiveByName) {
      await resetFilters()
      return
    }

    if (category.id) {
      await loadStoreDetail(category.id)
      return
    }

    await loadCategoryProductsByName(category.name)
  }

  const handleBrandClick = async (brand: DisplayBrand) => {
    if (loading) return

    if (selectedBrandName === brand.name) {
      await resetFilters()
      return
    }

    await loadBrandProducts(brand.name)
  }

  const handleBannerClick = (banner: HomeBanner) => {
    if (banner.product_id) {
      goToProduct(banner.product_id)
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

  const openSupportChat = () => {
    Taro.navigateTo({ url: '/pages/support-chat/index' })
  }

  return (
    <View className={`store-detail-page ${storeIsChuangyi ? 'store-detail-page--chuangyi' : ''}`}>
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
                  <Text className='store-kicker'>{storeIsChuangyi ? '创艺品牌馆' : '品牌馆'}</Text>
                  <Text className='store-name'>{store.name}</Text>
                  {!!store.description && <Text className='store-description'>{store.description}</Text>}
                </View>
              </View>

              <View className='store-hero-meta'>
                <View className='meta-pill'>
                  <AppIcon name='company' tone='primary' />
                  <Text>后台实时更新</Text>
                </View>
                <View className='meta-pill'>
                  <AppIcon name='credit' tone='primary' />
                  <Text>库存同步可见</Text>
                </View>
                <View className='meta-pill'>
                  <AppIcon name='message' tone='primary' />
                  <Text>支持问题反馈</Text>
                </View>
              </View>

              {storeIsChuangyi && (
                <View className='store-audience-row'>
                  {CHUANGYI_AUDIENCE.map(item => (
                    <View key={item} className='audience-pill'>{item}</View>
                  ))}
                </View>
              )}
            </View>
          </View>
        )}

        {displayCategories.length > 0 && (
          <View className='store-section'>
            <View className='section-header'>
              <View>
                <Text className='section-kicker'>产品类别</Text>
                <Text className='section-title'>按品类看品牌与商品</Text>
              </View>
            </View>

            <ScrollView className='category-scroll' scrollX scrollWithAnimation>
              <View className='category-track'>
                {displayCategories.map((category) => {
                  const isActive = (!!category.id && selectedCategoryId === category.id) || (!category.id && selectedCategoryName === category.name)
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
                      <Text className='category-copy'>{getCategoryCopy(category.name)}</Text>
                    </View>
                  )
                })}
              </View>
            </ScrollView>
          </View>
        )}

        {displayBrands.length > 0 && (
          <View className='store-section'>
            <View className='section-header'>
              <View>
                <Text className='section-kicker'>品牌分类</Text>
                <Text className='section-title'>
                  {selectedCategoryName || selectedCategoryId ? '当前分类下的品牌筛选' : '店铺品牌筛选'}
                </Text>
              </View>
            </View>

            <ScrollView className='brand-scroll' scrollX scrollWithAnimation>
              <View className='brand-track'>
                {displayBrands.map((brand) => {
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
                <Text className='section-title'>轮播展示价格和库存</Text>
              </View>
            </View>

            <Swiper className='showcase-swiper' autoplay circular indicatorDots>
              {carouselSlides.map((slide) => (
                <SwiperItem key={slide.id}>
                  <View className='showcase-card' onClick={() => handleShowcaseClick(slide)}>
                    <View className='showcase-media'>
                      <Image className='showcase-image' src={slide.imageUrl} mode='aspectFill' />
                      <View className='showcase-badge'>{slide.product?.tag === 'brand_direct' ? '品牌直发' : slide.product ? '产品推荐' : '品牌轮播'}</View>
                    </View>
                    <View className='showcase-body'>
                      <Text className='showcase-title'>{slide.product?.name || slide.title}</Text>
                      <Text className='showcase-desc'>
                        {slide.product?.description || (slide.banner?.title || '点击查看详细产品介绍')}
                      </Text>
                      <View className='showcase-footer'>
                        {slide.product ? (
                          <>
                            <PriceText value={getSellingPrice(slide.product)} size='lg' />
                            <View className='stock-pill'>{getStockLabel(slide.product)}</View>
                          </>
                        ) : (
                          <View className='showcase-footnote'>点击进入商品详情</View>
                        )}
                      </View>
                    </View>
                  </View>
                </SwiperItem>
              ))}
            </Swiper>
          </View>
        )}

        {arrivalCards.length > 0 && (
          <View className='store-section'>
            <View className='section-header'>
              <View>
                <Text className='section-kicker'>新品上新</Text>
                <Text className='section-title'>视频和图片一起看</Text>
              </View>
            </View>

            <ScrollView className='arrival-scroll' scrollX scrollWithAnimation>
              <View className='arrival-track'>
                {arrivalCards.map((item) => (
                  <View key={item.id} className='arrival-card' onClick={() => goToProduct(item.product.id)}>
                    <View className='arrival-media'>
                      {item.videoUrl ? (
                        <Video
                          className='arrival-video'
                          src={item.videoUrl}
                          poster={item.imageUrl}
                          controls
                          objectFit='cover'
                        />
                      ) : item.imageUrl ? (
                        <Image className='arrival-image' src={item.imageUrl} mode='aspectFill' />
                      ) : (
                        <View className='arrival-fallback'>
                          <AppIcon name='package' tone='muted' />
                        </View>
                      )}
                      <View className='arrival-badge'>新品</View>
                    </View>
                    <View className='arrival-body'>
                      <Text className='arrival-name'>{item.product.name}</Text>
                      <Text className='arrival-desc'>{item.product.brand || '品牌更新中'}</Text>
                      <View className='arrival-footer'>
                        <PriceText value={getSellingPrice(item.product)} size='sm' />
                        <Text className='arrival-stock'>{getStockLabel(item.product)}</Text>
                      </View>
                    </View>
                  </View>
                ))}
              </View>
            </ScrollView>
          </View>
        )}

        {zones.length > 0 && (
          <View className='store-section'>
            <View className='section-header'>
              <View>
                <Text className='section-kicker'>品牌专区</Text>
                <Text className='section-title'>专题活动和方案入口</Text>
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

        {storeIsChuangyi && (
          <View className='store-section support-section'>
            <View className='section-header'>
              <View>
                <Text className='section-kicker'>问题与需求</Text>
                <Text className='section-title'>直接上传图片、视频和文字</Text>
              </View>
            </View>
            <View className='support-card' onClick={openSupportChat}>
              <View className='support-icon'>
                <AppIcon name='message' tone='primary' />
              </View>
              <View className='support-copy'>
                <Text className='support-title'>材料部 / 设计师 / 工程部 / 零售客户</Text>
                <Text className='support-desc'>
                  有选型问题、现场需求、补货咨询或替换建议，直接发图发视频，我们通过管理账号统一查看和回复。
                </Text>
              </View>
              <View className='support-action'>
                <Text>去反馈</Text>
              </View>
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
              {storeIsChuangyi && (
                <View className='empty-action' onClick={openSupportChat}>
                  <AppIcon name='message' tone='primary' />
                  <Text>提交需求</Text>
                </View>
              )}
            </View>
          )}
          {!loading && !hasMore && storeProducts.length > 0 && <View className='status-text'>没有更多商品了</View>}
        </View>
      </ScrollView>
    </View>
  )
}
