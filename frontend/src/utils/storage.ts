import Taro from '@tarojs/taro'

// 缓存管理工具
export const Storage = {
  // 设置缓存
  set(key: string, data: any, expire?: number) {
    const value = {
      data,
      expire: expire ? Date.now() + expire : null
    }
    Taro.setStorageSync(key, value)
  },
  
  // 获取缓存
  get<T = any>(key: string): T | null {
    const value = Taro.getStorageSync(key)
    if (!value) return null
    
    // 检查是否过期
    if (value.expire && Date.now() > value.expire) {
      Taro.removeStorageSync(key)
      return null
    }
    
    return value.data as T
  },
  
  // 删除缓存
  remove(key: string) {
    Taro.removeStorageSync(key)
  },
  
  // 清空缓存
  clear() {
    Taro.clearStorageSync()
  }
}

// 缓存键常量
export const CACHE_KEYS = {
  CATEGORIES: 'cache_categories',
  BRANDS: 'cache_brands',
  USER_INFO: 'cache_user_info'
}
