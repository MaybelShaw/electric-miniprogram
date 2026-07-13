import Taro from '@tarojs/taro'

const DEFAULT_API_BASE_URL = 'https://www.qxelectric.cn/api'
const REQUEST_TIMEOUT = 30000

export const BASE_URL = process.env.TARO_APP_API_BASE_URL || DEFAULT_API_BASE_URL

let activeLoadingCount = 0

function showRequestLoading() {
  if (activeLoadingCount === 0) {
    Taro.showLoading({ title: '加载中...', mask: true })
  }
  activeLoadingCount += 1
}

function hideRequestLoading() {
  if (activeLoadingCount === 0) return
  activeLoadingCount -= 1
  if (activeLoadingCount === 0) {
    Taro.hideLoading()
  }
}

interface RequestOptions {
  url: string
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  data?: any
  needAuth?: boolean
  showError?: boolean
  showLoading?: boolean
}

type HttpOptions = boolean | { needAuth?: boolean, showError?: boolean, showLoading?: boolean }

function parseHttpOptions(options: HttpOptions) {
  if (typeof options === 'boolean') {
    return { needAuth: options, showError: true, showLoading: true }
  }

  return {
    needAuth: options.needAuth ?? true,
    showError: options.showError ?? true,
    showLoading: options.showLoading ?? true,
  }
}

interface ApiResponse<T = any> {
  data?: T
  error?: string
  message?: string
  detail?: string
  details?: any
}

function stringifyApiError(value: any): string {
  if (!value) return ''
  if (typeof value === 'string') return value
  if (Array.isArray(value)) {
    return value.map(stringifyApiError).filter(Boolean).join('；')
  }
  if (typeof value === 'object') {
    return Object.values(value).map(stringifyApiError).filter(Boolean).join('；')
  }
  return String(value)
}

function getApiErrorMessage(errorData: ApiResponse): string {
  return (
    stringifyApiError(errorData.message) ||
    stringifyApiError(errorData.error) ||
    stringifyApiError(errorData.detail) ||
    stringifyApiError(errorData.details) ||
    '请求失败'
  )
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
        data: { refresh: refreshToken },
        timeout: REQUEST_TIMEOUT,
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
  const { url, method = 'GET', data, needAuth = true, showError = true, showLoading = true } = options
  let loadingShown = false

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
    if (showLoading) {
      showRequestLoading()
      loadingShown = true
    }
    
    const fullUrl = `${BASE_URL}${url}`
    
    const res = await Taro.request({
      url: fullUrl,
      method,
      data,
      header,
      dataType: 'json',  // Explicitly set dataType
      timeout: REQUEST_TIMEOUT,
    })

    hideRequestLoading()
    loadingShown = false

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
      const errorMsg = getApiErrorMessage(errorData)
      
      if (showError) {
        // 429 限流错误
        if (res.statusCode === 429) {
          Taro.showToast({ title: '请求过于频繁，请稍后再试', icon: 'none', duration: 2000 })
        } else {
          Taro.showToast({ title: errorMsg, icon: 'none', duration: 2000 })
        }
      }
      
      const error = new Error(errorMsg)
      ;(error as any).statusCode = res.statusCode
      ;(error as any).data = errorData
      // 标记为已处理的API错误
      ;(error as any).isApiError = true
      throw error
    }
    
    return res.data as T
  } catch (error: any) {
    if (loadingShown) {
      hideRequestLoading()
      loadingShown = false
    }

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
  get: <T = any>(url: string, params?: any, options: HttpOptions = true) => {
    const { needAuth, showError, showLoading } = parseHttpOptions(options)

    // GET 请求需要将参数转换为查询字符串
    let fullUrl = url
    if (params && Object.keys(params).length > 0) {
      const queryString = Object.entries(params)
        .filter(([_, value]) => value !== undefined && value !== null)
        .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`)
        .join('&')
      fullUrl = `${url}${url.includes('?') ? '&' : '?'}${queryString}`
    }
    return request<T>({ url: fullUrl, method: 'GET', needAuth, showError, showLoading })
  },

  post: <T = any>(url: string, data?: any, options: HttpOptions = true) => {
    const { needAuth, showError, showLoading } = parseHttpOptions(options)
    return request<T>({ url, method: 'POST', data, needAuth, showError, showLoading })
  },

  put: <T = any>(url: string, data?: any, options: HttpOptions = true) => {
    const { needAuth, showError, showLoading } = parseHttpOptions(options)
    return request<T>({ url, method: 'PUT', data, needAuth, showError, showLoading })
  },

  patch: <T = any>(url: string, data?: any, options: HttpOptions = true) => {
    const { needAuth, showError, showLoading } = parseHttpOptions(options)
    return request<T>({ url, method: 'PATCH', data, needAuth, showError, showLoading })
  },

  delete: <T = any>(url: string, data?: any, options: HttpOptions = true) => {
    const { needAuth, showError, showLoading } = parseHttpOptions(options)
    return request<T>({ url, method: 'DELETE', data, needAuth, showError, showLoading })
  }
}

export async function fetchAllPaginated<T>(
  url: string,
  params?: Record<string, any>,
  pageSize = 100,
  options: HttpOptions = false,
): Promise<T[]> {
  const first: any = await http.get<any>(url, { ...(params || {}), page: 1, page_size: pageSize }, options)
  if (Array.isArray(first)) return first as T[]

  const items: T[] = Array.isArray(first?.results) ? (first.results as T[]) : []
  const totalPages = Number(first?.total_pages)
  const hasNextFromFirst = typeof first?.has_next === 'boolean' ? first.has_next : Boolean(first?.next)
  if (!hasNextFromFirst && (!Number.isFinite(totalPages) || totalPages <= 1)) return items

  const out: T[] = [...items]
  const maxPages = Number.isFinite(totalPages) && totalPages > 0 ? Math.min(totalPages, 200) : 200
  for (let page = 2; page <= maxPages; page += 1) {
    const res: any = await http.get<any>(url, { ...(params || {}), page, page_size: pageSize }, options)
    if (Array.isArray(res)) {
      out.push(...(res as T[]))
      break
    }
    const pageItems: T[] = Array.isArray(res?.results) ? (res.results as T[]) : []
    out.push(...pageItems)
    const hasNext = typeof res?.has_next === 'boolean' ? res.has_next : Boolean(res?.next)
    const pageTotalPages = Number(res?.total_pages)
    if (!hasNext && (!Number.isFinite(pageTotalPages) || page >= pageTotalPages)) break
  }
  return out
}
