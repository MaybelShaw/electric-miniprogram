# 信用账户系统 (Credit Account System)

## 概述

为经销商提供赊账下单功能的账务管理系统。

## 核心概念

### 1. 信用账户 (CreditAccount)

每个经销商拥有一个信用账户，包含：

- **信用额度** (credit_limit): 最大欠款限额
- **可用额度** (available_credit): 信用额度 - 未结清欠款
- **账期** (payment_term_days): 赊账后允许的最长还款时间（如30天）
- **未结清欠款** (outstanding_debt): 当前总欠款

### 2. 账务对账单 (AccountStatement)

定期生成的财务汇总报表，包含：

- **上期结余**: 上一期未付金额
- **本期采购**: 本期新增采购金额
- **本期付款**: 本期已付款金额
- **本期退款**: 本期退款金额
- **期末未付**: 本期结束时的未付金额
- **账期内应付**: 在账期内应付的金额
- **账期内已付**: 在账期内已付的金额
- **往来余额（逾期）**: 超过账期的逾期金额

### 3. 账务交易记录 (AccountTransaction)

每笔交易的详细记录，类型包括：

- **采购** (purchase): 赊账下单，增加欠款
- **付款** (payment): 还款，减少欠款
- **退款** (refund): 订单退款，减少欠款
- **调整** (adjustment): 手动调整

## API 端点

### 管理员端点

#### 信用账户管理

```
GET    /api/v1/credit-accounts/          # 查看所有信用账户
POST   /api/v1/credit-accounts/          # 创建信用账户
GET    /api/v1/credit-accounts/{id}/     # 查看信用账户详情
PATCH  /api/v1/credit-accounts/{id}/     # 更新信用额度和账期
```

#### 对账单管理

```
GET    /api/v1/account-statements/                # 查看所有对账单
POST   /api/v1/account-statements/                # 创建对账单
GET    /api/v1/account-statements/{id}/           # 查看对账单详情
POST   /api/v1/account-statements/{id}/confirm/   # 确认对账单
POST   /api/v1/account-statements/{id}/settle/    # 结清对账单
GET    /api/v1/account-statements/{id}/export/    # 导出Excel
```

#### 交易记录查询

```
GET    /api/v1/account-transactions/      # 查看所有交易记录
GET    /api/v1/account-transactions/{id}/ # 查看交易详情
```

### 经销商端点

```
GET    /api/v1/credit-accounts/my_account/           # 查看自己的信用账户
GET    /api/v1/account-statements/my_statements/     # 查看自己的对账单列表
GET    /api/v1/account-statements/{id}/              # 查看对账单详情
GET    /api/v1/account-transactions/my_transactions/ # 查看自己的交易记录
```

## 使用流程

### 1. 为经销商创建信用账户

管理员审核通过经销商认证后，创建信用账户：

```bash
POST /api/v1/credit-accounts/
{
  "user": 123,
  "credit_limit": 100000.00,
  "payment_term_days": 30
}
```

### 2. 经销商赊账下单

经销商下单时，系统自动：
1. 检查可用额度是否足够
2. 创建采购交易记录
3. 增加未结清欠款
4. 计算应付日期（下单日期 + 账期天数）

```python
from users.credit_services import CreditAccountService

# 在订单创建时调用
CreditAccountService.record_purchase(
    credit_account=user.credit_account,
    amount=order.total_amount,
    order_id=order.id,
    description=f"订单 #{order.id}"
)
```

### 3. 经销商付款

经销商付款时，系统自动：
1. 减少未结清欠款
2. 创建付款交易记录
3. 按FIFO原则标记未付采购为已付

```python
CreditAccountService.record_payment(
    credit_account=user.credit_account,
    amount=payment_amount,
    description="银行转账"
)
```

### 4. 生成对账单

管理员定期（如每月）生成对账单：

```python
from users.credit_services import AccountStatementService

statement = AccountStatementService.generate_statement(
    credit_account=credit_account,
    period_start=date(2025, 11, 1),
    period_end=date(2025, 11, 30)
)
```

### 5. 确认和结清对账单

```python
# 确认对账单
AccountStatementService.confirm_statement(statement)

# 结清对账单（付清所有款项后）
AccountStatementService.settle_statement(statement)
```

## 定时任务

建议设置定时任务更新逾期状态：

```python
from users.credit_services import CreditAccountService

# 每天运行一次
CreditAccountService.update_overdue_status()
```

## 数据库模型

### CreditAccount

```python
- user: OneToOne -> User (经销商)
- credit_limit: Decimal (信用额度)
- payment_term_days: Integer (账期天数)
- outstanding_debt: Decimal (未结清欠款)
- is_active: Boolean (账户状态)
```

### AccountStatement

```python
- credit_account: ForeignKey -> CreditAccount
- period_start: Date (账期开始)
- period_end: Date (账期结束)
- previous_balance: Decimal (上期结余)
- current_purchases: Decimal (本期采购)
- current_payments: Decimal (本期付款)
- current_refunds: Decimal (本期退款)
- period_end_balance: Decimal (期末未付)
- due_within_term: Decimal (账期内应付)
- paid_within_term: Decimal (账期内已付)
- overdue_amount: Decimal (逾期金额)
- status: Choice (draft/confirmed/settled)
```

### AccountTransaction

```python
- credit_account: ForeignKey -> CreditAccount
- statement: ForeignKey -> AccountStatement
- transaction_type: Choice (purchase/payment/refund/adjustment)
- amount: Decimal (交易金额)
- balance_after: Decimal (交易后余额)
- order_id: BigInteger (关联订单ID)
- due_date: Date (应付日期)
- paid_date: Date (实付日期)
- payment_status: Choice (unpaid/paid/overdue)
- description: String (备注)
```

## 权限控制

- **管理员**: 可以管理所有信用账户、对账单和交易记录
- **经销商**: 只能查看自己的信用账户、对账单和交易记录
- **个人用户**: 无权访问信用账户功能

## 注意事项

1. 只有角色为 `dealer` 的用户才能创建信用账户
2. 下单前必须检查可用额度是否足够
3. 付款采用FIFO原则，优先结清最早的采购记录
4. 对账单一旦确认，不可修改
5. 结清对账单会自动更新信用账户的未结清欠款
6. 建议定期运行定时任务更新逾期状态
