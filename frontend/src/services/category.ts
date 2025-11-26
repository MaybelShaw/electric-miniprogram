import { http } from '../utils/request'
import { Category } from '../types'

export const categoryService = {
  // 获取分类列表
  async getCategories(): Promise<Category[]> {
    const response = await http.get<{ count: number; results: Category[] }>('/categories/')
    return response.results
  },
  
  // 获取分类详情
  async getCategoryById(id: number): Promise<Category> {
    return http.get<Category>(`/categories/${id}/`)
  }
}
