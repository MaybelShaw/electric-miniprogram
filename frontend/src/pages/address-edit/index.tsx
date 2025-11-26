import { useState, useEffect } from 'react'
import { View, Input, Switch } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { addressService } from '../../services/address'
import { Address } from '../../types'
import './index.scss'

export default function AddressEdit() {
  const [id, setId] = useState<number | null>(null)
  const [formData, setFormData] = useState({
    contact_name: '',
    phone: '',
    province: '',
    city: '',
    district: '',
    detail: '',
    is_default: false
  })
  const [submitting, setSubmitting] = useState(false)
  const [fullAddress, setFullAddress] = useState('')
  const [parsing, setParsing] = useState(false)

  useEffect(() => {
    const instance = Taro.getCurrentInstance()
    const addressId = instance.router?.params?.id
    
    if (addressId) {
      setId(Number(addressId))
      loadAddress(Number(addressId))
    }
  }, [])

  const loadAddress = async (addressId: number) => {
    try {
      const addresses = await addressService.getAddresses()
      const address = addresses.find(item => item.id === addressId)
      if (address) {
        setFormData({
          contact_name: address.contact_name,
          phone: address.phone,
          province: address.province,
          city: address.city,
          district: address.district,
          detail: address.detail,
          is_default: address.is_default
        })
      }
    } catch (error) {
      Taro.showToast({ title: '加载失败', icon: 'none' })
    }
  }

  const handleInputChange = (field: string, value: string) => {
    setFormData({ ...formData, [field]: value })
  }

  const handleSwitchChange = (e: any) => {
    setFormData({ ...formData, is_default: e.detail.value })
  }

  const handleParseAddress = async () => {
    if (!fullAddress.trim()) {
      Taro.showToast({ title: '请输入完整地址', icon: 'none' })
      return
    }

    if (parsing) return

    setParsing(true)
    try {
      const result = await addressService.parseAddress(fullAddress)
      
      if (result.success && result.data) {
        // 更新表单数据
        setFormData({
          ...formData,
          province: result.data.province || '',
          city: result.data.city || '',
          district: result.data.district || '',
          detail: result.data.detail || ''
        })
        Taro.showToast({ title: '识别成功', icon: 'success' })
        setFullAddress('') // 清空输入框
      } else {
        Taro.showToast({ 
          title: result.message || '识别失败，请手动填写', 
          icon: 'none' 
        })
      }
    } catch (error: any) {
      Taro.showToast({ 
        title: error.message || '识别失败，请手动填写', 
        icon: 'none' 
      })
    } finally {
      setParsing(false)
    }
  }

  const handleSubmit = async () => {
    // 验证
    if (!formData.contact_name.trim()) {
      Taro.showToast({ title: '请输入联系人', icon: 'none' })
      return
    }
    if (!formData.phone.trim()) {
      Taro.showToast({ title: '请输入手机号', icon: 'none' })
      return
    }
    if (!/^1[3-9]\d{9}$/.test(formData.phone)) {
      Taro.showToast({ title: '手机号格式不正确', icon: 'none' })
      return
    }
    if (!formData.province.trim() || !formData.city.trim() || !formData.district.trim()) {
      Taro.showToast({ title: '请完整填写省市区', icon: 'none' })
      return
    }
    if (!formData.detail.trim()) {
      Taro.showToast({ title: '请输入详细地址', icon: 'none' })
      return
    }

    if (submitting) return

    setSubmitting(true)
    try {
      if (id) {
        await addressService.updateAddress(id, formData)
        Taro.showToast({ title: '修改成功', icon: 'success' })
      } else {
        await addressService.createAddress(formData as any)
        Taro.showToast({ title: '添加成功', icon: 'success' })
      }
      
      setTimeout(() => {
        Taro.navigateBack()
      }, 1500)
    } catch (error) {
      Taro.showToast({ title: '保存失败', icon: 'none' })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <View className='address-edit'>
      <View className='form'>
        <View className='form-item'>
          <View className='label'>联系人</View>
          <Input
            className='input'
            placeholder='请输入联系人姓名'
            value={formData.contact_name}
            onInput={(e) => handleInputChange('contact_name', e.detail.value)}
          />
        </View>

        <View className='form-item'>
          <View className='label'>手机号</View>
          <Input
            className='input'
            type='number'
            placeholder='请输入手机号'
            value={formData.phone}
            onInput={(e) => handleInputChange('phone', e.detail.value)}
          />
        </View>

        <View className='smart-parse-section'>
          <View className='section-title'>智能识别地址</View>
          <View className='parse-input-wrapper'>
            <Input
              className='parse-input'
              placeholder='粘贴完整地址，如：广东省深圳市南山区科技园南区XX路XX号'
              value={fullAddress}
              onInput={(e) => setFullAddress(e.detail.value)}
            />
          </View>
          <View className='parse-btn' onClick={handleParseAddress}>
            {parsing ? '识别中...' : '智能识别'}
          </View>
          <View className='parse-tip'>提示：粘贴完整地址后点击识别，系统将自动填充下方表单</View>
        </View>

        <View className='form-item'>
          <View className='label'>省份</View>
          <Input
            className='input'
            placeholder='请输入省份'
            value={formData.province}
            onInput={(e) => handleInputChange('province', e.detail.value)}
          />
        </View>

        <View className='form-item'>
          <View className='label'>城市</View>
          <Input
            className='input'
            placeholder='请输入城市'
            value={formData.city}
            onInput={(e) => handleInputChange('city', e.detail.value)}
          />
        </View>

        <View className='form-item'>
          <View className='label'>区县</View>
          <Input
            className='input'
            placeholder='请输入区县'
            value={formData.district}
            onInput={(e) => handleInputChange('district', e.detail.value)}
          />
        </View>

        <View className='form-item'>
          <View className='label'>详细地址</View>
          <Input
            className='input'
            placeholder='请输入详细地址'
            value={formData.detail}
            onInput={(e) => handleInputChange('detail', e.detail.value)}
          />
        </View>

        <View className='form-item switch-item'>
          <View className='label'>设为默认地址</View>
          <Switch checked={formData.is_default} onChange={handleSwitchChange} color='#1989FA' />
        </View>
      </View>

      <View className='submit-btn' onClick={handleSubmit}>
        {submitting ? '保存中...' : '保存'}
      </View>
    </View>
  )
}
