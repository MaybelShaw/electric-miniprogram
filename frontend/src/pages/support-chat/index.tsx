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
}

interface OfflineMessage {
  content: string
  tempId: string
  timestamp: number
  // Simple offline support for text only for now
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

  const fetchMessages = async (after: string | null, isInitial = false) => {
    try {
      const params: any = {}
      if (after) {
        params.after = after
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

  const handleOrder = () => {
    Taro.showToast({ title: '选择订单功能开发中', icon: 'none' })
  }

  const handleProduct = () => {
    Taro.showToast({ title: '选择商品功能开发中', icon: 'none' })
  }
  
  const handleInputFocus = () => {
    if (showPanel) {
      setShowPanel(false)
    }
  }

  const handleSend = () => {
    sendContent()
  }

  const sendContent = async (contentStr?: string, attachment?: { path: string, type: 'image' | 'video' }) => {
    const content = contentStr !== undefined ? contentStr : inputValue.trim()
    if ((!content && !attachment) || !currentUser) return
    
    if (!attachment) {
      setInputValue('')
    }
    
    const tempId = `temp_${Date.now()}`
    const tempMsg: ExtendedSupportMessage = {
      id: -1,
      ticket: 0,
      sender: currentUser.id,
      sender_username: currentUser.username || 'Me',
      role: currentUser.role || 'user',
      content: content || (attachment ? (attachment.type === 'image' ? '[图片]' : '[视频]') : ''),
      attachment_url: attachment ? attachment.path : undefined,
      attachment_type: attachment ? attachment.type : undefined,
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
      const res = await supportService.sendMessage(content, attachment)
      
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
        queue.push({ content, tempId, timestamp: Date.now() })
        Taro.setStorageSync(queueKey, queue)
        
        Taro.showToast({ title: '发送失败，已保存到离线队列', icon: 'none' })
      } else {
        Taro.showToast({ title: '发送图片/视频失败', icon: 'none' })
      }
    }
  }

  const retryOfflineMessages = async () => {
    const queueKey = 'offline_queue'
    const queue: OfflineMessage[] = Taro.getStorageSync(queueKey) || []
    if (queue.length === 0) return

    const newQueue: OfflineMessage[] = []

    for (const item of queue) {
      try {
        const res = await supportService.sendMessage(item.content)
        
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
                    {msg.attachment_type === 'image' ? (
                      <Image 
                        src={msg.attachment_url || msg.tempFilePath || ''} 
                        mode='widthFix' 
                        className='message-image'
                        onClick={() => Taro.previewImage({ urls: [msg.attachment_url || msg.tempFilePath || ''] })}
                      />
                    ) : msg.attachment_type === 'video' ? (
                      <Video 
                        src={msg.attachment_url || msg.tempFilePath || ''}
                        className='message-video'
                      />
                    ) : (
                      <Text>{msg.content}</Text>
                    )}
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
        <View id="bottom-anchor" style={{ height: showPanel ? 'calc(500rpx + 120rpx + env(safe-area-inset-bottom))' : 'calc(120rpx + env(safe-area-inset-bottom))' }}></View>
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
          <View className='media-btn' onClick={handleTogglePanel}>
            <Text className='plus-icon'>+</Text>
          </View>
        </View>

        {showPanel && (
          <View className='action-panel'>
            <View className='action-item' onClick={handleCamera}>
              <View className='icon-wrapper'>
                <Image src={cameraIcon} className='action-icon' />
              </View>
              <Text className='label'>拍摄</Text>
            </View>
            <View className='action-item' onClick={handleAlbum}>
              <View className='icon-wrapper'>
                <Image src={pictureIcon} className='action-icon' />
              </View>
              <Text className='label'>相册</Text>
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
