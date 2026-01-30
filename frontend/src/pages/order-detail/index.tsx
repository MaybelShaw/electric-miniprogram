import { useState, useEffect } from 'react'
import { View, ScrollView, Image, Text, Input, Textarea } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { orderService } from '../../services/order'
import { paymentService } from '../../services/payment'
import { refundService } from '../../services/refund'
import { uploadService } from '../../services/upload'
import { Order, Payment, WechatPayParams } from '../../types'
import { formatPrice, getOrderStatusText, formatTime } from '../../utils/format'
import { resolvePaymentErrorMessage } from '../../utils/payment'
import { BASE_URL, TokenManager } from '../../utils/request'
import './index.scss'

export default function OrderDetail() {
  const [order, setOrder] = useState<Order | null>(null)
  const [payment, setPayment] = useState<Payment | null>(null)
  const [loading, setLoading] = useState(true)
  const [paying, setPaying] = useState(false)
  const [timeLeft, setTimeLeft] = useState('')
  const [refundSubmitting, setRefundSubmitting] = useState(false)
  const [refundModalOpen, setRefundModalOpen] = useState(false)
  const [refundAmountInput, setRefundAmountInput] = useState('')
  const [refundReason, setRefundReason] = useState('')
  const [refundImages, setRefundImages] = useState<string[]>([])
  const [refundUploading, setRefundUploading] = useState(false)
  const formatCountdown = (diff: number) => {
    if (diff <= 0) return '已超时'
    const totalSeconds = Math.floor(diff / 1000)
    const days = Math.floor(totalSeconds / 86400)
    const hours = Math.floor((totalSeconds % 86400) / 3600)
    const minutes = Math.floor((totalSeconds % 3600) / 60)
    const seconds = totalSeconds % 60
    if (days > 0) {
      return `${days}天${hours}小时${minutes}分${seconds}秒`
    }
    if (hours > 0) {
      return `${hours}小时${minutes}分${seconds}秒`
    }
    return `${minutes}分${seconds}秒`
  }

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

  useEffect(() => {
    if (!order || order.status !== 'pending' || !order.expires_at) return

    const calculateTimeLeft = () => {
      const now = new Date().getTime()
      const expireTime = new Date(order.expires_at!).getTime()
      const diff = expireTime - now

      const nextText = formatCountdown(diff)
      setTimeLeft(nextText)
    }

    calculateTimeLeft()
    const timer = setInterval(calculateTimeLeft, 1000)

    return () => clearInterval(timer)
  }, [order?.status, order?.expires_at])

  const returnStatusMap: Record<string, string> = {
    requested: '等待商家处理',
    approved: '已同意退货',
    in_transit: '退货中',
    received: '已收到退货',
    rejected: '已拒绝退货',
  }

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
        const invalidStatuses = new Set(['cancelled', 'expired', 'failed'])
        const validPayments = res.results.filter((item) => !invalidStatuses.has(item.status))
        setPayment(validPayments[0] || null)
      }
    } catch (error) {
      // 静默失败
    }
  }

  const resolveTotalCents = (payParams: WechatPayParams) => {
    const toNumber = (val: any) => {
      const num = Number(val)
      return Number.isFinite(num) ? num : undefined
    }

    // 优先使用后端返回的分值（若缺失则兜底取金额再转换）
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

  const resolveOrderTotal = (target: Order | null) => {
    if (!target) return 0
    if (target.items && target.items.length > 0) {
      return target.items.reduce((sum, item) => {
        const unit = Number(item.unit_price || 0)
        const qty = Number(item.quantity || 0)
        return sum + unit * qty
      }, 0)
    }
    if (target.total_amount !== undefined && target.total_amount !== null) {
      return Number(target.total_amount || 0)
    }
    return Number(target.actual_amount || 0)
  }

  const resolveNumber = (value: any) => {
    const num = Number(value)
    return Number.isFinite(num) ? num : 0
  }

  const getRefundedAmount = (target: Order | null) => resolveNumber(target?.refunded_amount)

  const getRefundableAmount = (target: Order | null) => resolveNumber(target?.refundable_amount)

  const resolveImageUrl = (url?: string) => {
    if (!url) return ''
    if (url.startsWith('https://')) return url
    if (url.startsWith('http://')) return `https://${url.slice(7)}`
    if (url.startsWith('//')) return `https:${url}`
    const base = BASE_URL.replace(/\/api\/?$/, '')
    if (url.startsWith('/')) return `${base}${url}`
    return `${base}/${url}`
  }

  const requestWechatPayment = async (payParams: WechatPayParams) => {
    const payload: any = {
      timeStamp: payParams.timeStamp,
      nonceStr: payParams.nonceStr,
      package: payParams.package,
      signType: payParams.signType as any,
      paySign: payParams.paySign,
    }

    const cents = resolveTotalCents(payParams)
    if (cents !== undefined) {
      payload.total_fee = cents
      payload.total = cents
    }

    await Taro.requestPayment(payload)
  }

  const isInvalidPaymentStatus = (status?: string) =>
    status ? ['cancelled', 'expired', 'failed'].includes(status) : false

  const refreshPaymentRecord = async (paymentRecord: Payment | null) => {
    if (!paymentRecord) return null
    try {
      const detail = await paymentService.getPaymentDetail(paymentRecord.id)
      setPayment(detail)
      return detail
    } catch {
      return paymentRecord
    }
  }

  const isNotStartableError = (error: any) => {
    const detail = error?.data?.detail || error?.message || ''
    return String(detail).includes('不可继续') || String(detail).includes('cancelled') || String(detail).includes('过期')
  }

  const handlePay = async () => {
    if (!order || paying) return

    setPaying(true)
    let paymentRecord: Payment | null = null
    try {
      // 如果没有支付记录，先创建
      paymentRecord = await refreshPaymentRecord(payment)
      const invalidStatus = paymentRecord && isInvalidPaymentStatus(paymentRecord.status)
      if (!paymentRecord || invalidStatus) {
        paymentRecord = await paymentService.createPayment({
          order_id: order.id,
          method: 'wechat'
        })
        setPayment(paymentRecord)
      }

      // 获取微信支付参数并拉起支付
      let startRes: { payment?: Payment; pay_params?: WechatPayParams | null } | null = null
      try {
        startRes = await paymentService.startPayment(paymentRecord.id, { provider: 'wechat' })
      } catch (error: any) {
        if (isNotStartableError(error)) {
          const nextPayment = await paymentService.createPayment({
            order_id: order.id,
            method: 'wechat'
          })
          setPayment(nextPayment)
          paymentRecord = nextPayment
          startRes = await paymentService.startPayment(paymentRecord.id, { provider: 'wechat' })
        } else {
          throw error
        }
      }
      if (!startRes) {
        throw new Error('未获取到支付参数')
      }
      if (startRes.payment) {
        setPayment(startRes.payment)
      }
      const payParams = startRes.pay_params
      if (!payParams) {
        throw new Error('未获取到支付参数')
      }

      await requestWechatPayment(payParams)

      Taro.redirectTo({
        url: `/pages/payment-result/index?status=success&orderId=${order.id}&paymentId=${paymentRecord.id}`
      })
    } catch (error: any) {
      const msg = resolvePaymentErrorMessage(error, '支付未完成')
      Taro.showToast({ title: msg, icon: 'none' })
      Taro.redirectTo({
        url: `/pages/payment-result/index?status=fail&orderId=${order?.id || ''}&paymentId=${paymentRecord?.id || payment?.id || ''}&reason=${encodeURIComponent(msg)}`
      })
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
        const result: any = await orderService.cancelOrder(order.id, { reason: (res as any).content })
        if (result?.refund_started) {
          if (result?.refund_channel === 'credit') {
            Taro.showToast({ title: '已取消，信用退款已冲减', icon: 'success' })
          } else {
            Taro.showToast({ title: '已取消，退款处理中', icon: 'success' })
          }
        } else if (result?.refund_error) {
          const tip = result.refund_channel === 'credit' ? '信用支付需人工处理' : '请稍后重试或联系客户支持'
          Taro.showToast({ title: `取消成功，退款失败：${result.refund_error}，${tip}`, icon: 'none' })
        } else {
          Taro.showToast({ title: '取消成功', icon: 'success' })
        }
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

  const handleDownloadInvoice = async () => {
    if (!order?.invoice_info?.id) return;
    const token = TokenManager.getAccessToken();
    if (!token) {
        Taro.showToast({ title: '请先登录', icon: 'none' });
        return;
    }
    const url = `${BASE_URL}/invoices/${order.invoice_info.id}/download/`;
    
    Taro.showLoading({ title: '下载中...' });
    try {
        const res = await Taro.downloadFile({
            url: url,
            header: {
                'Authorization': `Bearer ${token}`
            }
        });
        Taro.hideLoading();
        if (res.statusCode === 200) {
            const filePath = res.tempFilePath;
            const lowerPath = filePath.toLowerCase();
            if (lowerPath.endsWith('.jpg') || lowerPath.endsWith('.jpeg') || lowerPath.endsWith('.png') || lowerPath.endsWith('.gif')) {
                Taro.previewImage({
                    urls: [filePath]
                });
            } else {
                Taro.openDocument({
                    filePath: filePath,
                    success: function () {
                        console.log('打开文档成功');
                    },
                    fail: function (err) {
                        console.log('打开文档失败', err);
                        Taro.showToast({ title: '无法打开文件', icon: 'none' });
                    }
                });
            }
        } else {
            Taro.showToast({ title: '下载失败', icon: 'none' });
        }
    } catch (error) {
        Taro.hideLoading();
        Taro.showToast({ title: '下载出错', icon: 'none' });
    }
  };

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

  const handleRequestReturn = () => {
    if (!order) return
    Taro.navigateTo({ url: `/pages/request-return/index?id=${order.id}` })
  }

  const handleReturnTracking = () => {
    if (!order) return
    Taro.navigateTo({ url: `/pages/return-tracking/index?id=${order.id}` })
  }

  const resetRefundForm = () => {
    setRefundAmountInput('')
    setRefundReason('')
    setRefundImages([])
  }

  const handleRequestRefund = () => {
    if (!order || refundSubmitting) return
    const refundable = getRefundableAmount(order)
    if (refundable <= 0) {
      Taro.showToast({ title: '暂无可退金额', icon: 'none' })
      return
    }
    resetRefundForm()
    setRefundModalOpen(true)
  }

  const handleRefundChooseImage = () => {
    if (refundUploading || refundImages.length >= 3) return
    Taro.chooseImage({
      count: 3 - refundImages.length,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: async (res) => {
        setRefundUploading(true)
        Taro.showLoading({ title: '上传中...' })
        try {
          const uploadPromises = res.tempFilePaths.map((path) => uploadService.uploadImage(path))
          const urls = await Promise.all(uploadPromises)
          setRefundImages((prev) => [...prev, ...urls])
        } catch (error) {
          Taro.showToast({ title: '上传失败', icon: 'none' })
        } finally {
          Taro.hideLoading()
          setRefundUploading(false)
        }
      }
    })
  }

  const handleRefundRemoveImage = (index: number) => {
    setRefundImages((prev) => prev.filter((_, idx) => idx !== index))
  }

  const handleRefundSubmit = async () => {
    if (!order || refundSubmitting || refundUploading) return
    const refundable = getRefundableAmount(order)
    const amount = Number(refundAmountInput)
    if (!Number.isFinite(amount) || amount <= 0) {
      Taro.showToast({ title: '请输入正确的退款金额', icon: 'none' })
      return
    }
    if (amount > refundable) {
      Taro.showToast({ title: `退款金额超出可退金额：${formatPrice(refundable)}`, icon: 'none' })
      return
    }
    if (!refundReason.trim()) {
      Taro.showToast({ title: '请填写退款原因', icon: 'none' })
      return
    }

    setRefundSubmitting(true)
    try {
      await refundService.createRefund({
        order: order.id,
        amount,
        reason: refundReason.trim(),
        evidence_images: refundImages
      })
      Taro.showToast({ title: '已提交审核', icon: 'success' })
      setRefundModalOpen(false)
      resetRefundForm()
      loadOrderDetail(order.id)
    } catch (error: any) {
      const msg = error?.message || '申请失败'
      Taro.showToast({ title: msg, icon: 'none' })
    } finally {
      setRefundSubmitting(false)
    }
  }

  const canConfirmReceipt = !!order && order.status === 'shipped' && !order.return_info && !['refunding', 'refunded', 'cancelled'].includes(order.status)
  const canRequestRefund = !!order &&
    order.status === 'completed' &&
    !order.return_info &&
    !order.refund_pending &&
    !order.refund_locked &&
    getRefundableAmount(order) > 0

  const getDisplayStatus = (order: Order) => {
    const refundedAmount = getRefundedAmount(order)
    if (order.refund_pending) {
      return order.status === 'refunding' ? '退款处理中' : '退款审核中'
    }
    if (refundedAmount > 0) {
      return `已退款 ${formatPrice(refundedAmount)}`
    }
    if (order.return_info) {
      const returnStatus = order.return_info.status;
      if (returnStatus === 'requested') return '待商家处理';
      if (returnStatus === 'approved') return '待退货';
      if (returnStatus === 'in_transit') return '退货中';
      if (returnStatus === 'received') return '商家已收货';
      if (returnStatus === 'rejected') return '退货被拒';
    }
    return getOrderStatusText(order.status);
  }

  const getStatusIcon = (order: Order) => {
    if (order.return_info) {
      const returnStatus = order.return_info.status;
      if (returnStatus === 'requested') return '⏳';
      if (returnStatus === 'approved') return '📦';
      if (returnStatus === 'in_transit') return '🚚';
      if (returnStatus === 'received') return '✅';
      if (returnStatus === 'rejected') return '❌';
    }
    
    switch (order.status) {
      case 'pending': return '⏰';
      case 'paid': return '✅';
      case 'shipped': return '🚚';
      case 'completed': return '✨';
      case 'cancelled': return '❌';
      case 'returning': return '🚚';
      case 'refunding': return '💸';
      case 'refunded': return '💰';
      default: return '✨';
    }
  }

  const getStatusClass = (order: Order) => {
    if (order.return_info) {
       if (order.return_info.status === 'rejected') return 'cancelled';
       return 'returning';
    }
    if (order.refund_pending) {
      return 'refunding'
    }
    if (getRefundedAmount(order) > 0) {
      return 'refunded'
    }
    return order.status;
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
        <View className={`status-card ${getStatusClass(order)}`}>
          <View className='status-icon'>
            {getStatusIcon(order)}
          </View>
          <View className='status-text-container'>
            <View className='status-text'>{getDisplayStatus(order)}</View>
            {order.status === 'pending' && timeLeft && (
              <View className='status-countdown'>剩余支付时间：{timeLeft}</View>
            )}
          </View>
        </View>

        {/* 物流信息 */}
        {order.logistics_info && (
          <View className='info-card'>
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
        <View className='order-product-card'>
          {order.items && order.items.length > 0 ? (
            order.items.map(item => (
              <View key={item.id} className='product-item'>
                  <Image
                    className='product-image'
                    src={
                      resolveImageUrl(item.snapshot_image || item.product?.main_images?.[0]) ||
                      '/assets/icons/product.png'
                    }
                    mode='aspectFill'
                  />
                <View className='product-info'>
                  <View className='product-name'>{item.product_name || item.product?.name}</View>
                  {item.sku_specs && Object.keys(item.sku_specs).length > 0 && (
                    <View className='product-spec'>{Object.values(item.sku_specs).join(' / ')}</View>
                  )}
                  <View className='product-bottom'>
                    <View className='product-price'>{Number(item.unit_price || 0).toFixed(2)}</View>
                    <View className='product-quantity'>x{item.quantity}</View>
                  </View>
                </View>
              </View>
            ))
          ) : (
            <View className='product-item'>
              <Image
                className='product-image'
                src={resolveImageUrl(order.product?.main_images?.[0]) || '/assets/icons/product.png'}
                mode='aspectFill'
              />
              <View className='product-info'>
                <View className='product-name'>{order.product?.name}</View>
                <View className='product-bottom'>
                  <View className='product-price'>{Number(order.product?.price || 0).toFixed(2)}</View>
                  <View className='product-quantity'>x{order.quantity}</View>
                </View>
              </View>
            </View>
          )}
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

        {/* 退货信息 */}
        {order.return_info && (
          <View className='info-card'>
            <View className='info-row' style={{ borderBottom: '1rpx solid #f5f6f7', paddingBottom: '16rpx', marginBottom: '16rpx' }}>
              <Text className='info-label' style={{ fontWeight: 'bold', color: '#323233' }}>退货申请</Text>
              <Text className='info-value' style={{ color: '#1989fa', fontWeight: 'bold' }}>{returnStatusMap[order.return_info.status] || order.return_info.status_display}</Text>
            </View>
            <View className='info-row'>
              <Text className='info-label'>退货原因</Text>
              <Text className='info-value'>{order.return_info.reason}</Text>
            </View>
            {order.return_info.tracking_number && (
              <View className='info-row'>
                <Text className='info-label'>退货单号</Text>
                <Text className='info-value'>{order.return_info.tracking_number}</Text>
              </View>
            )}
            {order.return_info.processed_note && (
              <View className='info-row'>
                <Text className='info-label'>处理备注</Text>
                <Text className='info-value'>{order.return_info.processed_note}</Text>
              </View>
            )}
          </View>
        )}

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
            {order.invoice_info && order.invoice_info.status === 'issued' && (
               <View className='info-row'>
                  <Text className='info-label'>发票文件</Text>
                  <Text className='info-value' onClick={handleDownloadInvoice} style={{color: '#1989FA'}}>
                    下载/查看
                  </Text>
               </View>
            )}
          </View>
        )}

        {/* 价格明细 */}
        <View className='price-card'>
          <View className='price-row'>
            <Text className='price-label'>商品总价</Text>
            <Text className='price-value'>{formatPrice(resolveOrderTotal(order))}</Text>
          </View>
          <View className='price-row total'>
            <Text className='price-label'>实付款</Text>
            <Text className='price-value'>{Number(order.actual_amount ?? order.total_amount ?? 0).toFixed(2)}</Text>
          </View>
          {getRefundedAmount(order) > 0 && (
            <View className='price-row'>
              <Text className='price-label'>已退款</Text>
              <Text className='price-value'>{formatPrice(getRefundedAmount(order))}</Text>
            </View>
          )}
          {order.refund_pending && (
            <View className='price-row'>
              <Text className='price-label'>退款状态</Text>
              <Text className='price-value'>{order.status === 'refunding' ? '处理中' : '审核中'}</Text>
            </View>
          )}
          {order.status === 'completed' && !order.refund_locked && getRefundableAmount(order) > 0 && (
            <View className='price-row'>
              <Text className='price-label'>可退金额</Text>
              <Text className='price-value'>{formatPrice(getRefundableAmount(order))}</Text>
            </View>
          )}
        </View>

        <View className='bottom-placeholder' />
      </ScrollView>

      {/* 底部操作栏 */}
      {(['pending', 'paid', 'shipped', 'completed'].includes(order.status) || (order.return_info && order.return_info.status === 'requested')) && (
        <View className='footer-bar'>
          {(['pending', 'paid'].includes(order.status)) && !order.return_info && (
            <View className='cancel-btn' onClick={handleCancelOrder}>
              {order.status === 'paid' ? '取消并退款' : '取消订单'}
            </View>
          )}
          
          {/* 申请退货: 仅已发货/已完成 且无退货申请 */}
          {['shipped', 'completed'].includes(order.status) && !order.return_info && (
            <View className='cancel-btn ghost' onClick={handleRequestReturn} style={{ marginLeft: '20rpx' }}>
              申请退货
            </View>
          )}

          {canRequestRefund && (
            <View className='cancel-btn ghost' onClick={handleRequestRefund} style={{ marginLeft: '20rpx' }}>
              申请退款
            </View>
          )}
          {order.refund_pending && (
            <View className='cancel-btn ghost disabled' style={{ marginLeft: '20rpx' }}>
              {order.status === 'refunding' ? '退款处理中' : '退款审核中'}
            </View>
          )}

          {order.status === 'pending' && (
            <View className='pay-btn' onClick={handlePay}>
              {paying ? '支付中...' : `立即支付 ${formatPrice(order.actual_amount || order.total_amount)}`}
            </View>
          )}
          
          {canConfirmReceipt && (
            <View className='confirm-btn' onClick={handleConfirmReceipt}>
              确认收货
            </View>
          )}

          {/* 填写退货物流: 退货申请需管理员同意(approved) */}
          {order.return_info && order.return_info.status === 'approved' && (
            <View className='return-tracking-btn' onClick={handleReturnTracking}>
              填写退货物流
            </View>
          )}
        </View>
      )}
      {refundModalOpen && (
        <View className='refund-modal'>
          <View className='refund-modal-mask' onClick={() => !refundSubmitting && !refundUploading && setRefundModalOpen(false)} />
          <View className='refund-modal-card'>
            <View className='refund-modal-header'>
              <Text>申请退款</Text>
              <Text className='refund-modal-close' onClick={() => !refundSubmitting && !refundUploading && setRefundModalOpen(false)}>×</Text>
            </View>
            <View className='refund-modal-body'>
            <View className='refund-field'>
              <Text className='refund-label'>退款金额<Text className='refund-required'>*</Text></Text>
              <Input
                className='refund-input'
                type='digit'
                placeholder={`可退 ${formatPrice(getRefundableAmount(order))}`}
                value={refundAmountInput}
                onInput={(e) => setRefundAmountInput(e.detail.value)}
              />
              <View className='refund-tips'>可退金额 {formatPrice(getRefundableAmount(order))}</View>
            </View>
            <View className='refund-field'>
              <Text className='refund-label'>退款原因<Text className='refund-required'>*</Text></Text>
              <Textarea
                className='refund-textarea'
                placeholder='请填写退款原因'
                  value={refundReason}
                  onInput={(e) => setRefundReason(e.detail.value)}
                  maxlength={200}
                />
              </View>
              <View className='refund-field'>
                <Text className='refund-label'>凭证图片（可选，最多3张）</Text>
                <View className='refund-image-list'>
                  {refundImages.map((url, index) => (
                    <View key={url} className='refund-image-item'>
                      <Image className='refund-image' src={url} mode='aspectFill' />
                      <View className='refund-image-remove' onClick={() => handleRefundRemoveImage(index)}>×</View>
                    </View>
                  ))}
                  {refundImages.length < 3 && (
                    <View className='refund-image-add' onClick={handleRefundChooseImage}>
                      <Text className='refund-image-plus'>+</Text>
                    </View>
                  )}
                </View>
              </View>
            </View>
            <View className='refund-modal-footer'>
              <View className='refund-btn cancel' onClick={() => !refundSubmitting && !refundUploading && setRefundModalOpen(false)}>取消</View>
              <View
                className={`refund-btn confirm ${refundSubmitting || refundUploading ? 'disabled' : ''}`}
                onClick={handleRefundSubmit}
              >
                {refundSubmitting ? '提交中...' : '提交'}
              </View>
            </View>
          </View>
        </View>
      )}
    </View>
  )
}
