import request from '@/utils/request';
import type { CurrentStoreContext, StoreProfitSharingEntry, WechatProfitSharingOrder } from './types';
import { withSelectedStoreId } from '@/utils/storeScope';

// 登录
export const loginAdmin = (data: { username: string; password: string }) =>
  request.post('/admin/login/', data);

export const loginSupport = (data: { username: string; password: string }) =>
  request.post('/password_login/', data);

// 兼容旧调用
export const login = (data: { username: string; password: string }) =>
  request.post('/admin/login/', data);

// 店铺上下文
export const getCurrentStoreContext = (): Promise<CurrentStoreContext> =>
  request.get('/stores/current/');
export const getStores = (params?: any) => request.get('/stores/', { params });
export const createStore = (data: any) => request.post('/stores/', data);
export const updateStore = (id: number, data: any) => request.patch(`/stores/${id}/`, data);
export const getStoreMembers = (params?: any) => request.get('/stores/members/', { params });
export const getStoreMemberCandidates = (params?: any) => request.get('/stores/members/available_users/', { params });
export const createStoreMember = (data: any) => request.post('/stores/members/', data);
export const createStoreMemberUser = (data: any) => request.post('/stores/members/create_user_member/', data);
export const updateStoreMember = (id: number, data: any) => request.patch(`/stores/members/${id}/`, data);
export const deleteStoreMember = (id: number) => request.delete(`/stores/members/${id}/`);
export const getStoreCustomerGroups = (params?: any) => request.get('/stores/customer-groups/', { params });
export const createStoreCustomerGroup = (data: any) => request.post('/stores/customer-groups/', data);
export const updateStoreCustomerGroup = (id: number, data: any) => request.patch(`/stores/customer-groups/${id}/`, data);
export const deleteStoreCustomerGroup = (id: number) => request.delete(`/stores/customer-groups/${id}/`);
export const getStoreCustomerGroupMembers = (params?: any) => request.get('/stores/customer-group-members/', { params });
export const createStoreCustomerGroupMember = (data: any) => request.post('/stores/customer-group-members/', data);
export const updateStoreCustomerGroupMember = (id: number, data: any) => request.patch(`/stores/customer-group-members/${id}/`, data);
export const deleteStoreCustomerGroupMember = (id: number) => request.delete(`/stores/customer-group-members/${id}/`);
export const getStoreCustomerGroupPrices = (params?: any) => request.get('/stores/customer-group-prices/', { params });
export const createStoreCustomerGroupPrice = (data: any) => request.post('/stores/customer-group-prices/', data);
export const updateStoreCustomerGroupPrice = (id: number, data: any) => request.patch(`/stores/customer-group-prices/${id}/`, data);
export const deleteStoreCustomerGroupPrice = (id: number) => request.delete(`/stores/customer-group-prices/${id}/`);

// 用户管理
export const getUsers = (params?: any) => request.get('/users/', { params });
export const exportUsers = (params?: any) => request.get('/users/export/', { params, responseType: 'blob' });
export const getUser = (id: number) => request.get(`/users/${id}/`);
export const createUser = (data: any) => request.post('/users/', data);
export const updateUser = (id: number, data: any) => request.patch(`/users/${id}/`, data);
export const deleteUser = (id: number) => request.delete(`/users/${id}/`);
export const forceDeleteUser = (id: number) => request.post(`/users/${id}/force_delete/`);
export const setAdmin = (id: number) => request.post(`/users/${id}/set_admin/`);
export const unsetAdmin = (id: number) => request.post(`/users/${id}/unset_admin/`);
export const getUserTransactionStats = (id: number, params?: any) => request.get(`/users/${id}/transaction_stats/`, { params });
export const exportUserTransactionStats = (id: number, params?: any) => request.get(`/users/${id}/export_transaction_stats/`, { params, responseType: 'blob' });
export const getCustomersTransactionStats = (params?: any) => request.get(`/users/customers_transaction_stats/`, { params });
export const exportCustomersTransactionStats = (params?: any) => request.get(`/users/export_customers_transaction_stats/`, { params, responseType: 'blob' });

