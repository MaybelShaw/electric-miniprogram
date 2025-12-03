import { useState, useEffect } from 'react'
import { View, ScrollView, Image, Input } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { productService } from '../../services/product'
import { Category } from '../../types'
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

  // 初始化：加载大类
  useEffect(() => {
    loadMajorCategories()
  }, [])

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
      setMajorCategories(data)
      if (data.length > 0) {
        // 默认选中第一个
        setActiveMajorId(data[0].id)
      }
    } catch (error) {
      console.error('加载品类失败', error)
      Taro.showToast({ title: '加载品类失败', icon: 'none' })
    }
  }

  const loadSubCategories = async (parentId: number) => {
    setLoading(true)
    try {
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

  const handleItemClick = (item: Category, minorId: number) => {
    console.log('handleItemClick', item, minorId)
    // 跳转到商品列表页，携带分类筛选
    const url = `/pages/product-list/index?majorId=${activeMajorId}&minorId=${minorId}&itemId=${item.id}&title=${encodeURIComponent(item.name)}`
    console.log('navigating to', url)
    Taro.navigateTo({
      url: url,
      fail: (err) => {
          console.error('navigation failed', err)
          Taro.showToast({ title: `跳转失败: ${err.errMsg}`, icon: 'none', duration: 3000 })
      }
    })
  }
  
  const handleSearch = () => {
    if (!searchValue.trim()) return
    Taro.navigateTo({ url: `/pages/search/index?keyword=${searchValue}` })
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
            subCategories.map(subCat => (
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
                        <Image 
                          className='item-image' 
                          src={item.logo || 'https://placeholder.com/120'} 
                          mode='aspectFit'
                        />
                        <View className='item-name'>{item.name}</View>
                      </View>
                    ))
                  ) : (
                    <View className='empty-items' style={{gridColumn: '1 / -1', textAlign: 'center', color: '#999', fontSize: '24px', padding: '20px 0'}}>
                      暂无品项
                    </View>
                  )}
                </View>
              </View>
            ))
          ) : (
            !loading && (
              <View className='empty-state'>
                该分类下暂无子分类
              </View>
            )
          )}
          {loading && <View style={{textAlign: 'center', padding: '20px', color: '#999'}}>加载中...</View>}
        </ScrollView>
      </View>
    </View>
  )
}
