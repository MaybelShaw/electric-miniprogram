// 格式化价格
export function formatPrice(price: string | number): string {
  const num = typeof price === 'string' ? parseFloat(price) : price
  return `¥${num.toFixed(2)}`
}

// 格式化数量
export function formatNumber(num: number): string {
  if (num >= 10000) {
    return `${(num / 10000).toFixed(1)}万`
  }
  return num.toString()
}

// 格式化销量
export function formatSalesCount(count: number): string {
  if (count <= 100) {
    return count.toString()
  }
  if (count < 10000) {
    const hundreds = Math.floor(count / 100) * 100
    return `${hundreds}+`
  }
  const tenThousands = Math.floor(count / 10000)
  return `${tenThousands}万+`
}

// 格式化时间
export function formatTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  
  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour
  
  if (diff < minute) {
    return '刚刚'
  } else if (diff < hour) {
    return `${Math.floor(diff / minute)}分钟前`
  } else if (diff < day) {
    return `${Math.floor(diff / hour)}小时前`
  } else if (diff < 7 * day) {
    return `${Math.floor(diff / day)}天前`
  } else {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const dayNum = String(date.getDate()).padStart(2, '0')
    return `${year}-${month}-${dayNum}`
  }
}

// 订单状态文本
export function getOrderStatusText(status: string): string {
  const statusMap: Record<string, string> = {
    pending: '待支付',
    paid: '待发货',
    shipped: '待收货',
    completed: '已完成',
    cancelled: '已取消',
    returning: '退货中',
    refunding: '退款中',
    refunded: '已退款'
  }
  return statusMap[status] || status
}
