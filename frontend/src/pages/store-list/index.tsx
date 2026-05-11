import { useEffect, useState } from 'react'
import { View, ScrollView, Image, Text } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { storeService } from '../../services/store'
import { Store } from '../../types'
import { resolveLocalMediaUrl } from '../../utils/media'
import './index.scss'

export default function StoreListPage() {
  const [stores, setStores] = useState<Store[]>([])
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)

  useEffect(() => {
    Taro.setNavigationBarTitle({ title: '品牌专区' })
    loadStores(1)
  }, [])

  const loadStores = async (pageNum: number) => {
    if (loading) return
    setLoading(true)
    try {
      const res = await storeService.getPartnerStores({ page: pageNum, page_size: 20 })
      setStores(prev => (pageNum === 1 ? res.results : [...prev, ...res.results]))
      setPage(pageNum)
      setHasMore(res.has_next || false)
    } catch (error) {
      Taro.showToast({ title: '加载店铺失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }

  const goToStore = (store: Store) => {
    Taro.navigateTo({
      url: `/pages/store-detail/index?id=${store.id}`,
    })
  }

  return (
    <View className='store-list-page'>
      <ScrollView
        className='store-list-scroll'
        scrollY
        refresherEnabled
        refresherTriggered={loading && page === 1}
        onRefresherRefresh={() => loadStores(1)}
        onScrollToLower={() => hasMore && loadStores(page + 1)}
      >
        <View className='store-list'>
          {stores.map(store => (
            <View key={store.id} className='store-card' onClick={() => goToStore(store)}>
              {store.cover_image ? (
                <Image className='store-cover' src={resolveLocalMediaUrl(store.cover_image)} mode='aspectFill' />
              ) : (
                <View className='store-cover placeholder'>
                  {store.logo ? <Image className='store-logo-only' src={resolveLocalMediaUrl(store.logo)} mode='aspectFill' /> : store.name.charAt(0)}
                </View>
              )}
              <View className='store-content'>
                <View className='store-title-row'>
                  {store.logo && <Image className='store-logo' src={resolveLocalMediaUrl(store.logo)} mode='aspectFill' />}
                  <Text className='store-name'>{store.name}</Text>
                </View>
                {!!store.description && <Text className='store-desc'>{store.description}</Text>}
              </View>
            </View>
          ))}

          {loading && <View className='status-text'>加载中...</View>}
          {!loading && stores.length === 0 && <View className='status-text'>暂无合作方店铺</View>}
          {!loading && !hasMore && stores.length > 0 && <View className='status-text'>没有更多店铺了</View>}
        </View>
      </ScrollView>
    </View>
  )
}
