# API完整参考文档

## 基础信息

### Base URL
```
开发环境: http://localhost:8000/api
生产环境: https://api.yourdomain.com/api
```

### 认证方式

#### JWT Token认证
```
Authorization: Bearer <your_jwt_token>
```

#### 获取Token
```
POST /api/users/login/
POST /api/users/admin-login/
```

### 通用响应格式

#### 成功响应
```json
{
    "success": true,
    "code": 200,
    "message": "操作成功",
    "data": {...}
}
```

#### 错误响应
```json
{
    "success": false,
    "code": 400,
    "message": "错误信息",
    "error_code": "ERROR_CODE"
}
```

## 用户模块 API

### 1. 微信小程序登录
```
POST /api/users/login/
```

**请求参数：**
```json
{
    "code": "wx_code_from_miniprogram"
}
```

**响应：**
```json
{
    "token": "jwt_token",
    "user": {
        "id": 1,
        "openid": "xxx",
        "nickname": "用户昵称",
        "avatar": "http://..."
    }
}
```

### 2. 管理员登录
```
POST /api/users/admin-login/
```

**请求参数：**
```json
{
    "username": "admin",
    "password": "password"
}
```

### 3. 获取当前用户信息
```
GET /api/users/me/
Authorization: Bearer <token>
```

### 4. 更新用户资料
```
PATCH /api/users/me/
Authorization: Bearer <token>
```

**请求参数：**
```json
{
    "nickname": "新昵称",
    "avatar": "http://...",
    "phone": "13800138000"
}
```

### 5. 收货地址列表
```
GET /api/addresses/
Authorization: Bearer <token>
```

### 6. 创建收货地址
```
POST /api/addresses/
Authorization: Bearer <token>
```

**请求参数：**
```json
{
    "contact_name": "张三",
    "phone": "13800138000",
    "province": "北京市",
    "city": "北京市",
    "district": "朝阳区",
    "detail": "建国路88号",
    "is_default": true
}
```

### 7. 地址智能解析
```
POST /api/addresses/parse/
Authorization: Bearer <token>
```

**请求参数：**
```json
{
    "address": "北京市朝阳区建国路88号"
}
```

## 商品目录 API

### 8. 商品列表
```
GET /api/products/
```

**查询参数：**
- page: 页码
- page_size: 每页数量
- category: 分类ID
- brand: 品牌ID
- search: 搜索关键词
- min_price: 最低价格
- max_price: 最高价格
- is_featured: 是否推荐
- ordering: 排序（price, -price, sales, -sales）

### 9. 商品详情
```
GET /api/products/{id}/
```

### 10. 分类列表
```
GET /api/categories/
```

### 11. 品牌列表
```
GET /api/brands/
```

### 12. 商品搜索
```
GET /api/products/search/?q=关键词
```

### 13. 收藏列表
```
GET /api/favorites/
Authorization: Bearer <token>
```

### 14. 添加收藏
```
POST /api/favorites/
Authorization: Bearer <token>
```

**请求参数：**
```json
{
    "product": 1
}
```

### 15. 取消收藏
```
DELETE /api/favorites/{id}/
Authorization: Bearer <token>
```

### 16. 购物车列表
```
GET /api/cart/
Authorization: Bearer <token>
```

### 17. 添加到购物车
```
POST /api/cart/
Authorization: Bearer <token>
```

**请求参数：**
```json
{
    "product": 1,
    "quantity": 2
}
```

### 18. 更新购物车
```
PATCH /api/cart/{id}/
Authorization: Bearer <token>
```

**请求参数：**
```json
{
    "quantity": 3
}
```

### 19. 删除购物车项
```
DELETE /api/cart/{id}/
Authorization: Bearer <token>
```

### 20. 清空购物车
```
POST /api/cart/clear/
Authorization: Bearer <token>
```

## 订单模块 API

### 21. 订单列表
```
GET /api/orders/
Authorization: Bearer <token>
```

**查询参数：**
- status: 订单状态
- start_date: 开始日期
- end_date: 结束日期
- page: 页码

### 22. 创建订单
```
POST /api/orders/
Authorization: Bearer <token>
```

**请求参数：**
```json
{
    "address": 1,
    "items": [
        {
            "product": 1,
            "quantity": 2
        }
    ],
    "remark": "备注",
    "use_cart": true
}
```

### 23. 订单详情
```
GET /api/orders/{id}/
Authorization: Bearer <token>
```

### 24. 取消订单
```
POST /api/orders/{id}/cancel/
Authorization: Bearer <token>
```

**请求参数：**
```json
{
    "reason": "不想要了"
}
```

### 25. 确认收货
```
POST /api/orders/{id}/confirm/
Authorization: Bearer <token>
```

### 26. 申请退款
```
POST /api/orders/{id}/refund/
Authorization: Bearer <token>
```

