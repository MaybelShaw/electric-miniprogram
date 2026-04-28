import { useMemo, useState } from 'react'
import { View, Text, Button } from '@tarojs/components'
import Taro, { useRouter } from '@tarojs/taro'
import { authService } from '../../services/auth'
import { TokenManager } from '../../utils/request'
import './index.scss'

function decodeParam(value?: string) {
  if (!value) return ''
  try {
    return decodeURIComponent(value)
  } catch {
    return value
  }
}

function buildRedirectUrl(redirect: string, intent: string) {
  if (!intent) return redirect
  const connector = redirect.includes('?') ? '&' : '?'
  return `${redirect}${connector}intent=${encodeURIComponent(intent)}`
}

export default function LoginPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)

  const redirect = useMemo(() => decodeParam(router.params?.redirect), [router.params?.redirect])
  const intent = useMemo(() => decodeParam(router.params?.intent), [router.params?.intent])

  const jumpAfterLogin = async () => {
    if (redirect) {
      const targetUrl = buildRedirectUrl(redirect, intent)
      await Taro.redirectTo({ url: targetUrl })
      return
    }
    await Taro.switchTab({ url: '/pages/profile/index' })
  }

  const handleLogin = async () => {
    if (loading) return
    setLoading(true)
    try {
      const res = await authService.login()
      TokenManager.setTokens(res.access, res.refresh)
      Taro.eventCenter.trigger('userLogin')
      Taro.showToast({ title: '登录成功', icon: 'success' })
      await jumpAfterLogin()
    } catch (error) {
      Taro.showToast({ title: '登录失败，请重试', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <View className='login-page'>
      <View className='login-card'>
        <View className='card-content'>
          <View className='top-content'>
            <View className='avatar' />
            <View className='title'>登录授权</View>
            <Text className='desc'>登陆后可继续操作</Text>
          </View>
          <Button className='login-btn' loading={loading} disabled={loading} onTap={handleLogin}>
            {loading ? '登录中...' : '微信授权登录'}
          </Button>
        </View>
      </View>
    </View>
  )
}
