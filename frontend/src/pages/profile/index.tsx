import { useEffect, useState } from 'react'
import { View, Image, Text, Button } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { authService } from '../../services/auth'
import { notificationService } from '../../services/notification'
import { TokenManager } from '../../utils/request'
import { resumePendingAuthAction } from '../../utils/auth-guard'
import { resolveLocalMediaUrl } from '../../utils/media'
import { User } from '../../types'
import { withPrivacyCheck } from '../../components/withPrivacyCheck'
import AppIcon from '../../components/AppIcon'
import './index.scss'

function Profile() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(false)
  const [unreadCount, setUnreadCount] = useState(0)

  useDidShow(() => {
    if (TokenManager.getAccessToken()) {
      loadUserInfo()
      loadNotificationStats()
    } else {
      setUnreadCount(0)
    }
  })

  useEffect(() => {
    const refreshUnread = () => {
      if (TokenManager.getAccessToken()) {
        loadNotificationStats()
      } else {
        setUnreadCount(0)
      }
    }
    const clearUnread = () => setUnreadCount(0)

    Taro.eventCenter.on('notificationsUpdated', refreshUnread)
    Taro.eventCenter.on('userLogin', refreshUnread)
    Taro.eventCenter.on('userLogout', clearUnread)

    return () => {
      Taro.eventCenter.off('notificationsUpdated', refreshUnread)
      Taro.eventCenter.off('userLogin', refreshUnread)
      Taro.eventCenter.off('userLogout', clearUnread)
    }
  }, [])

  async function loadUserInfo() {
    try {
      const data = await authService.getUserProfile()
      setUser(data)
    } catch (error) {
      // 静默失败
    }
  }

  async function loadNotificationStats() {
    try {
      const data = await notificationService.getStats()
      setUnreadCount(data.unread_count || 0)
    } catch (error) {
      setUnreadCount(0)
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
      loadNotificationStats()
      
      // 触发登录成功事件，通知其他页面刷新
      Taro.eventCenter.trigger('userLogin')

      Taro.showToast({ title: '登录成功', icon: 'success' })
      try {
        await resumePendingAuthAction()
      } catch {
        Taro.showToast({ title: '回跳失败，请返回商品页继续操作', icon: 'none' })
      }
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
      setUnreadCount(0)
      
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

  const goToMessages = () => {
    if (!user) {
      Taro.showToast({ title: '请先登录', icon: 'none' })
      return
    }
    Taro.navigateTo({ url: '/pages/message-center/index' })
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

  const getCertificationBadge = () => {
    if (!user) return null
    if (user.role === 'dealer') {
      return { text: '已认证', className: 'success' }
    }
    if (!user.has_company_info || !user.company_status) return null
    const statusMap: Record<string, { text: string; className: string }> = {
      pending: { text: '审核中', className: 'warning' },
      rejected: { text: '未通过', className: 'danger' },
      withdrawn: { text: '已撤回', className: 'info' },
      approved: { text: '已认证', className: 'success' }
    }
    return statusMap[user.company_status] || null
  }

  const certificationBadge = getCertificationBadge()
  const userAvatarUrl = user ? resolveLocalMediaUrl(user.avatar_url) : ''

  return (
    <View className='profile'>
      {/* 用户信息区域 */}
      <View className='user-section'>
        {user ? (
          <View className='user-info' onTap={goToProfileEdit}>
            {userAvatarUrl ? (
              <Image className='avatar' src={userAvatarUrl} />
            ) : (
              <View className='avatar avatar-placeholder'><AppIcon name='profile' tone='muted' /></View>
            )}
            <View className='user-details'>
              <View className='username'>{user.username || '未设置昵称'}</View>
              {user.company_name && user.role === 'dealer' && (
                <View className='company-name'>
                  <AppIcon name='company' tone='gold' className='company-icon' />
                  <Text className='company-text'>{user.company_name}</Text>
                </View>
              )}
            </View>
          </View>
        ) : (
          <View className='login-section'>
            <View className='avatar avatar-placeholder'><AppIcon name='profile' tone='muted' /></View>
            <Button
              className='login-text'
              openType='getPhoneNumber'
              loading={loading}
              disabled={loading}
              onGetPhoneNumber={handleLogin}
            >
              {loading ? '登录中...' : '点击授权'}
            </Button>
          </View>
        )}
      </View>

      {/* 订单入口 */}
      <View className='order-section'>
        <View className='section-header'>
          <Text className='section-title'>商城订单</Text>
          <View className='view-all' onTap={() => goToOrders()}>
            <Text className='view-all-text'>全部订单</Text>
            <Text className='arrow' />
          </View>
        </View>
        <View className='order-menu'>
          <View className='order-item' onTap={() => goToOrders('pending')}>
            <View className='order-icon-wrapper'>
              <AppIcon name='pay' tone='gold' />
            </View>
            <Text className='order-text'>待支付</Text>
          </View>
          <View className='order-item' onTap={() => goToOrders('paid')}>
            <View className='order-icon-wrapper'>
              <AppIcon name='package' tone='primary' />
            </View>
            <Text className='order-text'>待发货</Text>
          </View>
          <View className='order-item' onTap={() => goToOrders('shipped')}>
            <View className='order-icon-wrapper'>
              <AppIcon name='ship' tone='primary' />
            </View>
            <Text className='order-text'>待收货</Text>
          </View>
          <View className='order-item' onTap={() => goToOrders('completed')}>
            <View className='order-icon-wrapper'>
              <AppIcon name='done' tone='default' />
            </View>
            <Text className='order-text'>已完成</Text>
          </View>
          <View className='order-item' onTap={() => goToOrders('returning,refunding,refunded')}>
            <View className='order-icon-wrapper'>
              <AppIcon name='refund' tone='danger' />
            </View>
            <Text className='order-text'>退货/售后</Text>
          </View>
        </View>
      </View>

      {/* 功能菜单 */}
      <View className='menu-section'>
        <View className='menu-item' onTap={goToMessages}>
          <View className='menu-left'>
            <AppIcon name='message' tone='muted' className='menu-icon' />
            <Text className='menu-text'>消息中心</Text>
            {unreadCount > 0 && (
              <View className='badge danger'>{unreadCount > 99 ? '99+' : unreadCount}</View>
            )}
          </View>
          <Text className='arrow' />
        </View>

        <View className='menu-item' onTap={goToAddresses}>
          <View className='menu-left'>
            <AppIcon name='location' tone='muted' className='menu-icon' />
            <Text className='menu-text'>收货地址</Text>
          </View>
          <Text className='arrow' />
        </View>
        

        <View className='menu-item' onTap={goToCertification}>
          <View className='menu-left'>
            <AppIcon name='company' tone='muted' className='menu-icon' />
            <Text className='menu-text'>经销商认证</Text>
            {certificationBadge && (
              <View className={`badge ${certificationBadge.className}`}>
                {certificationBadge.text}
              </View>
            )}
          </View>
          <Text className='arrow' />
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
                <AppIcon name='credit' tone='muted' className='menu-icon' />
                <Text className='menu-text'>信用账户</Text>
              </View>
              <Text className='arrow' />
            </View>
          </>
        )}

        <View className='menu-item' onTap={goToSupport}>
          <View className='menu-left'>
            <AppIcon name='service' tone='muted' className='menu-icon' />
            <Text className='menu-text'>客服支持</Text>
          </View>
          <Text className='arrow' />
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

export default withPrivacyCheck(Profile)
