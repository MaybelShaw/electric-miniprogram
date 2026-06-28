import { useEffect, useState } from 'react'
import { Image, ScrollView, Text, View } from '@tarojs/components'
import Taro, { useRouter } from '@tarojs/taro'
import AppIcon from '../../components/AppIcon'
import StoreBottomNav from '../../components/StoreBottomNav'
import { productService } from '../../services/product'
import { storeService } from '../../services/store'
import { Category, Store } from '../../types'
import { resolveLocalMediaUrl } from '../../utils/media'
import './index.scss'

export default function StoreCategoriesPage() {
  const router = useRouter()
  const storeId = Number(router.params.store_id || router.params.store || 0)

  const [store, setStore] = useState<Store | null>(null)
  const [majorCategories, setMajorCategories] = useState<Category[]>([])
  const [activeMajorId, setActiveMajorId] = useState<number | null>(null)
  const [subCategories, setSubCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(false)
  const [subLoading, setSubLoading] = useState(false)

  useEffect(() => {
    if (!storeId) {
      Taro.showToast({ title: '店铺不存在', icon: 'none' })
      return
    }
    loadStoreCategories()
  }, [storeId])

  useEffect(() => {
    if (activeMajorId) {
      loadSubCategories(activeMajorId)
    }
  }, [activeMajorId])

  const loadStoreCategories = async () => {
    setLoading(true)
    try {
      const [detail, majors] = await Promise.all([
        storeService.getStoreDetail(storeId),
        productService.getCategories({ level: 'major', store: storeId }),
      ])
      if (detail.store.is_main) {
        Taro.switchTab({ url: '/pages/home/index' })
        return
      }

      setStore(detail.store)
      setMajorCategories(majors || [])
      setActiveMajorId((majors || [])[0]?.id || null)
      Taro.setNavigationBarTitle({ title: '分类' })
    } catch {
      Taro.showToast({ title: '加载分类失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }

  const loadSubCategories = async (parentId: number) => {
    setSubLoading(true)
    setSubCategories([])
    try {
      const data = await productService.getCategories({ parent_id: parentId, store: storeId })
      setSubCategories(data || [])
    } catch {
      Taro.showToast({ title: '加载子分类失败', icon: 'none' })
      setSubCategories([])
    } finally {
      setSubLoading(false)
    }
  }

  const handleMajorClick = (category: Category) => {
    if (category.id === activeMajorId) return
    setActiveMajorId(category.id)
  }

  const goToCategory = (category: Category) => {
    Taro.navigateTo({
      url: `/pages/store-category/index?store_id=${storeId}&category_id=${category.id}&category_name=${encodeURIComponent(category.name)}`,
    })
  }

  const activeMajor = majorCategories.find(category => category.id === activeMajorId) || null

  return (
    <View className='store-categories-page'>
      <View className='store-strip'>
        <View className='store-logo-wrap'>
          {resolveLocalMediaUrl(store?.logo) ? (
            <Image className='store-logo' src={resolveLocalMediaUrl(store?.logo)} mode='aspectFit' />
          ) : (
            <AppIcon name='store' tone='gold' />
          )}
        </View>
        <View className='store-copy'>
          <Text className='store-kicker'>店铺分类</Text>
          <Text className='store-name'>{store?.name || '加盟店铺'}</Text>
          {!!store?.description && <Text className='store-description'>{store.description}</Text>}
        </View>
      </View>

      <View className='category-content'>
        <ScrollView className='category-sidebar' scrollY>
          {majorCategories.map(category => (
            <View
              key={category.id}
              className={`category-tab ${activeMajorId === category.id ? 'active' : ''}`}
              onClick={() => handleMajorClick(category)}
            >
              <Text>{category.name}</Text>
            </View>
          ))}
        </ScrollView>

        <ScrollView className='sub-category-container' scrollY>
          {activeMajor && (
            <View className='current-major-card' onClick={() => goToCategory(activeMajor)}>
              <View className='current-major-copy'>
                <Text className='current-major-title'>全部{activeMajor.name}</Text>
                <Text className='current-major-desc'>查看该品类下的全部商品</Text>
              </View>
              <View className='current-major-icon'>
                {resolveLocalMediaUrl(activeMajor.logo) ? (
                  <Image className='current-major-image' src={resolveLocalMediaUrl(activeMajor.logo)} mode='aspectFit' />
                ) : (
                  <AppIcon name='package' tone='primary' />
                )}
              </View>
            </View>
          )}

          {subCategories.map(subCat => (
            <View key={subCat.id} className='sub-category-section'>
              <View className='section-title' onClick={() => goToCategory(subCat)}>
                <Text className='section-name'>{subCat.name}</Text>
                <Text className='section-action'>全部</Text>
              </View>
              <View className='items-grid'>
                {subCat.children && subCat.children.length > 0 ? (
                  subCat.children.map(item => (
                    <View key={item.id} className='category-node' onClick={() => goToCategory(item)}>
                      {resolveLocalMediaUrl(item.logo) ? (
                        <Image className='node-image' src={resolveLocalMediaUrl(item.logo)} mode='aspectFit' />
                      ) : (
                        <View className='node-image node-image-placeholder'>
                          <AppIcon name='package' tone='muted' />
                        </View>
                      )}
                      <Text className='node-name'>{item.name}</Text>
                    </View>
                  ))
                ) : (
                  <View className='category-node' onClick={() => goToCategory(subCat)}>
                    {resolveLocalMediaUrl(subCat.logo) ? (
                      <Image className='node-image' src={resolveLocalMediaUrl(subCat.logo)} mode='aspectFit' />
                    ) : (
                      <View className='node-image node-image-placeholder'>
                        <AppIcon name='package' tone='muted' />
                      </View>
                    )}
                    <Text className='node-name'>{subCat.name}</Text>
                  </View>
                )}
              </View>
            </View>
          ))}

          {loading && <View className='status-text'>加载中...</View>}
          {subLoading && <View className='status-text'>加载子分类中...</View>}
          {!loading && !subLoading && majorCategories.length === 0 && <View className='status-text'>暂无分类</View>}
          {!loading && !subLoading && activeMajor && subCategories.length === 0 && (
            <View className='status-text'>暂无子分类，可查看全部{activeMajor.name}</View>
          )}
        </ScrollView>
      </View>
      <StoreBottomNav storeId={storeId} storeIsMain={store?.is_main} active='category' />
    </View>
  )
}
