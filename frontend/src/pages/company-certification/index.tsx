import { useState, useEffect } from 'react'
import { View, Form, Input, Button, Text } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { companyService } from '../../services/company'
import { TokenManager } from '../../utils/request'
import './index.scss'

export default function CompanyCertification() {
  const [formData, setFormData] = useState({
    company_name: '',
    business_license: '',
    legal_representative: '',
    contact_person: '',
    contact_phone: '',
    contact_email: '',
    province: '',
    city: '',
    district: '',
    detail_address: '',
    business_scope: ''
  })
  
  const [loading, setLoading] = useState(false)
  const [existingInfo, setExistingInfo] = useState<any>(null)

  useEffect(() => {
    checkLoginAndLoad()
  }, [])

  const checkLoginAndLoad = async () => {
    const token = TokenManager.getAccessToken()
    if (!token) {
      Taro.showToast({
        title: '请先登录',
        icon: 'none'
      })
      setTimeout(() => {
        Taro.switchTab({ url: '/pages/profile/index' })
      }, 1500)
      return
    }
    loadCompanyInfo()
  }

  const loadCompanyInfo = async () => {
    try {
      const data = await companyService.getCompanyInfo()
      if (data) {
        setExistingInfo(data)
        setFormData({
          company_name: data.company_name || '',
          business_license: data.business_license || '',
          legal_representative: data.legal_representative || '',
          contact_person: data.contact_person || '',
          contact_phone: data.contact_phone || '',
          contact_email: data.contact_email || '',
          province: data.province || '',
          city: data.city || '',
          district: data.district || '',
          detail_address: data.detail_address || '',
          business_scope: data.business_scope || ''
        })
      }
    } catch (error) {
      // 没有公司信息，继续填写
    }
  }

  const handleInputChange = (field: string, value: string) => {
    setFormData({ ...formData, [field]: value })
  }

  const handleSubmit = async () => {
    // 验证必填字段
    const requiredFields = [
      { field: 'company_name', label: '公司名称' },
      { field: 'business_license', label: '营业执照号' },
      { field: 'legal_representative', label: '法人代表' },
      { field: 'contact_person', label: '联系人' },
      { field: 'contact_phone', label: '联系电话' }
    ]
    
    for (const { field, label } of requiredFields) {
      if (!formData[field] || !formData[field].trim()) {
        Taro.showToast({
          title: `请填写${label}`,
          icon: 'none'
        })
        return
      }
    }
    
    // 验证手机号格式
    if (!/^1[3-9]\d{9}$/.test(formData.contact_phone)) {
      Taro.showToast({
        title: '请输入正确的手机号',
        icon: 'none'
      })
      return
    }

    setLoading(true)
    try {
      if (existingInfo && existingInfo.status !== 'approved') {
        // 更新
        await companyService.updateCompanyInfo(existingInfo.id, formData)
        Taro.showToast({
          title: '更新成功',
          icon: 'success'
        })
      } else {
        // 创建
        await companyService.createCompanyInfo(formData)
        Taro.showToast({
          title: '提交成功，等待审核',
          icon: 'success'
        })
      }
      
      setTimeout(() => {
        Taro.navigateBack()
      }, 1500)
    } catch (error: any) {
      console.error('提交公司信息失败:', error)
      let errorMsg = '提交失败'
      
      if (error.message) {
        errorMsg = error.message
      } else if (error.errMsg) {
        errorMsg = error.errMsg
      }
      
      // 如果是权限错误，提示用户重新登录
      if (errorMsg.includes('403') || errorMsg.includes('权限') || errorMsg.includes('Forbidden')) {
        errorMsg = '权限不足，请重新登录'
        TokenManager.clearTokens()
        setTimeout(() => {
          Taro.switchTab({ url: '/pages/profile/index' })
        }, 1500)
      }
      
      Taro.showToast({
        title: errorMsg,
        icon: 'none',
        duration: 2000
      })
    } finally {
      setLoading(false)
    }
  }

  const getStatusText = (status: string) => {
    const statusMap = {
      pending: '审核中',
      approved: '已通过',
      rejected: '已拒绝'
    }
    return statusMap[status] || status
  }

  const canEdit = !existingInfo || existingInfo.status !== 'approved'

  return (
    <View className='company-certification'>
      <View className='page-header'>
        <Text className='page-title'>经销商认证</Text>
        {existingInfo && (
          <View className={`status-badge status-${existingInfo.status}`}>
            {getStatusText(existingInfo.status)}
          </View>
        )}
      </View>

      {existingInfo?.status === 'approved' && (
        <View className='info-banner success'>
          <Text>您已通过经销商认证</Text>
        </View>
      )}

      {existingInfo?.status === 'rejected' && (
        <View className='info-banner error'>
          <Text>❌ 认证未通过，请修改信息后重新提交</Text>
        </View>
      )}

      {existingInfo?.status === 'pending' && (
        <View className='info-banner warning'>
          <Text>⏳ 您的认证申请正在审核中，请耐心等待</Text>
        </View>
      )}

      <Form className='form'>
        <View className='form-section'>
          <View className='section-title'>公司基本信息</View>
          
          <View className='form-item'>
            <View className='label required'>公司名称</View>
            <Input
              className='input'
              placeholder='请输入公司名称'
              value={formData.company_name}
              onInput={(e) => handleInputChange('company_name', e.detail.value)}
              disabled={!canEdit}
            />
          </View>

          <View className='form-item'>
            <View className='label required'>营业执照号</View>
            <Input
              className='input'
              placeholder='请输入营业执照号'
              value={formData.business_license}
              onInput={(e) => handleInputChange('business_license', e.detail.value)}
              disabled={!canEdit}
            />
          </View>

          <View className='form-item'>
            <View className='label required'>法人代表</View>
            <Input
              className='input'
              placeholder='请输入法人代表姓名'
              value={formData.legal_representative}
              onInput={(e) => handleInputChange('legal_representative', e.detail.value)}
              disabled={!canEdit}
            />
          </View>
        </View>

        <View className='form-section'>
          <View className='section-title'>联系信息</View>
          
          <View className='form-item'>
            <View className='label required'>联系人</View>
            <Input
              className='input'
              placeholder='请输入联系人姓名'
              value={formData.contact_person}
              onInput={(e) => handleInputChange('contact_person', e.detail.value)}
              disabled={!canEdit}
            />
          </View>

          <View className='form-item'>
            <View className='label required'>联系电话</View>
            <Input
              className='input'
              type='number'
              placeholder='请输入联系电话'
              value={formData.contact_phone}
              onInput={(e) => handleInputChange('contact_phone', e.detail.value)}
              disabled={!canEdit}
            />
          </View>

          <View className='form-item'>
            <View className='label'>联系邮箱</View>
            <Input
              className='input'
              placeholder='请输入联系邮箱（选填）'
              value={formData.contact_email}
              onInput={(e) => handleInputChange('contact_email', e.detail.value)}
              disabled={!canEdit}
            />
          </View>
        </View>

        <View className='form-section'>
          <View className='section-title'>公司地址</View>
          
          <View className='form-item'>
            <View className='label'>省份</View>
            <Input
              className='input'
              placeholder='请输入省份'
              value={formData.province}
              onInput={(e) => handleInputChange('province', e.detail.value)}
              disabled={!canEdit}
            />
          </View>

          <View className='form-item'>
            <View className='label'>城市</View>
            <Input
              className='input'
              placeholder='请输入城市'
              value={formData.city}
              onInput={(e) => handleInputChange('city', e.detail.value)}
              disabled={!canEdit}
            />
          </View>

          <View className='form-item'>
            <View className='label'>区县</View>
            <Input
              className='input'
              placeholder='请输入区县'
              value={formData.district}
              onInput={(e) => handleInputChange('district', e.detail.value)}
              disabled={!canEdit}
            />
          </View>

          <View className='form-item'>
            <View className='label'>详细地址</View>
            <Input
              className='input'
              placeholder='请输入详细地址'
              value={formData.detail_address}
              onInput={(e) => handleInputChange('detail_address', e.detail.value)}
              disabled={!canEdit}
            />
          </View>
        </View>

        <View className='form-section'>
          <View className='section-title'>经营范围</View>
          
          <View className='form-item'>
            <View className='label'>经营范围</View>
            <Input
              className='input textarea'
              placeholder='请输入经营范围（选填）'
              value={formData.business_scope}
              onInput={(e) => handleInputChange('business_scope', e.detail.value)}
              disabled={!canEdit}
            />
          </View>
        </View>

        {canEdit && (
          <View className='form-actions'>
            <Button
              className='submit-btn'
              type='primary'
              onClick={handleSubmit}
              loading={loading}
            >
              {existingInfo?.status === 'rejected' ? '重新提交认证' : existingInfo ? '更新信息' : '提交认证'}
            </Button>
          </View>
        )}
      </Form>
    </View>
  )
}
