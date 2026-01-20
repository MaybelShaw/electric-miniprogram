import { View, Text, Image, ScrollView } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useState, useEffect } from 'react'
import { fetchAllPaginated } from '../../../utils/request'
import { formatPrice } from '../../../utils/format'
import './index.scss'

export default function SelectProduct() {
  const [products, setProducts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const instance = Taro.getCurrentInstance()

  useEffect(() => {
    loadProducts()
  }, [])

  const loadProducts = async () => {
    try {
      setLoading(true)
      const data = await fetchAllPaginated<any>('/catalog/products/', {}, 100, true)
      setProducts(data)
    } catch (e) {
      console.error(e)
      Taro.showToast({ title: '加载商品失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }

  const handleSelect = (product: any) => {
    // Use getCurrentPages to reliably get the current page instance in Mini Program
    const pages = Taro.getCurrentPages()
    const current = pages[pages.length - 1]

    if (current && current.getOpenerEventChannel) {
      const eventChannel = current.getOpenerEventChannel()
      eventChannel.emit('acceptSelectedProduct', product)
    } else {
      console.error('Event channel not available')
      Taro.showToast({ title: '无法发送商品', icon: 'none' })
    }
    Taro.navigateBack()
  }

  const getSellingPrice = (product: any) => {
    const basePrice = Number(product.display_price ?? product.price ?? 0)
    return product.discounted_price && Number(product.discounted_price) < basePrice
      ? Number(product.discounted_price)
      : basePrice
  }

  return (
    <View className="select-product-page">
      <ScrollView scrollY className="product-list">
        {loading && <View className="loading">加载中...</View>}
        {!loading && products.length === 0 && <View className="empty">暂无商品</View>}
        
        {products.map(product => {
           const image = product.product_image_url || (product.main_images && product.main_images[0]) || ''
           return (
            <View key={product.id} className="product-item" onClick={() => handleSelect(product)}>
              <Image src={image} mode="aspectFill" className="product-img" />
              <View className="info">
                <Text className="name">{product.name}</Text>
                <Text className="price">{formatPrice(getSellingPrice(product))}</Text>
              </View>
            </View>
          )
        })}
      </ScrollView>
    </View>
  )
}
