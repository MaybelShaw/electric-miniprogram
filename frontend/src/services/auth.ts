import Taro from '@tarojs/taro'
import { http } from '../utils/request'
import { LoginResponse, User } from '../types'

export const authService = {
  // 显式微信登录：首次登录必须携带手机号授权 code
  async login(phoneCode?: string): Promise<LoginResponse> {
    const { code } = await Taro.login()
    return http.post<LoginResponse>(
      '/wechat/explicit-login/',
      {
        code,
        ...(phoneCode ? { phone_code: phoneCode } : {})
      },
      false
    )
  },

  async loginWithPhone(phoneCode: string): Promise<LoginResponse> {
    return this.login(phoneCode)
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
