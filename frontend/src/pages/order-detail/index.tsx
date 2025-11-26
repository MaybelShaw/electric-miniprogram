import { useState, useEffect } from 'react'
import { View, ScrollView, Image, Text } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { orderService } from '../../services/order'
import { paymentService } from '../../services/payment'
import { Order, Payment } from '../../types'
import { formatPrice, getOrderStatusText, formatTime } from '../../utils/format'
import './index.scss'

export default function OrderDetail() {
  const [order, setOrder] = useState<Order | null>(null)
  const [payment, setPayment] = useState<Payment | null>(null)
  const [loading, setLoading] = useState(true)
  const [paying, setPaying] = useState(false)

  useEffect(() => {
    const instance = Taro.getCurrentInstance()
    const { id } = instance.router?.params || {}
    if (id) {
      loadOrderDetail(Number(id))
    }
  }, [])

  const loadOrderDetail = async (id: number) => {
    try {
      const data = await orderService.getOrderDetail(id)
      setOrder(data)
      
      // 如果订单是待支付状态，加载支付信息
      if (data.status === 'pending') {
        loadPaymentInfo(id)
      }
    } catch (error) {
      Taro.showToast({ title: '加载失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }

  const loadPaymentInfo = async (orderId: number) => {
    try {
      const res = await paymentService.getPayments({ order_id: orderId })
      if (res.results && res.results.length > 0) {
        setPayment(res.results[0])
      }
    } catch (error) {
      // 静默失败
    }
  }

  const handlePay = async () => {
    if (!order || paying) return

    setPaying(true)
    try {
      // 如果没有支付记录，先创建
      let paymentRecord = payment
      if (!paymentRecord) {
        paymentRecord = await paymentService.createPayment({
          order_id: order.id,
          method: 'wechat'
        })
        setPayment(paymentRecord)
      }

      // 模拟支付流程
      Taro.showLoading({ title: '支付中...' })
      
      // 调用支付成功接口
      await paymentService.succeedPayment(paymentRecord.id)
      
      Taro.hideLoading()
      Taro.showToast({ title: '支付成功', icon: 'success' })
      
      // 重新加载订单详情
      setTimeout(() => {
        loadOrderDetail(order.id)
      }, 1500)
    } catch (error: any) {
      Taro.hideLoading()
      Taro.showToast({ title: error.message || '支付失败', icon: 'none' })
    } finally {
      setPaying(false)
    }
  }

  const handleCancelOrder = async () => {
    if (!order) return

    const res = await Taro.showModal({
      title: '提示',
      content: '确定要取消订单吗？'
    })

    if (res.confirm) {
      try {
        await orderService.cancelOrder(order.id)
        Taro.showToast({ title: '取消成功', icon: 'success' })
        loadOrderDetail(order.id)
      } catch (error) {
        Taro.showToast({ title: '取消失败', icon: 'none' })
      }
    }
  }

  if (loading) {
    return (
      <View className='order-detail loading'>
        <View className='loading-text'>加载中...</View>
      </View>
    )
  }

  if (!order) {
    return (
      <View className='order-detail error'>
        <View className='error-text'>订单不存在</View>
      </View>
    )
  }

  return (
    <View className='order-detail'>
      <ScrollView className='content' scrollY>
        {/* 订单状态 */}
        <View className='status-card'>
          <View className='status-icon'>
            {order.status === 'pending' && '⏰'}
            {order.status === 'paid' && '✅'}
            {order.status === 'shipped' && '🚚'}
            {order.status === 'completed' && '✨'}
            {order.status === 'cancelled' && '❌'}
          </View>
          <View className='status-text'>{getOrderStatusText(order.status)}</View>
        </View>

        {/* 收货地址 */}
        {order.snapshot_address && (
          <View className='address-card'>
            <View className='address-icon'>📍</View>
            <View className='address-content'>
              <View className='address-header'>
                <Text className='contact-name'>{order.snapshot_contact_name}</Text>
                <Text className='phone'>{order.snapshot_phone}</Text>
              </View>
              <View className='address-detail'>
                {order.snapshot_address}
              </View>
            </View>
          </View>
        )}

        {/* 商品信息 */}
        <View className='product-card'>
          <View className='product-item'>
            <Image
              className='product-image'
              src={order.product.main_images[0]}
              mode='aspectFill'
            />
            <View className='product-info'>
              <View className='product-name'>{order.product.name}</View>
              <View className='product-bottom'>
                <View className='product-price'>{formatPrice(order.product.price)}</View>
                <View className='product-quantity'>x{order.quantity}</View>
              </View>
            </View>
          </View>
        </View>

        {/* 订单信息 */}
        <View className='info-card'>
          <View className='info-row'>
            <Text className='info-label'>订单编号</Text>
            <Text className='info-value'>{order.order_number}</Text>
          </View>
          <View className='info-row'>
            <Text className='info-label'>创建时间</Text>
            <Text className='info-value'>{formatTime(order.created_at)}</Text>
          </View>
          {order.note && (
            <View className='info-row'>
              <Text className='info-label'>备注</Text>
              <Text className='info-value'>{order.note}</Text>
            </View>
          )}
        </View>

        {/* 价格明细 */}
        <View className='price-card'>
          <View className='price-row'>
            <Text className='price-label'>商品总价</Text>
            <Text className='price-value'>{formatPrice(order.total_amount)}</Text>
          </View>
          <View className='price-row total'>
            <Text className='price-label'>实付款</Text>
            <Text className='price-value'>{formatPrice(order.total_amount)}</Text>
          </View>
        </View>

        <View className='bottom-placeholder' />
      </ScrollView>

      {/* 底部操作栏 */}
      {order.status === 'pending' && (
        <View className='footer-bar'>
          <View className='cancel-btn' onClick={handleCancelOrder}>
            取消订单
          </View>
          <View className='pay-btn' onClick={handlePay}>
            {paying ? '支付中...' : `立即支付 ${formatPrice(order.total_amount)}`}
          </View>
        </View>
      )}
    </View>
  )
}
