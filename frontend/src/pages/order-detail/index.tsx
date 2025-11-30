import { useState, useEffect } from 'react'
import { View, ScrollView, Image, Text } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
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

  useDidShow(() => {
    const instance = Taro.getCurrentInstance()
    const { id } = instance.router?.params || {}
    if (id) {
      loadOrderDetail(Number(id))
    }
  })

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

    const options: any = {
      title: '取消订单',
      content: '',
      editable: true,
      placeholderText: '请输入取消原因（选填）'
    }
    const res = await Taro.showModal(options)

    if (res.confirm) {
      try {
        await orderService.cancelOrder(order.id, { reason: (res as any).content })
        Taro.showToast({ title: '取消成功', icon: 'success' })
        loadOrderDetail(order.id)
      } catch (error) {
        Taro.showToast({ title: '取消失败', icon: 'none' })
      }
    }
  }

  const handleRequestInvoice = () => {
    if (!order) return
    Taro.navigateTo({ url: `/pages/invoice-request/index?id=${order.id}` })
  }

  const handleCopy = (text: string) => {
    Taro.setClipboardData({
      data: text,
      success: () => {
        Taro.showToast({ title: '复制成功', icon: 'success' })
      }
    })
  }

  const handleConfirmReceipt = async () => {
    if (!order) return

    const res = await Taro.showModal({
      title: '提示',
      content: '确认已收到商品？'
    })

    if (res.confirm) {
      try {
        await orderService.confirmReceipt(order.id)
        Taro.showToast({ title: '确认收货成功', icon: 'success' })
        loadOrderDetail(order.id)
      } catch (error) {
        Taro.showToast({ title: '操作失败', icon: 'none' })
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
        <View className={`status-card ${order.status}`}>
          <View className='status-icon'>
            {order.status === 'pending' && '⏰'}
            {order.status === 'paid' && '✅'}
            {order.status === 'shipped' && '🚚'}
            {order.status === 'completed' && '✨'}
            {order.status === 'cancelled' && '❌'}
          </View>
          <View className='status-text'>{getOrderStatusText(order.status)}</View>
        </View>

        {/* 物流信息 */}
        {order.logistics_info && (
          <View className='info-card'>
            {order.logistics_info.logistics_company ? (
              <View className='info-row'>
                <Text className='info-label'>物流公司</Text>
                <Text className='info-value'>{order.logistics_info.logistics_company}</Text>
              </View>
            ) : null}
            {order.logistics_info.logistics_no ? (
              <View className='info-row'>
                <Text className='info-label'>快递单号</Text>
                <View className='info-right'>
                  <Text className='info-value' userSelect>{order.logistics_info.logistics_no}</Text>
                  <View className='copy-tag' onClick={() => handleCopy(order.logistics_info?.logistics_no || '')}>复制</View>
                </View>
              </View>
            ) : null}
            {order.logistics_info.delivery_record_code ? (
               <View className='info-row'>
                <Text className='info-label'>发货单号</Text>
                <Text className='info-value'>{order.logistics_info.delivery_record_code}</Text>
              </View>
            ) : null}
             {order.logistics_info.sn_code ? (
               <View className='info-row'>
                <Text className='info-label'>SN码</Text>
                <Text className='info-value'>{order.logistics_info.sn_code}</Text>
              </View>
            ) : null}
          </View>
        )}

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
                <View className='product-price'>{Number(order.product.price).toFixed(2)}</View>
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

        {/* 发票信息 */}
        {order.status === 'completed' && (
          <View className='info-card'>
            <View className='info-row'>
              <Text className='info-label'>发票</Text>
              <View className='info-value'>
                {order.invoice_info ? (
                   <Text style={{
                     color: order.invoice_info.status === 'issued' ? '#07c160' : 
                            order.invoice_info.status === 'cancelled' ? '#ff4d4f' : '#faad14',
                     fontWeight: 'bold'
                   }}>
                     {order.invoice_info.status_display}
                   </Text>
                ) : (
                   <View className='action-btn' onClick={handleRequestInvoice} style={{color: '#1989FA'}}>
                     申请发票
                   </View>
                )}
              </View>
            </View>
            {order.invoice_info && order.invoice_info.status === 'issued' && order.invoice_info.file_url && (
               <View className='info-row'>
                  <Text className='info-label'>下载</Text>
                  <Text className='info-value' onClick={() => {
                      if (order.invoice_info?.file_url) {
                        Taro.setClipboardData({ data: order.invoice_info.file_url })
                      }
                  }} style={{color: '#1989FA'}}>
                    复制链接
                  </Text>
               </View>
            )}
          </View>
        )}

        {/* 价格明细 */}
        <View className='price-card'>
          <View className='price-row'>
            <Text className='price-label'>商品总价</Text>
            <Text className='price-value'>{formatPrice(order.total_amount)}</Text>
          </View>
          <View className='price-row total'>
            <Text className='price-label'>实付款</Text>
            <Text className='price-value'>{Number(order.total_amount).toFixed(2)}</Text>
          </View>
        </View>

        <View className='bottom-placeholder' />
      </ScrollView>

      {/* 底部操作栏 */}
      {(order.status === 'pending' || order.status === 'paid' || order.status === 'shipped') && (
        <View className='footer-bar'>
          {(order.status === 'pending' || order.status === 'paid') && (
            <View className='cancel-btn' onClick={handleCancelOrder}>
              取消订单
            </View>
          )}
          {order.status === 'pending' && (
            <View className='pay-btn' onClick={handlePay}>
              {paying ? '支付中...' : `立即支付 ${formatPrice(order.total_amount)}`}
            </View>
          )}
          {order.status === 'shipped' && (
            <View className='confirm-btn' onClick={handleConfirmReceipt}>
              确认收货
            </View>
          )}
        </View>
      )}
    </View>
  )
}
