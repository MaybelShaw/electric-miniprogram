export interface User {
  id: number;
  username: string;
  openid: string;
  email: string;
  phone: string;
  role: 'individual' | 'dealer' | 'admin';
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
  logistics_company?: string;
  logistics_no?: string;
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
  created_at: string;
}

export interface PaginationResult<T> {
  results: T[];
  count: number;
  next?: string | null;
  previous?: string | null;
}
