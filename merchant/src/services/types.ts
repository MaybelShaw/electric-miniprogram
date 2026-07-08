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
  company_info?: {
    company_name?: string;
    status?: string;
  } | null;
  store_roles?: {
    store: number;
    store_name: string;
    store_is_main?: boolean;
    role: 'platform_admin' | 'store_admin' | 'store_sub_admin' | 'store_staff';
    permissions?: string[];
    status: 'active' | 'disabled';
  }[];
}

export interface Store {
  id: number;
  name: string;
  code: string;
  status: 'active' | 'disabled';
  is_main: boolean;
  store_type?: 'self_operated' | 'partner' | 'supplier';
  logo?: string;
  cover_image?: string;
  description?: string;
  is_visible?: boolean;
  show_on_home?: boolean;
  home_order?: number;
  contact_phone?: string;
  address?: string;
  allow_haier: boolean;
  show_customer_group_name?: boolean;
  created_at: string;
  updated_at: string;
}

export interface StoreMember {
  id: number;
  user: number;
  username: string;
  store: number;
  store_name: string;
  store_is_main?: boolean;
  role: 'platform_admin' | 'store_admin' | 'store_sub_admin' | 'store_staff';
  permissions?: string[];
  status: 'active' | 'disabled';
}

export interface CurrentStoreContext {
  is_platform_admin: boolean;
  default_store: Store | null;
  stores: Store[];
  memberships: StoreMember[];
}

export type ProfitSharingEntryStatus =
  | 'platform_retained'
  | 'pending_receiver_config'
  | 'frozen'
  | 'available'
  | 'available_for_manual_share'
  | 'processing'
  | 'shared'
  | 'failed'
  | 'manual_settled'
  | 'manual_settlement_required'
  | 'cancelled';

export interface StoreProfitSharingEntry {
  id: number;
  checkout_order: number;
  checkout_number: string;
  payment: number;
  order: number;
  suborder: number;
  suborder_number: string;
  store: number;
  store_name: string;
  store_type_snapshot: string;
  gross_amount: string | number;
  commission_rate_snapshot: string | number;
  commission_amount: string | number;
  sharing_amount: string | number;
  retained_amount: string | number;
  receiver_type: string;
  receiver_account: string;
  receiver_name_snapshot: string;
  status: ProfitSharingEntryStatus;
  available_at: string | null;
  shared_at: string | null;
  failure_reason: string;
  logs: Record<string, any>[];
  created_at: string;
  updated_at: string;
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
  dealer_price?: number | null;
  image?: string;
  description?: string;
  category_id?: number;
  brand_id?: number;
  brand?: string;
  category?: string;
  stock: number;
  main_images?: string[];
  detail_images?: string[];
  specifications?: Record<string, string | number | boolean>;
  is_active: boolean;
  sales_count?: number;
  view_count?: number;
  tag?: string;
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
  show_in_gift_zone?: boolean;
  show_in_designer_zone?: boolean;
  show_in_best_seller_zone?: boolean;
  show_in_promotion_zone?: boolean;
  store?: number;
  display_price?: string | number;
  discounted_price?: string | number;
  customer_group_id?: number | null;
  customer_group_name?: string;
  show_customer_group_name?: boolean;
}

