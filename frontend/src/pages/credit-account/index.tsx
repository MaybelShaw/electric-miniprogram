import { View, Text } from '@tarojs/components'
import { useEffect, useState } from 'react'
import Taro from '@tarojs/taro'
import { creditService, CreditAccount } from '../../services/credit'
import AppIcon from '../../components/AppIcon'
import './index.scss'

export default function CreditAccountPage() {
  const [account, setAccount] = useState<CreditAccount | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadAccount()

    // 监听信用账户更新事件
    const handleCreditAccountUpdated = () => {
      loadAccount()
    }
    Taro.eventCenter.on('creditAccountUpdated', handleCreditAccountUpdated)

    return () => {
      Taro.eventCenter.off('creditAccountUpdated', handleCreditAccountUpdated)
    }
  }, [])

  // 页面显示时重新加载数据
  Taro.useDidShow(() => {
    loadAccount()
  })

  const loadAccount = async () => {
    try {
      setLoading(true)
      const data = await creditService.getMyAccount()
      setAccount(data)
    } catch (error: any) {
      if (error.response?.status === 404) {
        Taro.showToast({
          title: '您还没有信用账户',
          icon: 'none'
        })
      } else {
        Taro.showToast({
          title: '加载失败',
          icon: 'none'
        })
      }
    } finally {
      setLoading(false)
    }
  }

  const formatMoney = (value: string) => {
    return `¥${Number(value).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  }

  const goToStatements = () => {
    Taro.navigateTo({ url: '/pages/account-statements/index' })
  }

  const goToTransactions = () => {
    Taro.navigateTo({ url: '/pages/account-transactions/index' })
  }

  if (loading) {
    return (
      <View className='credit-account-page'>
        <View className='loading'>加载中...</View>
      </View>
    )
  }

  if (!account) {
    return (
      <View className='credit-account-page'>
        <View className='empty'>
          <Text className='empty-text'>您还没有信用账户</Text>
          <Text className='empty-hint'>请联系管理员开通</Text>
        </View>
      </View>
    )
  }

  return (
    <View className='credit-account-page'>
      {/* 账户状态卡片 */}
      <View className='account-card'>
        <View className='account-header'>
          <Text className='account-title'>信用账户</Text>
          <View className={`account-status ${account.is_active ? 'active' : 'inactive'}`}>
            {account.is_active ? '正常' : '已停用'}
          </View>
        </View>

        <View className='account-balance'>
          <View className='balance-item main'>
            <Text className='balance-label'>可用额度</Text>
            <Text className='balance-value available'>{formatMoney(account.available_credit)}</Text>
          </View>
        </View>

        <View className='account-details'>
          <View className='detail-item'>
            <Text className='detail-label'>信用额度</Text>
            <Text className='detail-value'>{formatMoney(account.credit_limit)}</Text>
          </View>
          <View className='detail-item'>
            <Text className='detail-label'>未结清欠款</Text>
            <Text className='detail-value debt'>{formatMoney(account.outstanding_debt)}</Text>
          </View>
          <View className='detail-item'>
            <Text className='detail-label'>账期</Text>
            <Text className='detail-value'>{account.payment_term_days}天</Text>
          </View>
        </View>
      </View>

      {/* 功能菜单 */}
      <View className='menu-list'>
        <View className='menu-item' onTap={goToStatements}>
          <AppIcon name='order' tone='gold' className='menu-icon' />
          <View className='menu-content'>
            <Text className='menu-title'>对账单</Text>
            <Text className='menu-desc'>查看账期对账单</Text>
          </View>
          <Text className='menu-arrow'>›</Text>
        </View>

        <View className='menu-item' onTap={goToTransactions}>
          <AppIcon name='pay' tone='primary' className='menu-icon' />
          <View className='menu-content'>
            <Text className='menu-title'>交易记录</Text>
            <Text className='menu-desc'>查看所有交易明细</Text>
          </View>
          <Text className='menu-arrow'>›</Text>
        </View>

        <View className='menu-item' onTap={() => Taro.navigateTo({ url: '/pages/debt-reconciliation/index' })}>
          <AppIcon name='credit' tone='muted' className='menu-icon' />
          <View className='menu-content'>
            <Text className='menu-title'>欠款对账</Text>
            <Text className='menu-desc'>查看账务统计</Text>
          </View>
          <Text className='menu-arrow'>›</Text>
        </View>
      </View>

      {/* 提示信息 */}
      <View className='tips'>
        <Text className='tips-title'>温馨提示</Text>
        <Text className='tips-text'>• 可用额度 = 信用额度 - 未结清欠款</Text>
        <Text className='tips-text'>• 下单时会自动检查可用额度</Text>
        <Text className='tips-text'>• 请在账期内及时付款，避免逾期</Text>
      </View>
    </View>
  )
}
