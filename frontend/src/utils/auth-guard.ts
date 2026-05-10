import Taro from '@tarojs/taro'
import { TokenManager } from './request'

export type TransactionAction = 'buy' | 'cart'

interface PendingAuthAction {
  redirect: string
  action: TransactionAction
}

const PENDING_AUTH_ACTION_KEY = 'pending_auth_action'
const PROFILE_PAGE_URL = '/pages/profile/index'

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

function appendResumeAction(url: string, action: TransactionAction): string {
  const connector = url.includes('?') ? '&' : '?'
  return `${url}${connector}auth_action=${encodeURIComponent(action)}`
}

export function savePendingAuthAction(action: TransactionAction, redirect = getCurrentPageFullPath()) {
  const pending: PendingAuthAction = { redirect, action }
  Taro.setStorageSync(PENDING_AUTH_ACTION_KEY, pending)
}

export function consumePendingAuthAction(): PendingAuthAction | null {
  const pending = Taro.getStorageSync(PENDING_AUTH_ACTION_KEY) as PendingAuthAction | ''
  Taro.removeStorageSync(PENDING_AUTH_ACTION_KEY)
  if (!pending || !pending.redirect || !pending.action) return null
  return pending
}

export async function resumePendingAuthAction(): Promise<boolean> {
  const pending = consumePendingAuthAction()
  if (!pending) return false

  await Taro.navigateTo({
    url: appendResumeAction(pending.redirect, pending.action)
  })
  return true
}

export async function requireTransactionAuth(action: TransactionAction, redirect?: string): Promise<boolean> {
  if (TokenManager.getAccessToken()) {
    return true
  }

  savePendingAuthAction(action, redirect)
  await Taro.switchTab({ url: PROFILE_PAGE_URL })
  return false
}
