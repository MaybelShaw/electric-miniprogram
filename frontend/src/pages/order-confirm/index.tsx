import { useState, useEffect, useMemo } from 'react'
import { View, ScrollView, Image, Text, Input } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { addressService } from '../../services/address'
import { productService } from '../../services/product'
import { orderService } from '../../services/order'
import { userService } from '../../services/user'
import { creditService } from '../../services/credit'
import { Address, Product, ProductSKU, User } from '../../types'
import { resolveLocalMediaUrl } from '../../utils/media'
import AppIcon from '../../components/AppIcon'
import BottomActionBar from '../../components/BottomActionBar'
import './index.scss'

interface OrderItem {
  product_id: number
  quantity: number
  sku_id?: number | null
  store_id?: number
  store_name?: string
  store_logo?: string
  product?: Product
  sku?: ProductSKU | null
}

interface OrderStoreGroup {
  store_id: number
  store_name: string
  store_logo?: string
  items: OrderItem[]
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

    if (params.items) {
      try {
        const itemsData = JSON.parse(decodeURIComponent(params.items))
        loadMultipleProducts(itemsData)
        setFromCart(params.fromCart === 'true')
      } catch (error) {
        Taro.showToast({ title: '参数错误', icon: 'none' })
      }
    } else if (params.productId) {
      const singleItem: OrderItem = {
        product_id: Number(params.productId),
        quantity: Number(params.quantity) || 1,
        sku_id: params.skuId ? Number(params.skuId) : undefined,
      }
      loadMultipleProducts([singleItem])
      setFromCart(params.fromCart === 'true')
    }

    loadDefaultAddress()
    loadUserInfo()

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

      if (userData.role === 'dealer') {
        try {
          const account = await creditService.getMyAccount()
          setCreditAccount(account)
        } catch (error) {
          // 没有信用账户时保持在线支付。
        }
      }
    } catch (error) {
      // 静默失败，避免阻断普通下单。
    }
  }

  const loadMultipleProducts = async (orderItems: OrderItem[]) => {
    try {
      const products = await Promise.all(
        orderItems.map(item => productService.getProductDetail(item.product_id))
      )
      const itemsWithProducts = orderItems.map((item, index) => ({
        ...item,
        product: products[index],
        sku: item.sku_id ? products[index].skus?.find((sku) => sku.id === item.sku_id) || null : null,
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
      // 地址缺失时让用户在页面上选择。
    }
  }

  const handleSelectAddress = () => {
    Taro.navigateTo({
      url: '/pages/address-list/index?select=true',
    })
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

  const getStoreId = (item: OrderItem) => item.store_id || item.product?.store_id || item.product?.store || 0

  const orderGroups = useMemo<OrderStoreGroup[]>(() => {
    const groups = new Map<number, OrderStoreGroup>()
    items.forEach(item => {
      const storeId = getStoreId(item)
      if (!groups.has(storeId)) {
        groups.set(storeId, {
          store_id: storeId,
          store_name: item.store_name || `店铺 ${storeId || ''}`.trim(),
          store_logo: item.store_logo,
          items: [],
        })
      }
      groups.get(storeId)!.items.push(item)
    })
    return Array.from(groups.values())
  }, [items])

  const finalAmount = items.reduce((sum, item) => {
    return sum + getItemPrice(item) * item.quantity
  }, 0)

  const handleSubmit = async () => {
    if (!address) {
      Taro.showToast({ title: '请选择收货地址', icon: 'none' })
      return
    }

    if (items.length === 0 || submitting) return

    if (paymentMethod === 'credit') {
      if (!creditAccount) {
        Taro.showToast({ title: '您还没有信用账户', icon: 'none' })
        return
      }
      const availableCredit = parseFloat(creditAccount.available_credit)
      if (availableCredit < finalAmount) {
        Taro.showToast({ title: `信用额度不足，可用额度 ¥${availableCredit.toFixed(2)}`, icon: 'none' })
        return
      }
    }

    setSubmitting(true)
    try {
      const res = await orderService.createBatchOrders({
        items: items.map(item => ({
          product_id: item.product_id,
          quantity: item.quantity,
          sku_id: item.sku_id,
        })),
        address_id: address.id,
        note,
        payment_method: paymentMethod,
      })

      Taro.showToast({ title: '订单创建成功', icon: 'success' })

      if (paymentMethod === 'credit') {
        Taro.eventCenter.trigger('creditAccountUpdated')
      }

      if (fromCart) {
        try {
          const { cartService } = await import('../../services/cart')
          for (const item of items) {
            await cartService.removeItem(item.product_id, item.sku_id)
          }
        } catch (error) {
          // 订单已创建，购物车清理失败不阻断跳转。
        }
      }

      const createdOrders = res.orders && res.orders.length > 0 ? res.orders : (res.order ? [res.order] : [])
      setTimeout(() => {
        if (createdOrders.length === 1) {
          Taro.redirectTo({ url: `/pages/order-detail/index?id=${createdOrders[0].id}` })
        } else {
          Taro.redirectTo({ url: '/pages/order-list/index' })
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

  return (
    <View className='order-confirm'>
      <ScrollView className='content' scrollY>
        <View className='address-card' onClick={handleSelectAddress}>
          <View className='address-icon'><AppIcon name='location' tone='primary' /></View>
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
          <View className='arrow-right' />
        </View>

        <View className='order-confirm-product-card'>
          {orderGroups.map(group => (
            <View key={group.store_id} className='order-store-group'>
              <View className='store-header'>
                {group.store_logo ? (
                  <Image className='store-logo' src={resolveLocalMediaUrl(group.store_logo)} mode='aspectFill' />
                ) : (
                  <View className='store-logo fallback'>{group.store_name.charAt(0)}</View>
                )}
                <Text className='store-name'>{group.store_name}</Text>
                <Text className='store-count'>{group.items.length} 件</Text>
              </View>

              {group.items.map((item, index) => (
                <View key={`${item.product_id}-${item.sku_id || 'default'}-${index}`} className='product-item'>
                  <Image className='product-image' src={resolveLocalMediaUrl(item.sku?.image || item.product!.main_images[0])} mode='aspectFill' />
                  <View className='product-info'>
                    <View className='product-name'>{item.product!.name}</View>
                    {item.sku?.specs && (
                      <View className='product-spec'>{Object.values(item.sku.specs).join(' / ')}</View>
                    )}
                    <View className='product-bottom'>
                      <View className='product-price'>
                        <Text className='price-symbol'>¥</Text>
                        <Text className='price-value'>{getItemPrice(item).toFixed(2)}</Text>
                      </View>
                      <View className='quantity-text'>x{item.quantity}</View>
                    </View>
                  </View>
                </View>
              ))}
            </View>
          ))}
        </View>

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

        <View className='note-card'>
          <Text className='note-label'>备注</Text>
          <Input
            className='note-input'
            placeholder='无备注'
            value={note}
            onInput={(e) => setNote(e.detail.value)}
          />
          <View className='arrow-right' />
        </View>

        <View className='bottom-placeholder' />
      </ScrollView>

      <BottomActionBar className='footer-bar'>
        <View className='footer-left'>
          <View className='total-info'>
            <Text className='total-label'>合计：</Text>
            <Text className='total-price'>¥{finalAmount.toFixed(2)}</Text>
          </View>
        </View>
        <View className='submit-btn' onClick={handleSubmit}>
          {submitting ? '提交中...' : '提交订单'}
        </View>
      </BottomActionBar>
    </View>
  )
}
