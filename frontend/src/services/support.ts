import { http } from '../utils/request'

export interface SupportMessage {
  id: number
  ticket: number
  sender: number
  sender_username: string
  role: string
  content: string
  created_at: string
}

export const supportService = {
  // 获取聊天记录
  getMessages: (params?: { after?: string; limit?: number }) => 
    http.get<SupportMessage[]>('/support/chat/', params),
  
  // 发送消息
  sendMessage: (content: string) => 
    http.post<SupportMessage>('/support/chat/', { content }),
}
