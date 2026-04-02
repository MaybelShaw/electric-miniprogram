# 海尔 4.2 回调与混合订单拆单设计文档

**版本**: 1.0
**日期**: 2026-04-02
**作者**: Claude Code
**状态**: 待审批

---

## 1. 概述

### 1.1 背景

根据海尔 API 文档 4.2 节"取消订单/拦截/拒收回调"的最新规范，海尔回调接口支持：
- **State=2（部分成功）** - 支持一单多商品场景下的部分退货成功/失败
- **itemList 商品明细** - 回调中带入商品数量明细（签收、拒收、退货）
- **拒收通知场景** - 海尔主动触发通知（客户未发起取消请求时）

同时，业务需求支持用户混合下单（海尔商品 + 本地商品），系统需要自动拆单处理。

### 1.2 问题陈述

1. **4.2 回调数据格式变化**：现有 `update_from_haier_callback` 方法仅支持订单级别的状态更新，不支持商品级别的签收/拒收/退货数量
2. **混合订单无法推送**：当前实现检测到混合订单时直接返回错误，不支持自动拆单
3. **售后流程分离**：海尔商品和本地商品需要独立的售后流程

### 1.3 设计目标

1. 支持海尔 4.2 回调的商品级别状态更新
2. 支持海尔商品 + 本地商品混合下单，自动拆分为两个子订单
3. 主订单用于统一支付，子订单用于分别发货和售后
4. 保持与现有订单流程的兼容性

---

## 2. 架构设计

### 2.1 订单结构

```
┌─────────────────────────────────────────────────────────────┐
│                      主订单 (Main Order)                     │
│  - order_number: "202604021234567890"                       │
│  - order_type: "main"                                       │
│  - parent_order: NULL                                       │
│  - actual_amount: 1350.00 (海尔 900 + 本地 450)              │
│  - status: "paid"                                           │
│  - user_id: 123                                             │
└─────────────────────────────────────────────────────────────┘
                            │
            ┌───────────────┴───────────────┐
            │                               │
            ▼                               ▼
┌───────────────────────┐       ┌───────────────────────┐
│   海尔子订单           │       │   本地子订单           │
│   (Haier Child)       │       │   (Local Child)       │
├───────────────────────┤       ├───────────────────────┤
│ order_type: "haier"   │       │ order_type: "local"   │
│ parent_order: [主订单] │       │ parent_order: [主订单] │
│ actual_amount: 900.00 │       │ actual_amount: 450.00 │
│ haier_so_id: "SO.xxx" │       │ haier_so_id: NULL     │
│ status: "confirmed"   │       │ status: "pending"     │
├───────────────────────┤       ├───────────────────────┤
│ OrderItems:           │       │ OrderItems:           │
│ - 海尔商品 A x1        │       │ - 本地商品 B x1        │
│ - 海尔商品 C x2        │       │ - 本地商品 D x3        │
└───────────────────────┘       └───────────────────────┘
```

### 2.2 数据模型变更

#### 2.2.1 Order 模型新增字段

```python
# 父子订单关系
parent_order = models.ForeignKey(
    'self',
    null=True,
    blank=True,
    on_delete=models.PROTECT,
    related_name='child_orders',
    verbose_name='主订单'
)

order_type = models.CharField(
    max_length=20,
    choices=[
        ('main', '主订单'),
        ('haier', '海尔子订单'),
        ('local', '本地子订单')
    ],
    default='main',
    verbose_name='订单类型'
)

# 修改现有字段
haier_so_id = models.CharField(
    max_length=100,
    blank=True,
    null=True,  # 改为允许 NULL
    unique=False,  # 移除唯一约束
    verbose_name='海尔子订单号'
)
```

#### 2.2.2 OrderItem 模型新增字段

```python
# 海尔 4.2 回调状态字段
receive_qty = models.PositiveIntegerField(
    default=0,
    verbose_name='签收数量'
)
return_qty = models.PositiveIntegerField(
    default=0,
    verbose_name='退货数量'
)
reject_qty = models.PositiveIntegerField(
    default=0,
    verbose_name='拒收数量'
)
```

### 2.3 金额分配规则

由于折扣是按商品维度独立计算的，拆单后的金额分配非常简单：

- **主订单金额** = 所有商品的 `actual_amount` 之和
- **海尔子订单金额** = 所有海尔商品的 `actual_amount` 之和
- **本地子订单金额** = 所有本地商品的 `actual_amount` 之和

每个商品的 `actual_amount` = `unit_price × quantity - discount_amount`

