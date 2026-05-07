import { useState, useEffect } from 'react'
import { View, ScrollView, Image, Input } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { productService } from '../../services/product'
import { Category } from '../../types'
import { resolveLocalMediaUrl } from '../../utils/media'
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
      // 添加"全部商品"选项
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
        // 加载全部商品页面的特殊数据：热门品牌、热门分类
        try {
          const [brands, minors] = await Promise.all([
            productService.getBrands(),
            productService.getCategories({ level: 'minor' })
          ])

          const allProductsGroup: Category = {
            id: -100,
            name: '所有商品',
            order: 0,
            children: [{
              id: -1,
              name: '全部商品',
              order: 0,
              logo: ''
            }]
          }

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

          // 过滤掉"全部商品"本身，只显示真实的分类
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

          setSubCategories([allProductsGroup, brandsGroup, categoriesGroup])
        } catch (err) {
          console.error('Failed to load all products data', err)
          // Fallback
          setSubCategories([{
            id: -100,
            name: '全部',
            order: 0,
            children: [{
              id: -1,
              name: '全部商品',
              order: 0,
              logo: ''
            }]
          }])
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
    console.log('handleItemClick', item, minorId)
    
    // 处理"全部商品"点击
    if (item.id === -1) {
      Taro.navigateTo({
        url: '/pages/product-list/index?title=全部商品'
      })
      return
    }

    // 处理品牌点击
    if (item.isBrand) {
      Taro.navigateTo({
        url: `/pages/product-list/index?brand=${encodeURIComponent(item.name)}&title=${encodeURIComponent(item.name)}`
      })
      return
    }

    // 处理热门分类点击 (二级分类)
    if (item.isCategory) {
      // 如果点击的是热门分类中的二级分类，跳转到商品列表并筛选该二级分类
      // 需要同时传递 parent_id 作为 majorId，以便 product-list 页面正确加载左侧菜单
      const majorId = item.parent_id || ''
      Taro.navigateTo({
        url: `/pages/product-list/index?majorId=${majorId}&minorId=${item.id}&title=${encodeURIComponent(item.name)}`
      })
      return
    }

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
            subCategories.map(subCat => {
              // 特殊处理"所有商品"分类，显示为 Banner 样式
              if (subCat.id === -100 && subCat.children && subCat.children.length > 0) {
                const item = subCat.children[0]
                return (
                  <View 
                    key={subCat.id} 
                    className='all-products-banner'
                    onClick={() => handleItemClick(item, subCat.id)}
                  >
                    <View className='banner-info'>
                      <View className='banner-title'>全部商品</View>
                      <View className='banner-subtitle'>浏览所有商品列表</View>
                    </View>
                    {item.logo ? (
                      <Image
                        className='banner-icon'
                        src={resolveLocalMediaUrl(item.logo)}
                        mode='aspectFit'
                      />
                    ) : (
                      <View className='banner-icon banner-icon-placeholder'>全</View>
                    )}
                  </View>
                )
              }

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
                            <View className='item-image item-image-placeholder'>{item.name.charAt(0)}</View>
                          )}
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
              )
            })
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
