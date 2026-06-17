import { useState } from 'react'
import { View, ScrollView, Text } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { feedbackService, FeedbackTicket, FeedbackTicketStatus } from '../../services/feedback'
import { TokenManager } from '../../utils/request'
import { requireLogin } from '../../utils/login-guard'
import EmptyState from '../../components/EmptyState'
import './index.scss'

const TABS: Array<{ label: string; value: '' | FeedbackTicketStatus }> = [
  { label: '全部', value: '' },
  { label: '待处理', value: 'pending' },
  { label: '已回复', value: 'replied' },
  { label: '已关闭', value: 'closed' },
]

const STATUS_CLASS: Record<FeedbackTicketStatus, string> = {
  pending: 'pending',
  replied: 'replied',
  closed: 'closed',
}

export default function FeedbackList() {
  const [tickets, setTickets] = useState<FeedbackTicket[]>([])
  const [status, setStatus] = useState<'' | FeedbackTicketStatus>('')
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const [loading, setLoading] = useState(false)

  useDidShow(() => {
    if (!TokenManager.getAccessToken()) {
      requireLogin()
      return
    }
    loadTickets(1, true, status)
  })

  const loadTickets = async (pageNum = 1, reset = false, nextStatus = status) => {
    if (loading) return
    setLoading(true)
    try {
      const res = await feedbackService.getTickets({
        page: pageNum,
        page_size: 10,
        status: nextStatus || undefined,
      })
      setTickets(prev => (reset ? res.results : [...prev, ...res.results]))
      setPage(pageNum)
      setHasMore(Boolean(res.has_next))
    } catch (error: any) {
      Taro.showToast({ title: error?.message || '加载失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }

  const switchStatus = (value: '' | FeedbackTicketStatus) => {
    setStatus(value)
    setTickets([])
    setPage(1)
    setHasMore(true)
    loadTickets(1, true, value)
  }

  const openDetail = (ticket: FeedbackTicket) => {
    Taro.navigateTo({ url: `/pages/feedback-detail/index?id=${ticket.id}` })
  }

  const createTicket = () => {
    Taro.navigateTo({ url: '/pages/feedback-submit/index' })
  }

  return (
    <View className='feedback-list-page'>
      <View className='feedback-header'>
        <View>
          <Text className='title'>问题建议</Text>
          <Text className='subtitle'>提交问题或需求，店铺会在这里回复处理进度</Text>
        </View>
        <View className='create-btn' onTap={createTicket}>新建</View>
      </View>

      <View className='tabs'>
        {TABS.map(tab => (
          <View
            key={tab.value || 'all'}
            className={`tab ${status === tab.value ? 'active' : ''}`}
            onTap={() => switchStatus(tab.value)}
          >
            {tab.label}
          </View>
        ))}
      </View>

      <ScrollView
        className='ticket-scroll'
        scrollY
        refresherEnabled
        refresherTriggered={loading && page === 1}
        onRefresherRefresh={() => loadTickets(1, true)}
        onScrollToLower={() => hasMore && !loading && loadTickets(page + 1)}
      >
        <View className='ticket-list'>
          {tickets.map(ticket => (
            <View key={ticket.id} className='ticket-card' onTap={() => openDetail(ticket)}>
              <View className='card-top'>
                <Text className='ticket-no'>{ticket.ticket_number}</Text>
                <Text className={`status ${STATUS_CLASS[ticket.status]}`}>{ticket.status_display}</Text>
              </View>
              <View className='card-title'>{ticket.title}</View>
              <View className='card-content'>{ticket.content}</View>
              <View className='card-meta'>
                <Text>{ticket.ticket_type_display}</Text>
                <Text>{ticket.store_name}</Text>
                <Text>{ticket.created_at?.replace('T', ' ').slice(0, 16)}</Text>
              </View>
            </View>
          ))}

          {!loading && tickets.length === 0 && (
            <EmptyState
              className='empty'
              title='暂无问题建议'
              description='有问题或需求时，可以新建工单提交给店铺'
              icon='message'
            />
          )}
          {loading && <View className='loading'>加载中...</View>}
          {!loading && !hasMore && tickets.length > 0 && <View className='loading'>没有更多了</View>}
        </View>
      </ScrollView>
    </View>
  )
}
