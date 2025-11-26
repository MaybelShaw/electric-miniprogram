import { useState, useEffect } from 'react'
import { View, ScrollView, Image, Text } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { orderService } from '../../services/order'
import { Order } from '../../types'
import { formatPrice, getOrderStatusText, formatTime } from '../../utils/format'
import './index.scss'

export default function OrderList() {
  const [orders, setOrders] = useState<Order[]>([])
  const [status, setStatus] = useState<string>('')
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string>('')

  const tabs = [
    { key: '', label: '全部' },
    { key: 'pending', label: '待支付' },
    { key: 'paid', label: '待发货' },
    { key: 'shipped', label: '待收货' },
    { key: 'completed', label: '已完成' }
  ]

  useEffect(() => {
    const instance = Taro.getCurrentInstance()
    const statusParam = instance.router?.params?.status || ''
    setStatus(statusParam)
  }, [])

  useEffect(() => {
    loadOrders(1)
  }, [status])

  const loadOrders = async (pageNum: number) => {
    if (loading) return

    setLoading(true)
    setError('')
    try {
      const params: any = { page: pageNum, page_size: 20 }
      if (status) params.status = status

      const res = await orderService.getMyOrders(params)
      
      // 检查响应数据结构
      if (!res || !res.results) {
        setError('数据格式错误')
        return
      }
      
      if (pageNum === 1) {
        setOrders(res.results as any)
      } else {
        setOrders([...orders, ...(res.results as any)])
      }
      setHasMore(res.has_next || false)
      setPage(pageNum)
    } catch (error: any) {
      const errorMsg = error.message || '加载失败'
      setError(errorMsg)
      Taro.showToast({ 
        title: errorMsg, 
        icon: 'none' 
      })
    } finally {
      setLoading(false)
    }
  }

  const handleTabChange = (key: string) => {
    setStatus(key)
    setPage(1)
  }

  const handleCancelOrder = async (id: number) => {
    const res = await Taro.showModal({
      title: '提示',
      content: '确定要取消订单吗？'
    })

    if (res.confirm) {
      try {
        await orderService.cancelOrder(id)
        Taro.showToast({ title: '取消成功', icon: 'success' })
        loadOrders(1)
      } catch (error) {
        Taro.showToast({ title: '取消失败', icon: 'none' })
      }
    }
  }

  const goToDetail = (id: number) => {
    Taro.navigateTo({ url: `/pages/order-detail/index?id=${id}` })
  }

  const handlePayOrder = (e: any, id: number) => {
    e.stopPropagation()
    Taro.navigateTo({ url: `/pages/order-detail/index?id=${id}` })
  }

  const onLoadMore = () => {
    if (hasMore && !loading) {
      loadOrders(page + 1)
    }
  }

  return (
    <View className='order-list'>
      {/* 状态标签 */}
      <View className='tabs'>
        {tabs.map(tab => (
          <View
            key={tab.key}
            className={`tab-item ${status === tab.key ? 'active' : ''}`}
            onClick={() => handleTabChange(tab.key)}
          >
            {tab.label}
          </View>
        ))}
      </View>

      {/* 订单列表 */}
      <ScrollView className='order-scroll' scrollY onScrollToLower={onLoadMore}>
        {error && (
          <View className='error'>
            <Text className='error-text'>{error}</Text>
            <View className='retry-btn' onClick={() => loadOrders(1)}>
              重试
            </View>
          </View>
        )}
        {!error && !loading && (!orders || orders.length === 0) ? (
          <View className='empty'>
            <Text className='empty-text'>暂无订单</Text>
          </View>
        ) : (
          orders && orders.map(order => (
            <View key={order.id} className='order-item' onClick={() => goToDetail(order.id)}>
              <View className='order-header'>
                <Text className='order-time'>{formatTime(order.created_at)}</Text>
                <Text className='order-status'>{getOrderStatusText(order.status)}</Text>
              </View>
              <View className='order-content'>
                <Image
                  className='product-image'
                  src={order.product?.main_images?.[0] || '/assets/default-product.png'}
                  mode='aspectFill'
                />
                <View className='product-info'>
                  <View className='product-name'>{order.product?.name || '商品'}</View>
                  <View className='product-bottom'>
                    <View className='product-price'>{formatPrice(order.product?.price || '0')}</View>
                    <View className='product-quantity'>x{order.quantity || 0}</View>
                  </View>
                </View>
              </View>
              <View className='order-footer'>
                <View className='total-amount'>
                  合计：<Text className='amount'>{formatPrice(order.total_amount)}</Text>
                </View>
                {order.status === 'pending' && (
                  <View className='order-actions'>
                    <View
                      className='cancel-btn'
                      onClick={(e) => {
                        e.stopPropagation()
                        handleCancelOrder(order.id)
                      }}
                    >
                      取消订单
                    </View>
                    <View
                      className='pay-btn'
                      onClick={(e) => handlePayOrder(e, order.id)}
                    >
                      立即支付
                    </View>
                  </View>
                )}
              </View>
            </View>
          ))
        )}
        {loading && <View className='loading-text'>加载中...</View>}
        {!hasMore && orders && orders.length > 0 && <View className='loading-text'>没有更多了</View>}
      </ScrollView>
    </View>
  )
}
