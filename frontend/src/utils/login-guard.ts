import Taro from '@tarojs/taro'
import { TokenManager } from './request'

export interface RequireLoginOptions {
  intent?: 'buy' | 'cart' | string
  redirect?: string
}

const LOGIN_PAGE_URL = '/pages/login/index'

function buildQueryString(params: Record<string, string | undefined>): string {
  const entries = Object.entries(params).filter(([, value]) => value)
  if (entries.length === 0) return ''

  return entries
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value as string)}`)
    .join('&')
}

export function getCurrentPageFullPath(): string {
  const pages = Taro.getCurrentPages()
  const currentPage = pages[pages.length - 1] as {
    route?: string
    options?: Record<string, string>
  } | undefined

  if (!currentPage || !currentPage.route) {
    return '/pages/home/index'
  }

  const routePath = currentPage.route.startsWith('/') ? currentPage.route : `/${currentPage.route}`
  const queryString = buildQueryString(currentPage.options || {})

  return queryString ? `${routePath}?${queryString}` : routePath
}

function buildLoginUrl(options?: RequireLoginOptions): string {
  const redirect = options?.redirect || getCurrentPageFullPath()
  const queryString = buildQueryString({
    redirect,
    intent: options?.intent
  })

  return queryString ? `${LOGIN_PAGE_URL}?${queryString}` : LOGIN_PAGE_URL
}

export async function requireLogin(options?: RequireLoginOptions): Promise<boolean> {
  if (TokenManager.getAccessToken()) {
    return true
  }

  await Taro.navigateTo({
    url: buildLoginUrl(options)
  })

  return false
}
