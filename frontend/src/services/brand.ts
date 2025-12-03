import { http } from '../utils/request'
import { Brand } from '../types'

export const brandService = {
  // 获取品牌列表
  async getBrands(): Promise<Brand[]> {
    const response = await http.get<{ count: number; results: Brand[] }>('/catalog/brands/')
    return response.results
  },
  
  // 获取品牌详情
  async getBrandById(id: number): Promise<Brand> {
    return http.get<Brand>(`/catalog/brands/${id}/`)
  }
}
