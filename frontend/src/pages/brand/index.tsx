import { useState, useEffect } from 'react'
import { View, ScrollView, Image } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { productService } from '../../services/product'
import { Product } from '../../types'
import './index.scss'

export default function BrandPage() {
  const [brand, setBrand] = useState('')
  const [products, setProducts] = useState<Product[]>([])
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const instance = Taro.getCurrentInstance()
    const brandName = instance.router?.params?.brand
    if (brandName) {
      setBrand(brandName)
      Taro.setNavigationBarTitle({ title: brandName })
      loadProducts(brandName, 1)
    }
  }, [])

  const loadProducts = async (brandName: string, pageNum: number) => {
    if (loading) return

    setLoading(true)
    try {
      const res = await productService.getProductsByBrand({ brand: brandName, page: pageNum, page_size: 20 })
      if (pageNum === 1) {
        setProducts(res.results)
      } else {
        setProducts([...products, ...res.results])
      }
      setHasMore(res.has_next || false)
      setPage(pageNum)
    } catch (error) {
      Taro.showToast({ title: '加载失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }

  const onLoadMore = () => {
    if (hasMore && !loading && brand) {
      loadProducts(brand, page + 1)
    }
  }

  const goToDetail = (id: number) => {
    Taro.navigateTo({ url: `/pages/product-detail/index?id=${id}` })
  }

  const getSellingPrice = (product: Product) => {
    const basePrice = Number(product.display_price ?? product.price ?? 0)
    return product.discounted_price && Number(product.discounted_price) < basePrice
      ? Number(product.discounted_price)
      : basePrice
  }

  return (
    <View className='brand-page'>
      <ScrollView className='product-scroll' scrollY onScrollToLower={onLoadMore}>
        <View className='product-list'>
          {products.map(product => (
            <View key={product.id} className='product-item' onClick={() => goToDetail(product.id)}>
              <Image className='product-image' src={product.main_images[0]} mode='aspectFill' />
              <View className='product-info'>
                <View className='product-name'>{product.name}</View>
                <View className='product-bottom'>
                  <View className='product-price'>{Number(getSellingPrice(product)).toFixed(2)}</View>
                  <View className='product-sales'>销量 {product.sales_count}</View>
                </View>
              </View>
            </View>
          ))}
        </View>
        {loading && <View className='loading-text'>加载中...</View>}
        {!hasMore && products.length > 0 && <View className='loading-text'>没有更多了</View>}
      </ScrollView>
    </View>
  )
}
