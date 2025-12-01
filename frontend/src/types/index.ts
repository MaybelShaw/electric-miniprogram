// 用户相关
export interface User {
  id: number
  username: string
  avatar_url: string
  phone: string
  email: string
  role: 'individual' | 'dealer' | 'admin'
  last_login_at?: string
  orders_count?: number
  has_company_info?: boolean
  company_status?: 'pending' | 'approved' | 'rejected'
  company_name?: string
}

export interface LoginResponse {
  access: string
  refresh: string
  user: User
}

// 商品相关
export interface Product {
  id: number
  name: string
  description: string
  category: string  // 分类名称
  brand: string  // 品牌名称
  category_id: number
  brand_id: number
  price: string
  stock: number
  main_images: string[]
  detail_images: string[]
  specifications?: Record<string, any>  // 商品规格
  is_active: boolean
  sales_count: number
  view_count: number
  discounted_price: number  // 折扣后价格
  originalPrice: number  // 原价
  created_at: string
  updated_at: string
}

export interface ProductListResponse {
  results: Product[]
  total: number
  page: number
  total_pages: number
  has_next: boolean
  has_previous: boolean
}

// 分类相关
export interface Category {
  id: number
  name: string
  order: number
}

// 品牌相关
export interface Brand {
  id: number
  name: string
  logo: string
  description: string
  order: number
  is_active: boolean
}

// 购物车相关
export interface CartItem {
  id: number
  product: Product
  product_id: number
  quantity: number
  selected?: boolean // 前端状态
}

export interface Cart {
  id: number
  user: number
  items: CartItem[]
}

// 地址相关
export interface Address {
  id: number
  contact_name: string
  phone: string
  province: string
  city: string
  district: string
  detail: string
  is_default: boolean
}

// 订单相关
export type OrderStatus = 'pending' | 'paid' | 'shipped' | 'completed' | 'cancelled' | 'returning' | 'refunding' | 'refunded'

export interface Order {
  id: number
  order_number: string
  user: number
  user_username: string
  product: Product
  quantity: number
  total_amount: string
  status: OrderStatus
  status_label: string
  note: string
  snapshot_contact_name: string
  snapshot_phone: string
  snapshot_address: string
  created_at: string
  updated_at: string
  logistics_info?: {
    logistics_no: string
    delivery_record_code: string
    sn_code: string
    delivery_images: string[]
  }
  invoice_info?: {
    id: number
    status: string
    status_display: string
    file_url: string
    invoice_number: string
  }
  return_info?: ReturnRequest
}

export interface ReturnRequest {
  id: number
  status: 'requested' | 'approved' | 'in_transit' | 'received' | 'rejected'
  status_display: string
  reason: string
  tracking_number: string
  evidence_images: string[]
  created_at: string
  updated_at: string
  processed_note: string
  processed_at: string | null
}

export interface Payment {
  id: number
  order: number
  amount: string
  method: 'wechat' | 'alipay' | 'bank'
  status: 'pending' | 'processing' | 'succeeded' | 'failed' | 'cancelled' | 'expired'
  created_at: string
  updated_at: string
  expires_at: string
  logs: Array<{ t: string; event: string; detail?: string }>
}

export interface CreateOrderResponse {
  order: Order
  payment: Payment
}



// 分页响应
export interface PaginatedResponse<T> {
  results: T[]
  total: number
  page: number
  total_pages: number
  has_next: boolean
  has_previous: boolean
}
