import { fetchAllPaginated, http } from '../utils/request'
import { PaginatedResponse } from '../types'

export interface CreditAccount {
  id: number
  user: number
  user_name: string
  company_name: string
  credit_limit: string
  payment_term_days: number
  outstanding_debt: string
  available_credit: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface AccountStatement {
  id: number
  credit_account: number
  user_name: string
  company_name: string
  period_start: string
  period_end: string
  previous_balance: string
  current_purchases: string
  current_payments: string
  current_refunds: string
  period_end_balance: string
  due_within_term: string
  paid_within_term: string
  overdue_amount: string
  status: 'draft' | 'confirmed' | 'settled'
  created_at: string
  updated_at: string
  confirmed_at?: string
  settled_at?: string
  transactions?: AccountTransaction[]
}

export interface AccountTransaction {
  id: number
  credit_account: number
  user_name: string
  statement?: number
  transaction_type: 'purchase' | 'payment' | 'refund' | 'adjustment'
  transaction_type_display: string
  amount: string
  balance_after: string
  order_id?: number
  order_info?: {
    order_number: string
    product_name: string
    quantity: number
    status: string
    status_display: string
  }
  due_date?: string
  paid_date?: string
  payment_status: 'unpaid' | 'paid' | 'overdue'
  payment_status_display: string
  description: string
  created_at: string
}

export const creditService = {
  // 获取我的信用账户
  async getMyAccount(): Promise<CreditAccount> {
    return http.get<CreditAccount>('/credit-accounts/my_account/')
  },

  // 获取我的对账单列表
  async getMyStatements(params?: any): Promise<PaginatedResponse<AccountStatement>> {
    return http.get<PaginatedResponse<AccountStatement>>('/account-statements/my_statements/', params)
  },

  async getAllMyStatements(params?: any): Promise<AccountStatement[]> {
    return fetchAllPaginated<AccountStatement>('/account-statements/my_statements/', params, 100, true)
  },

  // 获取对账单详情
  async getStatementDetail(id: number): Promise<AccountStatement> {
    return http.get<AccountStatement>(`/account-statements/${id}/`)
  },

  // 获取我的交易记录
  async getMyTransactions(params?: any): Promise<PaginatedResponse<AccountTransaction>> {
    return http.get<PaginatedResponse<AccountTransaction>>('/account-transactions/my_transactions/', params)
  },

  async getAllMyTransactions(params?: any): Promise<AccountTransaction[]> {
    return fetchAllPaginated<AccountTransaction>('/account-transactions/my_transactions/', params, 100, true)
  },

  // 确认对账单
  async confirmStatement(id: number): Promise<any> {
    return http.post(`/account-statements/${id}/confirm/`)
  }
}
