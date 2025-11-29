import { http } from '../utils/request'
import { Order, CreateOrderResponse, PaginatedResponse } from '../types'

export const orderService = {
  // 创建订单
  async createOrder(data: {
    product_id: number
    address_id: number
    quantity: number
    note?: string
  }): Promise<CreateOrderResponse> {
    return http.post<CreateOrderResponse>('/orders/create_order/', data)
  },

  // 批量创建订单（购物车结算）
  async createBatchOrders(data: {
    items: Array<{ product_id: number; quantity: number }>
    address_id: number
    note?: string
    method?: string
  }): Promise<{
    orders: Order[]
    payments: any[]
  }> {
    return http.post('/orders/create_batch_orders/', data)
  },
  
  // 获取我的订单列表
  async getMyOrders(params?: {
    status?: string
    page?: number
    page_size?: number
  }): Promise<PaginatedResponse<Order>> {
    return http.get<PaginatedResponse<Order>>('/orders/my_orders/', params)
  },
  
  // 获取订单详情
  async getOrderDetail(id: number): Promise<Order> {
    return http.get<Order>(`/orders/${id}/`)
  },
  
  // 取消订单
  async cancelOrder(id: number): Promise<Order> {
    return http.patch<Order>(`/orders/${id}/cancel/`)
  },

  // 申请发票
  async requestInvoice(id: number, data: any): Promise<any> {
    return http.post(`/orders/${id}/request_invoice/`, data)
  }
}
