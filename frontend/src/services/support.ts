import { http, BASE_URL, TokenManager } from '../utils/request'
import Taro from '@tarojs/taro'

export interface SupportMessage {
  id: number
  conversation: number
  ticket?: number
  sender: number
  sender_username: string
  role: string
  content: string
  content_type?: 'text' | 'card' | 'quick_buttons'
  content_payload?: Record<string, any>
  template?: number | null
  attachment_url?: string
  attachment_type?: 'image' | 'video'
  order_info?: {
    id: number
    order_number: string
    status: string
    quantity: number
    total_amount: string
    product_name: string
    image: string
  }
  product_info?: {
    id: number
    name: string
    price: string
    image: string
  }
  created_at: string
}

export const supportService = {
  // 获取聊天记录
  getMessages: (params?: { after?: string; limit?: number }) => 
    http.get<SupportMessage[]>('/support/chat/', params),

  triggerAutoReply: () =>
    http.post<{ triggered: boolean; message?: SupportMessage }>('/support/chat/auto-reply/'),
  
  // 发送消息
  sendMessage: (content?: string, attachment?: { path: string, type: 'image' | 'video' }, extra?: { order_id?: number, product_id?: number }) => {
    if (!attachment) {
      return http.post<SupportMessage>('/support/chat/', { 
        content,
        order_id: extra?.order_id,
        product_id: extra?.product_id
      })
    }

    return new Promise<SupportMessage>((resolve, reject) => {
      const token = TokenManager.getAccessToken()
      const formData: any = {
        'attachment_type': attachment.type
      }
      if (content) formData.content = content
      if (extra?.order_id) formData.order_id = extra.order_id
      if (extra?.product_id) formData.product_id = extra.product_id
      
      Taro.uploadFile({
        url: `${BASE_URL}/support/chat/`,
        filePath: attachment.path,
        name: 'attachment',
        header: {
          'Authorization': `Bearer ${token}`
        },
        formData: formData,
        success: (res) => {
          if (res.statusCode >= 200 && res.statusCode < 300) {
            try {
              const data = JSON.parse(res.data)
              resolve(data)
            } catch (e) {
              reject(e)
            }
          } else {
            reject(new Error(`Upload failed: ${res.statusCode}`))
          }
        },
        fail: (err) => {
          reject(err)
        }
      })
    })
  }
}
