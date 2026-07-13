import { useEffect, useState } from 'react'
import { View, ScrollView } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { storeService } from '../../services/store'
import { PartnerEntryConfig, Store } from '../../types'
import StoreShowcaseCard from '../../components/StoreShowcaseCard'
import './index.scss'

export default function StoreListPage() {
  const [stores, setStores] = useState<Store[]>([])
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const [partnerEntryConfig, setPartnerEntryConfig] = useState<PartnerEntryConfig | null>(null)

  useEffect(() => {
    Taro.setNavigationBarTitle({ title: '供应链战略合作伙伴' })
    loadPartnerEntryConfig()
    loadStores(1)
  }, [])

  const loadPartnerEntryConfig = async () => {
    try {
      const data = await storeService.getPartnerEntryConfig()
      const title = data.section_title?.trim()
      setPartnerEntryConfig(data)
      if (title) {
        Taro.setNavigationBarTitle({ title })
      }
    } catch (error) {
      // 保留默认标题
    }
  }

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
    if (store.is_main) {
      Taro.switchTab({ url: '/pages/home/index' })
      return
    }

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
            <StoreShowcaseCard
              key={store.id}
              store={store}
              className='store-list-card'
              onClick={() => goToStore(store)}
            />
          ))}

          {loading && <View className='status-text'>加载中...</View>}
          {!loading && stores.length === 0 && <View className='status-text'>暂无合作方店铺</View>}
          {!loading && !hasMore && stores.length > 0 && <View className='status-text'>没有更多店铺了</View>}
        </View>
      </ScrollView>
    </View>
  )
}
