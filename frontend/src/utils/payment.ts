export const resolvePaymentErrorMessage = (error: unknown, fallback = '支付未完成') => {
  const raw = typeof error === 'string'
    ? error
    : (error as any)?.errMsg || (error as any)?.message || ''
  const message = String(raw || '').trim()
  if (!message) return fallback

  const lower = message.toLowerCase()
  const isDebug = lower.includes('requestpayment') || lower.includes('err') || lower.includes('error') || lower.includes('fail')

  if (isDebug || message.includes('取消') || message.includes('超时') || message.includes('失败')) {
    if (lower.includes('cancel') || message.includes('取消')) return '支付已取消'
    if (lower.includes('timeout') || message.includes('超时')) return '支付超时，请重试'
    return '支付失败，请重试'
  }

  return message
}