---

## 3. 流程设计

### 3.1 混合订单拆单流程

```
用户提交订单（海尔商品 + 本地商品）
         │
         ▼
┌─────────────────────────┐
│  create_order_with_split │
│  (新服务函数)            │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 1. 按 source 分组商品     │
│    - haier_items         │
│    - local_items         │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 2. 创建主订单            │
│    - order_type = "main" │
│    - amount = sum(all)   │
│    - parent_order = NULL │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 3. 创建海尔子订单         │
│    - order_type = "haier"│
│    - parent_order = 主订单│
│    - items = haier_items │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 4. 创建本地子订单         │
│    - order_type = "local"│
│    - parent_order = 主订单│
│    - items = local_items │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 5. 锁定库存              │
│    - 海尔商品：API 校验    │
│    - 本地商品：本地锁定    │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 6. 创建支付记录          │
│    - 关联主订单          │
│    - amount = 总金额      │
└─────────────────────────┘
         │
         ▼
用户支付主订单
```

### 3.2 海尔推送流程

```
管理员触发推送 / 自动推送
         │
         ▼
┌─────────────────────────┐
│ push_to_haier           │
│ (订单视图方法)          │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 检查是否为海尔子订单     │
│ - order_type == "haier" │
│ - parent_order != NULL  │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 准备海尔订单数据         │
│ prepare_haier_order_data│
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 调用易理货 API           │
│ YLHSystemAPI.create_order│
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 更新子订单状态          │
│ - haier_so_id           │
│ - haier_status          │
└─────────────────────────┘
```

### 3.3 海尔 4.2 回调处理流程

```
海尔平台回调通知
   POST /api/integrations/ylh/callback/
         │
         ▼
┌─────────────────────────┐
│ YLHCallbackHandler      │
│ route_callback          │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 根据 Method 路由         │
│ - hmm.scm_heorder.cancel│
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│ handle_order_cancel_... │
│ (新增 4.2 处理方法)      │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 1. 解析 itemList         │
│    - productCode         │
│    - receiveQty          │
│    - returnQty           │
│    - rejectQty           │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 2. 根据 PlatformOrderNo  │
│    查找海尔子订单        │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 3. 更新 OrderItem 状态   │
│    - receive_qty         │
│    - return_qty          │
│    - reject_qty          │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 4. 根据 State 更新订单   │
│    - State=1: 成功       │
│    - State=0: 失败       │
│    - State=2: 部分成功   │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 5. 触发本地售后流程      │
│    - 创建 ReturnRequest  │
│    - 更新订单状态        │
└─────────────────────────┘
```

---

## 4. 接口设计

### 4.1 Order 序列化器变更

```python
class OrderSerializer(serializers.ModelSerializer):
    # 新增字段
    order_type = serializers.CharField(read_only=True)
    order_type_label = serializers.SerializerMethodField()
    parent_order_id = serializers.IntegerField(read_only=True, allow_null=True)
    child_orders = serializers.SerializerMethodField()

    def get_order_type_label(self, obj):
        labels = {
            'main': '主订单',
            'haier': '海尔子订单',
            'local': '本地子订单',
        }
        return labels.get(obj.order_type, obj.order_type)

    def get_child_orders(self, obj):
        if obj.order_type != 'main':
            return []
        child_orders = Order.objects.filter(
            parent_order=obj
        ).prefetch_related('items__product', 'items__sku')
        return OrderSerializer(child_orders, many=True).data
```

### 4.2 订单列表接口变更

