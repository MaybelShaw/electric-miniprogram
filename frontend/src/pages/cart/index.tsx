import { useState, useEffect, useMemo } from 'react'
import { View, ScrollView, Image, Text } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { cartService } from '../../services/cart'
import { TokenManager } from '../../utils/request'
import { Cart, CartItem } from '../../types'
import { formatPrice } from '../../utils/format'
import { resolveLocalMediaUrl } from '../../utils/media'
import EmptyState from '../../components/EmptyState'
import QuantityStepper from '../../components/QuantityStepper'
import './index.scss'

interface CartStoreGroupView {
  store_id: number
  store_name: string
  store_logo?: string
  items: CartItem[]
}

export default function CartPage() {
  const [cartItems, setCartItems] = useState<CartItem[]>([])
  const [allSelected, setAllSelected] = useState(false)
  const [previousItemIds, setPreviousItemIds] = useState<Set<number>>(new Set())

  useDidShow(() => {
    if (TokenManager.getAccessToken()) {
      loadCart()
    } else {
      setCartItems([])
      setAllSelected(false)
      setPreviousItemIds(new Set())
    }
  })

  useEffect(() => {
    checkAllSelected()
  }, [cartItems])

  useEffect(() => {
    const handleLogout = () => {
      setCartItems([])
      setAllSelected(false)
      setPreviousItemIds(new Set())
    }

    const handleLogin = () => {
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

  const isItemAvailable = (item: CartItem) => item.is_available !== false

  const applyCartData = (data: Cart) => {
    const currentSelectionMap = new Map<number, boolean>()
    cartItems.forEach(item => {
      currentSelectionMap.set(item.id, item.selected || false)
    })

    const newItems = data.items.map(item => {
      const available = isItemAvailable(item)
      if (!available) {
        return { ...item, selected: false }
      }
      if (previousItemIds.has(item.id)) {
        return {
          ...item,
          selected: currentSelectionMap.get(item.id) || false,
        }
      }
      return { ...item, selected: true }
    })

    setPreviousItemIds(new Set(data.items.map(item => item.id)))
    setCartItems(newItems)
  }

  const loadCart = async () => {
    try {
      const data = await cartService.getCart()
      applyCartData(data)
    } catch (error) {
      // 保持当前购物车状态，避免网络抖动时闪空。
    }
  }

  const getStoreId = (item: CartItem) => item.store_id || item.product.store_id || item.product.store || 0

  const cartGroups = useMemo<CartStoreGroupView[]>(() => {
    const groups = new Map<number, CartStoreGroupView>()
    cartItems.forEach(item => {
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
  }, [cartItems])

  const checkAllSelected = () => {
    const selectableItems = cartItems.filter(isItemAvailable)
    if (selectableItems.length === 0) {
      setAllSelected(false)
      return
    }
    setAllSelected(selectableItems.every(item => item.selected))
  }

  const handleSelectItem = (id: number) => {
    const target = cartItems.find(item => item.id === id)
    if (target && !isItemAvailable(target)) {
      Taro.showToast({ title: target.unavailable_reason || '商品暂不可结算', icon: 'none' })
      return
    }
    setCartItems(cartItems.map(item =>
      item.id === id ? { ...item, selected: !item.selected } : item
    ))
  }

  const handleSelectStore = (storeId: number) => {
    const storeItems = cartItems.filter(item => getStoreId(item) === storeId && isItemAvailable(item))
    const nextSelected = !storeItems.every(item => item.selected)
    setCartItems(cartItems.map(item =>
      getStoreId(item) === storeId && isItemAvailable(item)
        ? { ...item, selected: nextSelected }
        : item
    ))
  }

  const handleSelectAll = () => {
    const nextSelected = !allSelected
    setCartItems(cartItems.map(item =>
      isItemAvailable(item) ? { ...item, selected: nextSelected } : item
    ))
  }

  const handleUpdateQuantity = async (itemId: number, productId: number, quantity: number, skuId?: number | null) => {
    if (quantity <= 0) {
      handleRemoveItem(itemId, productId, skuId)
      return
    }

    try {
      const data = await cartService.updateItem(productId, quantity, skuId)
      applyCartData(data)
    } catch (error) {
      Taro.showToast({ title: '更新失败', icon: 'none' })
    }
  }

  const handleRemoveItem = async (itemId: number, productId: number, skuId?: number | null) => {
    const res = await Taro.showModal({
      title: '提示',
      content: '确定要删除该商品吗？',
    })

    if (res.confirm) {
      try {
        const data = await cartService.removeItem(productId, skuId)
        applyCartData(data)
        Taro.showToast({ title: '删除成功', icon: 'success' })
      } catch (error) {
        Taro.showToast({ title: '删除失败', icon: 'none' })
      }
    }
  }

  const handleClearCart = async () => {
    const res = await Taro.showModal({
      title: '提示',
      content: '确定要清空购物车吗？',
    })

    if (res.confirm) {
      try {
        const data = await cartService.clearCart()
        applyCartData(data)
        Taro.showToast({ title: '清空成功', icon: 'success' })
      } catch (error) {
        Taro.showToast({ title: '清空失败', icon: 'none' })
      }
    }
  }

  const handleCheckout = () => {
    const selectedItems = cartItems.filter(item => item.selected && isItemAvailable(item))
    if (selectedItems.length === 0) {
      Taro.showToast({ title: '请选择商品', icon: 'none' })
      return
    }

    const items = selectedItems.map(item => ({
      product_id: item.product_id,
      quantity: item.quantity,
      sku_id: item.sku_id,
      store_id: getStoreId(item),
      store_name: item.store_name,
      store_logo: item.store_logo,
    }))
    const itemsParam = encodeURIComponent(JSON.stringify(items))
    Taro.navigateTo({
      url: `/pages/order-confirm/index?items=${itemsParam}&fromCart=true`,
    })
  }

  const goToDetail = (id: number) => {
    Taro.navigateTo({ url: `/pages/product-detail/index?id=${id}` })
  }

  const goToStore = (storeId: number) => {
    if (storeId) {
      Taro.navigateTo({ url: `/pages/store-detail/index?id=${storeId}` })
    }
  }

  const goToLogin = () => {
    Taro.switchTab({ url: '/pages/profile/index' })
  }

  const getItemPrice = (item: CartItem) => {
    if (item.sku) {
      const skuBasePrice = Number(item.sku.display_price ?? item.sku.price ?? 0)
      return item.sku.discounted_price && Number(item.sku.discounted_price) < skuBasePrice
        ? Number(item.sku.discounted_price)
        : skuBasePrice
    }
    const basePrice = Number(item.product.display_price ?? item.product.price ?? 0)
    return item.product.discounted_price && Number(item.product.discounted_price) < basePrice
      ? Number(item.product.discounted_price)
      : basePrice
  }

  const getStoreSubtotal = (items: CartItem[]) =>
    items
      .filter(item => item.selected && isItemAvailable(item))
      .reduce((sum, item) => sum + getItemPrice(item) * item.quantity, 0)

  const totalPrice = cartItems
    .filter(item => item.selected && isItemAvailable(item))
    .reduce((sum, item) => sum + getItemPrice(item) * item.quantity, 0)

  const selectedCount = cartItems.filter(item => item.selected && isItemAvailable(item)).length

  if (!TokenManager.getAccessToken()) {
    return (
      <View className='cart empty'>
        <EmptyState title='请先登录' description='登录后可查看购物车和继续结算' icon='profile' actionText='立即登录' onAction={goToLogin} />
      </View>
    )
  }

  if (cartItems.length === 0) {
    return (
      <View className='cart empty'>
        <EmptyState
          title='购物车是空的'
          description='先挑几件适合家的好物'
          icon='cart'
          actionText='去逛逛'
          onAction={() => Taro.switchTab({ url: '/pages/home/index' })}
        />
      </View>
    )
  }

  return (
    <View className='cart'>
      <ScrollView className='cart-list' scrollY>
        {cartGroups.map(group => {
          const availableStoreItems = group.items.filter(isItemAvailable)
          const storeChecked = availableStoreItems.length > 0 && availableStoreItems.every(item => item.selected)
          const storeIndeterminate = availableStoreItems.some(item => item.selected) && !storeChecked

          return (
            <View key={group.store_id} className='cart-store-group'>
              <View className='store-header'>
                <View
                  className={`checkbox ${storeChecked ? 'checked' : ''} ${storeIndeterminate ? 'indeterminate' : ''}`}
                  onClick={() => handleSelectStore(group.store_id)}
                />
                <View className='store-info' onClick={() => goToStore(group.store_id)}>
                  {group.store_logo ? (
                    <Image className='store-logo' src={resolveLocalMediaUrl(group.store_logo)} mode='aspectFill' />
                  ) : (
                    <View className='store-logo fallback'>{group.store_name.charAt(0)}</View>
                  )}
                  <Text className='store-name'>{group.store_name}</Text>
                </View>
                <Text className='store-count'>{group.items.length} 件</Text>
              </View>

              {group.items.map(item => {
                const available = isItemAvailable(item)
                return (
                  <View key={item.id} className={`cart-item ${available ? '' : 'unavailable'}`}>
                    <View
                      className={`checkbox ${item.selected ? 'checked' : ''}`}
                      onClick={() => handleSelectItem(item.id)}
                    />
                    <Image
                      className='product-image'
                      src={resolveLocalMediaUrl(item.sku?.image || item.product.main_images[0])}
                      mode='aspectFill'
                      onClick={() => goToDetail(item.product.id)}
                    />
                    <View className='product-info'>
                      <View className='product-name' onClick={() => goToDetail(item.product.id)}>
                        {item.product.name}
                      </View>
                      {((item.sku_specs && Object.keys(item.sku_specs).length > 0) || (item.sku?.specs && Object.keys(item.sku.specs).length > 0)) && (
                        <View className='product-spec'>{Object.values(item.sku_specs || item.sku?.specs || {}).join(' / ')}</View>
                      )}
                      {!available && (
                        <View className='unavailable-reason'>{item.unavailable_reason || '商品暂不可结算'}</View>
                      )}
                      <View className='product-bottom'>
                        <View className='product-price'>
                          {formatPrice(getItemPrice(item))}
                        </View>
                        <QuantityStepper
                          value={item.quantity}
                          onChange={(value) => handleUpdateQuantity(item.id, item.product_id, value, item.sku_id)}
                        />
                      </View>
                    </View>
                    <View className='delete-btn' onClick={() => handleRemoveItem(item.id, item.product_id, item.sku_id)}>
                      删除
                    </View>
                  </View>
                )
              })}

              <View className='store-summary'>
                <Text>本店小计</Text>
                <Text className='store-subtotal'>{formatPrice(getStoreSubtotal(group.items))}</Text>
              </View>
            </View>
          )
        })}
      </ScrollView>

      <View className='cart-footer'>
        <View className='footer-left'>
          <View className={`checkbox ${allSelected ? 'checked' : ''}`} onClick={handleSelectAll} />
          <Text className='select-all-text'>全选</Text>
          <Text className='clear-text' onClick={handleClearCart}>清空</Text>
        </View>
        <View className='footer-right'>
          <View className='total-price'>
            <Text className='label'>合计：</Text>
            <Text className='price'>{formatPrice(totalPrice)}</Text>
          </View>
          <View className='checkout-btn' onClick={handleCheckout}>
            结算({selectedCount})
          </View>
        </View>
      </View>
    </View>
  )
}
