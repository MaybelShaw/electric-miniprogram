import { View, Text, ScrollView, Button } from '@tarojs/components'
import { useEffect, useState } from 'react'
import Taro, { useRouter } from '@tarojs/taro'
import { creditService, AccountStatement } from '../../services/credit'
import './index.scss'

export default function StatementDetailPage() {
  const router = useRouter()
  const [statement, setStatement] = useState<AccountStatement | null>(null)
  const [loading, setLoading] = useState(true)
  const [confirming, setConfirming] = useState(false)

  useEffect(() => {
    const id = router.params.id
    if (id) {
      loadStatement(Number(id))
    }
  }, [])

  const loadStatement = async (id: number) => {
    try {
      setLoading(true)
      const data = await creditService.getStatementDetail(id)
      setStatement(data)
    } catch (error: any) {
      Taro.showToast({
        title: '加载失败',
        icon: 'none'
      })
    } finally {
      setLoading(false)
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

  const handleConfirm = async () => {
    if (!statement) return

    try {
      const res = await Taro.showModal({
        title: '确认对账单',
        content: '确认对账单无误吗？确认后将无法修改。',
        confirmColor: '#1989FA'
      })

      if (res.confirm) {
        setConfirming(true)
        await creditService.confirmStatement(statement.id)
        Taro.showToast({
          title: '已确认',
          icon: 'success'
        })
        // 重新加载数据
        loadStatement(statement.id)
        // 触发上一页更新
        Taro.eventCenter.trigger('creditAccountUpdated')
      }
    } catch (error: any) {
      Taro.showToast({
        title: error.response?.data?.error || '确认失败',
        icon: 'none'
      })
    } finally {
      setConfirming(false)
    }
  }

  if (loading) {
    return (
      <View className='statement-detail-page'>
        <View className='loading'>加载中...</View>
      </View>
    )
  }

  if (!statement) {
    return (
      <View className='statement-detail-page'>
        <View className='empty'>对账单不存在</View>
      </View>
    )
  }

  return (
    <View className='page-container'>
      <ScrollView scrollY className='statement-detail-page'>
        {/* 基本信息 */}
        <View className='detail-section'>
          <View className='section-header'>
            <Text className='section-title'>基本信息</Text>
            <View className={`status-tag ${getStatusClass(statement.status)}`}>
              {getStatusText(statement.status)}
            </View>
          </View>
          <View className='info-row'>
            <Text className='info-label'>账期</Text>
            <Text className='info-value'>{statement.period_start} 至 {statement.period_end}</Text>
          </View>
          <View className='info-row'>
            <Text className='info-label'>公司名称</Text>
            <Text className='info-value'>{statement.company_name}</Text>
          </View>
        </View>

        {/* 财务汇总 */}
        <View className='detail-section'>
          <View className='section-header'>
            <Text className='section-title'>财务汇总</Text>
          </View>
          
          <View className='summary-grid'>
            <View className='summary-item'>
              <Text className='summary-label'>上期结余</Text>
              <Text className='summary-value'>{formatMoney(statement.previous_balance)}</Text>
            </View>
            <View className='summary-item'>
              <Text className='summary-label'>本期采购</Text>
              <Text className='summary-value'>{formatMoney(statement.current_purchases)}</Text>
            </View>
            <View className='summary-item'>
              <Text className='summary-label'>本期付款</Text>
              <Text className='summary-value paid'>{formatMoney(statement.current_payments)}</Text>
            </View>
            <View className='summary-item'>
              <Text className='summary-label'>本期退款</Text>
              <Text className='summary-value paid'>{formatMoney(statement.current_refunds)}</Text>
            </View>
          </View>

          <View className='summary-highlight'>
            <View className='highlight-item'>
              <Text className='highlight-label'>期末未付</Text>
              <Text className='highlight-value debt'>{formatMoney(statement.period_end_balance)}</Text>
            </View>
          </View>

          <View className='summary-grid'>
            <View className='summary-item'>
              <Text className='summary-label'>账期内应付</Text>
              <Text className='summary-value'>{formatMoney(statement.due_within_term)}</Text>
            </View>
            <View className='summary-item'>
              <Text className='summary-label'>账期内已付</Text>
              <Text className='summary-value paid'>{formatMoney(statement.paid_within_term)}</Text>
            </View>
            <View className='summary-item'>
              <Text className='summary-label'>往来余额（逾期）</Text>
              <Text className='summary-value overdue'>{formatMoney(statement.overdue_amount)}</Text>
            </View>
          </View>
        </View>

        {/* 交易明细 */}
        {statement.transactions && statement.transactions.length > 0 && (
          <View className='detail-section'>
            <View className='section-header'>
              <Text className='section-title'>交易明细</Text>
              <Text className='section-count'>共{statement.transactions.length}笔</Text>
            </View>

            {statement.transactions.map(transaction => (
              <View key={transaction.id} className='transaction-item'>
                <View className='transaction-header'>
                  <Text className='transaction-type'>{transaction.transaction_type_display}</Text>
                  <Text className='transaction-amount'>{formatMoney(transaction.amount)}</Text>
                </View>
                
                <View className='transaction-info'>
                  <View className='info-row'>
                    <Text className='info-label'>日期</Text>
                    <Text className='info-value'>{transaction.created_at.split('T')[0]}</Text>
                  </View>
                  
                  {transaction.order_info ? (
                    <>
                      <View className='info-row'>
                        <Text className='info-label'>订单号</Text>
                        <Text className='info-value'>{transaction.order_info.order_number}</Text>
                      </View>
                      {transaction.order_info.product_name && (
                        <View className='info-row'>
                          <Text className='info-label'>商品</Text>
                          <Text className='info-value'>{transaction.order_info.product_name}</Text>
                        </View>
                      )}
                    </>
                  ) : transaction.order_id ? (
                    <View className='info-row'>
                      <Text className='info-label'>订单ID</Text>
                      <Text className='info-value'>#{transaction.order_id}</Text>
                    </View>
                  ) : null}
                  
                  {transaction.due_date && (
                    <View className='info-row'>
                      <Text className='info-label'>应付日期</Text>
                      <Text className='info-value'>{transaction.due_date}</Text>
                    </View>
                  )}
                  
                  {transaction.paid_date && (
                    <View className='info-row'>
                      <Text className='info-label'>实付日期</Text>
                      <Text className='info-value'>{transaction.paid_date}</Text>
                    </View>
                  )}
                  
                  <View className='info-row'>
                    <Text className='info-label'>付款状态</Text>
                    <View className={`payment-status ${getPaymentStatusClass(transaction.payment_status)}`}>
                      {getPaymentStatusText(transaction.payment_status)}
                    </View>
                  </View>
                  
                  {transaction.description && (
                    <View className='info-row'>
                      <Text className='info-label'>备注</Text>
                      <Text className='info-value'>{transaction.description}</Text>
                    </View>
                  )}
                </View>
              </View>
            ))}
          </View>
        )}
      </ScrollView>

      {statement.status === 'draft' && (
        <View className='bottom-bar'>
          <Button 
            className='confirm-btn' 
            loading={confirming}
            disabled={confirming}
            onTap={handleConfirm}
          >
            确认对账单
          </Button>
        </View>
      )}
    </View>
  )
}
