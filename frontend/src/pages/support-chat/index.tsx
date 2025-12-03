import { useState, useEffect, useRef } from 'react'
import { View, Text, Input, Button, ScrollView } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { supportService, SupportMessage } from '../../services/support'
import { authService } from '../../services/auth'
import { User } from '../../types'
import './index.scss'

interface ExtendedSupportMessage extends SupportMessage {
  local_id?: string
  status?: 'sending' | 'sent' | 'error'
}

interface OfflineMessage {
  content: string
  tempId: string
  timestamp: number
}

export default function SupportChat() {
  const [messages, setMessages] = useState<ExtendedSupportMessage[]>([])
  const [inputValue, setInputValue] = useState('')
  const [loading, setLoading] = useState(false)
  const [currentUser, setCurrentUser] = useState<User | null>(null)
  const [lastFetchedAt, setLastFetchedAt] = useState<string | null>(null)
  const [scrollIntoView, setScrollIntoView] = useState<string>('')
  
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

  const sendMessage = async () => {
    if (!inputValue.trim() || !currentUser) return
    
    const content = inputValue.trim()
    setInputValue('')
    
    const tempId = `temp_${Date.now()}`
    const tempMsg: ExtendedSupportMessage = {
      id: -1,
      ticket: 0,
      sender: currentUser.id,
      sender_username: currentUser.username || 'Me',
      role: currentUser.role || 'user',
      content,
      created_at: new Date().toISOString(),
      local_id: tempId,
      status: 'sending'
    }

    // Optimistic update
    setMessages(prev => {
      const newMsgs = [...prev, tempMsg]
      scrollToBottom(newMsgs)
      return newMsgs
    })

    try {
      const res = await supportService.sendMessage(content)
      
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
      
      const queueKey = 'offline_queue'
      const queue: OfflineMessage[] = Taro.getStorageSync(queueKey) || []
      queue.push({ content, tempId, timestamp: Date.now() })
      Taro.setStorageSync(queueKey, queue)
      
      Taro.showToast({ title: '发送失败，已保存到离线队列', icon: 'none' })
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
                    <Text>{msg.content}</Text>
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
        <View id="bottom-anchor" style={{ height: '1px' }}></View>
      </ScrollView>
      
      <View className='input-area'>
        <Input
          className='chat-input'
          value={inputValue}
          onInput={e => setInputValue(e.detail.value)}
          onConfirm={sendMessage}
          placeholder='请输入消息...'
          confirmType='send'
        />
        <Button 
          className={`send-btn ${!inputValue.trim() ? 'disabled' : ''}`}
          onClick={sendMessage}
        >
          发送
        </Button>
      </View>
    </View>
  )
}
