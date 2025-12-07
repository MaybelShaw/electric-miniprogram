import Taro from '@tarojs/taro'

export const BASE_URL = process.env.TARO_APP_API_BASE_URL || 'http://106.54.224.44:8000/api'

interface RequestOptions {
  url: string
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  data?: any
  needAuth?: boolean
  showError?: boolean
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
  const { url, method = 'GET', data, needAuth = true, showError = true } = options
  
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
        if (showError) {
          Taro.showToast({ title: '登录已过期', icon: 'none' })
        }
        Taro.navigateTo({ url: '/pages/login/index' })
        throw new Error('UNAUTHORIZED')
      }
    }
    
    // 处理其他错误
    if (res.statusCode >= 400) {
      const errorData = res.data as ApiResponse
      const errorMsg = errorData.message || '请求失败'
      
      if (showError) {
        // 429 限流错误
        if (res.statusCode === 429) {
          Taro.showToast({ title: '请求过于频繁，请稍后再试', icon: 'none', duration: 2000 })
        } else {
          Taro.showToast({ title: errorMsg, icon: 'none', duration: 2000 })
        }
      }
      
      const error = new Error(errorMsg)
      // 标记为已处理的API错误
      ;(error as any).isApiError = true
      throw error
    }
    
    return res.data as T
  } catch (error: any) {
    Taro.hideLoading()
    
    if (error.message === 'UNAUTHORIZED') {
      throw error
    }
    
    // 如果是API错误，且已经处理过（showError=true时已弹窗），直接抛出
    if (error.isApiError) {
      throw error
    }
    
    // 网络错误或其他未处理的错误
    if (showError) {
      Taro.showToast({ title: '网络错误，请重试', icon: 'none' })
    }
    
    throw error
  }
}

// 便捷方法
export const http = {
  get: <T = any>(url: string, params?: any, options: boolean | { needAuth?: boolean, showError?: boolean } = true) => {
    // 处理 options 参数
    let needAuth = true
    let showError = true
    
    if (typeof options === 'boolean') {
      needAuth = options
    } else {
      if (options.needAuth !== undefined) needAuth = options.needAuth
      if (options.showError !== undefined) showError = options.showError
    }

    // GET 请求需要将参数转换为查询字符串
    let fullUrl = url
    if (params && Object.keys(params).length > 0) {
      const queryString = Object.entries(params)
        .filter(([_, value]) => value !== undefined && value !== null)
        .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`)
        .join('&')
      fullUrl = `${url}${url.includes('?') ? '&' : '?'}${queryString}`
    }
    return request<T>({ url: fullUrl, method: 'GET', needAuth, showError })
  },
  
  post: <T = any>(url: string, data?: any, options: boolean | { needAuth?: boolean, showError?: boolean } = true) => {
    let needAuth = true
    let showError = true
    if (typeof options === 'boolean') {
      needAuth = options
    } else {
      if (options.needAuth !== undefined) needAuth = options.needAuth
      if (options.showError !== undefined) showError = options.showError
    }
    return request<T>({ url, method: 'POST', data, needAuth, showError })
  },
  
  put: <T = any>(url: string, data?: any, options: boolean | { needAuth?: boolean, showError?: boolean } = true) => {
    let needAuth = true
    let showError = true
    if (typeof options === 'boolean') {
      needAuth = options
    } else {
      if (options.needAuth !== undefined) needAuth = options.needAuth
      if (options.showError !== undefined) showError = options.showError
    }
    return request<T>({ url, method: 'PUT', data, needAuth, showError })
  },
  
  patch: <T = any>(url: string, data?: any, options: boolean | { needAuth?: boolean, showError?: boolean } = true) => {
    let needAuth = true
    let showError = true
    if (typeof options === 'boolean') {
      needAuth = options
    } else {
      if (options.needAuth !== undefined) needAuth = options.needAuth
      if (options.showError !== undefined) showError = options.showError
    }
    return request<T>({ url, method: 'PATCH', data, needAuth, showError })
  },
  
  delete: <T = any>(url: string, data?: any, options: boolean | { needAuth?: boolean, showError?: boolean } = true) => {
    let needAuth = true
    let showError = true
    if (typeof options === 'boolean') {
      needAuth = options
    } else {
      if (options.needAuth !== undefined) needAuth = options.needAuth
      if (options.showError !== undefined) showError = options.showError
    }
    return request<T>({ url, method: 'DELETE', data, needAuth, showError })
  }
}
