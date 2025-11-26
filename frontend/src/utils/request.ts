import Taro from '@tarojs/taro'

const BASE_URL = process.env.TARO_APP_API_BASE_URL || 'http://127.0.0.1:8000/api'

interface RequestOptions {
  url: string
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  data?: any
  needAuth?: boolean
}

interface ApiResponse<T = any> {
  data?: T
  error?: string
  message?: string
  details?: any
}

// Token 管理
export const TokenManager = {
  getAccessToken(): string | null {
    return Taro.getStorageSync('access_token')
  },
  
  getRefreshToken(): string | null {
    return Taro.getStorageSync('refresh_token')
  },
  
  setTokens(access: string, refresh: string) {
    Taro.setStorageSync('access_token', access)
    Taro.setStorageSync('refresh_token', refresh)
  },
  
  clearTokens() {
    Taro.removeStorageSync('access_token')
    Taro.removeStorageSync('refresh_token')
  },
  
  async refreshAccessToken(): Promise<boolean> {
    const refreshToken = this.getRefreshToken()
    if (!refreshToken) return false
    
    try {
      const res = await Taro.request({
        url: `${BASE_URL}/token/refresh/`,
        method: 'POST',
        data: { refresh: refreshToken }
      })
      
      if (res.statusCode === 200 && res.data.access) {
        Taro.setStorageSync('access_token', res.data.access)
        return true
      }
      return false
    } catch {
      return false
    }
  }
}

// 统一请求方法
export async function request<T = any>(options: RequestOptions): Promise<T> {
  const { url, method = 'GET', data, needAuth = true } = options
  
  const header: any = {}
  
  // 添加认证 Token
  if (needAuth) {
    const token = TokenManager.getAccessToken()
    if (token) {
      header['Authorization'] = `Bearer ${token}`
    }
  }
  
  // Let Taro automatically set Content-Type for JSON data
  // Don't manually set it as it might cause issues
  
  try {
    Taro.showLoading({ title: '加载中...', mask: true })
    
    const fullUrl = `${BASE_URL}${url}`
    
    const res = await Taro.request({
      url: fullUrl,
      method,
      data,
      header,
      dataType: 'json'  // Explicitly set dataType
    })
    
    Taro.hideLoading()
    
    // 处理 401 错误 - Token 过期
    if (res.statusCode === 401 && needAuth) {
      const refreshed = await TokenManager.refreshAccessToken()
      if (refreshed) {
        // 重试请求
        return request(options)
      } else {
        // 刷新失败，跳转登录
        TokenManager.clearTokens()
        Taro.showToast({ title: '登录已过期', icon: 'none' })
        Taro.navigateTo({ url: '/pages/login/index' })
        throw new Error('UNAUTHORIZED')
      }
    }
    
    // 处理其他错误
    if (res.statusCode >= 400) {
      const errorData = res.data as ApiResponse
      const errorMsg = errorData.message || '请求失败'
      
      // 429 限流错误
      if (res.statusCode === 429) {
        Taro.showToast({ title: '请求过于频繁，请稍后再试', icon: 'none', duration: 2000 })
      } else {
        Taro.showToast({ title: errorMsg, icon: 'none', duration: 2000 })
      }
      
      throw new Error(errorMsg)
    }
    
    return res.data as T
  } catch (error: any) {
    Taro.hideLoading()
    
    if (error.message !== 'UNAUTHORIZED') {
      Taro.showToast({ title: '网络错误，请重试', icon: 'none' })
    }
    
    throw error
  }
}

// 便捷方法
export const http = {
  get: <T = any>(url: string, params?: any, needAuth = true) => {
    // GET 请求需要将参数转换为查询字符串
    let fullUrl = url
    if (params && Object.keys(params).length > 0) {
      const queryString = Object.entries(params)
        .filter(([_, value]) => value !== undefined && value !== null)
        .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`)
        .join('&')
      fullUrl = `${url}${url.includes('?') ? '&' : '?'}${queryString}`
    }
    return request<T>({ url: fullUrl, method: 'GET', needAuth })
  },
  
  post: <T = any>(url: string, data?: any, needAuth = true) =>
    request<T>({ url, method: 'POST', data, needAuth }),
  
  put: <T = any>(url: string, data?: any, needAuth = true) =>
    request<T>({ url, method: 'PUT', data, needAuth }),
  
  patch: <T = any>(url: string, data?: any, needAuth = true) =>
    request<T>({ url, method: 'PATCH', data, needAuth }),
  
  delete: <T = any>(url: string, data?: any, needAuth = true) =>
    request<T>({ url, method: 'DELETE', data, needAuth })
}
