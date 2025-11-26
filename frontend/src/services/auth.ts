import Taro from '@tarojs/taro'
import { http } from '../utils/request'
import { LoginResponse, User } from '../types'

export const authService = {
  // 微信登录
  async login(): Promise<LoginResponse> {
    const { code } = await Taro.login()
    return http.post<LoginResponse>('/login/', { code }, false)
  },
  
  // 获取用户信息
  async getUserProfile(): Promise<User> {
    return http.get<User>('/user/profile/')
  },
  
  // 更新用户信息
  async updateUserProfile(data: Partial<User>): Promise<User> {
    return http.patch<User>('/user/profile/', data)
  }
}
