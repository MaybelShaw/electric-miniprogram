import { useEffect, useState } from 'react'
import { Button, Image, Text, View } from '@tarojs/components'
import Taro, { useDidShow, useRouter } from '@tarojs/taro'
import AppIcon from '../../components/AppIcon'
import StoreBottomNav from '../../components/StoreBottomNav'
import { authService } from '../../services/auth'
import { storeService } from '../../services/store'
import { Store, User } from '../../types'
import { resolveLocalMediaUrl } from '../../utils/media'
import { TokenManager } from '../../utils/request'
import './index.scss'

export default function StoreProfilePage() {
  const router = useRouter()
  const storeId = Number(router.params.store_id || router.params.store || 0)

  const [store, setStore] = useState<Store | null>(null)
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(false)

  useDidShow(() => {
    if (TokenManager.getAccessToken()) {
      loadUserInfo()
    } else {
      setUser(null)
    }
  })

  useEffect(() => {
    if (!storeId) {
      Taro.showToast({ title: '店铺不存在', icon: 'none' })
      return
    }
    loadStore()
  }, [storeId])

  const loadStore = async () => {
    try {
      const detail = await storeService.getStoreDetail(storeId)
      if (detail.store.is_main) {
        Taro.switchTab({ url: '/pages/home/index' })
        return
      }

      setStore(detail.store)
      Taro.setNavigationBarTitle({ title: '我的' })
    } catch {
      Taro.showToast({ title: '加载店铺失败', icon: 'none' })
    }
  }

  const loadUserInfo = async () => {
    try {
      const data = await authService.getUserProfile()
      setUser(data)
    } catch {
      setUser(null)
    }
  }

  const handleLogin = async (event?: any) => {
    if (loading) return

    const phoneCode = event?.detail?.code
    if (!phoneCode) {
      Taro.showToast({ title: '请授权手机号', icon: 'none' })
      return
    }

    setLoading(true)
    try {
      const res = await authService.loginWithPhone(phoneCode)
      TokenManager.setTokens(res.access, res.refresh)
      setUser(res.user)
      Taro.eventCenter.trigger('userLogin')
      Taro.showToast({ title: '登录成功', icon: 'success' })
    } catch {
      Taro.showToast({ title: '登录失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }

  const requireLogin = () => {
    if (!user) {
      Taro.showToast({ title: '请先登录', icon: 'none' })
      return false
    }
    return true
  }

  const goToOrders = (status?: string) => {
    if (!requireLogin()) return
    const query = [`store_id=${storeId}`]
    if (status) query.push(`status=${status}`)
    Taro.navigateTo({ url: `/pages/order-list/index?${query.join('&')}` })
  }

  const goToFeedback = () => {
    if (!requireLogin()) return
    Taro.navigateTo({ url: `/pages/feedback-list/index?store_id=${storeId}` })
  }

  const goToSupport = () => {
    if (!requireLogin()) return
    Taro.navigateTo({ url: `/pages/support-chat/index?store_id=${storeId}` })
  }

  const avatarUrl = user ? resolveLocalMediaUrl(user.avatar_url) : ''
  return (
    <View className='store-profile-page'>
      <View className='user-card'>
        {user ? (
          <>
            {avatarUrl ? (
              <Image className='avatar' src={avatarUrl} mode='aspectFill' />
            ) : (
              <View className='avatar avatar--fallback'><AppIcon name='profile' tone='muted' /></View>
            )}
            <View className='user-copy'>
              <Text className='username'>{user.username || '未设置昵称'}</Text>
              {!!user.phone && <Text className='user-phone'>{user.phone}</Text>}
            </View>
          </>
        ) : (
          <>
            <View className='avatar avatar--fallback'><AppIcon name='profile' tone='muted' /></View>
            <Button
              className='login-btn'
              openType='getPhoneNumber'
              loading={loading}
              disabled={loading}
              onGetPhoneNumber={handleLogin}
            >
              {loading ? '登录中...' : '手机号登录'}
            </Button>
          </>
        )}
      </View>

      <View className='menu-card'>
        <View className='menu-item' onClick={() => goToOrders()}>
          <View className='menu-left'><AppIcon name='order' tone='muted' /><Text>店铺订单</Text></View>
          <Text className='arrow' />
        </View>
        <View className='menu-item' onClick={() => goToOrders('pending')}>
          <View className='menu-left'><AppIcon name='pay' tone='muted' /><Text>待支付</Text></View>
          <Text className='arrow' />
        </View>
        <View className='menu-item' onClick={goToSupport}>
          <View className='menu-left'><AppIcon name='service' tone='muted' /><Text>店铺客服</Text></View>
          <Text className='arrow' />
        </View>
        <View className='menu-item' onClick={goToFeedback}>
          <View className='menu-left'><AppIcon name='message' tone='muted' /><Text>问题建议</Text></View>
          <Text className='arrow' />
        </View>
      </View>

      <StoreBottomNav storeId={storeId} storeIsMain={store?.is_main} active='profile' />
    </View>
  )
}
