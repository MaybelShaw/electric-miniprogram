import { useState, useEffect } from 'react'
import { View, Swiper, SwiperItem, Image, ScrollView, Input, Text } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { productService } from '../../services/product'
import { Product, Category, Brand, HomeBanner } from '../../types'
import { Storage, CACHE_KEYS } from '../../utils/storage'
import ProductCard from '../../components/ProductCard'
import './index.scss'

export default function Home() {
  const [searchValue, setSearchValue] = useState('')
  const [majorCategories, setMajorCategories] = useState<Category[]>([])
  const [brands, setBrands] = useState<Brand[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [banners, setBanners] = useState<HomeBanner[]>([])
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadBanners()
    loadCategories()
    loadBrands()
    loadProducts(1)
  }, [])

  // 加载轮播图
  const loadBanners = async () => {
    try {
      const data = await productService.getHomeBanners()
      setBanners(data)
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

  return (
    <View className='home'>
      {/* 搜索栏 */}
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
            <SwiperItem key={banner.id} onClick={() => {
              if (banner.link_url) {
                // 判断是否是 tab 页面
                const isTab = ['/pages/home/index', '/pages/category/index', '/pages/cart/index', '/pages/profile/index'].some(path => banner.link_url.includes(path))
                if (isTab) {
                  Taro.switchTab({ url: banner.link_url })
                } else {
                  Taro.navigateTo({ url: banner.link_url })
                }
              }
            }}>
              <Image className='banner-image' src={banner.image_url} mode='aspectFill' />
            </SwiperItem>
          ))}
        </Swiper>

        {/* 品类专区 (原空间专区) */}
        {majorCategories.length > 0 && (
          <View className='category-nav'>
            <View className='category-title'>品类专区</View>
            <ScrollView scrollX className='category-scroll'>
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
            </ScrollView>
          </View>
        )}

        {/* 品牌专区 */}
        {brands.length > 0 && (
          <View className='brand-section'>
            <View className='section-title'>品牌专区</View>
            <ScrollView scrollX className='brand-scroll'>
              {brands.map(brand => (
                <View key={brand.id} className='brand-item' onClick={() => goToBrand(brand.name)}>
                  <Image className='brand-logo' src={brand.logo} mode='aspectFit' />
                  <View className='brand-name'>{brand.name}</View>
                </View>
              ))}
            </ScrollView>
          </View>
        )}

        {/* 商品列表 */}
        <View className='product-section'>
          <View className='section-header'>
            <View className='section-title'>全部商品</View>
            <View className='section-subtitle'>{products.length} 件商品</View>
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