// 品牌管理
export const getBrands = (params?: any) => request.get('/catalog/brands/', { params });
export const createBrand = (data: any) => request.post('/catalog/brands/', withSelectedStoreId(data));
export const updateBrand = (id: number, data: any) => request.patch(`/catalog/brands/${id}/`, data);
export const deleteBrand = (id: number, force?: boolean) =>
  request.delete(`/catalog/brands/${id}/`, { params: { force_delete: force } });

// 品类管理
export const getCategories = (params?: any) => request.get('/catalog/categories/', { params });
export const createCategory = (data: any) => request.post('/catalog/categories/', withSelectedStoreId(data));
export const updateCategory = (id: number, data: any) => request.patch(`/catalog/categories/${id}/`, data);
export const deleteCategory = (id: number) => request.delete(`/catalog/categories/${id}/`);

// 产品管理
export const getProducts = (params?: any) => request.get('/catalog/products/', { params });
export const getProduct = (id: number) => request.get(`/catalog/products/${id}/`);
export const createProduct = (data: any) => request.post('/catalog/products/', withSelectedStoreId(data));
export const updateProduct = (id: number, data: any) => request.patch(`/catalog/products/${id}/`, data);
export const deleteProduct = (id: number) => request.delete(`/catalog/products/${id}/`);
export const exportProducts = (params?: any) => request.get('/catalog/products/export/', { params, responseType: 'blob' });
export const getProductActivities = (id: number) => request.get(`/catalog/products/${id}/activities/`);
export const updateProductActivities = (id: number, activityIds: number[]) =>
  request.put(`/catalog/products/${id}/activities/`, { activity_ids: activityIds });
export const getProductSkus = (params?: any) => request.get('/catalog/product-skus/', { params });
export const createProductSku = (data: any) => request.post('/catalog/product-skus/', data);
export const updateProductSku = (id: number, data: any) => request.patch(`/catalog/product-skus/${id}/`, data);
export const deleteProductSku = (id: number) => request.delete(`/catalog/product-skus/${id}/`);
export const getInventoryLogs = (params?: any) => request.get('/catalog/inventory-logs/', { params });
export const getSearchLogs = (params?: any) => request.get('/catalog/search-logs/', { params });
export const getHaierProducts = (productCodes: string) => request.get('/haier/api/products/', { params: { product_codes: productCodes } });
export const getHaierStock = (productCode: string, countyCode: string = '110101') => request.get('/haier/api/stock/', { params: { product_code: productCode, county_code: countyCode } });
export const getHaierPrices = (productCodes: string) => request.get('/haier/api/prices/', { params: { product_codes: productCodes } });

// 图片上传
export const uploadImage = (file: File, productId?: number, fieldName?: string) => {
  const formData = new FormData();
  formData.append('file', file);
  
  // 如果提供了产品ID和字段名，添加到表单数据中
  if (productId) {
    formData.append('product_id', productId.toString());
  }
  if (fieldName) {
    formData.append('field_name', fieldName);
  }
  
  return request.post('/catalog/media-images/', formData);
};
export const getMediaImages = (params?: any) => request.get('/catalog/media-images/', { params });
export const deleteMediaImage = (id: number) => request.delete(`/catalog/media-images/${id}/`);

// 订单管理
export const getOrders = (params?: any) => request.get('/orders/', { params });
export const exportOrders = (params?: any) => request.get('/orders/export/', { params, responseType: 'blob' });
export const getOrder = (id: number) => request.get(`/orders/${id}/`);
export const shipOrder = (id: number, data?: any) => request.patch(`/orders/${id}/ship/`, data || {});
export const cancelShipping = (id: number, data: { reason: string }) =>
  request.patch(`/orders/${id}/cancel_shipping/`, data);
export const getShippingActions = (id: number) =>
  request.get(`/orders/${id}/shipping_actions/`);
export const completeOrder = (id: number) => request.patch(`/orders/${id}/complete/`, {});
export const cancelOrder = (id: number, data?: any) => request.patch(`/orders/${id}/cancel/`, data || {});
export const adjustOrderAmount = (id: number, data: { actual_amount: number }) =>
  request.post(`/orders/${id}/adjust_amount/`, data);
