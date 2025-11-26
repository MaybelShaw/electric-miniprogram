import { http } from '../utils/request'
import { User } from '../types'

export const userService = {
  // 获取用户资料
  async getProfile(): Promise<User> {
    return http.get<User>('/user/profile/')
  },
  
  // 更新用户资料
  async updateProfile(data: Partial<User>): Promise<User> {
    return http.patch<User>('/user/profile/', data)
  },
  
  // 获取用户统计信息
  async getStatistics(): Promise<{ orders_count: number }> {
    return http.get<{ orders_count: number }>('/user/statistics/')
  }
}
