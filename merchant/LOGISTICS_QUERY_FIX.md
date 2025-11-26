# 物流查询功能修复

## 问题
查询海尔订单物流时返回 400 错误：
```
Bad Request: /api/orders/2/haier_logistics/
```

## 原因分析

### 1. 检查字段错误
- 代码检查 `order.haier_order_no` 是否存在
- 但推送订单时只设置了 `order.haier_so_id`
- 导致检查失败，返回 400 错误

### 2. API使用错误
- 原代码使用海尔API (`HaierAPI`) 查询物流
- 但物流信息应该从易理货系统 (`YLHSystemAPI`) 查询
- 海尔API的物流查询需要特殊的认证方式

## 修复内容

### 1. 修改检查逻辑
**文件**: `backend/orders/views.py`

修改前：
```python
if not order.haier_order_no:
    return Response(
        {'detail': '该订单未推送到海尔系统'},
        status=status.HTTP_400_BAD_REQUEST
    )
```

修改后：
```python
if not order.haier_so_id:
    return Response(
        {'detail': '该订单未推送到海尔系统'},
        status=status.HTTP_400_BAD_REQUEST
    )
```

### 2. 切换到易理货API
**文件**: `backend/orders/views.py`

修改前：
```python
from integrations.haierapi import HaierAPI
haier_api = HaierAPI(config)
logistics_info = haier_api.get_logistics_info(order.haier_order_no)
```

修改后：
```python
from integrations.ylhapi import YLHSystemAPI
ylh_api = YLHSystemAPI(config)
logistics_info = ylh_api.get_logistics_by_order_codes([order.haier_so_id])
```

### 3. 保存巨商汇订单号
**文件**: `backend/orders/views.py`

在推送订单成功后，保存返回的巨商汇订单号：
```python
# 更新订单的haier_so_id和haier_order_no
order.haier_so_id = order_data['soId']
# 从返回结果中获取巨商汇订单号（如果有）
if isinstance(result, dict) and result.get('data'):
    order.haier_order_no = result['data'].get('retailOrderNo', '')
order.save()
```

## 数据库字段说明

订单模型中的海尔相关字段：

| 字段 | 说明 | 何时设置 |
|------|------|----------|
| `haier_so_id` | 子订单号（SO单号） | 推送订单时设置，格式：`{order_number}-{order_id}` |
| `haier_order_no` | 巨商汇订单号 | 推送成功后从API返回结果中获取 |
| `haier_status` | 海尔订单状态 | 接收回调时更新 |

## API调用流程

### 推送订单
```
1. 准备订单数据（包含soId）
2. 调用 YLHSystemAPI.create_order()
3. 保存 haier_so_id 和 haier_order_no
4. 返回推送结果
```

### 查询物流
```
1. 检查 haier_so_id 是否存在
2. 调用 YLHSystemAPI.get_logistics_by_order_codes([haier_so_id])
3. 返回物流信息
```

## 物流信息格式

易理货API返回的物流信息包含：

```json
[
  {
    "orderCode": "订单号",
    "deliveryRecordCode": "发货单号",
    "logisticsList": [
      {
        "logisticsCompany": "物流公司",
        "logisticsNo": "物流单号",
        "snCode": "SN码"
      }
    ]
  }
]
```

## 测试步骤

1. **推送订单**
   ```bash
   POST /api/orders/{id}/push_to_haier/
   {
     "source_system": "MERCHANT_ADMIN",
     "shop_name": "测试店铺"
   }
   ```

2. **查询物流**
   ```bash
   GET /api/orders/{id}/haier_logistics/
   ```

3. **验证数据**
   ```sql
   SELECT id, order_number, haier_so_id, haier_order_no 
   FROM orders_order 
   WHERE id = {order_id};
   ```

## 注意事项

1. **SO单号格式**：`{order_number}-{order_id}`，例如：`1764050087579528-2`
2. **物流查询时机**：订单推送成功后才能查询物流
3. **API认证**：易理货API使用独立的认证系统，需要正确配置 YLH_* 环境变量
4. **批量查询**：`get_logistics_by_order_codes` 支持批量查询（最多100个）

## 相关文档

- [推送订单功能修复](./PUSH_ORDER_FIX.md)
- [海尔订单推送指南](./HAIER_ORDER_PUSH_GUIDE.md)
- [海尔订单问题排查](./HAIER_ORDER_TROUBLESHOOTING.md)
