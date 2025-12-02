import { useState, useEffect } from 'react'
import { View, ScrollView, Image, Input } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { productService } from '../../services/product'
import { Product, Category } from '../../types'
import { formatPrice } from '../../utils/format'
import './index.scss'

export default function CategoryPage() {
  const [categories, setCategories] = useState<Category[]>([])
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [products, setProducts] = useState<Product[]>([])
  const [searchValue, setSearchValue] = useState('')
  const [sortBy, setSortBy] = useState<string>('relevance')
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadCategories()
    
    // 监听从首页传来的分类选择
    const handleSelectCategory = (category: string) => {
      setSelectedCategory(category)
    }
    Taro.eventCenter.on('selectCategory', handleSelectCategory)
    
    return () => {
      Taro.eventCenter.off('selectCategory', handleSelectCategory)
    }
  }, [])

  useEffect(() => {
    if (selectedCategory) {
      loadProducts(1)
    }
  }, [selectedCategory, sortBy])

  const loadCategories = async () => {
    try {
      const data = await productService.getCategories()
      setCategories([{ id: 0, name: '全部', order: 0 }, ...data])
      if (data.length > 0 && !selectedCategory) {
        setSelectedCategory('全部')
      }
    } catch (error) {
      // 静默失败
    }
  }

  const loadProducts = async (pageNum: number) => {
    if (loading) return
    
    setLoading(true)
    try {
      const params: any = {
        page: pageNum,
        page_size: 20,
        sort_by: sortBy
      }
      
      let res
      if (selectedCategory === '全部') {
        res = await productService.getProducts(params)
      } else {
        params.category = selectedCategory
        res = await productService.getProductsByCategory(params)
      }
      
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

  const handleCategoryChange = (category: string) => {
    setSelectedCategory(category)
    setPage(1)
  }

  const handleSearch = () => {
    if (!searchValue.trim()) return
    Taro.navigateTo({ url: `/pages/search/index?keyword=${searchValue}` })
  }

  const handleSortChange = (sort: string) => {
    setSortBy(sort)
    setPage(1)
  }

  const onLoadMore = () => {
    if (hasMore && !loading) {
      loadProducts(page + 1)
    }
  }

  const goToDetail = (id: number) => {
    Taro.navigateTo({ url: `/pages/product-detail/index?id=${id}` })
  }

  return (
    <View className='category-page'>
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

      <View className='category-content'>
        {/* 左侧分类 */}
        <ScrollView className='category-sidebar' scrollY>
          {categories.map(cat => (
            <View
              key={cat.id}
              className={`category-item ${selectedCategory === cat.name ? 'active' : ''}`}
              onClick={() => handleCategoryChange(cat.name)}
            >
              {cat.name}
            </View>
          ))}
        </ScrollView>

        {/* 右侧商品列表 */}
        <View className='product-container'>
        {/* 排序栏 */}
        <View className='sort-bar'>
          <View
            className={`sort-item ${sortBy === 'relevance' ? 'active' : ''}`}
            onClick={() => handleSortChange('relevance')}
          >
            综合
          </View>
          <View
            className={`sort-item ${sortBy === 'sales' ? 'active' : ''}`}
            onClick={() => handleSortChange('sales')}
          >
            销量
          </View>
          <View
            className={`sort-item ${sortBy === 'price_asc' ? 'active' : ''}`}
            onClick={() => handleSortChange('price_asc')}
          >
            价格↑
          </View>
          <View
            className={`sort-item ${sortBy === 'price_desc' ? 'active' : ''}`}
            onClick={() => handleSortChange('price_desc')}
          >
            价格↓
          </View>
        </View>

        {/* 商品列表 */}
        <ScrollView className='product-scroll' scrollY onScrollToLower={onLoadMore}>
          <View className='product-list'>
            {products.map(product => (
              <View key={product.id} className='product-item' onClick={() => goToDetail(product.id)}>
                <Image className='product-image' src={product.main_images[0]} mode='aspectFill' />
                <View className='product-info'>
                  <View className='product-name'>{product.name}</View>
                  <View className='product-brand'>{product.brand}</View>
                  <View className='product-bottom'>
                    <View className='product-price'>{formatPrice(product.price)}</View>
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
      </View>
    </View>
  )
}
