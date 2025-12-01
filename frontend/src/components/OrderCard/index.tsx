import { View, Image, Text } from '@tarojs/components'
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

  return (
    <View className='order-card' onClick={handleCardClick}>
      <View className='order-header'>
        <Text className='order-time'>{formatTime(order.created_at)}</Text>
        <Text className={`order-status ${order.status}`}>{getOrderStatusText(order.status)}</Text>
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
            <View className='product-price'>{Number(order.product?.price || 0).toFixed(2)}</View>
            <View className='product-quantity'>x{order.quantity || 0}</View>
          </View>
        </View>
      </View>

      <View className='order-total'>
        <Text className='label'>合计</Text>
        <Text className='amount'>{formatPrice(order.total_amount)}</Text>
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
