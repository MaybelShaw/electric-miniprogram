import { useEffect, useState, useCallback } from 'react'
import { View, Text, Image } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { orderService } from '../../services/order'
import { paymentService } from '../../services/payment'
import { refundService } from '../../services/refund'
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
  const initialReason = params.reason ? decodeURIComponent(params.reason) : ''

  const [status, setStatus] = useState<StatusType>(statusParam)
  const [reasonText, setReasonText] = useState<string>(initialReason)
  const [order, setOrder] = useState<Order | null>(null)
  const [payment, setPayment] = useState<Payment | null>(null)
  const [retrying, setRetrying] = useState(false)
  const [refunding, setRefunding] = useState(false)
  const [loading, setLoading] = useState(true)

  const syncPaymentStatus = useCallback(
    async (pid?: number) => {
      if (!pid) return false
      try {
        const res = await paymentService.syncPayment(pid)
        if (res.payment) {
          setPayment(res.payment)
          if (res.payment.status === 'succeeded') {
            setStatus('success')
            return true
          }
        }
      } catch (e) {
        // ignore sync errors
      }
      return false
    },
    []
  )

  const loadData = useCallback(async () => {
    if (!orderId) return
    try {
      const orderRes = await orderService.getOrderDetail(orderId)
      setOrder(orderRes)
      const payRes = await paymentService.getPayments({ order_id: orderId })
      if (payRes.results && payRes.results.length > 0) {
        setPayment(payRes.results[0])
      }
      if (!payRes.results?.length && paymentId) {
        // 兜底拉取指定支付
        try {
          const detail = await paymentService.getPaymentDetail(paymentId)
          setPayment(detail)
        } catch (e) {
          // ignore
        }
      }
      // 订单已支付/已发货/已完成时，先同步支付状态确认
      if (orderRes.status && ['paid', 'shipped', 'completed'].includes(orderRes.status as any)) {
        const pid = paymentId || payRes.results?.[0]?.id
        const ok = await syncPaymentStatus(pid)
        if (ok) {
          setStatus('success')
        } else {
          setStatus('fail')
          setReasonText('支付状态未确认，请稍后刷新订单或联系客服')
        }
      } else if (status === 'success') {
        // 未确认支付成功时不展示成功态
        setStatus('fail')
        setReasonText('支付状态未确认，请稍后刷新订单或联系客服')
      }
    } catch (err) {
      Taro.showToast({ title: '加载失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }, [orderId, paymentId, syncPaymentStatus])

  useEffect(() => {
    loadData()
  }, [loadData])

  useDidShow(() => {
    loadData()
  })

  const resolveTotalCents = (payParams: WechatPayParams) => {
    const toNumber = (val: any) => {
      const num = Number(val)
      return Number.isFinite(num) ? num : undefined
    }

    const centsFromParams = toNumber(
      payParams.total_fee !== undefined && payParams.total_fee !== null
        ? payParams.total_fee
        : payParams.total
    )
    if (centsFromParams !== undefined) {
      return Math.max(0, Math.round(centsFromParams))
    }

    const yuanAmount =
      toNumber(payParams.amount) ??
      toNumber(order?.actual_amount || order?.total_amount) ??
      toNumber(payment?.amount)

    if (yuanAmount !== undefined) {
      return Math.max(0, Math.round(yuanAmount * 100))
    }

    return undefined
  }

  const requestWechatPayment = async (payParams: WechatPayParams) => {
    const payload: any = {
      timeStamp: payParams.timeStamp,
      nonceStr: payParams.nonceStr,
      package: payParams.package,
      signType: payParams.signType as any,
      paySign: payParams.paySign
    }
    const cents = resolveTotalCents(payParams)
    if (cents !== undefined) {
      payload.total_fee = cents
      payload.total = cents
    }
    await Taro.requestPayment(payload)
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

      setStatus('success')
      Taro.showToast({ title: '支付成功', icon: 'success' })
      Taro.redirectTo({
        url: `/pages/payment-result/index?status=success&orderId=${order.id}&paymentId=${paymentRecord.id}`
      })
    } catch (error: any) {
      const msg = error?.errMsg || error?.message || '支付失败'
      // 若订单/支付已在后端成功，兜底展示成功页
      try {
        const synced = await syncPaymentStatus(payment?.id)
        if (synced) {
          Taro.redirectTo({
            url: `/pages/payment-result/index?status=success&orderId=${order.id}&paymentId=${payment?.id || ''}`
          })
          return
        }
      } catch (e) {
        // ignore sync errors
      }
      setStatus('fail')
      setReasonText(order?.status && ['paid', 'shipped', 'completed'].includes(order.status as any) ? '支付状态未确认，请稍后刷新订单或联系客服' : msg)
      Taro.showToast({ title: msg, icon: 'none' })
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

  const handleRefund = async () => {
    if (!order || refunding) return
    if (!payment) {
      Taro.showToast({ title: '未找到支付记录，无法退款', icon: 'none' })
      return
    }
    setRefunding(true)
    try {
      const amount = String(order.actual_amount || order.total_amount || payment.amount)
      const refund = await refundService.createRefund({
        order: order.id,
        payment: payment.id,
        amount,
        reason: '用户申请退款'
      })
      await refundService.startRefund(refund.id, { provider: 'wechat' })
      Taro.showToast({ title: '退款申请已提交', icon: 'success' })
      await loadData()
    } catch (error: any) {
      const msg = error?.message || '退款申请失败'
      Taro.showToast({ title: msg, icon: 'none' })
    } finally {
      setRefunding(false)
    }
  }

  const showRetry =
    status === 'fail' &&
    order?.status === 'pending' &&
    payment?.status !== 'succeeded' &&
    payment?.status !== 'expired'

  // 支付结果页不直接暴露退款入口，避免干扰状态流转
  const showRefund = false

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
        {status === 'fail' && reasonText && <Text className='result-reason'>{reasonText}</Text>}
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
                <Text className='value'>{order.status_label || order.status}</Text>
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
        {showRefund && (
          <View className={`primary-btn ${refunding ? 'disabled' : ''}`} onClick={refunding ? undefined : handleRefund}>
            {refunding ? '退款申请中...' : '申请退款'}
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
