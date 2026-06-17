import { useState, useEffect } from 'react'
import { View, ScrollView } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { productService } from '../../services/product'
import { Product } from '../../types'
import EmptyState from '../../components/EmptyState'
import LoadingState from '../../components/LoadingState'
import ProductCard from '../../components/ProductCard'
import SearchBar from '../../components/SearchBar'
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

  return (
    <View className='search-page'>
      {/* 搜索栏 */}
      <View className='search-bar'>
        <SearchBar
          value={keyword}
          onInput={setKeyword}
          onConfirm={() => handleSearch()}
          buttonText='搜索'
          focus
        />
      </View>

      {/* 搜索结果 */}
      {keyword && (
        <ScrollView className='result-list' scrollY onScrollToLower={onLoadMore}>
          {products.length === 0 && !searching ? (
            <EmptyState title='未找到相关商品' description='换个关键词试试' icon='search' />
          ) : (
            <View className='product-list'>
              {products.map(product => (
                <ProductCard key={product.id} product={product} variant='list' />
              ))}
            </View>
          )}
          {searching && <LoadingState text='搜索中...' />}
          {!hasMore && products.length > 0 && <View className='loading-text'>没有更多了</View>}
        </ScrollView>
      )}
    </View>
  )
}
