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

// 通知中心
export type NotificationType = 'payment' | 'order' | 'refund' | 'return' | 'statement' | 'system'

export interface Notification {
  id: number
  title: string
  content: string
  type: NotificationType
  type_display?: string
  status: 'pending' | 'sent' | 'failed'
  status_display?: string
  metadata: Record<string, any>
  created_at: string
  sent_at?: string | null
  read_at?: string | null
  is_read: boolean
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
  total_stock?: number
  main_images: string[]
  detail_images: string[]
  specifications?: Record<string, any>  // 商品规格
  spec_options?: Record<string, string[]>
  skus?: ProductSKU[]
  is_active: boolean
  sales_count: number
  view_count: number
  discounted_price: number  // 折扣后价格
  originalPrice: number  // 原价
  created_at: string
  updated_at: string
}

export interface ProductSKU {
  id: number
  name: string
  sku_code?: string
  specs: Record<string, string>
  price: string | number
  stock: number
  image?: string
  is_active: boolean
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
  logo?: string
  level?: 'major' | 'minor' | 'item'
  parent_id?: number
  children?: Category[]
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

// 轮播图
export interface HomeBanner {
  id: number
  title: string
  link_url: string
  position: 'home' | 'gift' | 'designer'
  order: number
  image_url: string
  image_id: number
}

// 首页专区图片
export interface SpecialZoneCover {
  id: number
  type: 'gift' | 'designer'
  is_active: boolean
  image_url: string
  image_id: number
}

// 购物车相关
export interface CartItem {
  id: number
  product: Product
  product_id: number
  sku?: ProductSKU | null
  sku_id?: number | null
  sku_specs?: Record<string, string>
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
  product?: Product | null
  items?: OrderLineItem[]
  quantity: number
  total_amount: string
  discount_amount?: string
  actual_amount?: string
  status: OrderStatus
  status_label: string
  note: string
  snapshot_contact_name: string
  snapshot_phone: string
  snapshot_address: string
  created_at: string
  updated_at: string
  expires_at?: string
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

export interface OrderLineItem {
  id: number
  product: Product | null
  product_name: string
  sku?: ProductSKU | null
  sku_id?: number | null
  sku_specs?: Record<string, string>
  sku_code?: string
  snapshot_image?: string
  quantity: number
  unit_price: string
  discount_amount: string
  actual_amount: string
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
  status: 'init' | 'processing' | 'succeeded' | 'failed' | 'cancelled' | 'expired'
  created_at: string
  updated_at: string
  expires_at: string
  logs: Array<{ t: string; event: string; detail?: string }>
}

export interface WechatPayParams {
  appId: string
  mch_id: string
  timeStamp: string
  nonceStr: string
  package: string
  signType: string
  paySign: string
  prepay_id: string
  signPayload?: string
  payment_id?: number
  order_number?: string
  amount?: string
  total_fee?: number
  total?: number
}

export interface PaymentStartResponse {
  payment: Payment
  pay_params?: WechatPayParams | null
}

export interface Refund {
  id: number
  order: number
  order_number?: string
  payment?: number | null
  payment_method?: 'wechat' | 'alipay' | 'bank'
  amount: string
  status: 'pending' | 'processing' | 'succeeded' | 'failed'
  reason: string
  transaction_id?: string
  operator?: number | null
  logs: Array<Record<string, any>>
  created_at: string
  updated_at: string
}

export interface CreateOrderResponse {
  order: Order
  payment: Payment | null
}

// 案例相关
export interface CaseDetailBlock {
  id?: number
  block_type: 'text' | 'image'
  text: string
  image?: number | null
  image_url?: string
  order: number
}

export interface Case {
  id: number
  title: string
  cover_image: number
  cover_image_url?: string
  order: number
  is_active: boolean
  detail_blocks: CaseDetailBlock[]
  created_at: string
  updated_at: string
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
