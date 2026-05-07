import { useState, useEffect } from 'react'
import { View, ScrollView, Image, Text, Input } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { addressService } from '../../services/address'
import { productService } from '../../services/product'
import { orderService } from '../../services/order'
import { userService } from '../../services/user'
import { creditService } from '../../services/credit'
import { Address, Product, ProductSKU, User } from '../../types'
import { resolveLocalMediaUrl } from '../../utils/media'
import './index.scss'

interface OrderItem {
  product_id: number
  quantity: number
  sku_id?: number | null
  product?: Product
  sku?: ProductSKU | null
}

export default function OrderConfirm() {
  const [address, setAddress] = useState<Address | null>(null)
  const [items, setItems] = useState<OrderItem[]>([])
  const [note, setNote] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [fromCart, setFromCart] = useState(false)
  const [user, setUser] = useState<User | null>(null)
  const [paymentMethod, setPaymentMethod] = useState<'online' | 'credit'>('online')
  const [creditAccount, setCreditAccount] = useState<any>(null)

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
        quantity: Number(params.quantity) || 1,
        sku_id: params.skuId ? Number(params.skuId) : undefined
      }
      loadMultipleProducts([singleItem])
      setFromCart(params.fromCart === 'true')
    }
    
    loadDefaultAddress()
    loadUserInfo()

    // 监听地址选择事件
    const handleAddressSelected = (selectedAddress: Address) => {
      setAddress(selectedAddress)
    }

    Taro.eventCenter.on('addressSelected', handleAddressSelected)

    return () => {
      Taro.eventCenter.off('addressSelected', handleAddressSelected)
    }
  }, [])

  const loadUserInfo = async () => {
    try {
      const userData = await userService.getProfile()
      setUser(userData)
      
      // 如果是经销商，加载信用账户
      if (userData.role === 'dealer') {
        try {
          const account = await creditService.getMyAccount()
          setCreditAccount(account)
        } catch (error) {
          // 没有信用账户，静默失败
        }
      }
    } catch (error) {
      // 静默失败
    }
  }

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
        product: products[index],
        sku: item.sku_id ? products[index].skus?.find((s) => s.id === item.sku_id) || null : null
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

    // 如果使用信用支付，检查额度
    if (paymentMethod === 'credit') {
      if (!creditAccount) {
        Taro.showToast({ title: '您还没有信用账户', icon: 'none' })
        return
      }
      const availableCredit = parseFloat(creditAccount.available_credit)
      if (availableCredit < finalAmount) {
        Taro.showToast({ title: `信用额度不足，可用额度: ¥${availableCredit.toFixed(2)}`, icon: 'none' })
        return
      }
    }

    setSubmitting(true)
    try {
      // 使用批量创建订单API
      const res = await orderService.createBatchOrders({
        items: items.map(item => ({
          product_id: item.product_id,
          quantity: item.quantity,
          sku_id: item.sku_id
        })),
        address_id: address.id,
        note,
        payment_method: paymentMethod
      })

      Taro.showToast({ title: '订单创建成功', icon: 'success' })
      
      // 如果使用信用支付，触发信用账户更新事件
      if (paymentMethod === 'credit') {
        Taro.eventCenter.trigger('creditAccountUpdated')
      }
      
      // 如果是从购物车来的，清空购物车中对应的商品
      if (fromCart) {
        try {
          const { cartService } = await import('../../services/cart')
          // 删除所有已结算的商品
          for (const item of items) {
            await cartService.removeItem(item.product_id, item.sku_id)
          }
        } catch (error) {
          // 静默失败
        }
      }
      
      // 如果只有一个订单，跳转到订单详情
      // 如果有多个订单，跳转到订单列表
      const createdOrders = res.orders && res.orders.length > 0 ? res.orders : (res.order ? [res.order] : [])
      setTimeout(() => {
        if (createdOrders.length === 1) {
          Taro.redirectTo({ url: `/pages/order-detail/index?id=${createdOrders[0].id}` })
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

  const getItemPrice = (item: OrderItem) => {
    if (item.sku) {
      const skuBasePrice = Number(item.sku.display_price ?? item.sku.price ?? 0)
      return item.sku.discounted_price && Number(item.sku.discounted_price) < skuBasePrice
        ? Number(item.sku.discounted_price)
        : skuBasePrice
    }
    if (item.product) {
      const basePrice = Number(item.product.display_price ?? item.product.price ?? 0)
      return item.product.discounted_price && Number(item.product.discounted_price) < basePrice
        ? Number(item.product.discounted_price)
        : basePrice
    }
    return 0
  }

  // 计算总金额
  const finalAmount = items.reduce((sum, item) => {
    const price = getItemPrice(item)
    return sum + price * item.quantity
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
      <View className='order-confirm-product-card'>
        {items.map((item, index) => (
            <View key={index} className='product-item'>
              <Image className='product-image' src={resolveLocalMediaUrl(item.sku?.image || item.product!.main_images[0])} mode='aspectFill' />
              <View className='product-info'>
                <View className='product-name'>{item.product!.name}</View>
                {item.sku?.specs && (
                  <View className='product-spec'>{Object.values(item.sku.specs).join(' / ')}</View>
                )}
                <View className='product-bottom'>
                  <View className='product-price'>
                    <Text className='price-symbol'>¥</Text>
                    <Text className='price-value'>
                      {getItemPrice(item).toFixed(2)}
                    </Text>
                  </View>
                  <View className='quantity-text'>x{item.quantity}</View>
                </View>
              </View>
            </View>
          ))}
        </View>

        {/* 支付方式 - 仅经销商显示 */}
        {user?.role === 'dealer' && creditAccount && (
          <View className='payment-card'>
            <Text className='payment-label'>支付方式</Text>
            <View className='payment-options'>
              <View 
                className={`payment-option ${paymentMethod === 'online' ? 'active' : ''}`}
                onClick={() => setPaymentMethod('online')}
              >
                <View className='option-radio'>
                  {paymentMethod === 'online' && <View className='radio-dot' />}
                </View>
                <Text className='option-text'>在线支付</Text>
              </View>
              <View 
                className={`payment-option ${paymentMethod === 'credit' ? 'active' : ''}`}
                onClick={() => setPaymentMethod('credit')}
              >
                <View className='option-radio'>
                  {paymentMethod === 'credit' && <View className='radio-dot' />}
                </View>
                <View className='option-content'>
                  <Text className='option-text'>信用支付</Text>
                  <Text className='option-hint'>
                    可用额度: ¥{parseFloat(creditAccount.available_credit).toLocaleString()}
                  </Text>
                </View>
              </View>
            </View>
          </View>
        )}

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
