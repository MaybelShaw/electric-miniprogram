import { useState } from 'react'
import { View, ScrollView, Text } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { notificationService, SubscribeTemplate, NotificationStats } from '../../services/notification'
import { Notification } from '../../types'
import { TokenManager } from '../../utils/request'
import { requireLogin } from '../../utils/login-guard'
import './index.scss'

const TYPE_META: Record<
  Notification['type'],
  { label: string; color: string; bg: string }
> = {
  payment: { label: '支付', color: '#1989FA', bg: '#E6F3FF' },
  order: { label: '订单', color: '#07C160', bg: '#E6FFF5' },
  refund: { label: '退款', color: '#FF976A', bg: '#FFF3E6' },
  return: { label: '退货', color: '#EE0A24', bg: '#FFF1E6' },
  statement: { label: '对账', color: '#722ED1', bg: '#F5EDFF' },
  system: { label: '系统', color: '#646566', bg: '#F2F3F5' }
}

const formatTime = (value?: string | null) => {
  if (!value) return ''
  return value.replace('T', ' ').slice(0, 16)
}

export default function MessageCenter() {
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const [loading, setLoading] = useState(false)
  const [stats, setStats] = useState<NotificationStats>({ unread_count: 0, pending_count: 0, total: 0 })
  const [templates, setTemplates] = useState<SubscribeTemplate[]>([])

  useDidShow(() => {
    if (!TokenManager.getAccessToken()) {
      setNotifications([])
      setStats({ unread_count: 0, pending_count: 0, total: 0 })
      requireLogin()
      return
    }
    refreshAll()
  })

  const refreshAll = () => {
    loadStats()
    loadTemplates()
    loadNotifications(1, true)
  }

  const loadStats = async () => {
    try {
      const data = await notificationService.getStats()
      setStats(data)
    } catch (error) {
      // ignore silently
    }
  }

  const loadTemplates = async () => {
    try {
      const res = await notificationService.getTemplates()
      setTemplates(res.templates || [])
    } catch (error) {
      setTemplates([])
    }
  }

  const loadNotifications = async (pageNum = 1, reset = false) => {
    if (loading) return
    setLoading(true)
    try {
      const res = await notificationService.getList({ page: pageNum, page_size: 10 })
      const items = (res.results || []) as Notification[]
      setNotifications(prev => (reset ? items : [...prev, ...items]))
      const hasNext =
        typeof (res as any).has_next === 'boolean'
          ? !!(res as any).has_next
          : ((res as any).page || pageNum) < ((res as any).total_pages || pageNum)
      setHasMore(hasNext)
      setPage(pageNum)
    } catch (error: any) {
      Taro.showToast({ title: error?.message || '加载失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }

  const handleMarkAllRead = async () => {
    try {
      await notificationService.markAllRead()
      const now = new Date().toISOString()
      setNotifications(prev => prev.map(item => ({ ...item, is_read: true, read_at: item.read_at || now })))
      setStats(prev => ({ ...prev, unread_count: 0 }))
      Taro.eventCenter.trigger('notificationsUpdated')
      Taro.showToast({ title: '已全部设为已读', icon: 'success' })
    } catch (error) {
      Taro.showToast({ title: '操作失败', icon: 'none' })
    }
  }

  const navigateByNotification = (item: Notification) => {
    const meta = item.metadata || {}
    if (meta.page) {
      const path = String(meta.page).startsWith('/') ? String(meta.page) : `/${meta.page}`
      Taro.navigateTo({ url: path })
      return
    }
    if (meta.order_id) {
      Taro.navigateTo({ url: `/pages/order-detail/index?id=${meta.order_id}` })
      return
    }
    if (meta.statement_id) {
      Taro.navigateTo({ url: `/pages/statement-detail/index?id=${meta.statement_id}` })
      return
    }
    Taro.showModal({
      title: item.title,
      content: item.content || '',
      showCancel: false
    })
  }

  const handleCardClick = async (item: Notification) => {
    try {
      if (!item.is_read) {
        const updated = await notificationService.markRead(item.id)
        setNotifications(prev =>
          prev.map(n => (n.id === updated.id ? { ...n, is_read: true, read_at: updated.read_at || n.read_at } : n))
        )
        setStats(prev => ({ ...prev, unread_count: Math.max((prev.unread_count || 0) - 1, 0) }))
        Taro.eventCenter.trigger('notificationsUpdated')
      }
    } catch (error) {
      // ignore and still allow navigation
    }
    navigateByNotification(item)
  }

  const handleSubscribe = async () => {
    try {
      const tmplIds = templates.map(t => t.template_id).filter(Boolean)
      if (!tmplIds.length) {
        Taro.showToast({ title: '暂无可用的订阅模板', icon: 'none' })
        return
      }
      const res = await Taro.requestSubscribeMessage({ tmplIds } as any)
      const accepted = tmplIds.some(id => (res as any)[id] === 'accept')
      Taro.showToast({
        title: accepted ? '订阅成功' : '用户未授权订阅',
        icon: accepted ? 'success' : 'none'
      })
    } catch (error) {
      Taro.showToast({ title: '订阅失败', icon: 'none' })
    }
  }

  const renderCard = (item: Notification) => {
    const meta = TYPE_META[item.type] || TYPE_META.system
    return (
      <View key={item.id} className={`notice-card ${item.is_read ? 'read' : ''}`} onTap={() => handleCardClick(item)}>
        <View className='card-header'>
          <View className='header-left'>
            {!item.is_read && <View className='unread-dot' />}
            <Text className='type-tag' style={{ color: meta.color, backgroundColor: meta.bg }}>
              {meta.label}
            </Text>
            <Text className='card-title'>{item.title}</Text>
          </View>
          <Text className='card-time'>{formatTime(item.created_at)}</Text>
        </View>
        
        <View className='card-body'>
          <View className='card-content'>{item.content}</View>
        </View>

        <View className='card-footer'>
          <Text className={`status status-${item.status}`}>{item.status_display || item.status}</Text>
          {item.metadata?.order_number && (
            <Text className='tag'>订单 {item.metadata.order_number}</Text>
          )}
          {item.metadata?.amount && <Text className='tag'>金额 ¥{item.metadata.amount}</Text>}
        </View>
      </View>
    )
  }

  return (
    <View className='message-center'>
      <View className='header'>
        <View className='title-row'>
          <View>
            <Text className='title'>消息中心</Text>
            <Text className='subtitle'>订单、支付、退货、对账提醒都在这里</Text>
          </View>
          <View className='badge'>
            <Text className='badge-number'>{stats.unread_count}</Text>
            <Text className='badge-label'>未读</Text>
          </View>
        </View>
        <View className='header-actions'>
          <View className='action-btn primary' onTap={handleSubscribe}>
            <Text>开启订阅提醒</Text>
            <Text className='action-desc'>
              {templates.length ? `${templates.length} 个模板` : '需授权才能推送'}
            </Text>
          </View>
          <View className='action-btn ghost' onTap={handleMarkAllRead}>
            <Text>全部设为已读</Text>
            <Text className='action-desc'>清空红点</Text>
          </View>
        </View>
        <View className='header-meta'>
          <Text>共 {stats.total} 条</Text>
          <Text className='split'>|</Text>
          <Text>待推送 {stats.pending_count}</Text>
        </View>
      </View>

      <ScrollView
        className='list'
        scrollY
        lowerThreshold={80}
        onScrollToLower={() => hasMore && !loading && loadNotifications(page + 1)}
      >
        {notifications.length === 0 && !loading && (
          <View className='empty'>
            <Text className='empty-icon'>📭</Text>
            <Text className='empty-text'>暂时没有消息</Text>
          </View>
        )}

        {notifications.map(renderCard)}

        {loading && <View className='loading'>加载中...</View>}
        {!hasMore && notifications.length > 0 && <View className='loading'>没有更多了</View>}
      </ScrollView>
    </View>
  )
}
