import request from '@/utils/request';

// 登录
export const login = (data: { username: string; password: string }) =>
  request.post('/admin/login/', data);

// 用户管理
export const getUsers = (params?: any) => request.get('/users/', { params });
export const getUser = (id: number) => request.get(`/users/${id}/`);
export const createUser = (data: any) => request.post('/users/', data);
export const updateUser = (id: number, data: any) => request.patch(`/users/${id}/`, data);
export const deleteUser = (id: number) => request.delete(`/users/${id}/`);
export const setAdmin = (id: number) => request.post(`/users/${id}/set_admin/`);
export const unsetAdmin = (id: number) => request.post(`/users/${id}/unset_admin/`);
export const getUserTransactionStats = (id: number, params?: any) => request.get(`/users/${id}/transaction_stats/`, { params });
export const exportUserTransactionStats = (id: number, params?: any) => request.get(`/users/${id}/export_transaction_stats/`, { params, responseType: 'blob' });
export const getCustomersTransactionStats = (params?: any) => request.get(`/users/customers_transaction_stats/`, { params });
export const exportCustomersTransactionStats = (params?: any) => request.get(`/users/export_customers_transaction_stats/`, { params, responseType: 'blob' });

// 品牌管理
export const getBrands = (params?: any) => request.get('/brands/', { params });
export const createBrand = (data: any) => request.post('/brands/', data);
export const updateBrand = (id: number, data: any) => request.patch(`/brands/${id}/`, data);
export const deleteBrand = (id: number, force?: boolean) =>
  request.delete(`/brands/${id}/`, { params: { force_delete: force } });

// 品类管理
export const getCategories = (params?: any) => request.get('/categories/', { params });
export const createCategory = (data: any) => request.post('/categories/', data);
export const updateCategory = (id: number, data: any) => request.patch(`/categories/${id}/`, data);
export const deleteCategory = (id: number) => request.delete(`/categories/${id}/`);

// 产品管理
export const getProducts = (params?: any) => request.get('/products/', { params });
export const getProduct = (id: number) => request.get(`/products/${id}/`);
export const createProduct = (data: any) => request.post('/products/', data);
export const updateProduct = (id: number, data: any) => request.patch(`/products/${id}/`, data);
export const deleteProduct = (id: number) => request.delete(`/products/${id}/`);
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
  
  return request.post('/media-images/', formData);
};

// 订单管理
export const getOrders = (params?: any) => request.get('/orders/', { params });
export const getOrder = (id: number) => request.get(`/orders/${id}/`);
export const shipOrder = (id: number, data?: any) => request.patch(`/orders/${id}/ship/`, data || {});
export const completeOrder = (id: number) => request.patch(`/orders/${id}/complete/`, {});
export const cancelOrder = (id: number, data?: any) => request.patch(`/orders/${id}/cancel/`, data || {});
export const pushToHaier = (id: number, data?: any) => request.post(`/orders/${id}/push_to_haier/`, data || {});
export const getHaierLogistics = (id: number) => request.get(`/orders/${id}/haier_logistics/`);
export const receiveReturn = (id: number, data?: any) => request.patch(`/orders/${id}/receive_return/`, data || {});
export const completeRefund = (id: number) => request.patch(`/orders/${id}/complete_refund/`, {});
export const approveReturn = (id: number, data?: any) => request.patch(`/orders/${id}/approve_return/`, data || {});
export const rejectReturn = (id: number, data?: any) => request.patch(`/orders/${id}/reject_return/`, data || {});

// 折扣管理
export const getDiscounts = (params?: any) => request.get('/discounts/', { params });
export const createDiscount = (data: any) => request.post('/discounts/', data);
export const updateDiscount = (id: number, data: any) => request.patch(`/discounts/${id}/`, data);
export const deleteDiscount = (id: number) => request.delete(`/discounts/${id}/`);

// 公司认证管理
export const getCompanyInfoList = (params?: any) => request.get('/company-info/', { params });
export const getCompanyInfo = (id: number) => request.get(`/company-info/${id}/`);
export const approveCompanyInfo = (id: number) => request.post(`/company-info/${id}/approve/`);
export const rejectCompanyInfo = (id: number) => request.post(`/company-info/${id}/reject/`);

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

// 交易记录管理
export const getAccountTransactions = (params?: any) => request.get('/account-transactions/', { params });

// 统计分析
export const getRegionalSales = (params?: any) => request.get('/analytics/regional_sales/', { params });
export const getProductRegionDistribution = (params?: any) => request.get('/analytics/product_region_distribution/', { params });
export const getRegionProductStats = (params?: any) => request.get('/analytics/region_product_stats/', { params });

// 发票管理
export const getInvoices = (params?: any) => request.get('/invoices/', { params });
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
export const getHomeBanners = (params?: any) => request.get('/home-banners/', { params });
export const createHomeBanner = (data: any) => request.post('/home-banners/', data);
export const updateHomeBanner = (id: number, data: any) => request.patch(`/home-banners/${id}/`, data);
export const deleteHomeBanner = (id: number) => request.delete(`/home-banners/${id}/`);
export const uploadHomeBanner = (file: File, data?: any) => {
  const formData = new FormData();
  formData.append('file', file);
  if (data) {
    Object.keys(data).forEach(key => {
      formData.append(key, data[key]);
    });
  }
  return request.post('/home-banners/upload/', formData);
};
