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
export const shipOrder = (id: number) => request.patch(`/orders/${id}/ship/`, {});
export const completeOrder = (id: number) => request.patch(`/orders/${id}/complete/`, {});
export const cancelOrder = (id: number) => request.patch(`/orders/${id}/cancel/`, {});
export const pushToHaier = (id: number, data?: any) => request.post(`/orders/${id}/push_to_haier/`, data || {});
export const getHaierLogistics = (id: number) => request.get(`/orders/${id}/haier_logistics/`);

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
