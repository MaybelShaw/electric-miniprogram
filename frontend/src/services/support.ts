import { http, BASE_URL, TokenManager } from '../utils/request'
import Taro from '@tarojs/taro'

export interface SupportMessage {
  id: number
  ticket: number
  sender: number
  sender_username: string
  role: string
  content: string
  attachment_url?: string
  attachment_type?: 'image' | 'video'
  created_at: string
}

export const supportService = {
  // 获取聊天记录
  getMessages: (params?: { after?: string; limit?: number }) => 
    http.get<SupportMessage[]>('/support/chat/', params),
  
  // 发送消息
  sendMessage: (content: string, attachment?: { path: string, type: 'image' | 'video' }) => {
    if (!attachment) {
      return http.post<SupportMessage>('/support/chat/', { content })
    }

    return new Promise<SupportMessage>((resolve, reject) => {
      const token = TokenManager.getAccessToken()
      
      Taro.uploadFile({
        url: `${BASE_URL}/support/chat/`,
        filePath: attachment.path,
        name: 'attachment',
        header: {
          'Authorization': `Bearer ${token}`
        },
        formData: {
          'content': content || '',
          'attachment_type': attachment.type
        },
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
