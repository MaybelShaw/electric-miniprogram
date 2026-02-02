import Taro from '@tarojs/taro'
import type { Payment } from '../types'

export const getWechatConfirmReceiptAppId = () =>
  process.env.TARO_APP_WECHAT_CONFIRM_RECEIPT_APPID || ''
export const CONFIRM_RECEIPT_PENDING_KEY = 'wechat_confirm_receipt_pending'
export const CONFIRM_RECEIPT_DEBUG_KEY = 'wechat_confirm_receipt_debug'

export type PendingConfirmReceipt = {
  orderId: number
  orderNumber?: string
  transactionId?: string
  merchantId?: string
  createdAt: number
}

export type OpenConfirmResult = {
  opened: boolean
  reason?: 'unsupported' | 'missing' | 'fail'
  error?: unknown
}

export const resolveTransactionIdFromPayment = (payment?: Payment | null): string | null => {
  if (!payment) return null
  const direct = (payment as any)?.transaction_id || (payment as any)?.transactionId
  if (direct) return String(direct)
  const logs = (payment as any)?.logs
  if (!Array.isArray(logs)) return null
  for (const entry of logs) {
    if (entry && typeof entry === 'object' && (entry as any).transaction_id) {
      return String((entry as any).transaction_id)
    }
  }
  return null
}

export const getPendingConfirmReceipt = (): PendingConfirmReceipt | null => {
  try {
    return Taro.getStorageSync(CONFIRM_RECEIPT_PENDING_KEY) || null
  } catch (error) {
    return null
  }
}

export const savePendingConfirmReceipt = (data: PendingConfirmReceipt) => {
  try {
    Taro.setStorageSync(CONFIRM_RECEIPT_PENDING_KEY, data)
  } catch (error) {
    // ignore storage errors
  }
}

export const clearPendingConfirmReceipt = () => {
  try {
    Taro.removeStorageSync(CONFIRM_RECEIPT_PENDING_KEY)
  } catch (error) {
    // ignore storage errors
  }
}

export const openWechatConfirmReceipt = async (params: {
  orderId: number
  orderNumber?: string
  transactionId?: string | null
  merchantId?: string
}): Promise<OpenConfirmResult> => {
  const { orderId, orderNumber, transactionId, merchantId } = params

  const canOpen = typeof wx !== 'undefined' && typeof (wx as any).openBusinessView === 'function'
  if (!canOpen) {
    return { opened: false, reason: 'unsupported' }
  }

  const hasTransactionId = Boolean(transactionId)
  const hasMerchantInfo = Boolean(merchantId && orderNumber)
  if (!hasTransactionId && !hasMerchantInfo) {
    return { opened: false, reason: 'missing' }
  }

  savePendingConfirmReceipt({
    orderId,
    orderNumber,
    transactionId: transactionId || undefined,
    merchantId,
    createdAt: Date.now(),
  })

  return new Promise((resolve) => {
    ;(wx as any).openBusinessView({
      businessType: 'weappOrderConfirm',
      extraData: hasTransactionId
        ? { transaction_id: transactionId }
        : { merchant_id: merchantId, merchant_trade_no: orderNumber },
      success: () => resolve({ opened: true }),
      fail: (error: unknown) => {
        try {
          Taro.setStorageSync(CONFIRM_RECEIPT_DEBUG_KEY, {
            at: Date.now(),
            orderId,
            orderNumber,
            transactionId,
            merchantId,
            error,
          })
          Taro.showToast({
            title: String((error as any)?.errMsg || (error as any)?.message || '唤起失败'),
            icon: 'none',
            duration: 3000,
          })
        } catch (e) {
          // ignore
        }
        clearPendingConfirmReceipt()
        resolve({ opened: false, reason: 'fail', error })
      },
    })
  })
}
