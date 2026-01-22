import { useState, useEffect } from 'react'
import { View, Input, ScrollView, Image, Text } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { productService } from '../../services/product'
import { Product } from '../../types'
import './index.scss'

export default function Search() {
  const [keyword, setKeyword] = useState('')
  const [products, setProducts] = useState<Product[]>([])
  const [searching, setSearching] = useState(false)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)

  useEffect(() => {
    const instance = Taro.getCurrentInstance()
    const kw = instance.router?.params?.keyword
    if (kw) {
      setKeyword(kw)
      handleSearch(kw)
    }
  }, [])

  const handleSearch = async (kw?: string, pageNum = 1) => {
    const searchKeyword = kw || keyword
    if (!searchKeyword.trim()) {
      Taro.showToast({ title: '请输入搜索关键词', icon: 'none' })
      return
    }

    setSearching(true)
    try {
      const res = await productService.getProducts({
        search: searchKeyword,
        page: pageNum,
        page_size: 20
      })
      
      if (pageNum === 1) {
        setProducts(res.results)
      } else {
        setProducts([...products, ...res.results])
      }
      setHasMore(res.has_next || false)
      setPage(pageNum)
    } catch (error) {
      Taro.showToast({ title: '搜索失败', icon: 'none' })
    } finally {
      setSearching(false)
    }
  }

  const onLoadMore = () => {
    if (hasMore && !searching && keyword) {
      handleSearch(keyword, page + 1)
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
    <View className='search-page'>
      {/* 搜索栏 */}
      <View className='search-bar'>
        <View className='search-input'>
          <Image className='search-icon' src='/assets/search.png' />
          <Input
            className='input'
            placeholder='搜索商品'
            value={keyword}
            onInput={(e) => setKeyword(e.detail.value)}
            onConfirm={() => handleSearch()}
            focus
          />
        </View>
        <View className='search-btn' onClick={() => handleSearch()}>搜索</View>
      </View>

      {/* 搜索结果 */}
      {keyword && (
        <ScrollView className='result-list' scrollY onScrollToLower={onLoadMore}>
          {products.length === 0 && !searching ? (
            <View className='empty'>
              <Image className='empty-icon' src='/assets/empty-search.png' />
              <Text className='empty-text'>未找到相关商品</Text>
            </View>
          ) : (
            <View className='product-list'>
              {products.map(product => (
                <View key={product.id} className='product-item' onClick={() => goToDetail(product.id)}>
                  <Image className='product-image' src={product.main_images[0]} mode='aspectFill' />
                  <View className='product-info'>
                    <View className='product-name'>{product.name}</View>
                    <View className='product-brand'>{product.brand}</View>
                    <View className='product-bottom'>
                      <View className='product-price'>{Number(getSellingPrice(product)).toFixed(2)}</View>
                      <View className='product-sales'>销量 {product.sales_count}</View>
                    </View>
                  </View>
                </View>
              ))}
            </View>
          )}
          {searching && <View className='loading-text'>搜索中...</View>}
          {!hasMore && products.length > 0 && <View className='loading-text'>没有更多了</View>}
        </ScrollView>
      )}
    </View>
  )
}
