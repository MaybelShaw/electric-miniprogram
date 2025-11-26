import { useState, useEffect } from 'react'
import { View, ScrollView, Image, Text, Input } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { addressService } from '../../services/address'
import { productService } from '../../services/product'
import { orderService } from '../../services/order'
import { Address, Product } from '../../types'
import './index.scss'

interface OrderItem {
  product_id: number
  quantity: number
  product?: Product
}

export default function OrderConfirm() {
  const [address, setAddress] = useState<Address | null>(null)
  const [items, setItems] = useState<OrderItem[]>([])
  const [note, setNote] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [fromCart, setFromCart] = useState(false)

  useEffect(() => {
    const instance = Taro.getCurrentInstance()
    const params = instance.router?.params || {}
    
    // 检查是否从购物车来（多商品模式）
    if (params.items) {
      try {
        const itemsData = JSON.parse(decodeURIComponent(params.items))
        loadMultipleProducts(itemsData)
        setFromCart(params.fromCart === 'true')
      } catch (error) {
        Taro.showToast({ title: '参数错误', icon: 'none' })
      }
    }
    // 单商品模式（从商品详情页来）
    else if (params.productId) {
      const singleItem: OrderItem = {
        product_id: Number(params.productId),
        quantity: Number(params.quantity) || 1
      }
      loadMultipleProducts([singleItem])
      setFromCart(params.fromCart === 'true')
    }
    
    loadDefaultAddress()

    // 监听地址选择事件
    const handleAddressSelected = (selectedAddress: Address) => {
      setAddress(selectedAddress)
    }

    Taro.eventCenter.on('addressSelected', handleAddressSelected)

    return () => {
      Taro.eventCenter.off('addressSelected', handleAddressSelected)
    }
  }, [])

  const loadMultipleProducts = async (orderItems: OrderItem[]) => {
    try {
      // 加载所有商品的详细信息
      const productsPromises = orderItems.map(item => 
        productService.getProductDetail(item.product_id)
      )
      const products = await Promise.all(productsPromises)
      
      // 将商品信息关联到订单项
      const itemsWithProducts = orderItems.map((item, index) => ({
        ...item,
        product: products[index]
      }))
      
      setItems(itemsWithProducts)
    } catch (error) {
      Taro.showToast({ title: '加载商品失败', icon: 'none' })
    }
  }

  const loadDefaultAddress = async () => {
    try {
      const addresses = await addressService.getAddresses()
      const defaultAddr = addresses.find(addr => addr.is_default) || addresses[0]
      setAddress(defaultAddr || null)
    } catch (error) {
      // 静默失败
    }
  }

  const handleSelectAddress = () => {
    Taro.navigateTo({
      url: '/pages/address-list/index?select=true'
    })
  }

  const handleSubmit = async () => {
    if (!address) {
      Taro.showToast({ title: '请选择收货地址', icon: 'none' })
      return
    }

    if (items.length === 0) return

    if (submitting) return

    setSubmitting(true)
    try {
      // 使用批量创建订单API
      const res = await orderService.createBatchOrders({
        items: items.map(item => ({
          product_id: item.product_id,
          quantity: item.quantity
        })),
        address_id: address.id,
        note
      })

      Taro.showToast({ title: '订单创建成功', icon: 'success' })
      
      // 如果是从购物车来的，清空购物车中对应的商品
      if (fromCart) {
        try {
          const { cartService } = await import('../../services/cart')
          // 删除所有已结算的商品
          for (const item of items) {
            await cartService.removeItem(item.product_id)
          }
        } catch (error) {
          // 静默失败
        }
      }
      
      // 如果只有一个订单，跳转到订单详情
      // 如果有多个订单，跳转到订单列表
      setTimeout(() => {
        if (res.orders.length === 1) {
          Taro.redirectTo({ url: `/pages/order-detail/index?id=${res.orders[0].id}` })
        } else {
          Taro.redirectTo({ url: `/pages/order-list/index` })
        }
      }, 1500)
    } catch (error: any) {
      Taro.showToast({ title: error.message || '创建订单失败', icon: 'none' })
    } finally {
      setSubmitting(false)
    }
  }

  if (items.length === 0 || items.some(item => !item.product)) {
    return (
      <View className='order-confirm loading'>
        <View className='loading-text'>加载中...</View>
      </View>
    )
  }

  // 计算总金额
  const finalAmount = items.reduce((sum, item) => {
    if (item.product) {
      return sum + parseFloat(item.product.price) * item.quantity
    }
    return sum
  }, 0)

  return (
    <View className='order-confirm'>
      <ScrollView className='content' scrollY>
        {/* 收货地址 */}
        <View className='address-card' onClick={handleSelectAddress}>
          <View className='address-icon'>📍</View>
          {address ? (
            <View className='address-content'>
              <View className='address-header'>
                <Text className='contact-name'>{address.contact_name}</Text>
                <Text className='phone'>{address.phone}</Text>
              </View>
              <View className='address-detail'>
                {address.province}{address.city}{address.district}{address.detail}
              </View>
            </View>
          ) : (
            <View className='address-content'>
              <View className='no-address-text'>请选择收货地址</View>
            </View>
          )}
          <View className='arrow-right'>›</View>
        </View>

        {/* 商品信息卡片 */}
        <View className='product-card'>
          {items.map((item, index) => (
            <View key={index} className='product-item'>
              <Image className='product-image' src={item.product!.main_images[0]} mode='aspectFill' />
              <View className='product-info'>
                <View className='product-name'>{item.product!.name}</View>
                <View className='product-bottom'>
                  <View className='product-price'>
                    <Text className='price-symbol'>¥</Text>
                    <Text className='price-value'>{parseFloat(item.product!.price).toFixed(2)}</Text>
                  </View>
                  <View className='quantity-text'>x{item.quantity}</View>
                </View>
              </View>
            </View>
          ))}
        </View>

        {/* 备注 */}
        <View className='note-card'>
          <Text className='note-label'>备注</Text>
          <Input
            className='note-input'
            placeholder='无备注'
            value={note}
            onInput={(e) => setNote(e.detail.value)}
          />
          <View className='arrow-right'>›</View>
        </View>

        {/* 底部占位 */}
        <View className='bottom-placeholder' />
      </ScrollView>

      {/* 底部提交栏 */}
      <View className='footer-bar'>
        <View className='footer-left'>
          <View className='total-info'>
            <Text className='total-label'>合计：</Text>
            <Text className='total-price'>¥{finalAmount.toFixed(2)}</Text>
          </View>
        </View>
        <View className='submit-btn' onClick={handleSubmit}>
          {submitting ? '提交中...' : '提交订单'}
        </View>
      </View>
    </View>
  )
}
