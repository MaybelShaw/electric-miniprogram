# 订单模块文档 (orders)

## 模块概述

订单模块负责订单的创建、管理、状态流转、支付处理等核心业务功能。

## 数据模型

### Order (订单)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BigAutoField | 主键 |
| order_no | CharField(32) | 订单号（唯一） |
| user | ForeignKey | 用户 |
| status | CharField(20) | 订单状态 |
| total_amount | DecimalField | 订单总金额 |
| shipping_fee | DecimalField | 运费 |
| discount_amount | DecimalField | 优惠金额 |
| final_amount | DecimalField | 实付金额 |
| shipping_address | JSONField | 收货地址 |
| remark | TextField | 备注 |
| created_at | DateTimeField | 创建时间 |
| paid_at | DateTimeField | 支付时间 |
| shipped_at | DateTimeField | 发货时间 |
| completed_at | DateTimeField | 完成时间 |
| cancelled_at | DateTimeField | 取消时间 |
| cancel_reason | CharField | 取消原因 |

**订单状态：**
- `pending`: 待支付
- `paid`: 已支付
- `shipped`: 已发货
- `completed`: 已完成
- `cancelled`: 已取消
- `refunding`: 退款中
- `refunded`: 已退款

### OrderItem (订单明细)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BigAutoField | 主键 |
| order | ForeignKey | 订单 |
| product | ForeignKey | 商品 |
| product_name | CharField | 商品名称（快照） |
| product_sku | CharField | 商品SKU（快照） |
| product_image | URLField | 商品图片（快照） |
| price | DecimalField | 单价（快照） |
| quantity | IntegerField | 数量 |
| subtotal | DecimalField | 小计 |

### Payment (支付记录)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BigAutoField | 主键 |
| order | ForeignKey | 订单 |
| payment_no | CharField(64) | 支付单号（唯一） |
| payment_method | CharField(20) | 支付方式 |
| amount | DecimalField | 支付金额 |
| status | CharField(20) | 支付状态 |
| transaction_id | CharField | 第三方交易号 |
| callback_data | JSONField | 回调数据 |
| created_at | DateTimeField | 创建时间 |
| paid_at | DateTimeField | 支付时间 |

**支付方式：**
- `wechat`: 微信支付
- `alipay`: 支付宝
- `balance`: 余额支付
- `offline`: 线下支付

**支付状态：**
- `pending`: 待支付
- `success`: 支付成功
- `failed`: 支付失败
- `cancelled`: 已取消
- `refunding`: 退款中
- `refunded`: 已退款

## 订单状态机

### 状态转换规则
```
pending → paid → shipped → completed
   ↓        ↓        ↓         ↓
cancelled  cancelled  refunding  refunding
                        ↓
                     refunded
```

### 状态转换验证
```python
TRANSITIONS = {
    'pending': ['paid', 'cancelled'],
    'paid': ['shipped', 'cancelled', 'refunding'],
    'shipped': ['completed', 'refunding'],
    'completed': ['refunding'],
    'cancelled': [],
    'refunding': ['refunded', 'paid'],
    'refunded': []
}
```

## API端点

### 订单管理
- `GET /api/orders/` - 订单列表
  - 查询参数：status, start_date, end_date, page
- `GET /api/orders/{id}/` - 订单详情
- `POST /api/orders/` - 创建订单
- `POST /api/orders/{id}/cancel/` - 取消订单
- `POST /api/orders/{id}/confirm/` - 确认收货
- `POST /api/orders/{id}/refund/` - 申请退款
- `GET /api/orders/statistics/` - 订单统计

### 支付管理
- `POST /api/payments/` - 创建支付
- `GET /api/payments/{id}/status/` - 查询支付状态
- `POST /api/payments/wechat-callback/` - 微信支付回调

### 管理员功能
- `GET /api/orders/admin-orders/` - 管理员订单列表
- `POST /api/orders/{id}/ship/` - 发货
- `GET /api/orders/analytics/` - 订单分析
- `POST /api/orders/batch-action/` - 批量操作

## 业务流程

### 创建订单流程
1. 验证收货地址
2. 验证商品库存
3. 计算订单金额
4. 创建订单记录
5. 创建订单明细
6. 扣减商品库存
7. 清空购物车（可选）

### 支付流程
1. 创建支付记录
2. 调用支付接口
3. 返回支付参数
4. 用户完成支付
5. 接收支付回调
6. 更新订单状态
7. 推送到海尔系统

### 发货流程
1. 验证订单状态
2. 更新订单状态为已发货
3. 记录物流信息
4. 发送发货通知

### 退款流程
1. 验证订单状态
2. 创建退款申请
3. 审核退款申请
4. 处理退款
5. 更新订单状态
6. 恢复商品库存

## 权限控制
- 查看订单：订单所有者或管理员
- 创建订单：认证用户
- 取消订单：订单所有者
- 发货：管理员
- 退款审核：管理员

## 索引设计
```sql
-- 订单表索引
CREATE INDEX idx_order_no ON orders_order(order_no);
CREATE INDEX idx_order_user ON orders_order(user_id);
CREATE INDEX idx_order_status ON orders_order(status);
CREATE INDEX idx_order_created ON orders_order(created_at DESC);
CREATE INDEX idx_order_user_status ON orders_order(user_id, status);

-- 订单明细索引
CREATE INDEX idx_orderitem_order ON orders_orderitem(order_id);
CREATE INDEX idx_orderitem_product ON orders_orderitem(product_id);

-- 支付记录索引
CREATE INDEX idx_payment_no ON orders_payment(payment_no);
CREATE INDEX idx_payment_order ON orders_payment(order_id);
CREATE INDEX idx_payment_status ON orders_payment(status);
CREATE INDEX idx_payment_transaction ON orders_payment(transaction_id);
```

## 使用示例

### 创建订单
```python
POST /api/orders/
Authorization: Bearer <token>

{
    "address": 1,
    "items": [
        {
            "product": 1,
            "quantity": 2
        }
    ],
    "remark": "请尽快发货",
    "use_cart": true
}
```

### 创建支付
```python
POST /api/payments/
Authorization: Bearer <token>

{
    "order": 1,
    "payment_method": "wechat"
}
```

### 取消订单
```python
POST /api/orders/1/cancel/
Authorization: Bearer <token>

{
    "reason": "不想要了"
}
```

### 发货
```python
POST /api/orders/1/ship/
Authorization: Bearer <admin_token>

{
    "tracking_no": "SF1234567890",
    "shipping_company": "顺丰速运"
}
```

## 最佳实践

1. **订单号生成**
   - 使用时间戳+随机数
   - 确保唯一性
   - 便于追踪

2. **库存管理**
   - 创建订单时锁定库存
   - 支付成功后扣减库存
   - 取消订单时释放库存
   - 使用事务保证一致性

3. **状态管理**
   - 使用状态机模式
   - 严格验证状态转换
   - 记录状态变更日志

4. **支付安全**
   - 验证支付签名
   - 防止重复支付
   - 验证支付金额
   - 记录支付日志

5. **性能优化**
   - 使用select_related优化查询
   - 使用事务处理订单创建
   - 异步处理耗时操作
   - 合理使用缓存

6. **异常处理**
   - 库存不足
   - 支付失败
   - 状态转换错误
   - 第三方API调用失败

详细API文档请参考：[API完整参考文档](./07_API_REFERENCE.md)
