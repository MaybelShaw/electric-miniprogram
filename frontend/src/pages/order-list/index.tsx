import { useState, useEffect } from 'react'
import { View, ScrollView, Text } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { orderService } from '../../services/order'
import { paymentService } from '../../services/payment'
import { Order } from '../../types'
import OrderCard from '../../components/OrderCard'
import { openWechatConfirmReceipt, resolveTransactionIdFromPayment } from '../../utils/wechat-confirm-receipt'
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
    { key: 'completed', label: '已完成' },
    { key: 'returning,refunding,refunded', label: '退货/售后' }
  ]

  useEffect(() => {
    const instance = Taro.getCurrentInstance()
    const statusParam = instance.router?.params?.status || ''
    setStatus(statusParam)
  }, [])

  useEffect(() => {
    loadOrders(1)
  }, [status])

  useEffect(() => {
    const handleReceiptConfirmed = () => {
      loadOrders(1)
    }
    Taro.eventCenter.on('orderReceiptConfirmed', handleReceiptConfirmed)
    return () => {
      Taro.eventCenter.off('orderReceiptConfirmed', handleReceiptConfirmed)
    }
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
    const options: any = {
      title: '取消订单',
      content: '',
      editable: true,
      placeholderText: '请输入取消原因（选填）'
    }
    const res = await Taro.showModal(options)

    if (res.confirm) {
      try {
        await orderService.cancelOrder(id, { reason: (res as any).content })
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

  const handleConfirmReceipt = async (id: number) => {
    const res = await Taro.showModal({
      title: '提示',
      content: '确认已收到商品？'
    })

    if (res.confirm) {
      const targetOrder = orders.find(item => item.id === id)
      if (!targetOrder?.payment_method || targetOrder.payment_method !== 'wechat') {
        try {
          await orderService.confirmReceipt(id)
          Taro.showToast({ title: '确认收货成功', icon: 'success' })
          loadOrders(1)
        } catch (error) {
          Taro.showToast({ title: '操作失败', icon: 'none' })
        }
        return
      }

      let transactionId: string | null = null
      try {
        const payments = await paymentService.getPayments({ order_id: id })
        if (payments.results && payments.results.length > 0) {
          const invalidStatuses = new Set(['cancelled', 'expired', 'failed'])
          const validPayments = payments.results.filter((item) => !invalidStatuses.has(item.status))
          
          // Find the first payment with a transaction ID
          for (const payment of validPayments) {
            const tid = resolveTransactionIdFromPayment(payment)
            if (tid) {
              transactionId = tid
              break
            }
          }
        }
      } catch (error) {
        console.error('Failed to fetch payments for order confirmation:', error)
      }

      const openResult = await openWechatConfirmReceipt({
        orderId: id,
        orderNumber: targetOrder?.order_number,
        transactionId,
      })

      if (openResult.opened) {
        Taro.showToast({ title: '已唤起微信确认收货', icon: 'none' })
        return
      }

      if (openResult.reason === 'missing') {
        const fallback = await Taro.showModal({
          title: '无法唤起微信确认收货',
          content: '未获取到微信交易号，是否仅确认本地收货？'
        })
        if (!fallback.confirm) return
      } else if (openResult.reason === 'unsupported') {
        const fallback = await Taro.showModal({
          title: '当前微信版本不支持',
          content: '是否仅确认本地收货？'
        })
        if (!fallback.confirm) return
      } else if (openResult.reason === 'fail') {
        Taro.showToast({ title: '唤起微信确认收货失败', icon: 'none' })
        return
      }

      try {
        await orderService.confirmReceipt(id)
        Taro.showToast({ title: '确认收货成功', icon: 'success' })
        loadOrders(1)
      } catch (error) {
        Taro.showToast({ title: '操作失败', icon: 'none' })
      }
    }
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
            <OrderCard
              key={order.id}
              order={order}
              onClick={goToDetail}
              onCancel={handleCancelOrder}
              onPay={handlePayOrder}
              onConfirmReceipt={handleConfirmReceipt}
            />
          ))
        )}
        {loading && <View className='loading-text'>加载中...</View>}
        {!hasMore && orders && orders.length > 0 && <View className='loading-text'>没有更多了</View>}
      </ScrollView>
    </View>
  )
}
