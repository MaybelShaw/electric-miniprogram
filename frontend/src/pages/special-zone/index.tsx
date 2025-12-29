import { useState, useEffect } from 'react'
import { View, Text, Image, Swiper, SwiperItem, ScrollView } from '@tarojs/components'
import Taro, { useRouter } from '@tarojs/taro'
import { productService } from '../../services/product'
import { caseService } from '../../services/case'
import { Product, Case, HomeBanner } from '../../types'
import ProductCard from '../../components/ProductCard'
import './index.scss'

export default function SpecialZone() {
  const router = useRouter()
  const { type = 'gift', title = '专区' } = router.params
  
  const [products, setProducts] = useState<Product[]>([])
  const [cases, setCases] = useState<Case[]>([])
  const [banners, setBanners] = useState<HomeBanner[]>([])
  const [loading, setLoading] = useState(false)
  
  useEffect(() => {
    Taro.setNavigationBarTitle({ title: decodeURIComponent(title) })
    loadBanners()
    loadProducts()
    if (type === 'designer') {
      loadCases()
    }
  }, [type])

  const loadBanners = async () => {
    try {
        const res = await productService.getHomeBanners(type as 'gift' | 'designer')
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

  const loadProducts = async () => {
    setLoading(true)
    try {
      // In a real app, we might filter by category or tag corresponding to the zone type
      // For now, we'll just fetch products and maybe slice them or show all
      // If backend supported search by tag: await productService.getProducts({ search: type })
      const res = await productService.getProducts({ page: 1, page_size: 20 })
      setProducts(res.results)
    } catch (error) {
      Taro.showToast({ title: '加载商品失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }

  const goToCaseDetail = (id: number) => {
    Taro.navigateTo({ url: `/pages/case-detail/index?id=${id}` })
  }

  const handleBannerClick = (banner: HomeBanner) => {
    if (banner.link_url) {
        // 判断是否是内部页面
        if (banner.link_url.startsWith('/')) {
            Taro.navigateTo({ url: banner.link_url })
        } else {
            // 外部链接可能需要 webview 或复制链接
            // 这里简单处理为不做操作或后续扩展
        }
    }
  }

  return (
    <View className='special-zone'>
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
      {type === 'designer' && cases.length > 0 && (
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
        <View className='section-title'>产品展示</View>
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
    </View>
  )
}