export interface ProductSKU {
  id: number;
  product: number;
  product_id?: number;
  product_name: string;
  name: string;
  sku_code: string;
  specs: Record<string, string | number | boolean>;
  price: string | number;
  display_price?: string | number;
  discounted_price?: string | number;
  stock: number;
  image: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface StoreCustomerGroup {
  id: number;
  store: number;
  store_name?: string;
  name: string;
  description?: string;
  status: 'active' | 'disabled';
  member_count?: number;
  active_member_count?: number;
  price_count?: number;
  created_at: string;
  updated_at: string;
}

export interface StoreCustomerGroupMember {
  id: number;
  store: number;
  store_name?: string;
  group: number;
  group_name?: string;
  user?: number | null;
  username?: string | null;
  phone: string;
  status: 'active' | 'disabled';
  created_at: string;
  updated_at: string;
}

export interface StoreCustomerGroupPrice {
  id: number;
  store: number;
  group: number;
  group_name?: string;
  product: number;
  product_name?: string;
  product_source?: 'local' | 'haier';
  product_price?: string | number;
  sku?: number | null;
  sku_name?: string | null;
  sku_code?: string | null;
  sku_price?: string | number | null;
  price: string | number;
  created_at: string;
  updated_at: string;
}

export interface MediaImage {
  id: number;
  file?: string;
  url: string;
  original_name: string;
  content_type: string;
  size: number;
  created_at: string;
}

export interface SearchLog {
  id: number;
  keyword: string;
  user_id?: number | null;
  username?: string | null;
  created_at: string;
}

export interface InventoryLog {
  id: number;
  product: number;
  product_name: string;
  sku?: number | null;
  sku_name?: string | null;
  change_type: 'lock' | 'release' | 'adjust';
  change_type_display: string;
  quantity: number;
  reason: string;
  created_by?: number | null;
  created_by_username?: string | null;
  created_at: string;
}

export interface SpecialZone {
  id: number;
  store: number;
  store_id?: number;
  title: string;
  slug: string;
  kind: 'platform_activity' | 'store_activity' | 'activity' | 'promotion' | 'category' | 'brand' | 'custom';
  subtitle: string;
  cover_image: string;
  is_active: boolean;
  show_on_home: boolean;
  home_order: number;
  description?: string;
  rules?: string;
  start_at: string | null;
  end_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface SpecialZoneProduct {
  id: number;
  zone: number;
  product: Product;
  product_id: number;
  is_active: boolean;
  order: number;
  created_at: string;
}

export interface ProductActivities {
  available: SpecialZone[];
  selected: SpecialZone[];
  can_edit: boolean;
}

export interface HomeStoreCard {
  id: number;
  store: number;
  store_id?: number;
  store_name?: string;
  title: string;
  subtitle: string;
  order: number;
  is_active: boolean;
  main_product?: Product | null;
  secondary_products: Product[];
  categories: Category[];
  has_inactive_products: boolean;
  inactive_product_names: string[];
  created_at: string;
  updated_at: string;
}

export interface HaierOrderInfo {
  haier_so_id?: string;
  haier_order_no?: string;
  haier_status?: string;
  haier_fail_msg?: string;
  product_code?: string;
}

export interface ShippingItem {
  tracking_no?: string;
  express_company?: string;
  item_desc?: string;
  contact?: Record<string, string>;
}

export interface ShippingInfo {
  logistics_type?: number;
  delivery_mode?: number;
  is_all_delivered?: boolean | null;
  shipping_list?: ShippingItem[];
}

export interface LogisticsInfo {
  logistics_no?: string;
  delivery_record_code?: string;
  sn_code?: string;
  delivery_images?: string[];
  shipping_info?: ShippingInfo | null;
}

export interface ShippingSnapshot {
  logistics_no: string;
  shipping_info: ShippingInfo;
  delivery_record_code: string;
  sn_code: string;
  delivery_images: string[];
}

export interface OrderShippingAction {
  id: number;
  action: 'ship' | 'cancel_shipping' | 'reship';
  action_label: string;
  status: 'succeeded' | 'failed';
  status_label: string;
  shipping_snapshot: ShippingSnapshot;
  operator: number | null;
  operator_username: string | null;
  reason: string;
  wechat_sync_required: boolean;
  wechat_synced: boolean;
  wechat_response: {
    errcode?: number;
    errmsg?: string;
    error?: string;
  };
  created_at: string;
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
  discount_amount?: number;
  actual_amount?: number;
  refunded_amount?: number | string;
  refundable_amount?: number | string;
  refund_pending?: boolean;
  refund_action_required?: boolean;
  status: 'pending' | 'paid' | 'shipped' | 'completed' | 'cancelled' | 'returning' | 'refunding' | 'refunded';
  payment_method?: string;
  is_haier_order: boolean;
  haier_order_info?: HaierOrderInfo;
  snapshot_contact_name: string;
  snapshot_phone: string;
  snapshot_address: string;
  logistics_info?: LogisticsInfo;
  can_cancel_shipping: boolean;
  is_reshipment_pending: boolean;
  reship_requires_wechat_sync: boolean;
  shipping_cancel_count: number;
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
  position: 'home' | 'gift' | 'designer' | 'best_seller' | 'promotion';
  order: number;
  is_active: boolean;
  image_id: number;
  image_url: string;
  product_id?: number | null;
  product_name?: string;
  special_zone?: number | null;
  special_zone_id?: number | null;
  store?: number;
  created_at: string;
  updated_at: string;
}

export interface SpecialZoneCover {
  id: number;
  type: 'gift' | 'designer';
  is_active: boolean;
  image_id: number;
  image_url: string;
  store?: number;
  created_at: string;
  updated_at: string;
}

export interface SupportMessage {
  id: number;
  conversation: number;
  ticket?: number; // Backward compatibility
  sender: number;
  sender_username: string;
  role: string;
  content: string;
  content_type?: 'text' | 'card' | 'quick_buttons';
  content_payload?: Record<string, any>;
  template?: number | null;
  attachment_url?: string;
  attachment_type?: 'image' | 'video';
  order_info?: {
    id: number;
    order_number: string;
    status: string;
    quantity: number;
    total_amount: string;
    product_name: string;
    image: string;
  };
  product_info?: {
    id: number;
    name: string;
    price: string;
    image: string;
  };
  created_at: string;
}

export interface SupportConversation {
  id: number;
  store: number;
  store_name: string;
  user: number;
  user_username: string;
  created_at: string;
  updated_at: string;
  last_message?: SupportMessage;
  last_message_at?: string;
}

export type SupportTicket = SupportConversation; // Alias for backward compatibility during refactor

export interface SupportReplyTemplate {
  id: number;
  template_type: 'auto' | 'quick';
  title: string;
  content: string;
  content_type: 'text' | 'card' | 'quick_buttons';
  content_payload?: Record<string, any>;
  group_name?: string;
  is_pinned?: boolean;
  enabled: boolean;
  trigger_event?: 'first_contact' | 'idle_contact' | 'both' | null;
  idle_minutes?: number | null;
  daily_limit?: number;
  user_cooldown_days?: number;
  apply_channels?: string[];
  apply_user_tags?: string[];
  usage_count?: number;
  last_used_at?: string | null;
  sort_order?: number;
  created_at?: string;
  updated_at?: string;
}

export type FeedbackTicketType = 'question' | 'requirement';
export type FeedbackTicketStatus = 'pending' | 'replied' | 'closed';
export type FeedbackRecordType = 'user_supplement' | 'merchant_reply' | 'close';

export interface FeedbackTicketReply {
  id: number;
  ticket: number;
  sender: number;
  sender_username: string;
  record_type: FeedbackRecordType;
  record_type_display: string;
  content: string;
  attachments: string[];
  created_at: string;
}

export interface FeedbackTicket {
  id: number;
  ticket_number: string;
  store: number;
  store_name: string;
  user: number;
  user_username: string;
  user_phone?: string;
  ticket_type: FeedbackTicketType;
  ticket_type_display: string;
  title: string;
  content: string;
  contact_phone: string;
  attachments: string[];
  status: FeedbackTicketStatus;
  status_display: string;
  last_replied_at?: string | null;
  created_at: string;
  updated_at: string;
  replies: FeedbackTicketReply[];
}

export interface CaseDetailBlock {
  id?: number;
  block_type: 'text' | 'image';
  text: string;
  image?: number | null;
  image_url?: string;
  order: number;
}

export interface Case {
  id: number;
  title: string;
  cover_image: number;
  cover_image_url?: string;
  order: number;
  is_active: boolean;
  detail_blocks: CaseDetailBlock[];
  created_at: string;
  updated_at: string;
}
