import { View, Text, ScrollView, Picker } from '@tarojs/components'
import { useEffect, useState } from 'react'
import Taro from '@tarojs/taro'
import { creditService } from '../../services/credit'
import AppIcon from '../../components/AppIcon'
import EmptyState from '../../components/EmptyState'
import './index.scss'

export default function DebtReconciliation() {
  const [loading, setLoading] = useState(true)
  const [dateRange, setDateRange] = useState({ start: '', end: '' })
  const [selectedPeriod, setSelectedPeriod] = useState(0) // 0:本月, 1:上月, 2:本季度, 3:本年, 4:自定义
  const [previousPeriod, setPreviousPeriod] = useState(0) // 保存上一次的选择
  const [showCustomPicker, setShowCustomPicker] = useState(false)
  const [customStartDate, setCustomStartDate] = useState('')
  const [customEndDate, setCustomEndDate] = useState('')
  const [creditAccount, setCreditAccount] = useState<any>(null)
  const [hasData, setHasData] = useState(false)
  const [statistics, setStatistics] = useState({
    totalStatements: 0,
    dueWithinTerm: 0,
    paidWithinTerm: 0,
    previousBalance: 0,
    periodEndBalance: 0,
    overdueAmount: 0,
    statementDue: 0,
    statementPaid: 0,
    statementRefund: 0
  })

  const periodOptions = ['本月', '上月', '本季度', '本年', '自定义']

  useEffect(() => {
    // 设置默认日期范围为当月
    const now = new Date()
    const year = now.getFullYear()
    const month = String(now.getMonth() + 1).padStart(2, '0')
    const firstDay = `${year}-${month}-01`
    const lastDay = new Date(year, now.getMonth() + 1, 0).getDate()
    const lastDayStr = `${year}-${month}-${String(lastDay).padStart(2, '0')}`
    
    setDateRange({ start: firstDay, end: lastDayStr })
    loadData(firstDay, lastDayStr)
  }, [])

  // 页面显示时重新加载数据
  Taro.useDidShow(() => {
    if (dateRange.start && dateRange.end) {
      loadData(dateRange.start, dateRange.end)
    }
  })

  const loadData = async (startDate: string, endDate: string) => {
    try {
      setLoading(true)
      
      // 并行获取信用账户、对账单和交易记录
      const [accountRes, statementsRes, transactionsRes] = await Promise.all([
        creditService.getMyAccount().catch(() => null),
        creditService.getAllMyStatements({ start_date: startDate, end_date: endDate }),
        creditService.getAllMyTransactions({ start_date: startDate, end_date: endDate })
      ])
      
      setCreditAccount(accountRes)
      
      // 计算统计数据
      const stats = {
        totalStatements: statementsRes.length,
        dueWithinTerm: 0,
        paidWithinTerm: 0,
        previousBalance: 0,
        periodEndBalance: 0,
        overdueAmount: 0,
        statementDue: 0,
        statementPaid: 0,
        statementRefund: 0
      }
      
      const statementIds = new Set<number>()
      
      // 1. 统计对账单数据
      statementsRes.forEach(statement => {
        statementIds.add(statement.id)
        stats.dueWithinTerm += Number(statement.due_within_term)
        stats.paidWithinTerm += Number(statement.paid_within_term)
        
        // 上期结余：取最早的一个
        // 期末未付：累加（或者取最晚的一个？这里逻辑有点复杂，简单累加可能不对）
        // 如果是对账单列表，通常是连续的。
        // 简单的做法：
        // 上期结余 += previous_balance (不对，重复了)
        // 期末未付 += period_end_balance (也不对)
        
        // 正确做法：
        // 既然是统计"期间"，应该看作一个整体。
        // 期间开始的结余 = 最早对账单的 previous_balance
        // 期间结束的结余 = 最晚对账单的 period_end_balance
        // 但是如果有多个不连续的对账单怎么办？
        // 简单累加 overdue_amount, statementDue, statementPaid 是对的（流量）。
        // 存量（Balance）不能累加。
        
        stats.overdueAmount += Number(statement.overdue_amount)
        stats.statementDue += Number(statement.current_purchases)
        stats.statementPaid += Number(statement.current_payments)
        stats.statementRefund += Number(statement.current_refunds)
      })
      
      // 处理存量数据 (Balance)
      if (statementsRes.length > 0) {
        // 假设结果按时间倒序排列 (后端是 order_by('-period_end'))
        const sortedStatements = [...statementsRes].sort((a, b) => 
          new Date(a.period_start).getTime() - new Date(b.period_start).getTime()
        )
        stats.previousBalance = Number(sortedStatements[0].previous_balance)
        stats.periodEndBalance = Number(sortedStatements[sortedStatements.length - 1].period_end_balance)
      }
      
      // 2. 统计未包含在对账单中的交易 (补漏)
      const txs = transactionsRes || []
      let unbilledPurchases = 0
      let unbilledPayments = 0
      
      txs.forEach(tx => {
        // 如果该交易属于某个已获取的对账单，则跳过（避免重复统计）
        if (tx.statement && statementIds.has(tx.statement)) {
          return
        }
        
        const amount = Number(tx.amount)
        if (tx.transaction_type === 'purchase') {
          stats.statementDue += amount
          unbilledPurchases += amount
          if (tx.payment_status === 'unpaid' && tx.due_date) {
            stats.dueWithinTerm += amount
          }
        } else if (tx.transaction_type === 'payment') {
          stats.statementPaid += amount
          stats.paidWithinTerm += amount // 假设所有付款都在账期内（或者需要更复杂的判断）
          unbilledPayments += amount
        } else if (tx.transaction_type === 'refund') {
           stats.statementRefund += amount
           // 退款通常减少应付，这里简单处理
           unbilledPayments += amount
         }
      })
      
      // 更新期末余额：加上未结交易的影响
      stats.periodEndBalance += (unbilledPurchases - unbilledPayments)

      setHasData(stats.totalStatements > 0 || txs.length > 0)
      
      setStatistics(stats)
    } catch (error: any) {
      Taro.showToast({
        title: error.response?.data?.error || '加载失败',
        icon: 'none'
      })
    } finally {
      setLoading(false)
    }
  }

  const exportToExcel = async () => {
    Taro.showToast({
      title: '导出功能开发中',
      icon: 'none'
    })
  }

  const goToStatements = () => {
    Taro.navigateTo({ url: '/pages/account-statements/index' })
  }

  const formatMoney = (value: number) => {
    return value.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
  }

  const handlePeriodChange = (e: any) => {
    const index = Number(e.detail.value)
    
    // 如果选择自定义，先保存当前选择，然后打开弹窗
    if (index === 4) {
      setPreviousPeriod(selectedPeriod)
      setSelectedPeriod(index)
      handleCustomDatePicker()
      return
    }
    
    setSelectedPeriod(index)
    setPreviousPeriod(index)
    
    const now = new Date()
    let start = ''
    let end = ''
    
    switch (index) {
      case 0: // 本月
        start = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`
        end = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate()).padStart(2, '0')}`
        break
      case 1: // 上月
        const lastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1)
        start = `${lastMonth.getFullYear()}-${String(lastMonth.getMonth() + 1).padStart(2, '0')}-01`
        end = `${lastMonth.getFullYear()}-${String(lastMonth.getMonth() + 1).padStart(2, '0')}-${String(new Date(lastMonth.getFullYear(), lastMonth.getMonth() + 1, 0).getDate()).padStart(2, '0')}`
        break
      case 2: // 本季度
        const quarter = Math.floor(now.getMonth() / 3)
        start = `${now.getFullYear()}-${String(quarter * 3 + 1).padStart(2, '0')}-01`
        end = `${now.getFullYear()}-${String((quarter + 1) * 3).padStart(2, '0')}-${String(new Date(now.getFullYear(), (quarter + 1) * 3, 0).getDate()).padStart(2, '0')}`
        break
      case 3: // 本年
        start = `${now.getFullYear()}-01-01`
        end = `${now.getFullYear()}-12-31`
        break
    }
    
    setDateRange({ start, end })
    loadData(start, end)
  }

  const handleCustomDatePicker = () => {
    setCustomStartDate(dateRange.start)
    setCustomEndDate(dateRange.end)
    setShowCustomPicker(true)
  }

  const handleStartDateChange = (e: any) => {
    setCustomStartDate(e.detail.value)
  }

  const handleEndDateChange = (e: any) => {
    setCustomEndDate(e.detail.value)
  }

  const handleCustomDateConfirm = () => {
    // 验证日期范围
    if (!customStartDate || !customEndDate) {
      Taro.showToast({
        title: '请选择完整的日期范围',
        icon: 'none'
      })
      return
    }

    if (new Date(customStartDate) > new Date(customEndDate)) {
      Taro.showToast({
        title: '开始日期不能晚于结束日期',
        icon: 'none'
      })
      return
    }

    // 更新日期范围并加载数据
    setDateRange({ start: customStartDate, end: customEndDate })
    setPreviousPeriod(4) // 保存自定义选择
    setShowCustomPicker(false)
    loadData(customStartDate, customEndDate)
  }

  const handleCustomDateCancel = () => {
    // 恢复到之前的选择
    setSelectedPeriod(previousPeriod)
    setShowCustomPicker(false)
  }

  if (loading) {
    return (
      <View className='debt-reconciliation'>
        <View className='loading'>加载中...</View>
      </View>
    )
  }

  if (!creditAccount) {
    return (
      <View className='debt-reconciliation'>
        <View className='empty'>
          <Text className='empty-text'>您还没有信用账户</Text>
          <Text className='empty-hint'>请联系管理员开通</Text>
        </View>
      </View>
    )
  }

  return (
    <View className='debt-reconciliation'>
      <ScrollView scrollY className='content'>
        {/* 筛选器 */}
        <View className='filter-card'>
          <View className='filter-label'>
            <Text className='filter-label-text'>筛选期间</Text>
          </View>
          <Picker mode='selector' range={periodOptions} value={selectedPeriod} onChange={handlePeriodChange}>
            <View className='filter-selector'>
              <Text className='filter-value'>{periodOptions[selectedPeriod]}</Text>
              <Text className='filter-arrow'>▼</Text>
            </View>
          </Picker>
        </View>

        {/* 日期范围显示 */}
        <View className='date-range-card'>
          <View className='date-range-content'>
            <Text className='date-text'>{dateRange.start}</Text>
            <Text className='date-separator'>至</Text>
            <Text className='date-text'>{dateRange.end}</Text>
          </View>
        </View>

        {/* 往来账务总览 */}
        <View className='overview-card'>
          <View className='overview-header' onTap={goToStatements}>
            <Text className='overview-title'>往来账务</Text>
            <View className='view-link'>
              <Text className='link-text'>查看详情</Text>
              <Text className='arrow-right'>›</Text>
            </View>
          </View>
          
          <View className='overview-main'>
            <View className='main-stat'>
              <Text className='main-label'>往来余额（至今天）</Text>
              <Text className='main-value'>{formatMoney(Number(creditAccount?.outstanding_debt || 0))}</Text>
            </View>
            <View className='sub-info'>
              <Text className='sub-text'>共 {statistics.totalStatements} 张单据</Text>
            </View>
          </View>
        </View>

        {/* 账期统计 */}
        <View className='stats-section'>
          <View className='section-title-bar'>
            <Text className='section-title-text'>账期统计</Text>
          </View>
          <View className='stats-grid'>
            <View className='stat-item'>
              <Text className='stat-label'>账期内应付</Text>
              <Text className='stat-value'>{formatMoney(statistics.dueWithinTerm)}</Text>
            </View>
            <View className='stat-item'>
              <Text className='stat-label'>账期内已付</Text>
              <Text className='stat-value paid'>{formatMoney(statistics.paidWithinTerm)}</Text>
            </View>
          </View>
        </View>

        {/* 期间统计 */}
        <View className='stats-section'>
          <View className='section-title-bar'>
            <Text className='section-title-text'>期间统计</Text>
          </View>
          <View className='stats-grid'>
            <View className='stat-item'>
              <Text className='stat-label'>上期结余</Text>
              <Text className='stat-value'>{formatMoney(statistics.previousBalance)}</Text>
            </View>
            <View className='stat-item'>
              <Text className='stat-label'>期末未付</Text>
              <Text className='stat-value debt'>{formatMoney(statistics.periodEndBalance)}</Text>
            </View>
          </View>
        </View>

        {/* 对账单统计 */}
        <View className='stats-section'>
          <View className='section-title-bar'>
            <Text className='section-title-text'>对账单统计</Text>
          </View>
          <View className='stats-grid'>
            <View className='stat-item'>
              <Text className='stat-label'>对账单应付</Text>
              <Text className='stat-value'>{formatMoney(statistics.statementDue)}</Text>
            </View>
            <View className='stat-item'>
              <Text className='stat-label'>对账单已付</Text>
              <Text className='stat-value paid'>{formatMoney(statistics.statementPaid)}</Text>
            </View>
            <View className='stat-item'>
              <Text className='stat-label'>对账单欠款</Text>
              <Text className='stat-value debt'>{formatMoney(statistics.statementRefund)}</Text>
            </View>
          </View>
        </View>

        {/* 空状态 */}
        {!hasData && (
          <EmptyState
            className='debt-empty'
            title='暂无账务数据'
            description='切换账期后可查看采购、付款和退款统计'
            icon='credit'
          />
        )}

        {/* 底部占位 */}
        <View className='bottom-placeholder' />
      </ScrollView>

      {/* 底部导出按钮 */}
      <View className='footer-bar'>
        <View className='export-btn' onTap={exportToExcel}>
          <AppIcon name='order' tone='primary' className='export-icon' />
          <Text className='export-text'>导出Excel</Text>
        </View>
      </View>

      {/* 自定义日期选择弹窗 */}
      {showCustomPicker && (
        <View className='custom-date-modal'>
          <View className='modal-mask' onTap={handleCustomDateCancel} />
          <View className='modal-content'>
            <View className='modal-header'>
              <Text className='modal-title'>自定义日期范围</Text>
            </View>
            
            <View className='modal-body'>
              <View className='date-picker-row'>
                <Text className='date-picker-label'>开始日期</Text>
                <Picker mode='date' value={customStartDate} onChange={handleStartDateChange}>
                  <View className='date-picker-value'>
                    <Text className='date-value-text'>{customStartDate || '请选择'}</Text>
                    <Text className='date-picker-arrow'>▼</Text>
                  </View>
                </Picker>
              </View>

              <View className='date-picker-row'>
                <Text className='date-picker-label'>结束日期</Text>
                <Picker mode='date' value={customEndDate} onChange={handleEndDateChange}>
                  <View className='date-picker-value'>
                    <Text className='date-value-text'>{customEndDate || '请选择'}</Text>
                    <Text className='date-picker-arrow'>▼</Text>
                  </View>
                </Picker>
              </View>
            </View>

            <View className='modal-footer'>
              <View className='modal-btn cancel' onTap={handleCustomDateCancel}>
                <Text>取消</Text>
              </View>
              <View className='modal-btn confirm' onTap={handleCustomDateConfirm}>
                <Text>确定</Text>
              </View>
            </View>
          </View>
        </View>
      )}
    </View>
  )
}
