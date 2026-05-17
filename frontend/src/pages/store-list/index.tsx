import { useEffect, useState } from 'react'
import { View, ScrollView } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { storeService } from '../../services/store'
import { Store } from '../../types'
import StoreShowcaseCard from '../../components/StoreShowcaseCard'
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
            <StoreShowcaseCard key={store.id} store={store} className='store-list-card' onClick={() => goToStore(store)} />
          ))}

          {loading && <View className='status-text'>加载中...</View>}
          {!loading && stores.length === 0 && <View className='status-text'>暂无合作方店铺</View>}
          {!loading && !hasMore && stores.length > 0 && <View className='status-text'>没有更多店铺了</View>}
        </View>
      </ScrollView>
    </View>
  )
}