export const pushToHaier = (id: number, data?: any) => request.post(`/orders/${id}/push_to_haier/`, data || {});
export const getHaierLogistics = (id: number) => request.get(`/orders/${id}/haier_logistics/`);
export const getDeliveryCompanies = () => request.get('/haier/wechat/delivery-companies/');
export const receiveReturn = (id: number, data?: any) => request.patch(`/orders/${id}/receive_return/`, data || {});
export const completeRefund = (id: number) => request.patch(`/orders/${id}/complete_refund/`, {});
export const approveReturn = (id: number, data?: any) => request.patch(`/orders/${id}/approve_return/`, data || {});
export const rejectReturn = (id: number, data?: any) => request.patch(`/orders/${id}/reject_return/`, data || {});

// 折扣管理
export const getDiscounts = (params?: any) => request.get('/discounts/', { params });
export const exportDiscounts = (params?: any) => request.get('/discounts/export/', { params, responseType: 'blob' });
export const createDiscount = (data: any) => request.post('/discounts/', data);
export const updateDiscount = (id: number, data: any) => request.patch(`/discounts/${id}/`, data);
export const deleteDiscount = (id: number) => request.delete(`/discounts/${id}/`);

// 公司认证管理
export const getCompanyInfoList = (params?: any) => request.get('/company-info/', { params });
export const getCompanyInfo = (id: number) => request.get(`/company-info/${id}/`);
export const approveCompanyInfo = (id: number) => request.post(`/company-info/${id}/approve/`);
export const rejectCompanyInfo = (id: number, data?: any) => request.post(`/company-info/${id}/reject/`, data || {});

// 信用账户管理
export const getCreditAccounts = (params?: any) => request.get('/credit-accounts/', { params });
export const getCreditAccount = (id: number) => request.get(`/credit-accounts/${id}/`);
export const createCreditAccount = (data: any) => request.post('/credit-accounts/', data);
export const updateCreditAccount = (id: number, data: any) => request.patch(`/credit-accounts/${id}/`, data);

// 对账单管理
export const getAccountStatements = (params?: any) => request.get('/account-statements/', { params });
export const getAccountStatement = (id: number) => request.get(`/account-statements/${id}/`);
export const createAccountStatement = (data: any) => request.post('/account-statements/', data);
export const confirmAccountStatement = (id: number) => request.post(`/account-statements/${id}/confirm/`);
export const settleAccountStatement = (id: number) => request.post(`/account-statements/${id}/settle/`);
export const exportAccountStatement = (id: number) => {
  return request.get(`/account-statements/${id}/export/`, { responseType: 'blob' });
};
export const exportAccountStatements = (params?: any) => request.get('/account-statements/export/', { params, responseType: 'blob' });

// 退款管理
export const getRefunds = (params?: any) => request.get('/refunds/', { params });
export const startRefund = (id: number, data?: any) => request.post(`/refunds/${id}/start/`, data || {});
export const failRefund = (id: number, data?: any) => request.post(`/refunds/${id}/fail/`, data || {});

// 交易记录管理
export const getAccountTransactions = (params?: any) => request.get('/account-transactions/', { params });
export const exportAccountTransactions = (params?: any) => request.get('/account-transactions/export/', { params, responseType: 'blob' });

// 微信分账管理
export const getProfitSharingEntries = (params?: any): Promise<any> =>
  request.get('/profit-sharing-entries/', { params });
export const markProfitSharingEntriesAvailable = (): Promise<{ updated: number }> =>
  request.post('/profit-sharing-entries/mark_available/', {});
export const shareProfitSharingEntries = (data: { entry_ids: number[]; unfreeze_unsplit?: boolean }): Promise<WechatProfitSharingOrder> =>
  request.post('/profit-sharing-entries/share/', data);
export const markProfitSharingEntryManualSettled = (id: number, data?: { note?: string }): Promise<StoreProfitSharingEntry> =>
  request.post(`/profit-sharing-entries/${id}/mark_manual_settled/`, data || {});
export const getWechatProfitSharingOrders = (params?: any): Promise<any> =>
  request.get('/wechat-profit-sharing-orders/', { params });
