import { PropsWithChildren } from 'react'
import Taro, { useLaunch } from '@tarojs/taro'
import { orderService } from './services/order'
import {
  clearPendingConfirmReceipt,
  getPendingConfirmReceipt,
} from './utils/wechat-confirm-receipt'

import './app.scss'

function App({ children }: PropsWithChildren<any>) {
  const checkConfirmReceipt = (options: any) => {
    const referrerInfo = options?.referrerInfo
    if (!referrerInfo || !referrerInfo.extraData) return

    const extraData = referrerInfo.extraData || {}
    const status = extraData.status
    if (!status) return

    const pending = getPendingConfirmReceipt()
    if (!pending) return

    const reqExtra = extraData.req_extradata || {}
    if (pending.transactionId && reqExtra.transaction_id && pending.transactionId !== reqExtra.transaction_id) {
      clearPendingConfirmReceipt()
      return
    }

    // Consume the pending receipt to prevent duplicate processing
    clearPendingConfirmReceipt()

    if (status === 'success') {
      orderService
        .getOrderDetail(pending.orderId)
        .then((order) => {
          if (order.status === 'completed') {
            Taro.showToast({ title: '确认收货成功', icon: 'success' })
            Taro.eventCenter.trigger('orderReceiptConfirmed', { orderId: pending.orderId })
            return
          }
          if (order.status !== 'shipped') {
            Taro.showToast({ title: '当前订单暂不可确认收货', icon: 'none' })
            return
          }
          return orderService.confirmReceipt(pending.orderId)
            .then(() => {
              Taro.showToast({ title: '确认收货成功', icon: 'success' })
              Taro.eventCenter.trigger('orderReceiptConfirmed', { orderId: pending.orderId })
            })
            .catch(() => {
              Taro.showToast({ title: '确认收货失败', icon: 'none' })
            })
        })
        .catch(() => {
          Taro.showToast({ title: '确认收货失败', icon: 'none' })
        })
      return
    }

    if (status === 'cancel') {
      Taro.showToast({ title: '已取消确认收货', icon: 'none' })
      return
    }
    if (status === 'fail') {
      Taro.showToast({ title: extraData.errormsg || '确认收货失败', icon: 'none' })
    }
  }

  useLaunch((options) => {
    // Check on launch (cold start)
    checkConfirmReceipt(options)

    // Register for future shows (hot start)
    Taro.onAppShow((res) => {
      checkConfirmReceipt(res)
    })
  })

  // children 是将要会渲染的页面
  return children
}
  


export default App
