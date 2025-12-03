export interface User {
  id: number;
  username: string;
  openid: string;
  email: string;
  phone: string;
  role: 'individual' | 'dealer' | 'admin' | 'support';
  is_staff: boolean;
  date_joined: string;
  last_login_at: string;
}

export interface Brand {
  id: number;
  name: string;
  logo?: string;
  description?: string;
}

export interface Category {
  id: number;
  name: string;
  icon?: string;
  parent?: number;
}

export interface Product {
  id: number;
  name: string;
  price: number;
  image?: string;
  description?: string;
  category_id?: number;
  brand_id?: number;
  brand?: string;
  category?: string;
  stock: number;
  main_images?: string[];
  detail_images?: string[];
  is_active: boolean;
  sales_count?: number;
  view_count?: number;
  source: 'local' | 'haier';
  min_price?: number;
  max_price?: number;
  product_code?: string;
  product_model?: string;
  product_group?: string;
  supply_price?: number;
  invoice_price?: number;
  market_price?: number;
  stock_rebate?: number;
  rebate_money?: number;
  warehouse_code?: string;
  warehouse_grade?: string;
  is_sales?: string;
  no_sales_reason?: string;
}

export interface HaierOrderInfo {
  haier_so_id?: string;
  haier_order_no?: string;
}

export interface LogisticsInfo {
  logistics_no?: string;
}

export interface ReturnInfo {
  status: 'requested' | 'approved' | 'in_transit' | 'received' | 'rejected';
  status_display: string;
  reason: string;
  tracking_number: string;
  evidence_images: string[];
  created_at: string;
  updated_at: string;
  processed_note: string;
  processed_at: string | null;
}

export interface Order {
  id: number;
  order_number: string;
  user_username: string;
  product: Product;
  quantity: number;
  total_amount: number;
  status: 'pending' | 'paid' | 'shipped' | 'completed' | 'cancelled' | 'refunding' | 'refunded';
  is_haier_order: boolean;
  haier_order_info?: HaierOrderInfo;
  snapshot_contact_name: string;
  snapshot_phone: string;
  snapshot_address: string;
  logistics_info?: LogisticsInfo;
  return_info?: ReturnInfo;
  invoice_info?: {
    id: number;
    status: string;
    status_display: string;
    file_url: string;
    invoice_number: string;
  };
  created_at: string;
}

export interface PaginationResult<T> {
  results: T[];
  count: number;
  next?: string | null;
  previous?: string | null;
}

export interface HomeBanner {
  id: number;
  title: string;
  link_url: string;
  order: number;
  is_active: boolean;
  image_id: number;
  image_url: string;
  created_at: string;
  updated_at: string;
}

export interface SupportMessage {
  id: number;
  ticket: number;
  sender: number;
  sender_username: string;
  role: string;
  content: string;
  attachment_url?: string;
  attachment_type?: 'image' | 'video';
  created_at: string;
}

export interface SupportTicket {
  id: number;
  user: number;
  user_username: string;
  order: number | null;
  order_number?: string;
  subject: string;
  status: 'open' | 'pending' | 'resolved' | 'closed';
  priority: 'low' | 'normal' | 'high';
  assigned_to: number | null;
  assigned_to_username?: string;
  created_at: string;
  updated_at: string;
  messages?: SupportMessage[];
}
