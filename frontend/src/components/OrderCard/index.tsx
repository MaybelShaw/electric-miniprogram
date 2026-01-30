import { View, Image, Text } from '@tarojs/components'
import { useState, useEffect } from 'react'
import { Order } from '../../types'
import { formatPrice, getOrderStatusText, formatTime } from '../../utils/format'
import { BASE_URL } from '../../utils/request'
import './index.scss'

interface OrderCardProps {
  order: Order
  onCancel?: (id: number) => void
  onPay?: (e: any, id: number) => void
  onConfirmReceipt?: (id: number) => void
  onClick?: (id: number) => void
}

export default function OrderCard({ 
  order, 
  onCancel, 
  onPay, 
  onConfirmReceipt,
  onClick 
}: OrderCardProps) {
  
  const [timeLeft, setTimeLeft] = useState('')
  const primaryItem = order.items && order.items.length > 0 ? order.items[0] : null
  const displayProduct = primaryItem?.product || order.product
  const resolveImageUrl = (url?: string) => {
    if (!url) return ''
    if (url.startsWith('https://')) return url
    if (url.startsWith('http://')) return `https://${url.slice(7)}`
    if (url.startsWith('//')) return `https:${url}`
    const base = BASE_URL.replace(/\/api\/?$/, '')
    if (url.startsWith('/')) return `${base}${url}`
    return `${base}/${url}`
  }
  const displayImage = resolveImageUrl(primaryItem?.snapshot_image) ||
    resolveImageUrl(displayProduct?.main_images?.[0]) ||
    '/assets/icons/product.png'
  const specsText = primaryItem?.sku_specs ? Object.values(primaryItem.sku_specs).join(' / ') : ''
  const resolveNumber = (value: any) => {
    const num = Number(value)
    return Number.isFinite(num) ? num : 0
  }
  const refundedAmount = resolveNumber(order.refunded_amount)
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
    if (order.status !== 'pending' || !order.expires_at) return

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
  }, [order.status, order.expires_at])

  const handleCardClick = () => {
    onClick?.(order.id)
  }

  const handleCancel = (e: any) => {
    e.stopPropagation()
    onCancel?.(order.id)
  }

  const handlePay = (e: any) => {
    e.stopPropagation()
    onPay?.(e, order.id)
  }

  const handleConfirm = (e: any) => {
    e.stopPropagation()
    onConfirmReceipt?.(order.id)
  }

  const hasActions = 
    ((order.status === 'pending' || order.status === 'paid') && !!onCancel) ||
    (order.status === 'pending' && !!onPay) ||
    (order.status === 'shipped' && !!onConfirmReceipt)

  const getDisplayStatus = () => {
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

  const getStatusClass = () => {
    if (order.return_info) {
      if (order.return_info.status === 'rejected') return 'cancelled';
      return 'returning'; // You might need to add this class to OrderCard.scss too
    }
    if (order.refund_pending) {
      return 'refunding'
    }
    if (refundedAmount > 0) {
      return 'refunded'
    }
    return order.status;
  }

  return (
    <View className='order-card' onClick={handleCardClick}>
      <View className='order-header'>
        {order.status === 'pending' && timeLeft ? (
          <Text className='order-countdown'>剩余 {timeLeft}</Text>
        ) : (
          <Text className='order-time'>{formatTime(order.created_at)}</Text>
        )}
        <Text className={`order-status ${getStatusClass()}`}>{getDisplayStatus()}</Text>
      </View>
      
      <View className='order-content'>
        <Image
          className='product-image'
          src={displayImage}
          mode='aspectFill'
        />
        <View className='product-info'>
          <View className='product-name'>
            {displayProduct?.name || '商品'}
            {order.items && order.items.length > 1 ? (
              <Text className='item-count'> 等{order.items.length}件</Text>
            ) : null}
          </View>
          {specsText ? <View className='product-spec'>{specsText}</View> : null}
          <View className='product-bottom'>
            <View className='product-price'>
              {formatPrice(
                primaryItem
                  ? primaryItem.unit_price
                  : (order.product?.price || 0)
              )}
            </View>
            <View className='product-quantity'>x{order.quantity || 0}</View>
          </View>
        </View>
      </View>

      <View className='order-total'>
        <Text className='label'>实付款</Text>
        <Text className='amount'>{formatPrice(order.actual_amount || order.total_amount)}</Text>
      </View>
      {refundedAmount > 0 && (
        <View className='order-total refund'>
          <Text className='label'>已退款</Text>
          <Text className='amount'>{formatPrice(refundedAmount)}</Text>
        </View>
      )}
      
      {hasActions && (
        <View className='order-footer'>
          <View className='order-actions'>
            {(order.status === 'pending' || order.status === 'paid') && onCancel && (
              <View className='cancel-btn' onClick={handleCancel}>
                取消订单
              </View>
            )}
            
            {order.status === 'pending' && onPay && (
              <View className='pay-btn' onClick={handlePay}>
                立即支付
              </View>
            )}
            
            {order.status === 'shipped' && onConfirmReceipt && (
              <View className='confirm-btn' onClick={handleConfirm}>
                确认收货
              </View>
            )}
          </View>
        </View>
      )}
    </View>
  )
}
