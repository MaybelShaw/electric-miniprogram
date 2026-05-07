import { useEffect, useState } from 'react'
import { View, ScrollView, Image, Swiper, SwiperItem, Text } from '@tarojs/components'
import Taro, { useRouter, useShareAppMessage, useShareTimeline } from '@tarojs/taro'
import ProductCard from '../../components/ProductCard'
import { productService } from '../../services/product'
import { storeService } from '../../services/store'
import { Category, HomeBanner, Product, SpecialZone, Store } from '../../types'
import { resolveLocalMediaUrl } from '../../utils/media'
import './index.scss'

export default function StoreDetailPage() {
  const router = useRouter()
  const storeId = Number(router.params.id || router.params.store_id || 0)
  const [store, setStore] = useState<Store | null>(null)
  const [banners, setBanners] = useState<HomeBanner[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [zones, setZones] = useState<SpecialZone[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)

  useEffect(() => {
    if (!storeId) {
      Taro.showToast({ title: '店铺不存在', icon: 'none' })
      return
    }
    loadStoreDetail()
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

  const loadStoreDetail = async () => {
    setLoading(true)
    try {
      const detail = await storeService.getStoreDetail(storeId)
      setStore(detail.store)
      setBanners(detail.banners || [])
      setCategories(detail.categories || [])
      setZones(detail.special_zones || [])
      setProducts(detail.products || [])
      setPage(1)
      setHasMore((detail.products || []).length >= 20)
      Taro.setNavigationBarTitle({ title: detail.store.name })
    } catch (error) {
      Taro.showToast({ title: '加载店铺失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }

  const loadMoreProducts = async () => {
    if (loading || !hasMore) return
    setLoading(true)
    try {
      const nextPage = page + 1
      const res = await productService.getProducts({ store: storeId, page: nextPage, page_size: 20 })
      setProducts(prev => [...prev, ...res.results])
      setPage(nextPage)
      setHasMore(res.has_next || false)
    } catch (error) {
      Taro.showToast({ title: '加载商品失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }

  const goToZone = (zone: SpecialZone) => {
    Taro.navigateTo({ url: `/pages/special-zone/index?zone_id=${zone.id}&store_id=${storeId}` })
  }

  const goToCategory = (category: Category) => {
    Taro.navigateTo({
      url: `/pages/product-list/index?majorId=${category.id}&title=${encodeURIComponent(category.name)}&store=${storeId}`,
    })
  }

  const handleBannerClick = (banner: HomeBanner) => {
    if (banner.product_id) {
      Taro.navigateTo({ url: `/pages/product-detail/index?id=${banner.product_id}` })
    }
  }

  return (
    <View className='store-detail-page'>
      <ScrollView className='store-detail-scroll' scrollY onScrollToLower={loadMoreProducts}>
        {store && (
          <View className='store-hero'>
            {store.cover_image ? (
              <Image className='store-hero-image' src={resolveLocalMediaUrl(store.cover_image)} mode='aspectFill' />
            ) : (
              <View className='store-hero-fallback'>{store.name.charAt(0)}</View>
            )}
            <View className='store-hero-info'>
              {store.logo && <Image className='store-logo' src={resolveLocalMediaUrl(store.logo)} mode='aspectFill' />}
              <View className='store-copy'>
                <Text className='store-name'>{store.name}</Text>
                {!!store.description && <Text className='store-description'>{store.description}</Text>}
              </View>
            </View>
          </View>
        )}

        {banners.length > 0 && (
          <Swiper className='store-banner' autoplay circular indicatorDots>
            {banners.map(banner => (
              <SwiperItem key={banner.id} onClick={() => handleBannerClick(banner)}>
                <Image className='store-banner-image' src={resolveLocalMediaUrl(banner.image_url)} mode='aspectFill' />
              </SwiperItem>
            ))}
          </Swiper>
        )}

        {zones.length > 0 && (
          <View className='store-section'>
            <View className='section-title'>店铺专区</View>
            <View className='zone-grid'>
              {zones.map(zone => (
                <View key={zone.id} className='zone-card' onClick={() => goToZone(zone)}>
                  {zone.cover_image ? <Image className='zone-image' src={resolveLocalMediaUrl(zone.cover_image)} mode='aspectFill' /> : null}
                  <View className='zone-title'>{zone.title}</View>
                  {!!zone.subtitle && <View className='zone-subtitle'>{zone.subtitle}</View>}
                </View>
              ))}
            </View>
          </View>
        )}

        {categories.length > 0 && (
          <View className='store-section'>
            <View className='section-title'>店铺分类</View>
            <View className='category-row'>
              {categories.map(category => (
                <View key={category.id} className='category-pill' onClick={() => goToCategory(category)}>
                  {category.name}
                </View>
              ))}
            </View>
          </View>
        )}

        <View className='store-section product-section'>
          <View className='section-title'>店铺商品</View>
          <View className='product-list'>
            {products.map(product => <ProductCard key={product.id} product={product} />)}
          </View>
          {loading && <View className='status-text'>加载中...</View>}
          {!loading && products.length === 0 && <View className='status-text'>暂无商品</View>}
          {!loading && !hasMore && products.length > 0 && <View className='status-text'>没有更多商品了</View>}
        </View>
      </ScrollView>
    </View>
  )
}
