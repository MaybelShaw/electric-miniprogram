import { View, Text, ScrollView } from '@tarojs/components'
import { useEffect, useState } from 'react'
import Taro from '@tarojs/taro'
import { creditService, AccountTransaction } from '../../services/credit'
import AppIcon, { AppIconName } from '../../components/AppIcon'
import './index.scss'

export default function AccountTransactionsPage() {
  const [transactions, setTransactions] = useState<AccountTransaction[]>([])
  const [loading, setLoading] = useState(true)
  const [hasMore, setHasMore] = useState(true)
  const [page, setPage] = useState(1)

  useEffect(() => {
    loadTransactions()
  }, [])

  // 页面显示时重新加载数据
  Taro.useDidShow(() => {
    loadTransactions(1)
  })

  const loadTransactions = async (pageNum = 1) => {
    try {
      setLoading(true)
      const data = await creditService.getMyTransactions({ page: pageNum, page_size: 20 })
      
      if (pageNum === 1) {
        setTransactions(data.results)
      } else {
        setTransactions([...transactions, ...data.results])
      }
      
      setHasMore(data.results.length === 20)
      setPage(pageNum)
    } catch (error: any) {
      Taro.showToast({
        title: error.response?.data?.error || '加载失败',
        icon: 'none'
      })
    } finally {
      setLoading(false)
    }
  }

  const loadMore = () => {
    if (!loading && hasMore) {
      loadTransactions(page + 1)
    }
  }

  const formatMoney = (value: string) => {
    return `¥${Number(value).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  }

  const getPaymentStatusText = (status: string) => {
    const map = {
      unpaid: '未付款',
      paid: '已付款',
      overdue: '已逾期'
    }
    return map[status] || status
  }

  const getPaymentStatusClass = (status: string) => {
    const map = {
      unpaid: 'unpaid',
      paid: 'paid',
      overdue: 'overdue'
    }
    return map[status] || 'unpaid'
  }

  const getTransactionIcon = (type: string): AppIconName => {
    const map: Record<string, AppIconName> = {
      purchase: 'cart',
      payment: 'pay',
      refund: 'refund',
      adjustment: 'credit'
    }
    return map[type] || 'order'
  }

  if (loading && page === 1) {
    return (
      <View className='transactions-page'>
        <View className='loading'>加载中...</View>
      </View>
    )
  }

  if (transactions.length === 0) {
    return (
      <View className='transactions-page'>
        <View className='empty'>
          <Text className='empty-text'>暂无交易记录</Text>
        </View>
      </View>
    )
  }

  return (
    <View className='transactions-page'>
      <ScrollView
        scrollY
        className='transactions-list'
        onScrollToLower={loadMore}
      >
        {transactions.map(transaction => (
          <View key={transaction.id} className='transaction-card'>
            <View className='transaction-main'>
              <View className='transaction-left'>
                <View className='transaction-icon'>
                  <AppIcon name={getTransactionIcon(transaction.transaction_type)} tone='muted' />
                </View>
                <View className='transaction-info'>
                  <Text className='transaction-type'>{transaction.transaction_type_display}</Text>
                  <Text className='transaction-date'>
                    {transaction.created_at.split('T')[0]} {transaction.created_at.split('T')[1]?.substring(0, 5)}
                  </Text>
                  {transaction.order_info && (
                    <Text className='transaction-order'>
                      订单 #{transaction.order_info.order_number}
                    </Text>
                  )}
                </View>
              </View>
              <View className='transaction-right'>
                <Text className='transaction-amount'>{formatMoney(transaction.amount)}</Text>
                {transaction.transaction_type === 'purchase' && (
                  <View className={`payment-status ${getPaymentStatusClass(transaction.payment_status)}`}>
                    {getPaymentStatusText(transaction.payment_status)}
                  </View>
                )}
              </View>
            </View>

            {/* 订单详情 */}
            {transaction.order_info && (
              <View className='order-info'>
                <View className='order-info-row'>
                  <Text className='order-info-label'>商品</Text>
                  <Text className='order-info-value'>{transaction.order_info.product_name}</Text>
                </View>
                <View className='order-info-row'>
                  <Text className='order-info-label'>数量</Text>
                  <Text className='order-info-value'>x{transaction.order_info.quantity}</Text>
                </View>
              </View>
            )}

            {/* 其他详情 */}
            {(transaction.due_date || transaction.paid_date || transaction.description) && (
              <View className='transaction-details'>
                {transaction.due_date && (
                  <View className='detail-row'>
                    <Text className='detail-label'>应付日期</Text>
                    <Text className='detail-value'>{transaction.due_date}</Text>
                  </View>
                )}
                {transaction.paid_date && (
                  <View className='detail-row'>
                    <Text className='detail-label'>实付日期</Text>
                    <Text className='detail-value'>{transaction.paid_date}</Text>
                  </View>
                )}
                {transaction.description && (
                  <View className='detail-row'>
                    <Text className='detail-label'>备注</Text>
                    <Text className='detail-value'>{transaction.description}</Text>
                  </View>
                )}
              </View>
            )}
          </View>
        ))}

        {loading && page > 1 && (
          <View className='loading-more'>加载中...</View>
        )}

        {!hasMore && transactions.length > 0 && (
          <View className='no-more'>没有更多了</View>
        )}
      </ScrollView>
    </View>
  )
}
