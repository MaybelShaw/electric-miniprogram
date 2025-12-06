import { http } from '../utils/request'
import { Notification, PaginatedResponse } from '../types'

export interface NotificationStats {
  unread_count: number
  pending_count: number
  total: number
}

export interface SubscribeTemplate {
  scene: string
  template_id: string
  page?: string
}

export const notificationService = {
  getList(params?: {
    page?: number
    page_size?: number
    type?: string
    status?: string
    read?: boolean | string
  }): Promise<PaginatedResponse<Notification>> {
    return http.get<PaginatedResponse<Notification>>('/notifications/', params)
  },

  markRead(id: number): Promise<Notification> {
    return http.post<Notification>(`/notifications/${id}/mark_read/`)
  },

  markAllRead(): Promise<{ marked: number }> {
    return http.post<{ marked: number }>('/notifications/mark_all_read/')
  },

  getStats(): Promise<NotificationStats> {
    return http.get<NotificationStats>('/notifications/stats/')
  },

  getTemplates(): Promise<{ templates: SubscribeTemplate[]; default_page?: string }> {
    return http.get<{ templates: SubscribeTemplate[]; default_page?: string }>(
      '/notifications/subscribe_templates/'
    )
  }
}