**请求参数：**
```json
{
    "reason": "商品有质量问题",
    "amount": 2899.00
}
```

### 27. 订单统计
```
GET /api/orders/statistics/
Authorization: Bearer <token>
```

## 支付模块 API

### 28. 创建支付
```
POST /api/payments/
Authorization: Bearer <token>
```

**请求参数：**
```json
{
    "order": 1,
    "payment_method": "wechat"
}
```

### 29. 查询支付状态
```
GET /api/payments/{id}/status/
Authorization: Bearer <token>
```

### 30. 微信支付回调
```
POST /api/payments/wechat-callback/
```

## 集成模块 API

### 31. 同步海尔商品
```
POST /api/integrations/sync-products/
Authorization: Bearer <admin_token>
```

**请求参数：**
```json
{
    "product_codes": ["GA0SZC00U", "GA0SZC00V"]
}
```

### 32. 查询海尔商品价格
```
POST /api/integrations/query-prices/
Authorization: Bearer <admin_token>
```

**请求参数：**
```json
{
    "product_codes": ["GA0SZC00U"]
}
```

### 33. 查询库存
```
POST /api/integrations/check-stock/
Authorization: Bearer <admin_token>
```

**请求参数：**
```json
{
    "product_code": "GA0SZC00U",
    "county_code": "110101"
}
```

### 34. 查询物流
```
POST /api/integrations/query-logistics/
Authorization: Bearer <token>
```

**请求参数：**
```json
{
    "order_code": "SO202501011230001"
}
```

### 35. 同步日志列表
```
GET /api/integrations/sync-logs/
Authorization: Bearer <admin_token>
```

## 管理员 API

### 36. 用户列表
```
GET /api/users/admin-users/
Authorization: Bearer <admin_token>
```

### 37. 创建商品
```
POST /api/products/
Authorization: Bearer <admin_token>
Content-Type: multipart/form-data
```

### 38. 更新商品
```
PUT /api/products/{id}/
Authorization: Bearer <admin_token>
```

### 39. 删除商品
```
DELETE /api/products/{id}/
Authorization: Bearer <admin_token>
```

### 40. 订单发货
```
POST /api/orders/{id}/ship/
Authorization: Bearer <admin_token>
```

**请求参数：**
```json
{
    "tracking_no": "SF1234567890",
    "shipping_company": "顺丰速运"
}
```

### 41. 订单分析
```
GET /api/orders/analytics/
Authorization: Bearer <admin_token>
```

**查询参数：**
- period: day/week/month/year
- start_date: 开始日期
- end_date: 结束日期

## 错误码说明

| 错误码 | HTTP状态码 | 说明 |
|--------|-----------|------|
| BUSINESS_ERROR | 400 | 业务逻辑错误 |
| INSUFFICIENT_STOCK | 409 | 库存不足 |
| INVALID_ORDER_STATUS | 400 | 订单状态不合法 |
| PAYMENT_VERIFICATION_FAILED | 400 | 支付验证失败 |
| DUPLICATE_PAYMENT | 409 | 重复支付 |
| INVALID_PAYMENT_AMOUNT | 400 | 支付金额不匹配 |
| SUPPLIER_API_ERROR | 502 | 供应商API错误 |
| SUPPLIER_AUTH_FAILED | 401 | 供应商认证失败 |
| RESOURCE_CONFLICT | 409 | 资源冲突 |
| INVALID_FILE | 400 | 文件验证失败 |
| RATE_LIMIT_EXCEEDED | 429 | 请求频率超限 |

## 限流规则

### 用户级别限流
- 普通用户：100请求/分钟
- 管理员：1000请求/分钟

### 端点级别限流
- 登录接口：10请求/分钟
- 支付接口：20请求/分钟
- 查询接口：100请求/分钟

## 测试工具

### cURL示例

```bash
# 登录
curl -X POST http://localhost:8000/api/users/login/ \
  -H "Content-Type: application/json" \
  -d '{"code": "wx_code"}'

# 获取商品列表
curl -X GET http://localhost:8000/api/products/ \
  -H "Authorization: Bearer <token>"

# 创建订单
curl -X POST http://localhost:8000/api/orders/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"address": 1, "items": [{"product": 1, "quantity": 2}]}'
```

### Postman集合

导入Postman集合文件：`docs/postman_collection.json`

## API文档

### Swagger UI
```
http://localhost:8000/api/docs/
```

### ReDoc
```
http://localhost:8000/api/redoc/
```

## 版本控制

当前API版本：v1

版本号在URL中体现：
```
/api/v1/products/
```

## 更新日志

### v1.0.0 (2025-01-01)
- 初始版本发布
- 用户认证
- 商品管理
- 订单管理
- 支付功能
- 海尔API集成
