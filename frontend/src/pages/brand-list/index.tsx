import { useState, useEffect } from 'react'
import { View, Image, ScrollView } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { productService } from '../../services/product'
import { Brand } from '../../types'
import './index.scss'

export default function BrandListPage() {
  const [brands, setBrands] = useState<Brand[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadBrands()
  }, [])

  const loadBrands = async () => {
    setLoading(true)
    try {
      const data = await productService.getBrands()
      setBrands(data)
    } catch (error) {
      Taro.showToast({
        title: '加载品牌失败',
        icon: 'none'
      })
    } finally {
      setLoading(false)
    }
  }

  const goToBrand = (brand: string) => {
    Taro.navigateTo({ url: `/pages/brand/index?brand=${brand}` })
  }

  return (
    <View className='brand-list-page'>
      {loading ? (
        <View className='loading-state'>加载中...</View>
      ) : brands.length > 0 ? (
        <ScrollView scrollY>
          <View className='brand-grid'>
            {brands.map(brand => (
              <View key={brand.id} className='brand-item' onClick={() => goToBrand(brand.name)}>
                <View className='brand-logo-wrapper'>
                  <Image className='brand-logo' src={brand.logo} mode='aspectFit' />
                </View>
                <View className='brand-name'>{brand.name}</View>
              </View>
            ))}
          </View>
        </ScrollView>
      ) : (
        <View className='empty-state'>暂无品牌</View>
      )}
    </View>
  )
}
