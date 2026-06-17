import Taro from '@tarojs/taro'
import { http, BASE_URL, TokenManager } from '../utils/request'
import { PaginatedResponse, Store } from '../types'

export type FeedbackTicketType = 'question' | 'requirement'
export type FeedbackTicketStatus = 'pending' | 'replied' | 'closed'
export type FeedbackRecordType = 'user_supplement' | 'merchant_reply' | 'close'

export interface FeedbackTicketReply {
  id: number
  ticket: number
  sender: number
  sender_username: string
  record_type: FeedbackRecordType
  record_type_display: string
  content: string
  attachments: string[]
  created_at: string
}

export interface FeedbackTicket {
  id: number
  ticket_number: string
  store: number
  store_name: string
  user: number
  user_username: string
  user_phone?: string
  ticket_type: FeedbackTicketType
  ticket_type_display: string
  title: string
  content: string
  contact_phone: string
  attachments: string[]
  status: FeedbackTicketStatus
  status_display: string
  last_replied_at?: string | null
  created_at: string
  updated_at: string
  replies: FeedbackTicketReply[]
}

interface TicketPayload {
  store_id?: number
  ticket_type?: FeedbackTicketType
  title?: string
  content?: string
  contact_phone?: string
}

function uploadOneImage(path: string) {
  return new Promise<{ path: string; url: string }>((resolve, reject) => {
    const token = TokenManager.getAccessToken()
    Taro.uploadFile({
      url: `${BASE_URL}/support/feedback-tickets/upload-image/`,
      filePath: path,
      name: 'image',
      header: token ? { Authorization: `Bearer ${token}` } : {},
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          try {
            resolve(JSON.parse(res.data))
          } catch (error) {
            reject(error)
          }
          return
        }
        reject(new Error(`Upload failed: ${res.statusCode}`))
      },
      fail: reject,
    })
  })
}

async function uploadImages(images: string[]) {
  const paths: string[] = []
  for (const image of images) {
    const res: any = await uploadOneImage(image)
    if (res?.path) paths.push(res.path)
  }
  return paths
}

export const feedbackService = {
  getStores: () => http.get<Store[]>('/support/feedback-tickets/stores/'),

  getTickets: (params?: { page?: number; page_size?: number; status?: string }) =>
    http.get<PaginatedResponse<FeedbackTicket>>('/support/feedback-tickets/', params),

  getTicket: (id: number | string) =>
    http.get<FeedbackTicket>(`/support/feedback-tickets/${id}/`),

  createTicket: async (data: TicketPayload, images: string[]) => {
    const attachments = await uploadImages(images)
    return http.post<FeedbackTicket>('/support/feedback-tickets/', { ...data, attachments })
  },

  supplementTicket: async (id: number | string, data: { content?: string }, images: string[]) => {
    const attachments = await uploadImages(images)
    return http.post<FeedbackTicket>(`/support/feedback-tickets/${id}/supplement/`, { ...data, attachments })
  },
}
