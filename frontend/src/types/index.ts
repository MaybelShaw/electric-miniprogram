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
  company_status?: 'pending' | 'approved' | 'rejected' | 'withdrawn'
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
  store?: number
  store_id?: number
  store_type?: StoreType
  store_is_main?: boolean
  name: string
  description: string
  category: string  // 分类名称
  brand: string  // 品牌名称
  category_id: number
  brand_id: number
  price: string
  display_price?: string | number
  dealer_price?: string | number
  customer_group_id?: number | null
  customer_group_name?: string
  show_customer_group_name?: boolean
  stock: number
  total_stock?: number
  main_images: string[]
  detail_images: string[]
  product_attachments?: ProductAttachment[]
  specifications?: Record<string, any>  // 商品规格
  spec_options?: Record<string, string[]>
  skus?: ProductSKU[]
  is_active: boolean
  sales_count: number
  view_count: number
  tag?: string  // 商品标签：brand_direct | source_factory
  discounted_price: number  // 折扣后价格
  originalPrice: number  // 原价
  show_in_gift_zone?: boolean
  show_in_designer_zone?: boolean
  show_in_best_seller_zone?: boolean
  show_in_promotion_zone?: boolean
  created_at: string
  updated_at: string
}

export interface ProductAttachment {
  name?: string
  original_name?: string
  url: string
  file_type?: 'pdf'
  size?: number
}

export interface ProductSKU {
  id: number
  name: string
  sku_code?: string
  specs: Record<string, string>
  price: string | number
  display_price?: string | number
  discounted_price?: string | number
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

export type LegacySpecialZoneType = 'gift' | 'designer' | 'best_seller' | 'promotion'
export type HomeBannerPosition = 'home' | LegacySpecialZoneType

// 轮播图
export interface HomeBanner {
  id: number
  title: string
  position: HomeBannerPosition
  order: number
  image_url: string
  image_id: number
  special_zone?: number | null
  special_zone_id?: number | null
  product_id?: number | null
  product_name?: string
}

export type SpecialZoneKind = 'platform_activity' | 'store_activity' | 'activity' | 'promotion' | 'category' | 'brand' | 'custom'

export interface SpecialZone {
  id: number
  store: number
  store_id?: number
  title: string
  slug: string
  kind: SpecialZoneKind
  subtitle: string
  cover_image: string
  is_active: boolean
  show_on_home: boolean
  home_order: number
  description?: string
  rules?: string
  start_at?: string | null
  end_at?: string | null
  created_at: string
  updated_at: string
}

export interface HomeStoreCard {
  id: number
  store: number
  store_id?: number
  store_type?: StoreType
  store_is_main?: boolean
  store_name?: string
  title: string
  subtitle: string
  order: number
  is_active: boolean
  main_product?: Product | null
  secondary_products: Product[]
  categories: Category[]
  has_inactive_products: boolean
  inactive_product_names: string[]
}

// 首页专区图片
export interface SpecialZoneCover {
  id: number
  store?: number
  store_id?: number
  type: LegacySpecialZoneType
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
  store_id?: number
  store_name?: string
  store_logo?: string
  store_type?: StoreType
  store_is_main?: boolean
  is_available?: boolean
  unavailable_reason?: string
  selected?: boolean // 前端状态
}

export interface CartStoreGroup {
  store_id: number
  store_name: string
  store_logo?: string
  store_type?: StoreType
  store_is_main?: boolean
  item_count: number
  total_quantity: number
  items: CartItem[]
}

export interface Cart {
  id: number
  user: number
  items: CartItem[]
  store_groups?: CartStoreGroup[]
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
  refunded_amount?: string
  refundable_amount?: string
  refund_pending?: boolean
  refund_locked?: boolean
  payment_method?: 'wechat' | 'alipay' | 'bank' | 'credit' | 'unknown'
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
    shipping_info?: {
      logistics_type?: number
      delivery_mode?: number
      is_all_delivered?: boolean | null
      shipping_list?: Array<{
        tracking_no?: string
        express_company?: string
        express_company_name?: string
        item_desc?: string
        contact?: {
          receiver_contact?: string
        }
      }>
    }
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
  evidence_images?: string[]
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

export type StoreType = 'self_operated' | 'partner' | 'supplier'

export interface Store {
  id: number
  name: string
  code: string
  is_main?: boolean
  store_type: StoreType
  platform_store?: number | null
  logo?: string
  cover_image?: string
  description?: string
  contact_phone?: string
  address?: string
  home_order?: number
  show_customer_group_name?: boolean
}

export interface PublicStoreDetail {
  store: Store
  banners: HomeBanner[]
  categories: Category[]
  brands: Brand[]
  special_zones: SpecialZone[]
  products: Product[]
  new_arrivals: Product[]
}
