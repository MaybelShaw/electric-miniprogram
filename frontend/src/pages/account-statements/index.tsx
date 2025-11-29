import { View, Text, ScrollView } from '@tarojs/components'
import { useEffect, useState } from 'react'
import Taro from '@tarojs/taro'
import { creditService, AccountStatement } from '../../services/credit'
import './index.scss'

export default function AccountStatementsPage() {
  const [statements, setStatements] = useState<AccountStatement[]>([])
  const [loading, setLoading] = useState(true)
  const [hasMore, setHasMore] = useState(true)
  const [page, setPage] = useState(1)

  useEffect(() => {
    loadStatements()
  }, [])

  // 页面显示时重新加载数据
  Taro.useDidShow(() => {
    loadStatements(1)
  })

  const loadStatements = async (pageNum = 1) => {
    try {
      setLoading(true)
      const data = await creditService.getMyStatements({ page: pageNum, page_size: 10 })
      
      if (pageNum === 1) {
        setStatements(data.results)
      } else {
        setStatements([...statements, ...data.results])
      }
      
      setHasMore(data.results.length === 10)
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
      loadStatements(page + 1)
    }
  }

  const formatMoney = (value: string) => {
    return `¥${Number(value).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  }

  const getStatusText = (status: string) => {
    const map = {
      draft: '草稿',
      confirmed: '已确认',
      settled: '已结清'
    }
    return map[status] || status
  }

  const getStatusClass = (status: string) => {
    const map = {
      draft: 'draft',
      confirmed: 'confirmed',
      settled: 'settled'
    }
    return map[status] || 'draft'
  }

  const viewDetail = (id: number) => {
    Taro.navigateTo({ url: `/pages/statement-detail/index?id=${id}` })
  }

  if (loading && page === 1) {
    return (
      <View className='statements-page'>
        <View className='loading'>加载中...</View>
      </View>
    )
  }

  if (statements.length === 0) {
    return (
      <View className='statements-page'>
        <View className='empty'>
          <Text className='empty-text'>暂无对账单</Text>
        </View>
      </View>
    )
  }

  return (
    <View className='statements-page'>
      <ScrollView
        scrollY
        className='statements-list'
        onScrollToLower={loadMore}
      >
        {statements.map(statement => (
          <View
            key={statement.id}
            className='statement-card'
            onTap={() => viewDetail(statement.id)}
          >
            <View className='statement-header'>
              <View className='statement-period'>
                <Text className='period-text'>
                  {statement.period_start} 至 {statement.period_end}
                </Text>
              </View>
              <View className={`statement-status ${getStatusClass(statement.status)}`}>
                {getStatusText(statement.status)}
              </View>
            </View>

            <View className='statement-summary'>
              <View className='summary-row'>
                <View className='summary-item'>
                  <Text className='summary-label'>本期采购</Text>
                  <Text className='summary-value'>{formatMoney(statement.current_purchases)}</Text>
                </View>
                <View className='summary-item'>
                  <Text className='summary-label'>本期付款</Text>
                  <Text className='summary-value paid'>{formatMoney(statement.current_payments)}</Text>
                </View>
              </View>

              <View className='summary-row'>
                <View className='summary-item'>
                  <Text className='summary-label'>期末未付</Text>
                  <Text className='summary-value debt'>{formatMoney(statement.period_end_balance)}</Text>
                </View>
                <View className='summary-item'>
                  <Text className='summary-label'>逾期金额</Text>
                  <Text className='summary-value overdue'>{formatMoney(statement.overdue_amount)}</Text>
                </View>
              </View>
            </View>

            <View className='statement-footer'>
              <Text className='view-detail'>查看详情 ›</Text>
            </View>
          </View>
        ))}

        {loading && page > 1 && (
          <View className='loading-more'>加载中...</View>
        )}

        {!hasMore && statements.length > 0 && (
          <View className='no-more'>没有更多了</View>
        )}
      </ScrollView>
    </View>
  )
}
