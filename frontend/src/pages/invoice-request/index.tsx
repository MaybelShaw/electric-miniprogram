import { useState, useEffect } from 'react'
import { View, Input, Picker, Text } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { orderService } from '../../services/order'
import './index.scss'

export default function InvoiceRequest() {
  const [orderId, setOrderId] = useState<number | null>(null)
  const [formData, setFormData] = useState({
    title: '',
    taxpayer_id: '',
    email: '',
    phone: '',
    address: '',
    bank_account: '',
    invoice_type: 'normal' // normal, special
  })
  const [submitting, setSubmitting] = useState(false)

  const invoiceTypes = [
    { key: 'normal', value: '普通发票' },
    { key: 'special', value: '专用发票' }
  ]

  useEffect(() => {
    const instance = Taro.getCurrentInstance()
    const id = instance.router?.params?.id
    if (id) {
      setOrderId(Number(id))
    } else {
      Taro.showToast({ title: '订单参数错误', icon: 'none' })
      setTimeout(() => Taro.navigateBack(), 1500)
    }
  }, [])

  const handleInputChange = (field: string, value: string) => {
    setFormData({ ...formData, [field]: value })
  }

  const handleTypeSelect = (type: string) => {
    setFormData({ ...formData, invoice_type: type })
  }

  const handleSubmit = async () => {
    if (!formData.title.trim()) {
      Taro.showToast({ title: '请输入发票抬头', icon: 'none' })
      return
    }
    if (!formData.email.trim()) {
      Taro.showToast({ title: '请输入接收邮箱', icon: 'none' })
      return
    }
    
    // 邮箱格式校验
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(formData.email.trim())) {
      Taro.showToast({ title: '请输入正确的邮箱地址', icon: 'none' })
      return
    }
    
    // 专用发票必填项校验
    if (formData.invoice_type === 'special') {
      if (!formData.taxpayer_id.trim()) {
        Taro.showToast({ title: '请输入纳税人识别号', icon: 'none' })
        return
      }
      if (!formData.address.trim()) {
        Taro.showToast({ title: '请输入公司地址', icon: 'none' })
        return
      }
      if (!formData.phone.trim()) {
        Taro.showToast({ title: '请输入联系电话', icon: 'none' })
        return
      }
      if (!formData.bank_account.trim()) {
        Taro.showToast({ title: '请输入开户行及账号', icon: 'none' })
        return
      }
    }

    if (submitting || !orderId) return

    setSubmitting(true)
    try {
      await orderService.requestInvoice(orderId, formData)
      Taro.showToast({ title: '申请成功', icon: 'success' })
      setTimeout(() => {
        Taro.navigateBack()
      }, 1500)
    } catch (error: any) {
      Taro.showToast({ title: error.message || '申请失败', icon: 'none' })
    } finally {
      setSubmitting(false)
    }
  }

  const isSpecial = formData.invoice_type === 'special'

  return (
    <View className='invoice-request'>
      <View className='form'>
        <View className='form-item'>
          <View className='label'>
            <Text className='required'>*</Text>
            发票类型
          </View>
          <View className='type-selector'>
            {invoiceTypes.map(type => (
              <View 
                key={type.key}
                className={`type-item ${formData.invoice_type === type.key ? 'active' : ''}`}
                onClick={() => handleTypeSelect(type.key)}
              >
                {type.value}
              </View>
            ))}
          </View>
        </View>

        <View className='form-item'>
          <View className='label'>
            <Text className='required'>*</Text>
            发票抬头
          </View>
          <Input
            className='input'
            placeholder='请输入发票抬头'
            value={formData.title}
            onInput={(e) => handleInputChange('title', e.detail.value)}
          />
        </View>

        <View className='form-item'>
          <View className='label'>
            {isSpecial && <Text className='required'>*</Text>}
            税号
          </View>
          <Input
            className='input'
            placeholder={isSpecial ? '请输入纳税人识别号' : '纳税人识别号（选填）'}
            value={formData.taxpayer_id}
            onInput={(e) => handleInputChange('taxpayer_id', e.detail.value)}
          />
        </View>

        <View className='form-item'>
          <View className='label'>
            <Text className='required'>*</Text>
            邮箱
          </View>
          <Input
            className='input'
            placeholder='接收电子发票的邮箱'
            value={formData.email}
            onInput={(e) => handleInputChange('email', e.detail.value)}
          />
        </View>

        <View className='form-item'>
          <View className='label'>
            {isSpecial && <Text className='required'>*</Text>}
            电话
          </View>
          <Input
            className='input'
            placeholder={isSpecial ? '请输入联系电话' : '联系电话（选填）'}
            value={formData.phone}
            onInput={(e) => handleInputChange('phone', e.detail.value)}
          />
        </View>

        <View className='form-item'>
          <View className='label'>
            {isSpecial && <Text className='required'>*</Text>}
            地址
          </View>
          <Input
            className='input'
            placeholder={isSpecial ? '请输入公司地址' : '公司地址（选填）'}
            value={formData.address}
            onInput={(e) => handleInputChange('address', e.detail.value)}
          />
        </View>

        <View className='form-item'>
          <View className='label'>
            {isSpecial && <Text className='required'>*</Text>}
            开户行
          </View>
          <Input
            className='input'
            placeholder={isSpecial ? '请输入开户行及账号' : '开户行及账号（选填）'}
            value={formData.bank_account}
            onInput={(e) => handleInputChange('bank_account', e.detail.value)}
          />
        </View>
      </View>

      <View className='submit-btn' onClick={handleSubmit}>
        {submitting ? '提交中...' : '提交申请'}
      </View>
    </View>
  )
}