**GET /api/orders/my_orders/**

```json
{
  "count": 1,
  "results": [
    {
      "id": 100,
      "order_number": "202604021234567890",
      "order_type": "main",
      "order_type_label": "主订单",
      "actual_amount": "1350.00",
      "status": "paid",
      "child_orders": [
        {
          "id": 101,
          "order_number": "202604021234567890-H",
          "order_type": "haier",
          "order_type_label": "海尔子订单",
          "actual_amount": "900.00",
          "status": "confirmed",
          "haier_order_no": "SO.20260402.000001",
          "items": [...]
        },
        {
          "id": 102,
          "order_number": "202604021234567890-L",
          "order_type": "local",
          "order_type_label": "本地子订单",
          "actual_amount": "450.00",
          "status": "pending",
          "items": [...]
        }
      ]
    }
  ]
}
```

### 4.3 OrderItem 序列化器变更

```python
class OrderItemSerializer(serializers.ModelSerializer):
    # 新增字段
    receive_qty = serializers.IntegerField(read_only=True)
    return_qty = serializers.IntegerField(read_only=True)
    reject_qty = serializers.IntegerField(read_only=True)
    is_haier_item = serializers.BooleanField(read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            # 现有字段...
            'receive_qty',
            'return_qty',
            'reject_qty',
            'is_haier_item',
        ]
```

---

## 5. 实现计划

### 5.1 第一阶段：模型变更

1. **修改 Order 模型**
   - 添加 `parent_order` 字段
   - 添加 `order_type` 字段
   - 修改 `haier_so_id` 为 `unique=False`

2. **修改 OrderItem 模型**
   - 添加 `receive_qty`, `return_qty`, `reject_qty` 字段

3. **创建数据库迁移**

### 5.2 第二阶段：拆单服务

1. **实现 `create_order_with_split` 函数**
   - 按 `source` 分组商品
   - 创建主订单和子订单
   - 处理支付逻辑

2. **修改现有下单接口**
   - `POST /api/orders/create_order/`
   - `POST /api/orders/create_batch_orders/`

### 5.3 第三阶段：回调处理

1. **更新 `handle_order_cancel_callback` 方法**
   - 解析 `itemList`
   - 更新 `OrderItem` 状态字段
   - 处理 `State=2` 部分成功场景

2. **新增售后流程触发**
   - 自动创建 `ReturnRequest`
   - 触发本地退款流程

### 5.4 第四阶段：接口适配

1. **更新序列化器**
   - `OrderSerializer` 增加子订单字段
   - `OrderItemSerializer` 增加回调状态字段

2. **前端适配**
   - 订单列表展示子订单
   - 售后界面支持子订单

---

## 6. 错误处理

### 6.1 拆单失败场景

| 场景 | 错误信息 | 处理方式 |
|------|----------|----------|
| 海尔商品库存不足 | "海尔商品 [名称] 库存不足" | 整体订单失败，不拆单 |
| 本地商品库存不足 | "商品 [名称] 库存不足" | 整体订单失败，不拆单 |
| 海尔 API 不可用 | "海尔系统暂不可用，请稍后重试" | 整体订单失败，不拆单 |

### 6.2 回调处理失败场景

| 场景 | 错误信息 | 处理方式 |
|------|----------|----------|
| 子订单不存在 | "订单不存在" | 返回失败响应，记录日志 |
| 商品编码不匹配 | "商品 [编码] 未在订单中找到" | 跳过该商品，继续处理其他商品 |
| 签名验证失败 | "签名验证失败" | 返回失败响应，拒绝回调 |

---

## 7. 测试计划

### 7.1 单元测试

1. **拆单服务测试**
   - 纯海尔商品订单（不拆单）
   - 纯本地商品订单（不拆单）
   - 混合商品订单（拆单）
   - 金额分配正确性

2. **回调处理测试**
   - State=1（成功）场景
   - State=0（失败）场景
   - State=2（部分成功）场景
   - itemList 解析正确性

### 7.2 集成测试

1. **下单流程**
   - 混合下单 → 拆单 → 支付
   - 海尔推送 → 回调 → 状态同步

2. **售后流程**
   - 海尔商品退货 → 回调 → 本地退款
   - 本地商品退货 → 本地流程

### 7.3 回归测试

1. **现有功能**
   - 纯海尔商品订单流程
   - 纯本地商品订单流程
   - 现有售后流程

---

## 8. 风险评估

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| 数据库迁移失败 | 低 | 高 | 先备份，分步执行 |
| 拆单逻辑与现有代码冲突 | 中 | 中 | 充分测试，保持兼容 |
| 回调处理遗漏商品 | 低 | 高 | 记录详细日志，监控告警 |
| 前端适配工作量大 | 中 | 低 | 提供清晰接口文档 |

---

## 9. 附录

### 9.1 海尔 4.2 回调 Data 格式

```json
{
  "ExtOrderNo": "SO.20260402.000001",
  "PlatformOrderNo": "202604021234567890-H",
  "State": 2,
  "FailMsg": "",
  "itemList": [
    {
      "productCode": "GA0SZC00U",
      "totalQty": 2,
      "receiveQty": 1,
      "returnQty": 0,
      "rejectQty": 1
    }
  ]
}
```

### 9.2 相关文件

- `backend/orders/models.py` - 订单模型
- `backend/orders/services.py` - 订单服务
- `backend/integrations/ylhapi.py` - 易理货 API 集成
- `haier_api.md` - 海尔 API 文档 4.2 节