export const markWechatProfitSharingOrderSucceeded = (id: number, data?: { wechat_response?: Record<string, any> }): Promise<WechatProfitSharingOrder> =>
  request.post(`/wechat-profit-sharing-orders/${id}/mark_succeeded/`, data || {});
export const markWechatProfitSharingOrderFailed = (id: number, data?: { error_message?: string }): Promise<WechatProfitSharingOrder> =>
  request.post(`/wechat-profit-sharing-orders/${id}/mark_failed/`, data || {});

// 统计分析
export const getRegionalSales = (params?: any) => request.get('/analytics/regional_sales/', { params });
export const getProductRegionDistribution = (params?: any) => request.get('/analytics/product_region_distribution/', { params });
export const getRegionProductStats = (params?: any) => request.get('/analytics/region_product_stats/', { params });
export const exportRegionalSales = (params?: any) => request.get('/analytics/export_regional_sales/', { params, responseType: 'blob' });
export const exportProductRegionDistribution = (params?: any) => request.get('/analytics/export_product_region_distribution/', { params, responseType: 'blob' });
export const exportRegionProductStats = (params?: any) => request.get('/analytics/export_region_product_stats/', { params, responseType: 'blob' });

// 发票管理
export const getInvoices = (params?: any) => request.get('/invoices/', { params });
export const exportInvoices = (params?: any) => request.get('/invoices/export/', { params, responseType: 'blob' });
export const getInvoice = (id: number) => request.get(`/invoices/${id}/`);
export const uploadInvoice = (id: number, file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  return request.post(`/invoices/${id}/upload_file/`, formData);
};
export const downloadInvoice = (id: number) => request.get(`/invoices/${id}/download/`, { responseType: 'blob' });

export const issueInvoice = (id: number, data: any) => request.post(`/invoices/${id}/issue/`, data);
export const cancelInvoice = (id: number) => request.post(`/invoices/${id}/cancel/`);

// 轮播图管理
export const getHomeBanners = (params?: any) => request.get('/catalog/home-banners/', { params });
export const createHomeBanner = (data: any) =>
  request.post('/catalog/home-banners/', withSelectedStoreId(data), { params: data?.store_id ? { store: data.store_id } : undefined });
export const updateHomeBanner = (id: number, data: any) => request.patch(`/catalog/home-banners/${id}/`, data);
export const deleteHomeBanner = (id: number) => request.delete(`/catalog/home-banners/${id}/`);
export const uploadHomeBanner = (file: File, data?: any) => {
  const formData = new FormData();
  formData.append('file', file);
  if (data) {
    Object.keys(data).forEach(key => {
      formData.append(key, data[key]);
    });
  }
  return request.post('/catalog/home-banners/upload/', formData);
};

// 首页专区图片管理
export const getSpecialZoneCovers = (params?: any) => request.get('/catalog/special-zone-covers/', { params });
export const createSpecialZoneCover = (data: any) => request.post('/catalog/special-zone-covers/', withSelectedStoreId(data));
export const updateSpecialZoneCover = (id: number, data: any) => request.patch(`/catalog/special-zone-covers/${id}/`, data);
export const deleteSpecialZoneCover = (id: number) => request.delete(`/catalog/special-zone-covers/${id}/`);

// 动态运营专区管理
export const getSpecialZones = (params?: any) => request.get('/catalog/special-zones/', { params });
export const createSpecialZone = (data: any) =>
  request.post('/catalog/special-zones/', withSelectedStoreId(data), { params: data?.store_id ? { store: data.store_id } : undefined });
export const updateSpecialZone = (id: number, data: any) => request.patch(`/catalog/special-zones/${id}/`, data);
export const deleteSpecialZone = (id: number) => request.delete(`/catalog/special-zones/${id}/`);
export const getSpecialZoneProducts = (zoneId: number, params?: any) =>
  request.get(`/catalog/special-zones/${zoneId}/products/`, { params });
export const bindSpecialZoneProduct = (zoneId: number, data: any) =>
  request.post(`/catalog/special-zones/${zoneId}/products/`, data);
