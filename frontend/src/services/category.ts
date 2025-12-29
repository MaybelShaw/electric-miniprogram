import { fetchAllPaginated, http } from '../utils/request'
import { Category } from '../types'

export const categoryService = {
  // 获取分类列表
  async getCategories(): Promise<Category[]> {
    return fetchAllPaginated<Category>('/catalog/categories/')
  },
  
  // 获取分类详情
  async getCategoryById(id: number): Promise<Category> {
    return http.get<Category>(`/catalog/categories/${id}/`, undefined, false)
  }
}
