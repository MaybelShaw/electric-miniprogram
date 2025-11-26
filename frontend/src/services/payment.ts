import { http } from '../utils/request'
import { Payment, PaginatedResponse } from '../types'

export const paymentService = {
  // 获取支付记录列表
  async getPayments(params?: {
    order_id?: number
    page?: number
    page_size?: number
  }): Promise<PaginatedResponse<Payment>> {
    return http.get<PaginatedResponse<Payment>>('/payments/', params)
  },
  
  // 创建支付记录
  async createPayment(data: {
    order_id: number
    method?: 'wechat' | 'alipay' | 'bank'
    amount?: string
  }): Promise<Payment> {
    return http.post<Payment>('/payments/', data)
  },
  
  // 获取支付详情
  async getPaymentDetail(id: number): Promise<Payment> {
    return http.get<Payment>(`/payments/${id}/`)
  },
  
  // 开始支付
  async startPayment(id: number): Promise<Payment> {
    return http.post<Payment>(`/payments/${id}/start/`)
  },
  
  // 支付成功
  async succeedPayment(id: number): Promise<Payment> {
    return http.post<Payment>(`/payments/${id}/succeed/`)
  },
  
  // 支付失败
  async failPayment(id: number): Promise<Payment> {
    return http.post<Payment>(`/payments/${id}/fail/`)
  },
  
  // 取消支付
  async cancelPayment(id: number): Promise<Payment> {
    return http.post<Payment>(`/payments/${id}/cancel/`)
  },
  
  // 支付过期
  async expirePayment(id: number): Promise<Payment> {
    return http.post<Payment>(`/payments/${id}/expire/`)
  }
}
