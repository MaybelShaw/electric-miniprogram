import Taro from '@tarojs/taro'

export type OpenLogisticsParams = {
  deliveryId: string
  waybillId: string
  receiverPhone?: string
  sourcePath?: string
}

export type OpenLogisticsResult = {
  opened: boolean
  reason?: 'unsupported' | 'missing' | 'fail'
  error?: unknown
}

const resolveReceiverPhone = (phone?: string) => {
  if (!phone) return ''
  const digits = phone.replace(/\D/g, '')
  if (digits.length <= 4) return digits
  return digits.slice(-4)
}

export const openWechatLogistics = async (params: OpenLogisticsParams): Promise<OpenLogisticsResult> => {
  const { deliveryId, waybillId, receiverPhone, sourcePath } = params
  const canOpen = typeof wx !== 'undefined' && typeof (wx as any).openLogistics === 'function'
  if (!canOpen) {
    return { opened: false, reason: 'unsupported' }
  }

  if (!deliveryId || !waybillId) {
    return { opened: false, reason: 'missing' }
  }

  return new Promise((resolve) => {
    ;(wx as any).openLogistics({
      delivery_id: deliveryId,
      waybill_id: waybillId,
      phone: resolveReceiverPhone(receiverPhone),
      path: sourcePath || '',
      success: () => resolve({ opened: true }),
      fail: (error: unknown) => {
        try {
          Taro.showToast({
            title: String((error as any)?.errMsg || (error as any)?.message || '唤起失败'),
            icon: 'none',
            duration: 3000,
          })
        } catch (e) {
          // ignore
        }
        resolve({ opened: false, reason: 'fail', error })
      },
    })
  })
}
