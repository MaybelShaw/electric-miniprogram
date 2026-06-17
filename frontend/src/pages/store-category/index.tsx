import { useEffect, useState } from 'react'
import { View, ScrollView, Image, Text } from '@tarojs/components'
import Taro, { useRouter, useShareAppMessage, useShareTimeline } from '@tarojs/taro'
import ProductCard from '../../components/ProductCard'
import AppIcon from '../../components/AppIcon'
import StoreBottomNav from '../../components/StoreBottomNav'
import { productService } from '../../services/product'
import { storeService } from '../../services/store'
import { Brand, Product, Store } from '../../types'
import { resolveLocalMediaUrl } from '../../utils/media'
import './index.scss'

export default function StoreCategoryPage() {
  const router = useRouter()
  const storeId = Number(router.params.store_id || router.params.store || 0)
  const categoryId = Number(router.params.category_id || 0)
  const routeCategoryName = decodeURIComponent(router.params.category_name || '产品类别')

  const [store, setStore] = useState<Store | null>(null)
  const [brands, setBrands] = useState<Brand[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [selectedBrandName, setSelectedBrandName] = useState('')
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)

  useEffect(() => {
    if (!storeId || !categoryId) {
      Taro.showToast({ title: '类别不存在', icon: 'none' })
      return
    }

    Taro.setNavigationBarTitle({ title: routeCategoryName })
    Taro.showShareMenu({ withShareTicket: true })
    loadCategoryDetail()
  }, [storeId, categoryId])

  useShareAppMessage(() => ({
    title: `${store?.name || '店铺'} - ${routeCategoryName}`,
    path: `/pages/store-category/index?store_id=${storeId}&category_id=${categoryId}&category_name=${encodeURIComponent(routeCategoryName)}`,
  }))

  useShareTimeline(() => ({
    title: `${store?.name || '店铺'} - ${routeCategoryName}`,
    query: `store_id=${storeId}&category_id=${categoryId}&category_name=${encodeURIComponent(routeCategoryName)}`,
  }))

  const loadCategoryDetail = async () => {
    setLoading(true)
    try {
      const detail = await storeService.getStoreDetail(storeId, { category_id: categoryId })
      if (detail.store.is_main) {
        Taro.switchTab({ url: '/pages/home/index' })
        return
      }

      setStore(detail.store)
      setBrands(detail.brands || [])
      setProducts(detail.products || [])
      setSelectedBrandName('')
      setPage(1)
      setHasMore(false)
    } catch {
      Taro.showToast({ title: '加载类别失败', icon: 'none' })
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
        category_id: categoryId,
        page: pageNum,
        page_size: 20,
      })

      setProducts(prev => (pageNum === 1 ? res.results : [...prev, ...res.results]))
      setSelectedBrandName(brandName)
      setPage(pageNum)
      setHasMore(res.has_next || false)
    } catch {
      Taro.showToast({ title: '加载品牌失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }

  const handleBrandClick = async (brand: Brand) => {
    if (loading) return

    if (selectedBrandName === brand.name) {
      await loadCategoryDetail()
      return
    }

    await loadBrandProducts(brand.name)
  }

  const loadMoreProducts = async () => {
    if (loading || !hasMore || !selectedBrandName) return
    await loadBrandProducts(selectedBrandName, page + 1)
  }

  return (
    <View className='store-category-page'>
      <ScrollView className='store-category-scroll' scrollY onScrollToLower={loadMoreProducts}>
        <View className='category-hero'>
          <View className='category-hero-main'>
            <Text className='category-kicker'>{store?.name || '店铺类别'}</Text>
            <Text className='category-title'>{routeCategoryName}</Text>
          </View>
        </View>

        <View className='store-category-section'>
          <View className='section-header'>
            <View>
              <Text className='section-kicker'>品牌分类</Text>
            </View>
          </View>

          {brands.length > 0 ? (
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
                      {brand.description ? <Text className='brand-copy'>{brand.description}</Text> : null}
                    </View>
                  )
                })}
              </View>
            </ScrollView>
          ) : (
            <View className='status-text'>暂无品牌</View>
          )}
        </View>

        <View className='store-category-section product-section'>
          <View className='section-header'>
            <View>
              <Text className='section-kicker'>商品列表</Text>
              <Text className='section-title'>{selectedBrandName || routeCategoryName}</Text>
            </View>
          </View>
          <View className='product-list'>
            {products.map(product => (
              <ProductCard key={product.id} product={product} />
            ))}
          </View>
          {loading && <View className='status-text'>加载中...</View>}
          {!loading && products.length === 0 && <View className='status-text'>暂无商品</View>}
          {!loading && !hasMore && products.length > 0 && <View className='status-text'>没有更多商品了</View>}
        </View>
      </ScrollView>
      <StoreBottomNav storeId={storeId} storeIsMain={store?.is_main} active='category' />
    </View>
  )
}
