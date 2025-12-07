import { useState } from 'react'
import { View, ScrollView, Text } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { addressService } from '../../services/address'
import { Address } from '../../types'
import './index.scss'

export default function AddressList() {
  const [addresses, setAddresses] = useState<Address[]>([])
  const [selectMode, setSelectMode] = useState(false)

  useDidShow(() => {
    loadAddresses()
    
    // 检查是否是选择模式
    const instance = Taro.getCurrentInstance()
    const isSelect = instance.router?.params?.select === 'true'
    setSelectMode(isSelect)
  })

  const loadAddresses = async () => {
    try {
      const data = await addressService.getAddresses()
      setAddresses(data)
    } catch (error) {
      Taro.showToast({ title: '加载失败', icon: 'none' })
    }
  }

  const handleSetDefault = async (id: number) => {
    try {
      await addressService.setDefaultAddress(id)
      loadAddresses()
      Taro.showToast({ title: '设置成功', icon: 'success' })
    } catch (error) {
      Taro.showToast({ title: '设置失败', icon: 'none' })
    }
  }

  const handleDelete = async (id: number) => {
    const res = await Taro.showModal({
      title: '提示',
      content: '确定要删除该地址吗？'
    })

    if (res.confirm) {
      try {
        await addressService.deleteAddress(id)
        setAddresses(addresses.filter(item => item.id !== id))
        Taro.showToast({ title: '删除成功', icon: 'success' })
      } catch (error) {
        Taro.showToast({ title: '删除失败', icon: 'none' })
      }
    }
  }

  const handleEdit = (id: number) => {
    Taro.navigateTo({ url: `/pages/address-edit/index?id=${id}` })
  }

  const handleAdd = () => {
    Taro.navigateTo({ url: '/pages/address-edit/index' })
  }

  const handleSelectAddress = (address: Address) => {
    if (selectMode) {
      // 选择模式：返回选中的地址
      Taro.eventCenter.trigger('addressSelected', address)
      Taro.navigateBack()
    }
  }

  return (
    <View className='address-list'>
      <ScrollView className='content' scrollY>
        {addresses.map(address => (
          <View 
            key={address.id} 
            className='address-item'
            onClick={() => handleSelectAddress(address)}
          >
            <View className='address-info'>
              <View className='address-header'>
                <Text className='contact-name'>{address.contact_name}</Text>
                <Text className='phone'>{address.phone}</Text>
                {address.is_default && <View className='default-tag'>默认</View>}
              </View>
              <View className='address-detail'>
                {address.province} {address.city} {address.district} {address.detail}
              </View>
            </View>
            {!selectMode && (
              <View className='address-actions'>
                {!address.is_default && (
                  <View 
                    className='action-btn' 
                    onClick={(e) => {
                      e.stopPropagation()
                      handleSetDefault(address.id)
                    }}
                  >
                    设为默认
                  </View>
                )}
                <View 
                  className='action-btn edit-btn' 
                  onClick={(e) => {
                    e.stopPropagation()
                    handleEdit(address.id)
                  }}
                >
                  编辑
                </View>
                <View 
                  className='action-btn delete-btn' 
                  onClick={(e) => {
                    e.stopPropagation()
                    handleDelete(address.id)
                  }}
                >
                  删除
                </View>
              </View>
            )}
          </View>
        ))}
      </ScrollView>

      <View className='bottom-bar'>
        <View className='add-btn' onClick={handleAdd}>
          新增收货地址
        </View>
      </View>
    </View>
  )
}
