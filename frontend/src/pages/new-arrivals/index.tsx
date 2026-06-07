import { useEffect, useState } from 'react'
import { View, ScrollView, Image, Swiper, SwiperItem, Text } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import ProductCard from '../../components/ProductCard'
import AppIcon from '../../components/AppIcon'
import { storeService } from '../../services/store'
import { HomeBanner, Product, Store } from '../../types'
import { resolveLocalMediaUrl } from '../../utils/media'
import './index.scss'

const CURRENT_STORE_ID_KEY = 'current_store_id'
const CURRENT_STORE_NAME_KEY = 'current_store_name'

export default function NewArrivalsPage() {
  const [storeId, setStoreId] = useState<number | null>(null)
  const [storeName, setStoreName] = useState('')
  const [store, setStore] = useState<Store | null>(null)
  const [banners, setBanners] = useState<HomeBanner[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    Taro.setNavigationBarTitle({ title: '新品上新' })
  }, [])

  useDidShow(() => {
    const rememberedStoreId = Number(Taro.getStorageSync(CURRENT_STORE_ID_KEY) || 0) || null
    const rememberedStoreName = Taro.getStorageSync(CURRENT_STORE_NAME_KEY) || ''
    setStoreId(rememberedStoreId)
    setStoreName(rememberedStoreName)

    if (rememberedStoreId) {
      loadNewArrivals(rememberedStoreId)
    } else {
      setStore(null)
      setBanners([])
      setProducts([])
    }
  })

  const loadNewArrivals = async (id: number) => {
    setLoading(true)
    try {
      const detail = await storeService.getStoreDetail(id)
      setStore(detail.store)
      setStoreName(detail.store.name)
      setBanners((detail.banners || []).filter(banner => resolveLocalMediaUrl(banner.image_url)))
      setProducts(detail.new_arrivals || [])
    } catch {
      Taro.showToast({ title: '加载新品失败', icon: 'none' })
      setStore(null)
      setBanners([])
      setProducts([])
    } finally {
      setLoading(false)
    }
  }

  const goToStoreList = () => {
    Taro.navigateTo({ url: '/pages/store-list/index' })
  }

  const goToStoreHome = () => {
    if (!storeId) return
    Taro.navigateTo({ url: `/pages/store-detail/index?id=${storeId}` })
  }

  const handleBannerClick = (banner: HomeBanner) => {
    if (banner.product_id) {
      Taro.navigateTo({ url: `/pages/product-detail/index?id=${banner.product_id}` })
      return
    }
    if (banner.special_zone_id) {
      Taro.navigateTo({ url: `/pages/special-zone/index?zone_id=${banner.special_zone_id}&store_id=${storeId}` })
    }
  }

  if (!storeId) {
    return (
      <View className='new-arrivals-page'>
        <View className='empty-state'>
          <AppIcon name='store' tone='muted' />
          <Text className='empty-title'>请选择店铺</Text>
          <Text className='empty-desc'>新品上新按当前店铺展示，不展示平台混合数据。</Text>
          <View className='empty-action' onClick={goToStoreList}>去选择店铺</View>
        </View>
      </View>
    )
  }

  return (
    <View className='new-arrivals-page'>
      <ScrollView className='new-arrivals-scroll' scrollY>
        <View className='store-strip' onClick={goToStoreHome}>
          {resolveLocalMediaUrl(store?.logo) ? (
            <Image className='store-logo' src={resolveLocalMediaUrl(store?.logo)} mode='aspectFit' />
          ) : (
            <View className='store-logo store-logo--fallback'>
              <AppIcon name='store' tone='gold' />
            </View>
          )}
          <View className='store-copy'>
            <Text className='store-kicker'>当前店铺</Text>
            <Text className='store-name'>{store?.name || storeName}</Text>
          </View>
        </View>

        {banners.length > 0 && (
          <Swiper className='arrival-swiper' autoplay circular indicatorDots>
            {banners.map(banner => (
              <SwiperItem key={banner.id}>
                <View className='arrival-banner' onClick={() => handleBannerClick(banner)}>
                  <Image className='arrival-banner-image' src={resolveLocalMediaUrl(banner.image_url)} mode='aspectFill' />
                  {!!banner.title && <Text className='arrival-banner-title'>{banner.title}</Text>}
                </View>
              </SwiperItem>
            ))}
          </Swiper>
        )}

        <View className='section-header'>
          <Text className='section-kicker'>新品上新</Text>
          <Text className='section-title'>图片和新品商品</Text>
        </View>

        <View className='product-grid'>
          {products.map(product => (
            <ProductCard key={product.id} product={product} />
          ))}
        </View>

        {loading && <Text className='status-text'>加载中...</Text>}
        {!loading && products.length === 0 && <Text className='status-text'>当前店铺暂无新品</Text>}
      </ScrollView>
    </View>
  )
}
