import { useState } from 'react'
import { View, Form, Input, Button, Text } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { companyService } from '../../services/company'
import { TokenManager } from '../../utils/request'
import './index.scss'

export default function CompanyCertification() {
  const createEmptyFormData = () => ({
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

  const [formData, setFormData] = useState(createEmptyFormData())
  
  const [loading, setLoading] = useState(false)
  const [existingInfo, setExistingInfo] = useState<any>(null)

  useDidShow(() => {
    checkLoginAndLoad()
  })

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
    } catch (error: any) {
      if (error?.statusCode === 404) {
        setExistingInfo(null)
        setFormData(createEmptyFormData())
        return
      }
      Taro.showToast({ title: '加载认证信息失败', icon: 'none' })
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
      let savedInfo: any = null
      if (existingInfo && existingInfo.status !== 'approved') {
        // 更新
        savedInfo = await companyService.updateCompanyInfo(existingInfo.id, formData)
        Taro.showToast({
          title: '提交成功，等待审核',
          icon: 'success'
        })
      } else {
        // 创建
        savedInfo = await companyService.createCompanyInfo(formData)
        Taro.showToast({
          title: '提交成功，等待审核',
          icon: 'success'
        })
      }

      if (savedInfo) {
        setExistingInfo(savedInfo)
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

  const handleWithdraw = async () => {
    if (!existingInfo) return
    setLoading(true)
    try {
      const res: any = await companyService.withdrawCompanyInfo(existingInfo.id)
      const info = res?.company_info || res
      if (info) {
        setExistingInfo(info)
        setFormData({
          company_name: info.company_name || '',
          business_license: info.business_license || '',
          legal_representative: info.legal_representative || '',
          contact_person: info.contact_person || '',
          contact_phone: info.contact_phone || '',
          contact_email: info.contact_email || '',
          province: info.province || '',
          city: info.city || '',
          district: info.district || '',
          detail_address: info.detail_address || '',
          business_scope: info.business_scope || ''
        })
      }
      Taro.showToast({ title: '已撤回', icon: 'success' })
    } catch (error: any) {
      Taro.showToast({ title: error?.message || '撤回失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }

  const getStatusText = (status: string) => {
    const statusMap = {
      pending: '审核中',
      approved: '已通过',
      rejected: '已拒绝',
      withdrawn: '已撤回'
    }
    return statusMap[status] || status
  }

  const canEdit = !existingInfo || ['rejected', 'withdrawn'].includes(existingInfo.status)
  const canWithdraw = existingInfo?.status === 'pending'

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
          {existingInfo.reject_reason && (
            <Text className='reject-reason'>原因：{existingInfo.reject_reason}</Text>
          )}
        </View>
      )}

      {existingInfo?.status === 'pending' && (
        <View className='info-banner warning'>
          <Text>⏳ 您的认证申请正在审核中，请耐心等待</Text>
        </View>
      )}

      {existingInfo?.status === 'withdrawn' && (
        <View className='info-banner info'>
          <Text>已撤回审核，可修改信息后重新提交</Text>
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
              {existingInfo?.status === 'rejected' || existingInfo?.status === 'withdrawn'
                ? '重新提交认证'
                : existingInfo
                  ? '更新信息'
                  : '提交认证'}
            </Button>
          </View>
        )}

        {canWithdraw && (
          <View className='form-actions'>
            <Button className='withdraw-btn' onClick={handleWithdraw} loading={loading}>
              撤回审核
            </Button>
          </View>
        )}
      </Form>
    </View>
  )
}
