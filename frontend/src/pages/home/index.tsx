import { useState, useEffect } from 'react'
import { View, Swiper, SwiperItem, Image, ScrollView, Input, Text } from '@tarojs/components'
import Taro, { useShareAppMessage, useShareTimeline } from '@tarojs/taro'
import { productService } from '../../services/product'
import { specialZoneCoverService } from '../../services/special-zone-cover'
import { Product, Category, Brand, HomeBanner, SpecialZoneCover } from '../../types'
import { Storage, CACHE_KEYS } from '../../utils/storage'
import ProductCard from '../../components/ProductCard'
import { withPrivacyCheck } from '../../components/withPrivacyCheck'
import './index.scss'

function Home() {
  const [searchValue, setSearchValue] = useState('')
  const [majorCategories, setMajorCategories] = useState<Category[]>([])
  const [brands, setBrands] = useState<Brand[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [banners, setBanners] = useState<HomeBanner[]>([])
  const [giftZoneCover, setGiftZoneCover] = useState<SpecialZoneCover | null>(null)
  const [designerZoneCover, setDesignerZoneCover] = useState<SpecialZoneCover | null>(null)
  const [bestSellerZoneCover, setBestSellerZoneCover] = useState<SpecialZoneCover | null>(null)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadBanners()
    loadSpecialZones()
    loadCategories()
    loadBrands()
    loadProducts(1)
    
    // 确保显示分享菜单
    Taro.showShareMenu({
      withShareTicket: true
    })
  }, [])

  useShareAppMessage(() => ({
    title: '庆勋愉悦家',
    path: '/pages/home/index',
    ...(banners[0]?.image_url ? { imageUrl: banners[0].image_url } : {}),
  }))

  useShareTimeline(() => ({
    title: '庆勋愉悦家',
    ...(banners[0]?.image_url ? { imageUrl: banners[0].image_url } : {}),
  }))

  // 加载轮播图
  const loadBanners = async () => {
    try {
      const data = await productService.getHomeBanners('home')
      setBanners(data)
    } catch (error) {
      // 静默失败
    }
  }

  // 加载专区图片
  const loadSpecialZones = async () => {
    try {
      const [gift, designer, bestSeller] = await Promise.all([
        specialZoneCoverService.getCovers({ type: 'gift' }),
        specialZoneCoverService.getCovers({ type: 'designer' }),
        specialZoneCoverService.getCovers({ type: 'best_seller' }),
      ])
      setGiftZoneCover(gift[0] || null)
      setDesignerZoneCover(designer[0] || null)
      setBestSellerZoneCover(bestSeller[0] || null)
    } catch (error) {
      // 静默失败
    }
  }

  // 加载分类
  const loadCategories = async () => {
    try {
      // 加载空间 (Major Categories)
      const cachedMajor = Storage.get<Category[]>(CACHE_KEYS.MAJOR_CATEGORIES)
      if (cachedMajor) {
        setMajorCategories(cachedMajor)
      } else {
        const data = await productService.getCategories({ level: 'major' })
        setMajorCategories(data)
        Storage.set(CACHE_KEYS.MAJOR_CATEGORIES, data, 24 * 60 * 60 * 1000)
      }
    } catch (error) {
      // 静默失败
    }
  }

  // 加载品牌
  const loadBrands = async () => {
    try {
      const cached = Storage.get<Brand[]>(CACHE_KEYS.BRANDS)
      if (cached) {
        setBrands(cached)
        return
      }
      
      const data = await productService.getBrands()
      setBrands(data)
      Storage.set(CACHE_KEYS.BRANDS, data, 24 * 60 * 60 * 1000)
    } catch (error) {
      // 静默失败
    }
  }

  // 加载商品列表
  const loadProducts = async (pageNum: number) => {
    if (loading) return
    
    setLoading(true)
    try {
      const params = { page: pageNum, page_size: 20 }
      const res = await productService.getProducts(params)
      
      if (pageNum === 1) {
        setProducts(res.results)
      } else {
        setProducts([...products, ...res.results])
      }
      setHasMore(res.has_next || false)
      setPage(pageNum)
    } catch (error) {
      Taro.showToast({
        title: '加载商品失败',
        icon: 'none'
      })
    } finally {
      setLoading(false)
    }
  }

  // 下拉刷新
  const onRefresh = () => {
    loadProducts(1)
  }

  // 上拉加载更多
  const onLoadMore = () => {
    if (hasMore && !loading) {
      loadProducts(page + 1)
    }
  }

  // 搜索
  const handleSearch = () => {
    if (!searchValue.trim()) return
    Taro.navigateTo({ url: `/pages/search/index?keyword=${searchValue}` })
  }

  // 跳转分类
  const goToCategory = (category: string) => {
    Taro.switchTab({ url: '/pages/category/index' })
    // 通过事件总线传递分类参数
    Taro.eventCenter.trigger('selectCategory', category)
  }

  // 跳转品牌
  const goToBrand = (brand: string) => {
    Taro.navigateTo({ url: `/pages/brand/index?brand=${brand}` })
  }

  const handleBannerClick = (banner: HomeBanner) => {
    if (banner.product_id) {
      Taro.navigateTo({ url: `/pages/product-detail/index?id=${banner.product_id}` })
    }
  }

  // 跳转专区
  const goToSpecialZone = (type: 'gift' | 'designer' | 'best_seller', title: string) => {
    Taro.navigateTo({ url: `/pages/special-zone/index?type=${type}&title=${encodeURIComponent(title)}` })
  }

  const handleZoneClick = (type: 'gift' | 'designer' | 'best_seller') => {
    let title = ''
    switch (type) {
      case 'gift':
        title = '礼品专区'
        break
      case 'designer':
        title = '设计师专区'
        break
      case 'best_seller':
        title = '爆品专区'
        break
    }
    goToSpecialZone(type, title)
  }

  // 查看全部品类
  const goToAllCategories = () => {
    Taro.switchTab({ url: '/pages/category/index' })
  }

  // 查看全部品牌
  const goToAllBrands = () => {
    Taro.navigateTo({ url: '/pages/brand-list/index' })
  }

  return (
    <View className="home">
      {/* Search Bar */}
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
        refresherTriggered={loading && page === 1}
        onRefresherRefresh={onRefresh}
        onScrollToLower={onLoadMore}
      >
        {/* 轮播图 */}
        <Swiper className='banner' autoplay circular indicatorDots>
          {banners.map(banner => (
            <SwiperItem key={banner.id} onClick={() => handleBannerClick(banner)}>
              <Image className='banner-image' src={banner.image_url} mode='aspectFill' />
            </SwiperItem>
          ))}
        </Swiper>

        {/* 特色专区 */}
        <View className='special-zones'>
          <View className='zone-item gift-zone' onClick={() => handleZoneClick('gift')}>
            {giftZoneCover?.image_url && (
              <Image className='zone-image' src={giftZoneCover.image_url} mode='aspectFill' />
            )}
          </View>
          <View className='zone-item designer-zone' onClick={() => handleZoneClick('designer')}>
            {designerZoneCover?.image_url && (
              <Image className='zone-image' src={designerZoneCover.image_url} mode='aspectFill' />
            )}
          </View>
        </View>

        {/* 爆品专区 (单独一行) */}
        <View className='special-zones'>
          <View className='zone-item best-seller-zone' onClick={() => handleZoneClick('best_seller')}>
            {bestSellerZoneCover?.image_url && (
              <Image className='zone-image' src={bestSellerZoneCover.image_url} mode='widthFix' />
            )}
          </View>
        </View>

        {/* 品类专区 (原空间专区) */}
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
                    <Image className='category-icon-img' src={cat.logo} mode='aspectFill' />
                  ) : (
                    <View className='category-icon'>{cat.name.charAt(0)}</View>
                  )}
                  <View className='category-name'>{cat.name}</View>
                </View>
              ))}
            </View>
          </View>
        )}

        {/* 品牌专区 */}
        {brands.length > 0 && (
          <View className='brand-section'>
            <View className='section-header-row'>
              <View className='section-title'>品牌专区</View>
              <View className='more-btn' onClick={goToAllBrands}>更多 {'>'}</View>
            </View>
            <View className='brand-grid'>
              {brands.slice(0, 4).map(brand => (
                <View key={brand.id} className='brand-item' onClick={() => goToBrand(brand.name)}>
                  <Image className='brand-logo' src={brand.logo} mode='aspectFit' />
                  <View className='brand-name'>{brand.name}</View>
                </View>
              ))}
            </View>
          </View>
        )}

        {/* 商品列表 */}
        <View className='product-section'>
          <View className='section-header'>
            <View className='section-title'>全部商品</View>
          </View>
          <View className='product-list'>
            {products.map(product => (
              <ProductCard
                key={product.id}
                product={product}
              />
            ))}
          </View>
          
          {/* 加载状态 */}
          {loading && (
            <View className='loading-wrapper'>
              <View className='loading-spinner'></View>
              <Text className='loading-text'>加载中...</Text>
            </View>
          )}
          
          {/* 没有更多 */}
          {!hasMore && products.length > 0 && (
            <View className='no-more'>
              <View className='no-more-line'></View>
              <Text className='no-more-text'>没有更多商品了</Text>
              <View className='no-more-line'></View>
            </View>
          )}
          
          {/* 空状态 */}
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
