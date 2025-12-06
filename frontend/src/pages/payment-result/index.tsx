import { useEffect, useState, useCallback } from 'react'
import { View, Text, Image } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { orderService } from '../../services/order'
import { paymentService } from '../../services/payment'
import { Order, Payment, WechatPayParams } from '../../types'
import { formatPrice, formatTime } from '../../utils/format'
import './index.scss'

type StatusType = 'success' | 'fail'

export default function PaymentResult() {
  const instance = Taro.getCurrentInstance()
  const params = instance.router?.params || {}

  const statusParam = (params.status as StatusType) || 'success'
  const orderId = Number(params.orderId || 0)
  const paymentId = params.paymentId ? Number(params.paymentId) : undefined
  const reason = params.reason ? decodeURIComponent(params.reason) : ''

  const [status, setStatus] = useState<StatusType>(statusParam)
  const [order, setOrder] = useState<Order | null>(null)
  const [payment, setPayment] = useState<Payment | null>(null)
  const [retrying, setRetrying] = useState(false)

  const loadData = useCallback(async () => {
    if (!orderId) return
    try {
      const orderRes = await orderService.getOrderDetail(orderId)
      setOrder(orderRes)
      const payRes = await paymentService.getPayments({ order_id: orderId })
      if (payRes.results && payRes.results.length > 0) {
        setPayment(payRes.results[0])
      }
    } catch (err) {
      Taro.showToast({ title: '加载失败', icon: 'none' })
    }
  }, [orderId])

  useEffect(() => {
    loadData()
  }, [loadData])

  useDidShow(() => {
    loadData()
  })

  const requestWechatPayment = async (payParams: WechatPayParams) => {
    await Taro.requestPayment({
      timeStamp: payParams.timeStamp,
      nonceStr: payParams.nonceStr,
      package: payParams.package,
      signType: payParams.signType as any,
      paySign: payParams.paySign
    })
  }

  const handleRetry = async () => {
    if (!order) return
    setRetrying(true)
    try {
      let paymentRecord = payment
      if (!paymentRecord) {
        paymentRecord = await paymentService.createPayment({
          order_id: order.id,
          method: 'wechat'
        })
        setPayment(paymentRecord)
      }

      const startRes = await paymentService.startPayment(paymentRecord.id, { provider: 'wechat' })
      if (startRes.payment) {
        setPayment(startRes.payment)
      }
      const payParams = startRes.pay_params
      if (!payParams) throw new Error('未获取到支付参数')

      await requestWechatPayment(payParams)

      await paymentService.succeedPayment(paymentRecord.id, {
        transaction_id: payParams.prepay_id,
        prepay_id: payParams.prepay_id
      })

      setStatus('success')
      Taro.showToast({ title: '支付成功', icon: 'success' })
      Taro.redirectTo({
        url: `/pages/payment-result/index?status=success&orderId=${order.id}&paymentId=${paymentRecord.id}`
      })
    } catch (error: any) {
      const msg = error?.errMsg || error?.message || '支付失败'
      Taro.showToast({ title: msg, icon: 'none' })
      setStatus('fail')
    } finally {
      setRetrying(false)
    }
  }

  const goOrderDetail = () => {
    if (!orderId) return
    Taro.redirectTo({ url: `/pages/order-detail/index?id=${orderId}` })
  }

  const goHome = () => {
    Taro.switchTab({ url: '/pages/home/index' })
  }

  const showRetry =
    status === 'fail' &&
    order?.status === 'pending' &&
    payment?.status !== 'succeeded' &&
    payment?.status !== 'expired'

  return (
    <View className='payment-result-page'>
      <View className='result-card'>
        <Image
          className='result-icon'
          src={
            status === 'success'
              ? 'https://img.icons8.com/fluency/96/ok.png'
              : 'https://img.icons8.com/color/96/cancel--v1.png'
          }
        />
        <Text className='result-title'>
          {status === 'success' ? '支付成功' : '支付未完成'}
        </Text>
        {status === 'fail' && reason && <Text className='result-reason'>{reason}</Text>}
        <View className='result-info'>
          {order && (
            <>
              <View className='info-row'>
                <Text className='label'>订单号</Text>
                <Text className='value'>{order.order_number}</Text>
              </View>
              <View className='info-row'>
                <Text className='label'>支付金额</Text>
                <Text className='value price'>{formatPrice(order.actual_amount || order.total_amount)}</Text>
              </View>
              <View className='info-row'>
                <Text className='label'>下单时间</Text>
                <Text className='value'>{formatTime(order.created_at)}</Text>
              </View>
              <View className='info-row'>
                <Text className='label'>当前状态</Text>
                <Text className='value'>{order.status_display || order.status}</Text>
              </View>
            </>
          )}
        </View>
      </View>

      <View className='actions'>
        {showRetry && (
          <View className={`primary-btn ${retrying ? 'disabled' : ''}`} onClick={retrying ? undefined : handleRetry}>
            {retrying ? '重新支付中...' : '重新支付'}
          </View>
        )}
        <View className='secondary-btn' onClick={goOrderDetail}>
          查看订单
        </View>
        <View className='ghost-btn' onClick={goHome}>
          返回首页
        </View>
      </View>
    </View>
  )
}
