import { http } from '../utils/request'
import { Product, ProductListResponse, Category, Brand, HomeBanner } from '../types/index'

export const productService = {
  // 获取轮播图列表
  async getHomeBanners(): Promise<HomeBanner[]> {
    const response = await http.get<{ count: number; results: HomeBanner[] }>('/home-banners/', undefined, false)
    return response.results || []
  },

  // 获取商品列表
  async getProducts(params?: {
    page?: number
    page_size?: number
    sort_by?: 'sales' | 'price_asc' | 'price_desc' | 'created'
    search?: string
  }): Promise<ProductListResponse> {
    return http.get<ProductListResponse>('/products/', params, false)
  },
  
  // 获取商品详情
  async getProductDetail(id: number): Promise<Product> {
    return http.get<Product>(`/products/${id}/`, undefined, false)
  },
  
  // 按分类获取商品
  async getProductsByCategory(params: {
    category: string
    sort_by?: 'relevance' | 'sales' | 'price_asc' | 'price_desc'
    page?: number
    page_size?: number
  }): Promise<ProductListResponse> {
    return http.get<ProductListResponse>('/products/by_category/', params, false)
  },
  
  // 按品牌获取商品
  async getProductsByBrand(brand: string): Promise<ProductListResponse> {
    return http.get<ProductListResponse>('/products/by_brand/', { brand }, false)
  },
  
  // 获取分类列表
  async getCategories(params?: { level?: 'major' | 'minor' }): Promise<Category[]> {
    const response = await http.get<{ count: number; results: Category[] }>('/categories/', params, false)
    return response.results || []
  },
  
  // 获取品牌列表
  async getBrands(): Promise<Brand[]> {
    const response = await http.get<{ count: number; results: Brand[] }>('/brands/', undefined, false)
    return response.results || []
  },
  

  // 获取推荐商品
  async getRecommendations(params?: {
    type?: 'popular' | 'category' | 'trending'
    limit?: number
    category_id?: number
  }): Promise<Product[]> {
    return http.get<Product[]>('/products/recommendations/', params, false)
  },
  
  // 获取相关商品
  async getRelatedProducts(id: number, limit = 10): Promise<Product[]> {
    return http.get<Product[]>(`/products/${id}/related/`, { limit }, false)
  },
  

}
