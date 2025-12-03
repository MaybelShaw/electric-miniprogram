import { useState } from 'react'
import { View, Image, Text } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { authService } from '../../services/auth'
import { TokenManager } from '../../utils/request'
import { User } from '../../types'
import './index.scss'

export default function Profile() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(false)

  useDidShow(() => {
    if (TokenManager.getAccessToken()) {
      loadUserInfo()
    }
  })

  const loadUserInfo = async () => {
    try {
      const data = await authService.getUserProfile()
      setUser(data)
    } catch (error) {
      // 静默失败
    }
  }

  const handleLogin = async () => {
    if (loading) return
    
    setLoading(true)
    try {
      const res = await authService.login()
      TokenManager.setTokens(res.access, res.refresh)
      setUser(res.user)
      
      // 触发登录成功事件，通知其他页面刷新
      Taro.eventCenter.trigger('userLogin')
      
      Taro.showToast({ title: '登录成功', icon: 'success' })
    } catch (error) {
      Taro.showToast({ title: '登录失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = async () => {
    const res = await Taro.showModal({
      title: '提示',
      content: '确定要退出登录吗？'
    })

    if (res.confirm) {
      TokenManager.clearTokens()
      setUser(null)
      
      // 触发登出事件，通知其他页面清空状态
      Taro.eventCenter.trigger('userLogout')
      
      Taro.showToast({ title: '已退出登录', icon: 'success' })
    }
  }

  const goToOrders = (status?: string) => {
    if (!user) {
      Taro.showToast({ title: '请先登录', icon: 'none' })
      return
    }
    const url = status ? `/pages/order-list/index?status=${status}` : '/pages/order-list/index'
    Taro.navigateTo({ url })
  }

  const goToAddresses = () => {
    if (!user) {
      Taro.showToast({ title: '请先登录', icon: 'none' })
      return
    }
    Taro.navigateTo({ url: '/pages/address-list/index' })
  }



  const goToProfileEdit = () => {
    if (!user) {
      Taro.showToast({ title: '请先登录', icon: 'none' })
      return
    }
    Taro.navigateTo({ url: '/pages/profile-edit/index' })
  }

  const goToCertification = () => {
    if (!user) {
      Taro.showToast({ title: '请先登录', icon: 'none' })
      return
    }
    Taro.navigateTo({ url: '/pages/company-certification/index' })
  }


  const goToSupport = () => {
    if (!user) {
      Taro.showToast({ title: '请先登录', icon: 'none' })
      return
    }
    Taro.navigateTo({ url: '/pages/support-chat/index' })
  }

  return (
    <View className='profile'>
      {/* 用户信息区域 */}
      <View className='user-section'>
        {user ? (
          <View className='user-info' onTap={goToProfileEdit}>
            <Image className='avatar' src={user.avatar_url || '/assets/default-avatar.png'} />
            <View className='user-details'>
              <View className='username'>{user.username || '未设置昵称'}</View>
              {user.company_name && user.role === 'dealer' && (
                <View className='company-name'>
                  <Text className='company-icon'>🏢</Text>
                  <Text className='company-text'>{user.company_name}</Text>
                </View>
              )}
            </View>
          </View>
        ) : (
          <View className='login-section'>
            <Image className='avatar' src='/assets/default-avatar.png' />
            <View className='login-text' onTap={handleLogin}>
              {loading ? '登录中...' : '点击授权'}
            </View>
          </View>
        )}
      </View>

      {/* 订单入口 */}
      <View className='order-section'>
        <View className='section-header'>
          <Text className='section-title'>商城订单</Text>
          <View className='view-all' onTap={() => goToOrders()}>
            <Text className='view-all-text'>全部订单</Text>
            <Text className='arrow'>›</Text>
          </View>
        </View>
        <View className='order-menu'>
          <View className='order-item' onTap={() => goToOrders('pending')}>
            <View className='order-icon-wrapper'>
              <Text className='order-icon'>💰</Text>
            </View>
            <Text className='order-text'>待支付</Text>
          </View>
          <View className='order-item' onTap={() => goToOrders('paid')}>
            <View className='order-icon-wrapper'>
              <Text className='order-icon'>📦</Text>
            </View>
            <Text className='order-text'>待发货</Text>
          </View>
          <View className='order-item' onTap={() => goToOrders('shipped')}>
            <View className='order-icon-wrapper'>
              <Text className='order-icon'>🚚</Text>
            </View>
            <Text className='order-text'>待收货</Text>
          </View>
          <View className='order-item' onTap={() => goToOrders('completed')}>
            <View className='order-icon-wrapper'>
              <Text className='order-icon'>✅</Text>
            </View>
            <Text className='order-text'>已完成</Text>
          </View>
          <View className='order-item' onTap={() => goToOrders('returning,refunding,refunded')}>
            <View className='order-icon-wrapper'>
              <Text className='order-icon'>↩️</Text>
            </View>
            <Text className='order-text'>退货/售后</Text>
          </View>
        </View>
      </View>

      {/* 功能菜单 */}
      <View className='menu-section'>
        <View className='menu-item' onTap={goToAddresses}>
          <View className='menu-left'>
            <Text className='menu-icon'>📍</Text>
            <Text className='menu-text'>收货地址</Text>
          </View>
          <Text className='arrow'>›</Text>
        </View>
        

        <View className='menu-item' onTap={goToCertification}>
          <View className='menu-left'>
            <Text className='menu-icon'>🏢</Text>
            <Text className='menu-text'>经销商认证</Text>
            {user?.role === 'dealer' && (
              <View className='badge success'>已认证</View>
            )}
            {user?.has_company_info && user?.company_status === 'pending' && (
              <View className='badge warning'>审核中</View>
            )}
          </View>
          <Text className='arrow'>›</Text>
        </View>

        {user?.role === 'dealer' && (
          <>
            <View className='menu-item' onTap={() => {
              if (!user) {
                Taro.showToast({ title: '请先登录', icon: 'none' })
                return
              }
              Taro.navigateTo({ url: '/pages/credit-account/index' })
            }}>
              <View className='menu-left'>
                <Text className='menu-icon'>💳</Text>
                <Text className='menu-text'>信用账户</Text>
              </View>
              <Text className='arrow'>›</Text>
            </View>
          </>
        )}

        <View className='menu-item' onTap={goToSupport}>
          <View className='menu-left'>
            <Text className='menu-icon'>🎧</Text>
            <Text className='menu-text'>客服支持</Text>
          </View>
          <Text className='arrow'>›</Text>
        </View>
      </View>

      {/* 退出登录按钮 - 放在最底部 */}
      {user && (
        <View className='logout-section'>
          <View className='logout-button' onTap={handleLogout}>
            退出登录
          </View>
        </View>
      )}
    </View>
  )
}
