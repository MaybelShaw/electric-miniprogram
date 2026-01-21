import request from '@/utils/request';

// 登录
export const loginAdmin = (data: { username: string; password: string }) =>
  request.post('/admin/login/', data);

export const loginSupport = (data: { username: string; password: string }) =>
  request.post('/password_login/', data);

// 兼容旧调用
export const login = (data: { username: string; password: string }) =>
  request.post('/admin/login/', data);

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
export const createBrand = (data: any) => request.post('/catalog/brands/', data);
export const updateBrand = (id: number, data: any) => request.patch(`/catalog/brands/${id}/`, data);
export const deleteBrand = (id: number, force?: boolean) =>
  request.delete(`/catalog/brands/${id}/`, { params: { force_delete: force } });

// 品类管理
export const getCategories = (params?: any) => request.get('/catalog/categories/', { params });
export const createCategory = (data: any) => request.post('/catalog/categories/', data);
export const updateCategory = (id: number, data: any) => request.patch(`/catalog/categories/${id}/`, data);
export const deleteCategory = (id: number) => request.delete(`/catalog/categories/${id}/`);

// 产品管理
export const getProducts = (params?: any) => request.get('/catalog/products/', { params });
export const getProduct = (id: number) => request.get(`/catalog/products/${id}/`);
export const createProduct = (data: any) => request.post('/catalog/products/', data);
export const updateProduct = (id: number, data: any) => request.patch(`/catalog/products/${id}/`, data);
export const deleteProduct = (id: number) => request.delete(`/catalog/products/${id}/`);
export const exportProducts = (params?: any) => request.get('/catalog/products/export/', { params, responseType: 'blob' });
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

// 订单管理
export const getOrders = (params?: any) => request.get('/orders/', { params });
export const exportOrders = (params?: any) => request.get('/orders/export/', { params, responseType: 'blob' });
export const getOrder = (id: number) => request.get(`/orders/${id}/`);
export const shipOrder = (id: number, data?: any) => request.patch(`/orders/${id}/ship/`, data || {});
export const completeOrder = (id: number) => request.patch(`/orders/${id}/complete/`, {});
export const cancelOrder = (id: number, data?: any) => request.patch(`/orders/${id}/cancel/`, data || {});
export const adjustOrderAmount = (id: number, data: { actual_amount: number }) =>
  request.post(`/orders/${id}/adjust_amount/`, data);
export const pushToHaier = (id: number, data?: any) => request.post(`/orders/${id}/push_to_haier/`, data || {});
export const getHaierLogistics = (id: number) => request.get(`/orders/${id}/haier_logistics/`);
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
export const createHomeBanner = (data: any) => request.post('/catalog/home-banners/', data);
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
export const createSpecialZoneCover = (data: any) => request.post('/catalog/special-zone-covers/', data);
export const updateSpecialZoneCover = (id: number, data: any) => request.patch(`/catalog/special-zone-covers/${id}/`, data);
export const deleteSpecialZoneCover = (id: number) => request.delete(`/catalog/special-zone-covers/${id}/`);

// 案例管理
export const getCases = (params?: any) => request.get('/catalog/cases/', { params });
export const getCase = (id: number) => request.get(`/catalog/cases/${id}/`);
export const createCase = (data: any) => request.post('/catalog/cases/', data);
export const updateCase = (id: number, data: any) => request.patch(`/catalog/cases/${id}/`, data);
export const deleteCase = (id: number) => request.delete(`/catalog/cases/${id}/`);

// 客服会话管理
export const getSupportTickets = (params?: any) => request.get('/support/chat/conversations/', { params }); // Alias for getConversations
export const getConversations = (params?: any) => request.get('/support/chat/conversations/', { params });

// 新的聊天接口
export const getChatMessages = (userId: number, params?: any) => request.get('/support/chat/', { params: { user_id: userId, ...params } });
export const sendChatMessage = (userId: number, content: string, attachment?: File, attachmentType?: 'image' | 'video', extra?: { order_id?: number, product_id?: number, ticket_id?: number }) => {
  if (!attachment) {
    return request.post('/support/chat/', { 
      user_id: userId, 
      content,
      order_id: extra?.order_id,
      product_id: extra?.product_id,
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
  if (extra?.ticket_id) {
    formData.append('conversation_id', String(extra.ticket_id));
  }
  
  return request.post('/support/chat/', formData);
};
