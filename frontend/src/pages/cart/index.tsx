import { useState, useEffect } from 'react'
import { View, ScrollView, Image, Text } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { cartService } from '../../services/cart'
import { TokenManager } from '../../utils/request'
import { CartItem } from '../../types'
import { formatPrice } from '../../utils/format'
import './index.scss'

export default function Cart() {
  const [cartItems, setCartItems] = useState<CartItem[]>([])
  const [allSelected, setAllSelected] = useState(false)
  const [loading, setLoading] = useState(false)
  const [previousItemIds, setPreviousItemIds] = useState<Set<number>>(new Set())

  useDidShow(() => {
    if (TokenManager.getAccessToken()) {
      loadCart()
    } else {
      // 未登录时清空购物车状态
      setCartItems([])
    }
  })

  useEffect(() => {
    checkAllSelected()
  }, [cartItems])

  useEffect(() => {
    // 监听登出事件
    const handleLogout = () => {
      setCartItems([])
      setAllSelected(false)
      setPreviousItemIds(new Set())
    }

    // 监听登录成功事件
    const handleLogin = () => {
      // 登录成功后重新加载购物车
      if (TokenManager.getAccessToken()) {
        loadCart()
      }
    }

    Taro.eventCenter.on('userLogout', handleLogout)
    Taro.eventCenter.on('userLogin', handleLogin)

    return () => {
      Taro.eventCenter.off('userLogout', handleLogout)
      Taro.eventCenter.off('userLogin', handleLogin)
    }
  }, [])

  const loadCart = async () => {
    try {
      const data = await cartService.getCart()
      
      // 创建当前商品ID到勾选状态的映射
      const currentSelectionMap = new Map<number, boolean>()
      cartItems.forEach(item => {
        currentSelectionMap.set(item.id, item.selected || false)
      })
      
      // 处理新加载的商品
      const newItems = data.items.map(item => {
        // 如果是之前就存在的商品，保持原来的勾选状态
        if (previousItemIds.has(item.id)) {
          return { 
            ...item, 
            selected: currentSelectionMap.get(item.id) || false 
          }
        }
        // 如果是新商品，默认勾选
        return { ...item, selected: true }
      })
      
      // 更新商品ID集合
      const newItemIds = new Set(data.items.map(item => item.id))
      setPreviousItemIds(newItemIds)
      
      setCartItems(newItems)
    } catch (error) {
      // 静默失败
    }
  }

  const checkAllSelected = () => {
    if (cartItems.length === 0) {
      setAllSelected(false)
      return
    }
    setAllSelected(cartItems.every(item => item.selected))
  }

  const handleSelectItem = (id: number) => {
    setCartItems(cartItems.map(item =>
      item.id === id ? { ...item, selected: !item.selected } : item
    ))
  }

  const handleSelectAll = () => {
    const newSelected = !allSelected
    setCartItems(cartItems.map(item => ({ ...item, selected: newSelected })))
  }

  const handleUpdateQuantity = async (productId: number, quantity: number) => {
    if (quantity <= 0) {
      handleRemoveItem(productId)
      return
    }

    try {
      await cartService.updateItem(productId, quantity)
      setCartItems(cartItems.map(item =>
        item.product_id === productId ? { ...item, quantity } : item
      ))
    } catch (error) {
      Taro.showToast({ title: '更新失败', icon: 'none' })
    }
  }

  const handleRemoveItem = async (productId: number) => {
    const res = await Taro.showModal({
      title: '提示',
      content: '确定要删除该商品吗？'
    })

    if (res.confirm) {
      try {
        await cartService.removeItem(productId)
        setCartItems(cartItems.filter(item => item.product_id !== productId))
        Taro.showToast({ title: '删除成功', icon: 'success' })
      } catch (error) {
        Taro.showToast({ title: '删除失败', icon: 'none' })
      }
    }
  }

  const handleClearCart = async () => {
    const res = await Taro.showModal({
      title: '提示',
      content: '确定要清空购物车吗？'
    })

    if (res.confirm) {
      try {
        await cartService.clearCart()
        setCartItems([])
        Taro.showToast({ title: '清空成功', icon: 'success' })
      } catch (error) {
        Taro.showToast({ title: '清空失败', icon: 'none' })
      }
    }
  }

  const handleCheckout = () => {
    const selectedItems = cartItems.filter(item => item.selected)
    if (selectedItems.length === 0) {
      Taro.showToast({ title: '请选择商品', icon: 'none' })
      return
    }

    // 将选中的商品信息传递给确认订单页面
    const items = selectedItems.map(item => ({
      product_id: item.product_id,
      quantity: item.quantity
    }))
    
    // 使用URL参数传递商品列表（JSON字符串）
    const itemsParam = encodeURIComponent(JSON.stringify(items))
    Taro.navigateTo({ 
      url: `/pages/order-confirm/index?items=${itemsParam}&fromCart=true` 
    })
  }

  const goToDetail = (id: number) => {
    Taro.navigateTo({ url: `/pages/product-detail/index?id=${id}` })
  }

  const goToLogin = () => {
    // 跳转到"我的"页面（profile页面）
    Taro.switchTab({ url: '/pages/profile/index' })
  }

  // 计算总价
  const totalPrice = cartItems
    .filter(item => item.selected)
    .reduce((sum, item) => {
      const price = item.product.discounted_price && item.product.discounted_price < parseFloat(item.product.price)
        ? item.product.discounted_price
        : parseFloat(item.product.price)
      return sum + price * item.quantity
    }, 0)

  // 未登录状态
  if (!TokenManager.getAccessToken()) {
    return (
      <View className='cart empty'>
        <View className='empty-content'>
          <Image className='empty-icon' src='/assets/empty-cart.png' />
          <Text className='empty-text'>请先登录</Text>
          <View className='login-btn' onClick={goToLogin}>立即登录</View>
        </View>
      </View>
    )
  }

  // 购物车为空
  if (cartItems.length === 0) {
    return (
      <View className='cart empty'>
        <View className='empty-content'>
          <Image className='empty-icon' src='/assets/empty-cart.png' />
          <Text className='empty-text'>购物车是空的</Text>
          <View className='go-shopping-btn' onClick={() => Taro.switchTab({ url: '/pages/home/index' })}>
            去逛逛
          </View>
        </View>
      </View>
    )
  }

  return (
    <View className='cart'>
      <ScrollView className='cart-list' scrollY>
        {cartItems.map(item => (
          <View key={item.id} className='cart-item'>
            <View
              className={`checkbox ${item.selected ? 'checked' : ''}`}
              onClick={() => handleSelectItem(item.id)}
            />
            <Image
              className='product-image'
              src={item.product.main_images[0]}
              mode='aspectFill'
              onClick={() => goToDetail(item.product.id)}
            />
            <View className='product-info'>
              <View className='product-name' onClick={() => goToDetail(item.product.id)}>
                {item.product.name}
              </View>
              <View className='product-bottom'>
                <View className='product-price'>
                  {formatPrice(item.product.discounted_price && item.product.discounted_price < parseFloat(item.product.price)
                    ? item.product.discounted_price
                    : item.product.price)}
                </View>
                <View className='quantity-control'>
                  <View
                    className='btn minus'
                    onClick={() => handleUpdateQuantity(item.product_id, item.quantity - 1)}
                  >
                    -
                  </View>
                  <View className='quantity'>{item.quantity}</View>
                  <View
                    className='btn plus'
                    onClick={() => handleUpdateQuantity(item.product_id, item.quantity + 1)}
                  >
                    +
                  </View>
                </View>
              </View>
            </View>
            <View className='delete-btn' onClick={() => handleRemoveItem(item.product_id)}>
              删除
            </View>
          </View>
        ))}
      </ScrollView>

      <View className='cart-footer'>
        <View className='footer-left'>
          <View className={`checkbox ${allSelected ? 'checked' : ''}`} onClick={handleSelectAll} />
          <Text className='select-all-text'>全选</Text>
        </View>
        <View className='footer-right'>
          <View className='total-price'>
            <Text className='label'>合计：</Text>
            <Text className='price'>{formatPrice(totalPrice)}</Text>
          </View>
          <View className='checkout-btn' onClick={handleCheckout}>
            结算({cartItems.filter(item => item.selected).length})
          </View>
        </View>
      </View>
    </View>
  )
}
