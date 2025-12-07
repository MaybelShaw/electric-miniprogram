import { View, Image, Text } from '@tarojs/components'
import { useState, useEffect } from 'react'
import { Order } from '../../types'
import { formatPrice, getOrderStatusText, formatTime } from '../../utils/format'
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
  const displayImage = primaryItem?.snapshot_image || displayProduct?.main_images?.[0] || '/assets/default-product.png'
  const specsText = primaryItem?.sku_specs ? Object.values(primaryItem.sku_specs).join(' / ') : ''

  useEffect(() => {
    if (order.status !== 'pending' || !order.expires_at) return

    const calculateTimeLeft = () => {
      const now = new Date().getTime()
      const expireTime = new Date(order.expires_at!).getTime()
      const diff = expireTime - now

      if (diff <= 0) {
         setTimeLeft('已超时')
         return
      }

      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
      const seconds = Math.floor((diff % (1000 * 60)) / 1000)
      
      setTimeLeft(`${minutes}分${seconds}秒`)
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
        <Text className='label'>合计</Text>
        <Text className='amount'>{formatPrice(order.actual_amount || order.total_amount)}</Text>
      </View>
      
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
