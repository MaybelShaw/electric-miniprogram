# 信用账户系统实现总结

## 已实现功能

### 后端 (Backend)

#### 数据模型
- `CreditAccount` - 信用账户模型
- `AccountStatement` - 对账单模型  
- `AccountTransaction` - 交易记录模型

#### API端点
**管理员端点:**
- 信用账户管理 (CRUD)
- 对账单管理 (生成、确认、结清、导出Excel)
- 交易记录查询

**经销商端点:**
- 查看自己的信用账户
- 查看对账单列表和详情
- 查看交易记录

#### 业务逻辑
- 信用额度检查
- 采购/付款/退款交易记录
- 逾期状态自动更新
- 对账单自动生成和计算
- 订单创建时支持信用支付

### 商户管理后台 (Merchant Admin)

#### 页面
- `/credit-accounts` - 信用账户管理页面
- `/account-statements` - 对账单管理页面

#### 功能
- 创建和编辑信用账户
- 设置信用额度和账期
- 生成对账单
- 确认和结清对账单
- 导出对账单为Excel
- 查看交易明细

### 用户小程序 (Frontend Mini-Program)

#### 页面
- `/pages/credit-account/index` - 信用账户页面
- `/pages/account-statements/index` - 对账单列表页面
- `/pages/statement-detail/index` - 对账单详情页面
- `/pages/account-transactions/index` - 交易记录页面

#### 功能
- 查看信用额度和可用额度
- 查看对账单列表和详情
- 查看交易记录
- 下单时选择信用支付
- 信用额度实时检查

## 核心流程

### 1. 创建信用账户
管理员审核通过经销商认证后 → 创建信用账户 → 设置信用额度和账期

### 2. 赊账下单
经销商下单 → 选择信用支付 → 检查可用额度 → 创建订单 → 记录采购交易 → 增加欠款

### 3. 付款
经销商付款 → 记录付款交易 → 减少欠款 → 按FIFO标记采购为已付

### 4. 对账
管理员定期生成对账单 → 汇总财务数据 → 确认对账单 → 结清对账单

## 技术特点

- 使用Django事务保证数据一致性
- 支持Excel导出对账单
- 自动计算逾期金额
- FIFO付款分配策略
- 实时信用额度检查
- 响应式UI设计

## 文件清单

### Backend
- `backend/users/models.py` - 添加信用账户模型
- `backend/users/serializers.py` - 添加序列化器
- `backend/users/views.py` - 添加视图集
- `backend/users/urls.py` - 添加路由
- `backend/users/admin.py` - 添加管理后台
- `backend/users/credit_services.py` - 业务逻辑服务
- `backend/orders/services.py` - 订单服务集成
- `backend/orders/serializers.py` - 订单序列化器更新
- `backend/orders/views.py` - 订单视图更新

### Merchant Admin
- `merchant/src/services/api.ts` - API服务
- `merchant/src/pages/CreditAccounts/index.tsx` - 信用账户页面
- `merchant/src/pages/AccountStatements/index.