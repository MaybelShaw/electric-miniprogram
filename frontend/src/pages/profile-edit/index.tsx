import { useState, useEffect } from 'react'
import { View, Input, Button, Image } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { authService } from '../../services/auth'
import { uploadService } from '../../services/upload'
import { User } from '../../types'
import { resolveLocalMediaUrl } from '../../utils/media'
import AppIcon from '../../components/AppIcon'
import './index.scss'

const isLocalAvatarFile = (url: string) => (
  url.startsWith('wxfile://') ||
  url.startsWith('blob:') ||
  url.startsWith('http://tmp/') ||
  url.startsWith('https://tmp/') ||
  (!/^https?:\/\//.test(url) && !url.startsWith('/'))
)

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
        if (tempFilePath) {
          setAvatarUrl(tempFilePath)
        }
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
        let nextAvatarUrl = avatarUrl
        if (isLocalAvatarFile(avatarUrl)) {
          Taro.showLoading({ title: '上传头像...' })
          try {
            nextAvatarUrl = await uploadService.uploadImage(avatarUrl)
            setAvatarUrl(nextAvatarUrl)
          } finally {
            Taro.hideLoading()
          }
        }
        updateData.avatar_url = nextAvatarUrl
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

  const resolvedAvatarUrl = resolveLocalMediaUrl(avatarUrl)

  return (
    <View className='profile-edit'>
      {/* 头像 */}
      <View className='form-section'>
        <View className='form-item avatar-item'>
          <View className='item-label'>头像</View>
          <Button
            className='item-content avatar-button'
            onClick={handleChooseAvatar}
          >
            {resolvedAvatarUrl ? (
              <Image className='avatar' src={resolvedAvatarUrl} />
            ) : (
              <View className='avatar avatar-placeholder'><AppIcon name='profile' tone='muted' /></View>
            )}
            <View className='arrow-icon'>›</View>
          </Button>
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
