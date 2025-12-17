import { http } from '../utils/request'
import { Case, PaginatedResponse } from '../types/index'

export const caseService = {
  // 获取案例列表
  async getCases(params?: {
    page?: number
    page_size?: number
  }): Promise<PaginatedResponse<Case>> {
    return http.get<PaginatedResponse<Case>>('/catalog/cases/', params, false)
  },

  // 获取案例详情
  async getCaseDetail(id: number): Promise<Case> {
    return http.get<Case>(`/catalog/cases/${id}/`, undefined, false)
  }
}
