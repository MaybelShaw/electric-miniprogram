import { useState, useEffect } from 'react'
import { View, Input, Button, Image } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { authService } from '../../services/auth'
import { User } from '../../types'
import './index.scss'

export default function ProfileEdit() {
  const [user, setUser] = useState<User | null>(null)
  const [username, setUsername] = useState('')
  const [phone, setPhone] = useState('')
  const [email, setEmail] = useState('')
  const [avatarUrl, setAvatarUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    loadUserInfo()
  }, [])

  const loadUserInfo = async () => {
    setLoading(true)
    try {
      const data = await authService.getUserProfile()
      setUser(data)
      setUsername(data.username || '')
      setPhone(data.phone || '')
      setEmail(data.email || '')
      setAvatarUrl(data.avatar_url || '')
    } catch (error) {
      Taro.showToast({ title: '加载失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }

  const handleChooseAvatar = () => {
    Taro.chooseImage({
      count: 1,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const tempFilePath = res.tempFilePaths[0]
        setAvatarUrl(tempFilePath)
        // TODO: 上传图片到服务器
        // uploadImage(tempFilePath)
      }
    })
  }

  const handleSubmit = async () => {
    if (!username.trim()) {
      Taro.showToast({ title: '请输入昵称', icon: 'none' })
      return
    }

    if (submitting) return

    setSubmitting(true)
    try {
      const updateData: Partial<User> = {
        username: username.trim()
      }

      if (phone.trim()) {
        updateData.phone = phone.trim()
      }

      if (email.trim()) {
        updateData.email = email.trim()
      }

      if (avatarUrl && avatarUrl !== user?.avatar_url) {
        updateData.avatar_url = avatarUrl
      }

      await authService.updateUserProfile(updateData)
      
      Taro.showToast({ title: '保存成功', icon: 'success' })
      
      setTimeout(() => {
        Taro.navigateBack()
      }, 1500)
    } catch (error: any) {
      Taro.showToast({ 
        title: error.message || '保存失败', 
        icon: 'none' 
      })
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <View className='profile-edit loading'>
        <View className='loading-text'>加载中...</View>
      </View>
    )
  }

  return (
    <View className='profile-edit'>
      {/* 头像 */}
      <View className='form-section'>
        <View className='form-item avatar-item'>
          <View className='item-label'>头像</View>
          <View className='item-content' onClick={handleChooseAvatar}>
            <Image 
              className='avatar' 
              src={avatarUrl || '/assets/default-avatar.png'} 
            />
            <View className='arrow-icon'>›</View>
          </View>
        </View>
      </View>

      {/* 基本信息 */}
      <View className='form-section'>
        <View className='form-item'>
          <View className='item-label'>昵称</View>
          <Input
            className='item-input'
            placeholder='请输入昵称'
            value={username}
            onInput={(e) => setUsername(e.detail.value)}
            maxlength={20}
          />
        </View>

        <View className='form-item'>
          <View className='item-label'>手机号</View>
          <Input
            className='item-input'
            placeholder='请输入手机号'
            value={phone}
            onInput={(e) => setPhone(e.detail.value)}
            type='number'
            maxlength={11}
          />
        </View>

        <View className='form-item'>
          <View className='item-label'>邮箱</View>
          <Input
            className='item-input'
            placeholder='请输入邮箱'
            value={email}
            onInput={(e) => setEmail(e.detail.value)}
            type='text'
          />
        </View>
      </View>

      {/* 提交按钮 */}
      <View className='submit-section'>
        <Button 
          className='submit-btn' 
          onClick={handleSubmit}
          disabled={submitting}
        >
          {submitting ? '保存中...' : '保存'}
        </Button>
      </View>
    </View>
  )
}
