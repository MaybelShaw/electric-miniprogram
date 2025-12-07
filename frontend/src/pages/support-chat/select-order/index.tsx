import { View, Text, Image, ScrollView } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useState, useEffect } from 'react'
import { orderService } from '../../../services/order'
import './index.scss'

export default function SelectOrder() {
  const [orders, setOrders] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const instance = Taro.getCurrentInstance()

  useEffect(() => {
    loadOrders()
  }, [])

  const loadOrders = async () => {
    try {
      setLoading(true)
      // Assuming pageSize is handled by page_size param
      const res = await orderService.getMyOrders({ page: 1, page_size: 50 })
      setOrders(res.results || [])
    } catch (e) {
      console.error(e)
      Taro.showToast({ title: '加载订单失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }

  const handleSelect = (order: any) => {
    // Use getCurrentPages to reliably get the current page instance in Mini Program
    const pages = Taro.getCurrentPages()
    const current = pages[pages.length - 1]
    
    if (current && current.getOpenerEventChannel) {
      const eventChannel = current.getOpenerEventChannel()
      eventChannel.emit('acceptSelectedOrder', order)
    } else {
      console.error('Event channel not available')
      Taro.showToast({ title: '无法发送订单', icon: 'none' })
    }
    Taro.navigateBack()
  }

  const getStatusText = (status: string) => {
    const map = {
      pending: '待支付',
      paid: '待发货',
      shipped: '待收货',
      completed: '已完成',
      cancelled: '已取消',
      returning: '退货中',
      refunding: '退款中',
      refunded: '已退款'
    }
    return map[status] || status
  }

  return (
    <View className="select-order-page">
      <ScrollView scrollY className="order-list">
        {loading && <View className="loading">加载中...</View>}
        {!loading && orders.length === 0 && <View className="empty">暂无订单</View>}
        
        {orders.map(order => {
          const primaryItem = order.items && order.items.length > 0 ? order.items[0] : null
          const product = primaryItem?.product || order.product || {}
          const image = primaryItem?.snapshot_image || product.product_image_url || (product.main_images && product.main_images[0]) || ''
          
          return (
            <View key={order.id} className="order-item" onClick={() => handleSelect(order)}>
              <View className="header">
                <Text className="order-no">订单号: {order.order_number}</Text>
                <Text className="status">{getStatusText(order.status)}</Text>
              </View>
              <View className="content">
                <Image src={image} mode="aspectFill" className="product-img" />
                <View className="info">
                  <Text className="name">{primaryItem?.product_name || product.name || '商品'}</Text>
                  <Text className="meta">数量: {order.quantity} | 总价: ¥{order.total_amount}</Text>
                </View>
              </View>
            </View>
          )
        })}
      </ScrollView>
    </View>
  )
}
