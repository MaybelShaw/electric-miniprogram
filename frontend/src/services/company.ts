import { http } from '../utils/request'

export const companyService = {
  // 获取公司信息
  async getCompanyInfo() {
    return http.get('/company-info/', {}, true)
  },

  // 创建公司信息
  async createCompanyInfo(data) {
    return http.post('/company-info/', data)
  },

  // 更新公司信息
  async updateCompanyInfo(id: number, data) {
    return http.patch(`/company-info/${id}/`, data)
  }
}