export const updateSpecialZoneProduct = (zoneId: number, productId: number, data: any) =>
  request.post(`/catalog/special-zones/${zoneId}/products/`, { product_id: productId, ...data });
export const removeSpecialZoneProduct = (zoneId: number, productId: number) =>
  request.delete(`/catalog/special-zones/${zoneId}/products/`, { data: { product_id: productId } });

export const getHomeStoreCards = (params?: any) => request.get('/catalog/home-store-cards/', { params });
export const createHomeStoreCard = (data: any) => request.post('/catalog/home-store-cards/', data);
export const updateHomeStoreCard = (id: number, data: any) => request.patch(`/catalog/home-store-cards/${id}/`, data);
export const deleteHomeStoreCard = (id: number) => request.delete(`/catalog/home-store-cards/${id}/`);

// 案例管理
export const getCases = (params?: any) => request.get('/catalog/cases/', { params });
export const getCase = (id: number) => request.get(`/catalog/cases/${id}/`);
export const createCase = (data: any) => request.post('/catalog/cases/', data);
export const updateCase = (id: number, data: any) => request.patch(`/catalog/cases/${id}/`, data);
export const deleteCase = (id: number) => request.delete(`/catalog/cases/${id}/`);

// 客服会话管理
export const getSupportTickets = (params?: any) => request.get('/support/chat/conversations/', { params }); // Alias for getConversations
export const getConversations = (params?: any) => request.get('/support/chat/conversations/', { params });
export const getSupportReplyTemplates = (params?: any) => request.get('/support/reply-templates/', { params });
export const createSupportReplyTemplate = (data: any) => request.post('/support/reply-templates/', data);
export const updateSupportReplyTemplate = (id: number, data: any) => request.patch(`/support/reply-templates/${id}/`, data);
export const deleteSupportReplyTemplate = (id: number) => request.delete(`/support/reply-templates/${id}/`);
export const triggerConversationAutoReply = (conversationId: number) =>
  request.post(`/support/conversations/${conversationId}/auto-reply/`, {});

// 新的聊天接口
export const getChatMessages = (userId: number, params?: any) => request.get('/support/chat/', { params: { user_id: userId, ...params } });
export const sendChatMessage = (
  userId: number,
  content: string,
  attachment?: File,
  attachmentType?: 'image' | 'video',
  extra?: { order_id?: number, product_id?: number, ticket_id?: number, template_id?: number }
) => {
  if (!attachment) {
    return request.post('/support/chat/', { 
      user_id: userId, 
      content,
      order_id: extra?.order_id,
      product_id: extra?.product_id,
      template_id: extra?.template_id,
      conversation_id: extra?.ticket_id // Compatible with ticket_id param
    });
  }
  
  const formData = new FormData();
  formData.append('user_id', userId.toString());
  formData.append('content', content || '');
  formData.append('attachment', attachment);
  if (attachmentType) {
    formData.append('attachment_type', attachmentType);
  }
  if (extra?.order_id) {
    formData.append('order_id', extra.order_id.toString());
  }
  if (extra?.product_id) {
    formData.append('product_id', extra.product_id.toString());
  }
  if (extra?.template_id) {
    formData.append('template_id', String(extra.template_id));
  }
  if (extra?.ticket_id) {
    formData.append('conversation_id', String(extra.ticket_id));
  }
  
  return request.post('/support/chat/', formData);
};

// 问题建议工单
export const getFeedbackTickets = (params?: any) => request.get('/support/feedback-tickets/', { params });
export const getFeedbackTicket = (id: number) => request.get(`/support/feedback-tickets/${id}/`);
export const getFeedbackTicketStats = (params?: any) => request.get('/support/feedback-tickets/stats/', { params });
export const replyFeedbackTicket = (id: number, content: string, images: File[] = []) => {
  const formData = new FormData();
  formData.append('content', content);
  images.forEach(file => formData.append('images', file));
  return request.post(`/support/feedback-tickets/${id}/reply/`, formData);
};
export const closeFeedbackTicket = (id: number, content?: string) =>
  request.post(`/support/feedback-tickets/${id}/close/`, { content: content || '' });
