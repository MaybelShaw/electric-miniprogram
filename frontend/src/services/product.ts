import { fetchAllPaginated, http } from '../utils/request'
import { Product, ProductListResponse, Category, Brand, HomeBanner } from '../types/index'

export const productService = {
  // 获取轮播图列表
  async getHomeBanners(position?: 'home' | 'gift' | 'designer'): Promise<HomeBanner[]> {
    const params = position ? { position } : undefined
    const response = await http.get<{ count: number; results: HomeBanner[] }>('/catalog/home-banners/', params, false)
    return response.results || []
  },

  // 获取商品列表
  async getProducts(params?: {
    page?: number
    page_size?: number
    sort_by?: 'sales' | 'price_asc' | 'price_desc' | 'created'
    search?: string
  }): Promise<ProductListResponse> {
    return http.get<ProductListResponse>('/catalog/products/', params, false)
  },
  
  // 获取商品详情
  async getProductDetail(id: number): Promise<Product> {
    return http.get<Product>(`/catalog/products/${id}/`, undefined, false)
  },
  
  // 按分类获取商品
  async getProductsByCategory(params: {
    category: string
    sort_by?: 'relevance' | 'sales' | 'price_asc' | 'price_desc'
    page?: number
    page_size?: number
  }): Promise<ProductListResponse> {
    return http.get<ProductListResponse>('/catalog/products/by_category/', params, false)
  },
  
  // 按品牌获取商品
  async getProductsByBrand(params: {
    brand: string
    sort_by?: 'relevance' | 'sales' | 'price_asc' | 'price_desc'
    page?: number
    page_size?: number
  }): Promise<ProductListResponse> {
    return http.get<ProductListResponse>('/catalog/products/by_brand/', params, false)
  },
  
  // 获取分类列表
  async getCategories(params?: { level?: 'major' | 'minor' | 'item'; parent_id?: number }): Promise<Category[]> {
    return fetchAllPaginated<Category>('/catalog/categories/', params)
  },
  
  // 获取品牌列表
  async getBrands(): Promise<Brand[]> {
    return fetchAllPaginated<Brand>('/catalog/brands/')
  },
  

  // 获取推荐商品
  async getRecommendations(params?: {
    type?: 'popular' | 'category' | 'trending'
    limit?: number
    category_id?: number
  }): Promise<Product[]> {
    return http.get<Product[]>('/catalog/products/recommendations/', params, false)
  },
  
  // 获取相关商品
  async getRelatedProducts(id: number, limit = 10): Promise<Product[]> {
    return http.get<Product[]>(`/catalog/products/${id}/related/`, { limit }, false)
  },
  

}
