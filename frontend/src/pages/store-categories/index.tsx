import { useEffect, useState } from 'react'
import { Image, ScrollView, Text, View } from '@tarojs/components'
import Taro, { useRouter } from '@tarojs/taro'
import AppIcon from '../../components/AppIcon'
import StoreBottomNav from '../../components/StoreBottomNav'
import { storeService } from '../../services/store'
import { Category, Store } from '../../types'
import { resolveLocalMediaUrl } from '../../utils/media'
import './index.scss'

export default function StoreCategoriesPage() {
  const router = useRouter()
  const storeId = Number(router.params.store_id || router.params.store || 0)

  const [store, setStore] = useState<Store | null>(null)
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!storeId) {
      Taro.showToast({ title: '店铺不存在', icon: 'none' })
      return
    }
    loadCategories()
  }, [storeId])

  const loadCategories = async () => {
    setLoading(true)
    try {
      const detail = await storeService.getStoreDetail(storeId)
      if (detail.store.is_main) {
        Taro.switchTab({ url: '/pages/home/index' })
        return
      }

      setStore(detail.store)
      setCategories(detail.categories || [])
      Taro.setNavigationBarTitle({ title: '分类' })
    } catch {
      Taro.showToast({ title: '加载分类失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }

  const goToCategory = (category: Category) => {
    Taro.navigateTo({
      url: `/pages/store-category/index?store_id=${storeId}&category_id=${category.id}&category_name=${encodeURIComponent(category.name)}`,
    })
  }

  return (
    <View className='store-categories-page'>
      <ScrollView className='store-categories-scroll' scrollY>
        <View className='category-grid'>
          {categories.map(category => (
            <View key={category.id} className='category-card' onClick={() => goToCategory(category)}>
              <View className='category-media'>
                {resolveLocalMediaUrl(category.logo) ? (
                  <Image className='category-image' src={resolveLocalMediaUrl(category.logo)} mode='aspectFit' />
                ) : (
                  <View className='category-fallback'>
                    <AppIcon name='package' tone='muted' />
                  </View>
                )}
              </View>
              <Text className='category-name'>{category.name}</Text>
            </View>
          ))}
        </View>

        {loading && <View className='status-text'>加载中...</View>}
        {!loading && categories.length === 0 && <View className='status-text'>暂无分类</View>}
      </ScrollView>
      <StoreBottomNav storeId={storeId} storeIsMain={store?.is_main} active='category' />
    </View>
  )
}
