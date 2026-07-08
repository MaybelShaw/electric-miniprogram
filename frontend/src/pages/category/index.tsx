import { useState, useEffect } from 'react'
import { View, ScrollView, Image } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { productService } from '../../services/product'
import { Category } from '../../types'
import { resolveLocalMediaUrl } from '../../utils/media'
import EmptyState from '../../components/EmptyState'
import LoadingState from '../../components/LoadingState'
import SearchBar from '../../components/SearchBar'
import AppIcon from '../../components/AppIcon'
import './index.scss'

export default function CategoryPage() {
  // 左侧大类
  const [majorCategories, setMajorCategories] = useState<Category[]>([])
  // 当前选中的大类ID
  const [activeMajorId, setActiveMajorId] = useState<number | null>(null)
  // 右侧子类（包含品项）
  const [subCategories, setSubCategories] = useState<Category[]>([])
  
  const [searchValue, setSearchValue] = useState('')
  const [loading, setLoading] = useState(false)
  // 待选中的分类名称（用于从首页跳转）
  const [pendingCategory, setPendingCategory] = useState<string | null>(null)

  // 初始化：加载大类
  useEffect(() => {
    loadMajorCategories()
    
    // 监听分类选择事件
    const handleSelectCategory = (categoryName: string) => {
      setPendingCategory(categoryName)
    }
    Taro.eventCenter.on('selectCategory', handleSelectCategory)
    
    return () => {
      Taro.eventCenter.off('selectCategory', handleSelectCategory)
    }
  }, [])

  // 处理待选中的分类
  useEffect(() => {
    if (pendingCategory && majorCategories.length > 0) {
      const target = majorCategories.find(c => c.name === pendingCategory)
      if (target) {
        setActiveMajorId(target.id)
        setPendingCategory(null)
      }
    }
  }, [pendingCategory, majorCategories])

  // 当选中的大类变化时，加载子类
  useEffect(() => {
    if (activeMajorId) {
      loadSubCategories(activeMajorId)
    } else if (majorCategories.length > 0) {
      // 默认选中第一个
      setActiveMajorId(majorCategories[0].id)
    }
  }, [activeMajorId, majorCategories])

  const loadMajorCategories = async () => {
    try {
      const data = await productService.getCategories({ level: 'major' })
      const allOption: Category = { id: -1, name: '全部商品', order: 0, level: 'major' }
      const categories = [allOption, ...data]
      setMajorCategories(categories)
      
      if (categories.length > 0) {
        // 默认选中第一个
        setActiveMajorId(categories[0].id)
      }
    } catch (error) {
      console.error('加载品类失败', error)
      Taro.showToast({ title: '加载品类失败', icon: 'none' })
    }
  }

  const loadSubCategories = async (parentId: number) => {
    setLoading(true)
    try {
      if (parentId === -1) {
        try {
          const [brands, minors] = await Promise.all([
            productService.getBrands(),
            productService.getCategories({ level: 'minor' })
          ])

          const brandsGroup: Category = {
            id: -200,
            name: '热门品牌',
            order: 1,
            children: brands.map(b => ({
              id: b.id,
              name: b.name,
              logo: b.logo,
              order: b.order,
              // @ts-ignore
              isBrand: true
            } as any))
          }

          const categoriesGroup: Category = {
            id: -300,
            name: '热门分类',
            order: 2,
            children: minors.map(c => ({
              ...c,
              // @ts-ignore
              isCategory: true
            }))
          }

          setSubCategories([brandsGroup, categoriesGroup])
        } catch (err) {
          console.error('Failed to load all products data', err)
          setSubCategories([])
        }
        return
      }

      // 获取该大类下的所有子类（包含品项）
      // 后端 get_children 会填充子类的 children 字段为品项列表
      const data = await productService.getCategories({ parent_id: parentId })
      setSubCategories(data)
    } catch (error) {
      console.error('加载子分类失败', error)
      Taro.showToast({ title: '加载子分类失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }

  const handleMajorClick = (id: number) => {
    if (id === activeMajorId) return
    setActiveMajorId(id)
  }

  const handleItemClick = (item: Category & { isBrand?: boolean, isCategory?: boolean }, minorId: number) => {
    if (item.isBrand) {
      Taro.navigateTo({
        url: `/pages/product-list/index?brand=${encodeURIComponent(item.name)}&title=${encodeURIComponent(item.name)}`
      })
      return
    }

    if (item.isCategory) {
      const majorId = item.parent_id || ''
      Taro.navigateTo({
        url: `/pages/product-list/index?majorId=${majorId}&minorId=${item.id}&title=${encodeURIComponent(item.name)}`
      })
      return
    }

    // 跳转到商品列表页，携带分类筛选
    const url = `/pages/product-list/index?majorId=${activeMajorId}&minorId=${minorId}&itemId=${item.id}&title=${encodeURIComponent(item.name)}`
    Taro.navigateTo({
      url: url,
      fail: (err) => {
          console.error('navigation failed', err)
          Taro.showToast({ title: `跳转失败: ${err.errMsg}`, icon: 'none', duration: 3000 })
      }
    })
  }
  
  const handleSearch = () => {
    const keyword = searchValue.trim()
    if (!keyword) return
    Taro.navigateTo({ url: `/pages/search/index?keyword=${encodeURIComponent(keyword)}` })
  }

  return (
    <View className='category-page'>
      {/* 搜索栏 */}
      <View className='search-bar'>
        <SearchBar value={searchValue} onInput={setSearchValue} onConfirm={handleSearch} />
      </View>

      <View className='category-content'>
        {/* 左侧分类栏 */}
        <ScrollView className='category-sidebar' scrollY>
          {majorCategories.map(category => (
            <View
              key={category.id}
              className={`category-item ${activeMajorId === category.id ? 'active' : ''}`}
              onClick={() => handleMajorClick(category.id)}
            >
              {category.name}
            </View>
          ))}
        </ScrollView>

        {/* 右侧内容区 */}
        <ScrollView className='sub-category-container' scrollY>
          {subCategories.length > 0 ? (
            subCategories.map(subCat => {
              return (
                <View key={subCat.id} className='sub-category-section'>
                  <View className='section-title'>{subCat.name}</View>
                  <View className='items-grid'>
                    {subCat.children && subCat.children.length > 0 ? (
                      subCat.children.map(item => (
                        <View 
                          key={item.id} 
                          className='category-item-node'
                          onClick={() => handleItemClick(item, subCat.id)}
                        >
                          {item.logo ? (
                            <Image
                              className='item-image'
                              src={resolveLocalMediaUrl(item.logo)}
                              mode='aspectFit'
                            />
                          ) : (
                            <View className='item-image item-image-placeholder'>
                              <AppIcon name='package' tone='muted' />
                            </View>
                          )}
                          <View className='item-name'>{item.name}</View>
                        </View>
                      ))
                    ) : (
                      <View className='empty-items'>
                        暂无品项
                      </View>
                    )}
                  </View>
                </View>
              )
            })
          ) : (
            !loading && (
              <View className='empty-state'>
                <EmptyState title='该分类下暂无子分类' icon='package' />
              </View>
            )
          )}
          {loading && <LoadingState text='加载中...' />}
        </ScrollView>
      </View>
    </View>
  )
}
