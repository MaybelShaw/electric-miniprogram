import { useState, useEffect, useRef } from 'react'
import { View, Text, Input, Button, ScrollView, Image, Video } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { supportService, SupportMessage } from '../../services/support'
import { authService } from '../../services/auth'
import { User } from '../../types'
import cameraIcon from '../../assets/icons/camera.png'
import pictureIcon from '../../assets/icons/picture.png'
import orderIcon from '../../assets/icons/order.png'
import productIcon from '../../assets/icons/product.png'
import './index.scss'

interface ExtendedSupportMessage extends SupportMessage {
  local_id?: string
  status?: 'sending' | 'sent' | 'error'
  tempFilePath?: string // For local preview of uploaded media
  order_info?: any
  product_info?: any
}

interface OfflineMessage {
  content: string
  tempId: string
  timestamp: number
  extra?: { order_id?: number, product_id?: number }
}

export default function SupportChat() {
  const [messages, setMessages] = useState<ExtendedSupportMessage[]>([])
  const [inputValue, setInputValue] = useState('')
  const [loading, setLoading] = useState(false)
  const [currentUser, setCurrentUser] = useState<User | null>(null)
  const [lastFetchedAt, setLastFetchedAt] = useState<string | null>(null)
  const [scrollIntoView, setScrollIntoView] = useState<string>('')
  const [showPanel, setShowPanel] = useState(false)
  
  const pollingRef = useRef<any>()
  
  // Load user info
  useEffect(() => {
    const loadUser = async () => {
      try {
        const user = await authService.getUserProfile()
        setCurrentUser(user)
      } catch (error) {
        console.error('Failed to load user info', error)
      }
    }
    loadUser()
  }, [])

  // Load messages from cache and initial fetch
  useEffect(() => {
    const cacheKey = 'chat_messages'
    const cachedData = Taro.getStorageSync(cacheKey)
    
    if (cachedData) {
      try {
        const parsed = typeof cachedData === 'string' ? JSON.parse(cachedData) : cachedData
        if (parsed && parsed.messages) {
          setMessages(parsed.messages)
          setLastFetchedAt(parsed.lastFetchedAt || null)
          scrollToBottom(parsed.messages)
        }
      } catch (e) {
        console.error('Failed to parse cached messages', e)
      }
    } else {
      setLoading(true)
    }

    fetchMessages(null, true)
    
    return () => stopPolling()
  }, [])

  // Polling
  useEffect(() => {
    startPolling()
    return () => stopPolling()
  }, [lastFetchedAt])

  // Offline handling
  useEffect(() => {
    const onNetworkStatusChange = (res) => {
      if (res.isConnected) {
        retryOfflineMessages()
      }
    }
    Taro.onNetworkStatusChange(onNetworkStatusChange)
    
    // Check initial status
    Taro.getNetworkType({
      success: (res) => {
        if (res.networkType !== 'none') {
          retryOfflineMessages()
        }
      }
    })

    return () => {}
  }, [])

  const startPolling = () => {
    stopPolling()
    pollingRef.current = setInterval(() => {
      fetchMessages(lastFetchedAt)
    }, 3000)
  }

  const stopPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = undefined
    }
  }

  const resolveAfter = (after: string | null) => {
    if (!after) return null
    const parsed = new Date(after)
    if (Number.isNaN(parsed.getTime())) return after
    return new Date(parsed.getTime() - 1000).toISOString()
  }

  const fetchMessages = async (after: string | null, isInitial = false) => {
    try {
      const params: any = {}
      const resolvedAfter = resolveAfter(after)
      if (resolvedAfter) {
        params.after = resolvedAfter
      }
      
      const res = await supportService.getMessages(params)
      
      if (res && Array.isArray(res) && res.length > 0) {
        setMessages(prev => {
          const newMsgs = [...prev]
          res.forEach((msg: SupportMessage) => {
            if (!newMsgs.some(m => m.id === msg.id)) {
              newMsgs.push({ ...msg, status: 'sent' })
            }
          })
          
          newMsgs.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
          
          if (newMsgs.length > 0) {
            const lastMsg = newMsgs[newMsgs.length - 1]
            const newLastFetchedAt = lastMsg.created_at
            
            Taro.setStorageSync('chat_messages', {
              messages: newMsgs,
              lastFetchedAt: newLastFetchedAt
            })
            
            if (after !== newLastFetchedAt) {
              setLastFetchedAt(newLastFetchedAt)
            }
          }
          
          if (isInitial || res.length > 0) {
            scrollToBottom(newMsgs)
          }
          
          return newMsgs
        })
      }
    } catch (error) {
      console.error('Polling error:', error)
    } finally {
      if (isInitial) setLoading(false)
    }
  }

  const handleTogglePanel = () => {
    const willShow = !showPanel
    setShowPanel(willShow)
    // Adjust scroll to bottom when panel opens
    if (willShow) {
      setTimeout(() => {
        setScrollIntoView('')
        setTimeout(() => {
            setScrollIntoView('bottom-anchor')
        }, 50)
      }, 100)
    }
  }

  const handleCamera = async () => {
    try {
      const res = await Taro.chooseMedia({
        count: 1,
        mediaType: ['image', 'video'],
        sourceType: ['camera'],
      })
      handleMediaSelect(res)
    } catch (e) {
      console.log('Camera cancelled or failed', e)
    }
  }

  const handleAlbum = async () => {
    try {
      const res = await Taro.chooseMedia({
        count: 1,
        mediaType: ['image', 'video'],
        sourceType: ['album'],
      })
      handleMediaSelect(res)
    } catch (e) {
      console.log('Album cancelled or failed', e)
    }
  }

  const handleMediaSelect = async (res: Taro.chooseMedia.SuccessCallbackResult) => {
    const file = res.tempFiles[0]
    const type = res.type
    await sendContent('', { path: file.tempFilePath, type: type as 'image' | 'video' })
    setShowPanel(false)
  }

  const getStatusText = (status: string) => {
    const map = {
      pending: '待支付',
      paid: '待发货',
      shipped: '待收货',
      completed: '已完成',
      cancelled: '已取消',
      returning: '退货中',
      refunding: '退款中',
      refunded: '已退款'
    }
    return map[status] || status
  }

  const handleOrder = () => {
    Taro.navigateTo({
      url: '/pages/support-chat/select-order/index',
      events: {
        acceptSelectedOrder: (order) => {
          console.log('Received order:', order)
          sendOrder(order).catch(err => {
             console.error('Failed to send order:', err)
             Taro.showToast({ title: '发送订单失败', icon: 'none' })
          })
        }
      },
      fail: (err) => {
        console.error('Navigate to select-order failed:', err)
        Taro.showToast({ title: '无法打开订单列表', icon: 'none' })
      }
    })
    setShowPanel(false)
  }

  const handleProduct = () => {
    Taro.navigateTo({
      url: '/pages/support-chat/select-product/index',
      events: {
        acceptSelectedProduct: (product) => {
          console.log('Received product:', product)
          sendProduct(product).catch(err => {
             console.error('Failed to send product:', err)
             Taro.showToast({ title: '发送商品失败', icon: 'none' })
          })
        }
      },
      fail: (err) => {
        console.error('Navigate to select-product failed:', err)
        Taro.showToast({ title: '无法打开商品列表', icon: 'none' })
      }
    })
    setShowPanel(false)
  }

  const sendOrder = async (order: any) => {
    const primaryItem = order.items && order.items.length > 0 ? order.items[0] : null
    const product = primaryItem?.product || order.product || {}
    const image = primaryItem?.snapshot_image || product.product_image_url || (product.main_images && product.main_images[0]) || ''
    
    const orderInfo = {
      id: order.id,
      order_number: order.order_number,
      status: order.status,
      quantity: order.quantity,
      total_amount: order.total_amount,
      product_name: primaryItem?.product_name || product.name || '',
      image: image
    }
    
    await sendContent('', undefined, { order_id: order.id }, { order_info: orderInfo })
  }

  const sendProduct = async (product: any) => {
    const image = product.product_image_url || (product.main_images && product.main_images[0]) || ''
    
    const productInfo = {
      id: product.id,
      name: product.name,
      price: product.display_price ?? product.price,
      image: image
    }
    
    await sendContent('', undefined, { product_id: product.id }, { product_info: productInfo })
  }
  
  const handleInputFocus = () => {
    if (showPanel) {
      setShowPanel(false)
    }
  }

  const handleSend = () => {
    sendContent()
  }

  const sendContent = async (
    contentStr?: string, 
    attachment?: { path: string, type: 'image' | 'video' },
    extra?: { order_id?: number, product_id?: number },
    optimisticData?: { order_info?: any, product_info?: any }
  ) => {
    const content = contentStr !== undefined ? contentStr : inputValue.trim()
    if ((!content && !attachment && !extra) || !currentUser) return
    
    if (!attachment && !extra) {
      setInputValue('')
    }
    
    const tempId = `temp_${Date.now()}`
    const tempMsg: ExtendedSupportMessage = {
      id: -1,
      conversation: 0,
      ticket: 0,
      sender: currentUser.id,
      sender_username: currentUser.username || 'Me',
      role: currentUser.role || 'user',
      content: content || (attachment ? (attachment.type === 'image' ? '[图片]' : '[视频]') : (extra?.order_id ? '[订单]' : '[商品]')),
      attachment_url: attachment ? attachment.path : undefined,
      attachment_type: attachment ? attachment.type : undefined,
      order_info: optimisticData?.order_info,
      product_info: optimisticData?.product_info,
      created_at: new Date().toISOString(),
      local_id: tempId,
      status: 'sending',
      tempFilePath: attachment ? attachment.path : undefined
    }

    // Optimistic update
    setMessages(prev => {
      const newMsgs = [...prev, tempMsg]
      scrollToBottom(newMsgs)
      return newMsgs
    })

    try {
      const res = await supportService.sendMessage(content, attachment, extra)
      
      setMessages(prev => {
        const newMsgs = prev.map(m => 
          m.local_id === tempId ? { ...res, local_id: tempId, status: 'sent' } as ExtendedSupportMessage : m
        )
        
        const lastMsg = newMsgs[newMsgs.length - 1]
        if (lastMsg) {
          Taro.setStorageSync('chat_messages', {
            messages: newMsgs,
            lastFetchedAt: lastMsg.created_at
          })
          setLastFetchedAt(lastMsg.created_at)
        }
        return newMsgs
      })
    } catch (error) {
      console.error('Send error:', error)
      setMessages(prev => prev.map(m => 
        m.local_id === tempId ? { ...m, status: 'error' } : m
      ))
      
      if (!attachment) {
        const queueKey = 'offline_queue'
        const queue: OfflineMessage[] = Taro.getStorageSync(queueKey) || []
        queue.push({ content, tempId, timestamp: Date.now(), extra })
        Taro.setStorageSync(queueKey, queue)
        
        Taro.showToast({ title: '发送失败，已保存到离线队列', icon: 'none' })
      } else {
        Taro.showToast({ title: '发送图片/视频失败', icon: 'none' })
      }
    }
  }

  const handleCardClick = (payload?: Record<string, any>) => {
    const linkUrl = payload?.link_url
    if (!linkUrl) return
    if (linkUrl.startsWith('/pages/')) {
      Taro.navigateTo({ url: linkUrl })
      return
    }
    Taro.setClipboardData({ data: linkUrl })
    Taro.showToast({ title: '链接已复制', icon: 'none' })
  }

  const renderMessageBody = (msg: ExtendedSupportMessage) => {
    if (msg.order_info) {
      return (
        <View className='message-card' onClick={() => Taro.navigateTo({ url: `/pages/order-detail/index?id=${msg.order_info.id}` })}>
          <View className='card-header'>
            <Text>订单号: {msg.order_info.order_number}</Text>
            <Text className='order-tag'>{getStatusText(msg.order_info.status)}</Text>
          </View>
          <View className='card-content'>
            <Image src={msg.order_info.image} mode='aspectFill' className='card-img' />
            <View className='card-info'>
              <Text className='card-title'>{msg.order_info.product_name}</Text>
              <Text className='card-desc'>¥{msg.order_info.total_amount}</Text>
            </View>
          </View>
        </View>
      )
    }
    if (msg.product_info) {
      return (
        <View className='message-card' onClick={() => Taro.navigateTo({ url: `/pages/product-detail/index?id=${msg.product_info.id}` })}>
          <View className='card-content'>
            <Image src={msg.product_info.image} mode='aspectFill' className='card-img' />
            <View className='card-info'>
              <Text className='card-title'>{msg.product_info.name}</Text>
              <Text className='card-desc'>¥{msg.product_info.price}</Text>
            </View>
          </View>
        </View>
      )
    }
    if (msg.attachment_type === 'image') {
      return (
        <Image 
          src={msg.attachment_url || msg.tempFilePath || ''} 
          mode='widthFix' 
          className='message-image'
          onClick={() => Taro.previewImage({ urls: [msg.attachment_url || msg.tempFilePath || ''] })}
        />
      )
    }
    if (msg.attachment_type === 'video') {
      return (
        <Video 
          src={msg.attachment_url || msg.tempFilePath || ''}
          className='message-video'
        />
      )
    }
    if (msg.content_type === 'card') {
      const payload: any = msg.content_payload || {}
      return (
        <View className='reply-card' onClick={() => handleCardClick(payload)}>
          {payload.image_url && <Image src={payload.image_url} mode='aspectFill' className='reply-card-image' />}
          <View className='reply-card-body'>
            <Text className='reply-card-title'>{payload.title || msg.content}</Text>
            {payload.description && <Text className='reply-card-desc'>{payload.description}</Text>}
          </View>
        </View>
      )
    }
    if (msg.content_type === 'quick_buttons') {
      const payload: any = msg.content_payload || {}
      const buttons: any[] = Array.isArray(payload.buttons) ? payload.buttons : []
      return (
        <View className='quick-replies'>
          {msg.content ? <Text className='quick-replies-text'>{msg.content}</Text> : null}
          <View className='quick-replies-actions'>
            {buttons.map((btn, index) => (
              <View
                key={`${btn.text || btn.value}-${index}`}
                className='quick-replies-btn'
                onClick={() => sendContent(btn.value || btn.text || '')}
              >
                <Text>{btn.text || btn.value}</Text>
              </View>
            ))}
          </View>
        </View>
      )
    }
    return <Text>{msg.content}</Text>
  }

  const retryOfflineMessages = async () => {
    const queueKey = 'offline_queue'
    const queue: OfflineMessage[] = Taro.getStorageSync(queueKey) || []
    if (queue.length === 0) return

    const newQueue: OfflineMessage[] = []

    for (const item of queue) {
      try {
        const res = await supportService.sendMessage(item.content, undefined, item.extra)
        
        setMessages(prev => {
          const newMsgs = prev.map(m => 
            m.local_id === item.tempId ? { ...res, local_id: item.tempId, status: 'sent' } as ExtendedSupportMessage : m
          )
          // Also update cache
          const lastMsg = newMsgs[newMsgs.length - 1]
           if (lastMsg) {
             Taro.setStorageSync('chat_messages', {
               messages: newMsgs,
               lastFetchedAt: lastMsg.created_at
             })
             setLastFetchedAt(lastMsg.created_at)
           }
          return newMsgs
        })
      } catch (e) {
        newQueue.push(item)
      }
    }
    
    Taro.setStorageSync(queueKey, newQueue)
    if (newQueue.length < queue.length) {
      Taro.showToast({ title: '离线消息已发送', icon: 'success' })
    }
  }

  const scrollToBottom = (msgs: ExtendedSupportMessage[]) => {
    if (msgs.length > 0) {
      // Use setTimeout to ensure rendering is done
      setTimeout(() => {
        const lastId = msgs[msgs.length - 1].local_id || `msg_${msgs[msgs.length - 1].id}`
        setScrollIntoView(lastId)
      }, 100)
    }
  }

  return (
    <View className='chat-page'>
      <ScrollView 
        className='message-list' 
        scrollY 
        scrollIntoView={scrollIntoView}
        scrollWithAnimation
      >
        {loading && <View className='loading'>加载中...</View>}
        
        {messages.map((msg, index) => {
          // Check if message is from current user
          // 1. Compare ID (handle potential type mismatch)
          const isIdMatch = currentUser && (String(msg.sender) === String(currentUser.id))
          // 2. Check role (fallback if ID check fails or user loading)
          const isRoleMatch = ['individual', 'dealer', 'user'].includes(msg.role)
          
          // If it's a temp message, we know it's from us
          const isTemp = !!msg.local_id
          
          const isMe = isIdMatch || isRoleMatch || isTemp
          
          const showTime = index === 0 || 
            new Date(msg.created_at).getTime() - new Date(messages[index - 1].created_at).getTime() > 5 * 60 * 1000
            
          return (
            <View key={msg.local_id || msg.id} id={msg.local_id || `msg_${msg.id}`}>
              {showTime && (
                <View className='time-divider'>
                  <Text className='time-text'>
                    {new Date(msg.created_at).toLocaleString()}
                  </Text>
                </View>
              )}
              
              <View className={`message-item ${isMe ? 'me' : 'other'}`}>
                <View className='avatar'>
                  <Text>{isMe ? '我' : '服'}</Text>
                </View>
                <View className='content'>
                  {!isMe && msg.sender_username && (
                    <Text className='sender-name'>{msg.sender_username}</Text>
                  )}
                  <View className='bubble'>
                    {renderMessageBody(msg)}
                  </View>
                  {msg.status === 'error' && (
                    <Text className='status error'>发送失败</Text>
                  )}
                  {msg.status === 'sending' && (
                    <Text className='status sending'>发送中...</Text>
                  )}
                </View>
              </View>
            </View>
          )
        })}
        <View id="bottom-anchor" style={{ height: showPanel ? 'calc(320px + 120rpx + env(safe-area-inset-bottom))' : 'calc(120rpx + env(safe-area-inset-bottom))' }}></View>
      </ScrollView>
      
      <View className={`chat-footer ${showPanel ? 'has-panel' : ''}`}>
        <View className='input-area'>
          <Input
            className='chat-input'
            value={inputValue}
            onInput={e => setInputValue(e.detail.value)}
            onConfirm={handleSend}
            onFocus={handleInputFocus}
            placeholder='请输入消息...'
            confirmType='send'
          />
          {inputValue.trim() ? (
            <View className='send-btn' onClick={handleSend}>
              发送
            </View>
          ) : (
            <View className='media-btn' onClick={handleTogglePanel}>
              <Text className='plus-icon'>+</Text>
            </View>
          )}
        </View>

        {showPanel && (
          <View className='action-panel'>
            <View className='action-item' onClick={handleAlbum}>
              <View className='icon-wrapper'>
                <Image src={pictureIcon} className='action-icon' />
              </View>
              <Text className='label'>图片/视频</Text>
            </View>
            <View className='action-item' onClick={handleCamera}>
              <View className='icon-wrapper'>
                <Image src={cameraIcon} className='action-icon' />
              </View>
              <Text className='label'>拍摄</Text>
            </View>
            <View className='action-item' onClick={handleOrder}>
              <View className='icon-wrapper'>
                <Image src={orderIcon} className='action-icon' />
              </View>
              <Text className='label'>订单</Text>
            </View>
            <View className='action-item' onClick={handleProduct}>
              <View className='icon-wrapper'>
                <Image src={productIcon} className='action-icon' />
              </View>
              <Text className='label'>商品</Text>
            </View>
          </View>
        )}
      </View>
    </View>
  )
}
