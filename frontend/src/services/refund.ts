import { http } from '../utils/request'
import { PaginatedResponse, Refund } from '../types'

export const refundService = {
  // 获取退款列表
  async getRefunds(params?: { order_id?: number; page?: number; page_size?: number }): Promise<PaginatedResponse<Refund>> {
    return http.get<PaginatedResponse<Refund>>('/refunds/', params)
  },

  // 创建退款申请
  async createRefund(data: { order: number; payment?: number; amount: string | number; reason?: string; evidence_images?: string[] }): Promise<Refund> {
    return http.post<Refund>('/refunds/', data)
  },

  // 启动退款（默认调用微信退款）
  async startRefund(id: number, data?: { provider?: 'wechat' | 'alipay' | 'bank' | 'credit' }): Promise<any> {
    return http.post(`/refunds/${id}/start/`, data)
  }
}
