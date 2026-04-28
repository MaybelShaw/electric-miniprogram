## 📘 家电分销小程序后端 API 文档（最新版）

- Base URL: `http://127.0.0.1:8000/api/`
- 认证方式: 在需要鉴权的接口添加 `Authorization: Bearer <access_token>`（`/login/` 无需鉴权）
- API 版本: v1（支持向后兼容）

---

## 认证与授权

### 认证方式

所有需要鉴权的接口都需要在请求头中添加 JWT Token：

```
Authorization: Bearer <access_token>
```

### 权限说明

- **AllowAny**: 无需认证，所有用户可访问（如商品列表、分类列表）
- **IsAuthenticated**: 需要有效的 JWT Token
- **IsAdminOrReadOnly**: 管理员可执行所有操作，其他用户仅可读
- **IsOwnerOrAdmin**: 仅资源所有者或管理员可访问

### 错误响应

所有错误响应遵循统一格式：

```json
{
  "error": "错误代码",
  "message": "错误描述信息",
  "details": {}  // 可选，包含额外信息
}
```

### 常见错误码

| 状态码 | 错误代码 | 说明 |
|--------|---------|------|
| 400 | BAD_REQUEST | 请求参数错误或缺失 |
| 401 | UNAUTHORIZED | 缺少或无效的认证令牌 |
| 403 | FORBIDDEN | 无权限执行此操作 |
| 404 | NOT_FOUND | 资源不存在 |
| 429 | RATE_LIMIT_EXCEEDED | 请求过于频繁，已被限流 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

---

## 用户认证

**用户认证**
- `POST /login/`
  - 用途：微信小程序登录，用 `code` 换取 `access/refresh` 令牌与用户信息
  - 权限：AllowAny
  - 请求体：`{ "code": string }`
  - 响应：`{ "access": string, "refresh": string, "user": User }`
  - 说明：用户类型自动设置为 `wechat`，最后登录时间自动更新
  - 限流：5次/分钟

- `POST /admin/login/`
  - 用途：管理端用户名密码登录
  - 权限：AllowAny
  - 请求体：`{ "username": string, "password": string }`
  - 响应：`{ "access": string, "refresh": string, "user": User }`
  - 说明：仅管理员用户可登录，用户类型为 `admin`，最后登录时间自动更新
  - 限流：5次/分钟
  - 错误码：
    - `401 UNAUTHORIZED`: 用户名或密码错误
    - `403 FORBIDDEN`: 用户无管理员权限

- `POST /token/refresh/`
  - 用途：刷新 JWT 访问令牌
  - 权限：AllowAny
  - 请求体：`{ "refresh": string }`
  - 响应：`{ "access": string }`
  - 说明：使用 `refresh` 令牌获取新的 `access` 令牌

## 用户资料

- `GET /user/profile/`
  - 用途：获取当前用户信息
  - 权限：IsAuthenticated
  - 响应：`{ "id": number, "username": string, "avatar_url": string, "phone": string, "email": string, "user_type": "wechat|admin", "last_login_at": string(ISO), "orders_count": number, "favorites_count": number }`
  - 说明：返回用户统计信息（订单数、收藏数）

- `PATCH /user/profile/`
  - 用途：更新用户信息
  - 权限：IsAuthenticated
  - 请求体：`{ "username"?: string, "avatar_url"?: string, "phone"?: string, "email"?: string }`
  - 响应：更新后的用户对象
  - 说明：仅可更新自己的信息

**收货地址**（均需鉴权）
- `GET /addresses/` 获取当前用户地址列表
- `POST /addresses/` 创建地址
- `GET /addresses/{id}/` 获取地址详情
- `PUT/PATCH /addresses/{id}/` 更新地址
- `DELETE /addresses/{id}/` 删除地址
- `POST /addresses/{id}/set_default/` 设为默认地址
- 字段：`contact_name`, `phone`, `province`, `city`, `district`, `detail`, `is_default`

## 商品目录

- `GET /products/`
  - 用途：获取商品列表
  - 权限：AllowAny
  - 查询参数：
    - `search`: 模糊搜索商品名/描述
    - `category`: 按分类名筛选
    - `brand`: 按品牌名筛选
    - `min_price`: 最低价格
    - `max_price`: 最高价格
    - `sort_by`: 排序方式（relevance|price_asc|price_desc|sales|created）
    - `page`: 页码（默认1）
    - `page_size`: 每页数量（默认20）
  - 响应：`{ "results": Product[], "total": number, "page": number, "total_pages": number, "has_next": boolean, "has_previous": boolean }`
  - 说明：支持多条件组合搜索和排序

- `GET /products/{id}/`
  - 用途：获取商品详情
  - 权限：AllowAny
  - 响应：`{ "id": number, "name": string, "category": string, "brand": string, "category_id": number, "brand_id": number, "price": decimal, "stock": number, "description": string, "is_active": boolean, "sales_count": number, "view_count": number, "created_at": string(ISO), "updated_at": string(ISO) }`
  - 说明：当前版本不包含图片字段和规格字段

- `GET /products/by_category/?category=名称`
  - 用途：按分类获取商品
  - 权限：AllowAny
  - 查询参数：`category` (分类名称)
  - 响应：商品列表

- `GET /products/by_brand/?brand=名称`
  - 用途：按品牌获取商品
  - 权限：AllowAny
  - 查询参数：`brand` (品牌名称)
  - 响应：商品列表

- `GET /products/recommendations/`
  - 用途：获取推荐商品
  - 权限：AllowAny
  - 查询参数：
    - `type`: 推荐类型（popular|category|trending，默认popular）
    - `limit`: 返回数量（默认10，最大50）
    - `category_id`: 分类ID（仅当type=category时使用）
  - 响应：商品列表
  - 说明：
    - popular: 按销量推荐
    - trending: 按浏览量推荐
    - category: 按分类推荐

- `GET /products/{id}/related/`
  - 用途：获取相关商品
  - 权限：AllowAny
  - 查询参数：`limit` (返回数量，默认10，最大50)
  - 响应：同分类的相关商品列表
  - 说明：排除当前商品，按销量排序

## 分类

- `GET /categories/`
  - 用途：获取分类列表
  - 权限：AllowAny
  - 查询参数：`search` (按分类名称模糊搜索)
  - 响应：`{ "count": number, "results": [{ "id": number, "name": string }] }`
  - 说明：支持分页和搜索

- `GET /categories/{id}/`
  - 用途：获取分类详情
  - 权限：AllowAny
  - 响应：`{ "id": number, "name": string }`

- `POST /categories/`
  - 用途：创建分类
  - 权限：IsAdminOrReadOnly
  - 请求体：`{ "name": string }`
  - 响应：创建的分类对象

- `PUT /categories/{id}/`
  - 用途：更新分类
  - 权限：IsAdminOrReadOnly
  - 请求体：`{ "name": string }`
  - 响应：更新后的分类对象

- `DELETE /categories/{id}/`
  - 用途：删除分类
  - 权限：IsAdminOrReadOnly
  - 响应：`204 No Content`

## 品牌管理

- `GET /brands/`
  - 用途：获取品牌列表
  - 权限：AllowAny
  - 查询参数：`search` (按品牌名称模糊搜索)
  - 响应：`{ "count": number, "results": [{ "id": number, "name": string }] }`
  - 说明：支持分页和搜索

- `GET /brands/{id}/`
  - 用途：获取品牌详情
  - 权限：AllowAny
  - 响应：`{ "id": number, "name": string }`

- `POST /brands/`
  - 用途：创建品牌
  - 权限：IsAdminOrReadOnly
  - 请求体：`{ "name": string }`
  - 响应：创建的品牌对象
  - 说明：`name` 必填且唯一

- `PUT /brands/{id}/`
  - 用途：完整更新品牌
  - 权限：IsAdminOrReadOnly
  - 请求体：`{ "name": string }`
  - 响应：更新后的品牌对象

- `PATCH /brands/{id}/`
  - 用途：部分更新品牌
  - 权限：IsAdminOrReadOnly
  - 请求体：`{ "name"?: string }`
  - 响应：更新后的品牌对象

- `DELETE /brands/{id}/`
  - 用途：删除品牌
  - 权限：IsAdminOrReadOnly
  - 响应：`204 No Content`

## 媒体图片

**注意：媒体图片功能当前未实现，相关端点不可用**

## 购物车

**注意：购物车功能当前未在catalog应用中实现，相关端点可能在orders应用中**

## 订单管理

- `POST /orders/create_order/`
  - 用途：创建订单
  - 权限：IsAuthenticated
  - 请求体：`{ "product_id": number, "address_id": number, "quantity"?: number, "note"?: string }`
  - 响应：`{ "order": Order, "payment": Payment }`
  - 说明：
    - 同时创建初始支付记录，默认过期24小时
    - 库存自动锁定，库存不足返回 `400 BAD_REQUEST`
  - 错误码：
    - `400 BAD_REQUEST`: 库存不足或参数错误
    - `404 NOT_FOUND`: 商品或地址不存在

- `GET /orders/my_orders/`
  - 用途：获取当前用户订单列表
  - 权限：IsAuthenticated
  - 查询参数：`status` (pending|paid|shipped|completed|cancelled|refunding|refunded)
  - 响应：订单列表（分页）

- `GET /orders/`
  - 用途：获取订单列表
  - 权限：IsAuthenticated
  - 查询参数：`status` (订单状态筛选)
  - 说明：管理员可见全部订单，普通用户仅自身订单
  - 响应：订单列表（分页）

- `GET /orders/{id}/`
  - 用途：获取订单详情
  - 权限：IsOwnerOrAdmin
  - 响应：`{ "id": number, "user": number, "product": Product, "quantity": number, "total_amount": decimal, "status": string, "note": string, "created_at": string(ISO), "updated_at": string(ISO), "status_history": StatusHistory[] }`

- `PATCH /orders/{id}/cancel/`
  - 用途：取消订单
  - 权限：IsOwnerOrAdmin
  - 响应：更新后的订单对象
  - 说明：库存自动释放，仅待支付和已支付状态可取消
  - 错误码：
    - `400 BAD_REQUEST`: 订单状态不允许取消

- `PATCH /orders/{id}/ship/`
  - 用途：发货（管理员）
  - 权限：IsAdminOrReadOnly
  - 响应：更新后的订单对象
  - 说明：订单状态变更为 `shipped`

- `PATCH /orders/{id}/complete/`
  - 用途：完成订单（管理员）
  - 权限：IsAdminOrReadOnly
  - 响应：更新后的订单对象
  - 说明：订单状态变更为 `completed`

- 订单状态：`pending` (待支付) | `paid` (已支付) | `shipped` (已发货) | `completed` (已完成) | `cancelled` (已取消) | `refunding` (退款中) | `refunded` (已退款)

## 支付管理

- `GET /payments/`
  - 用途：获取支付记录列表
  - 权限：IsAuthenticated
  - 查询参数：`order_id` (可选，按订单筛选)
  - 说明：普通用户仅可见自己订单的支付记录，管理员可见全部
  - 响应：支付记录列表（分页）

- `POST /payments/`
  - 用途：为指定订单创建新的支付记录
  - 权限：IsAuthenticated
  - 请求体：`{ "order_id": number, "method"?: "wechat" | "alipay" | "bank" }`
  - 响应：创建的支付记录对象

- `POST /payments/{id}/start/`
  - 用途：开始支付
  - 权限：IsOwnerOrAdmin
  - 响应：更新后的支付记录（状态为 `processing`）

- `POST /payments/{id}/succeed/`
  - 用途：支付成功
  - 权限：IsOwnerOrAdmin
  - 响应：更新后的支付记录（状态为 `succeeded`）
  - 说明：同时更新订单状态为 `paid`

- `POST /payments/{id}/fail/`
  - 用途：支付失败
  - 权限：IsOwnerOrAdmin
  - 响应：更新后的支付记录（状态为 `failed`）

- `POST /payments/{id}/cancel/`
  - 用途：取消支付
  - 权限：IsOwnerOrAdmin
  - 响应：更新后的支付记录（状态为 `cancelled`）

- `POST /payments/{id}/expire/`
  - 用途：支付过期
  - 权限：IsOwnerOrAdmin
  - 响应：更新后的支付记录（状态为 `expired`）
  - 说明：同时更新订单状态为 `cancelled`，释放库存

- 支付字段：`id`, `order`, `amount`, `method`, `status`, `created_at`, `updated_at`, `expires_at`, `logs`
- 支付状态：`pending` (待支付) | `processing` (处理中) | `succeeded` (成功) | `failed` (失败) | `cancelled` (已取消) | `expired` (已过期)

## 支付回调（第三方集成）

- `POST /payments/callback/{provider}/`
  - 用途：处理第三方支付回调
  - 权限：AllowAny
  - 路由参数：`{provider}` 可取值：`mock` | `wechat`
  - 请求体：
    - `payment_id`: number (可选，支付记录ID)
    - `order_number` 或 `out_trade_no`: string (可选，订单号)
    - `status`: string (仅 mock provider，可取值：succeeded|failed|cancelled|expired|processing)
    - `result_code` 或 `trade_state`: string (仅 wechat provider，SUCCESS 表示成功)
    - `transaction_id`: string (可选，第三方交易ID)
  - 响应：`{ "id": number, "status": string, "logs": object[] }`
  - 说明：
    - 开发环境：`wechat` 仅在 `DEBUG=true` 时允许；`mock` 不受限制
    - 生产环境：仅允许真实的微信回调
    - 支付成功时自动更新订单状态为 `paid`
    - 支付过期时自动更新订单状态为 `cancelled` 并释放库存
    - 支付超时默认 `1440` 分钟（24小时），可通过环境变量 `ORDER_PAYMENT_TIMEOUT_MINUTES` 调整

### 回调示例

**模拟成功回调**
```bash
POST /payments/callback/mock/
Content-Type: application/json

{
  "payment_id": 123,
  "status": "succeeded",
  "transaction_id": "MOCK-2025-0001"
}
```

**微信开发环境回调**
```bash
POST /payments/callback/wechat/
Content-Type: application/json

{
  "out_trade_no": "202511071234567890",
  "result_code": "SUCCESS",
  "transaction_id": "4200000xxx"
}
```

## 折扣管理

- `GET /discounts/`
  - 用途：获取折扣规则列表
  - 权限：IsAuthenticated
  - 说明：管理员可见全部，普通用户仅可见与自己相关的
  - 响应：折扣规则列表（分页）

- `POST /discounts/`
  - 用途：创建折扣规则
  - 权限：IsAdminOrReadOnly
  - 请求体：`{ "user_id"?: number, "product_ids": number[], "discount_type"?: "amount" | "percent", "amount": decimal, "effective_time": string(ISO), "expiration_time": string(ISO), "priority"?: number }`
  - 说明：`discount_type=amount` 表示减免金额；`discount_type=percent` 表示折扣率（amount 为 0-10，如 9.5 表示 9.5 折）
  - 响应：创建的折扣规则对象

- `GET /discounts/{id}/`
  - 用途：获取折扣详情
  - 权限：IsAuthenticated
  - 响应：折扣规则对象

- `PATCH /discounts/{id}/`
  - 用途：更新折扣
  - 权限：IsAdminOrReadOnly
  - 请求体：可包含任意字段的子集
  - 响应：更新后的折扣规则对象

- `DELETE /discounts/{id}/`
  - 用途：删除折扣
  - 权限：IsAdminOrReadOnly
  - 响应：`{ "message": "折扣已删除" }`

- `POST /discounts/batch_set/`
  - 用途：批量为用户设置折扣
  - 权限：IsAdminOrReadOnly
  - 请求体：`{ "user_id": number, "product_ids": number[], "discount_type"?: "amount" | "percent", "amount": decimal, "effective_time": string(ISO), "expiration_time": string(ISO), "priority"?: number }`
  - 说明：`discount_type=amount` 表示减免金额；`discount_type=percent` 表示折扣率（amount 为 0-10，如 9.5 表示 9.5 折）
  - 响应：创建的折扣规则列表

- `GET /discounts/query_user_products/?product_ids=1,2,3`
  - 用途：查询当前用户针对一组商品的有效折扣
  - 权限：IsAuthenticated
  - 查询参数：`product_ids` (逗号分隔的商品ID)
  - 响应：`{ "product_id": { "amount": decimal, "discount_id": number, "discount_type": "amount|percent", "discount_value": decimal } }`

## 商品收藏

**注意：商品收藏功能当前未实现，相关端点不可用**

## 搜索与热门关键词

- `GET /search/hot_keywords/`
  - 用途：获取热门搜索关键词
  - 权限：AllowAny
  - 查询参数：`limit` (返回数量，默认10)
  - 响应：`{ "hot_keywords": [] }`
  - 说明：当前返回空数组，搜索日志功能待实现

## 数据统计（管理员）

- `GET /analytics/sales_summary/`
  - 用途：获取销售汇总统计
  - 权限：IsAdminOrReadOnly
  - 查询参数：`start_date`, `end_date` (ISO格式，可选)
  - 响应：`{ "total_orders": number, "total_amount": decimal, "avg_amount": decimal }`
  - 说明：数据缓存5分钟

- `GET /analytics/top_products/`
  - 用途：获取热销商品排行
  - 权限：IsAdminOrReadOnly
  - 查询参数：`limit` (默认10), `days` (统计天数，默认30)
  - 响应：`{ "product_id": number, "product_name": string, "total_quantity": number, "total_amount": decimal }[]`

- `GET /analytics/daily_sales/`
  - 用途：获取每日销售统计
  - 权限：IsAdminOrReadOnly
  - 查询参数：`days` (统计天数，默认30)
  - 响应：`{ "date": string(ISO), "orders": number, "amount": decimal }[]`

- `GET /analytics/user_growth/`
  - 用途：获取用户增长统计
  - 权限：IsAdminOrReadOnly
  - 查询参数：`days` (统计天数，默认30)
  - 响应：`{ "date": string(ISO), "new_users": number, "total_users": number }[]`

## 供应商集成（管理员）

- `GET /suppliers/`
  - 用途：获取供应商列表
  - 权限：IsAdminOrReadOnly
  - 响应：`{ "id": number, "name": string, "is_active": boolean, "created_at": string(ISO) }[]`

- `POST /suppliers/sync/`
  - 用途：手动触发供应商数据同步
  - 权限：IsAdminOrReadOnly
  - 请求体：`{ "supplier_name": string }`
  - 响应：`{ "status": "syncing", "sync_id": string }`
  - 说明：异步执行，返回同步任务ID

- `GET /suppliers/sync_logs/`
  - 用途：获取供应商同步日志
  - 权限：IsAdminOrReadOnly
  - 查询参数：`supplier` (供应商名称，可选)
  - 响应：`{ "id": number, "supplier": string, "sync_type": string, "status": string, "message": string, "created_at": string(ISO) }[]`

- `GET /suppliers/stock/`
  - 用途：查询供应商库存
  - 权限：IsAdminOrReadOnly
  - 查询参数：`supplier` (供应商名称), `product_code` (商品代码)
  - 响应：`{ "product_code": string, "stock": number, "last_updated": string(ISO) }`

## 系统健康检查

- `GET /healthz/`
  - 用途：系统健康检查
  - 权限：AllowAny
  - 响应：`{ "status": "ok", "database": "ok", "cache": "ok" }`
  - 说明：用于监控和部署检查

---

**响应示例**
- 登录：
  - `200 OK`
  - `{ "access": "...", "refresh": "...", "user": { "id": 1, "username": "用户_xxx", "avatar_url": "..." } }`
- 购物车 `my_cart`：
  - `{ "id": 10, "user": 1, "items": [ { "id": 99, "product": { "id": 1, "name": "海尔冰箱", "price": "2999.00" }, "product_id": 1, "quantity": 2 } ] }`

## 请求限流

系统对API请求进行频率限制以防止滥用：

| 用户类型 | 限制 | 说明 |
|---------|------|------|
| 匿名用户 | 20次/分钟 | 生产环境限制 |
| 认证用户 | 100次/分钟 | 生产环境限制 |
| 登录接口 | 5次/分钟 | 防止暴力破解 |
| 支付接口 | 10次/分钟 | 防止重复支付 |
| 开发环境 | 无限制 | 便于调试 |

当超过限制时，返回 `429 Too Many Requests` 状态码。

## 分页

列表接口支持分页，默认每页20条记录：

```json
{
  "results": [...],
  "total": 100,
  "page": 1,
  "total_pages": 5,
  "has_next": true,
  "has_previous": false
}
```

查询参数：
- `page`: 页码（默认1）
- `page_size`: 每页数量（默认20，最大100）

## 环境变量配置

### 生产环境必需

```bash
# 安全配置
DJANGO_ENV=production
SECRET_KEY=<your-secret-key>
DEBUG=False

# 数据库
POSTGRES_DB=electric_miniprogram
POSTGRES_USER=<database-user>
POSTGRES_PASSWORD=<strong-password>
POSTGRES_HOST=<database-host>
POSTGRES_PORT=5432

# CORS配置
CORS_ALLOWED_ORIGINS=https://example.com,https://admin.example.com
ALLOWED_HOSTS=example.com,admin.example.com

# SSL/HTTPS配置
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True

# 微信配置
WECHAT_APP_ID=<your-app-id>
WECHAT_APP_SECRET=<your-app-secret>

# 支付配置
PAYMENT_PROVIDER=wechat_pay
PAYMENT_MERCHANT_ID=<merchant-id>
PAYMENT_API_KEY=<api-key>

# 供应商配置
HAIER_CLIENT_ID=<client-id>
HAIER_CLIENT_SECRET=<client-secret>
HAIER_TOKEN_URL=https://api.haier.com/token
HAIER_BASE_URL=https://api.haier.com

# Redis缓存（推荐）
REDIS_URL=redis://<redis-host>:6379/0

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/django.log
```

### 开发环境

```bash
DJANGO_ENV=development
SECRET_KEY=dev-secret-key
DEBUG=True
CORS_ALLOWED_ORIGINS=http://localhost:*,http://127.0.0.1:*
ALLOWED_HOSTS=localhost,127.0.0.1
```

### 环境变量说明

| 变量名 | 必需 | 说明 |
|--------|------|------|
| DJANGO_ENV | 是 | 运行环境：development 或 production |
| SECRET_KEY | 是 | Django密钥，生产环境必须强密钥 |
| DEBUG | 是 | 调试模式，生产环境必须为False |
| POSTGRES_* | 是(生产) | PostgreSQL数据库配置 |
| CORS_ALLOWED_ORIGINS | 是(生产) | 允许的跨域源 |
| ALLOWED_HOSTS | 是(生产) | 允许的主机名 |
| SECURE_* | 否 | SSL/HTTPS安全配置 |
| WECHAT_* | 是 | 微信小程序配置 |
| PAYMENT_* | 是 | 支付网关配置 |
| HAIER_* | 是 | 海尔供应商API配置 |
| REDIS_URL | 否 | Redis缓存配置 |
| LOG_* | 否 | 日志配置 |

详见 `.env.example` 文件和 `DEPLOYMENT_GUIDE.md`。

---

## 认证详解

### JWT Token流程

1. **获取Token**
   - 小程序用户：调用 `POST /login/` 使用微信code获取token
   - 管理员用户：调用 `POST /admin/login/` 使用用户名密码获取token
   - 返回 `access` token（有效期15分钟）和 `refresh` token（有效期7天）

2. **使用Token**
   - 在请求头中添加：`Authorization: Bearer <access_token>`
   - 示例：`Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...`

3. **刷新Token**
   - 当 `access` token过期时，调用 `POST /token/refresh/`
   - 请求体：`{ "refresh": "<refresh_token>" }`
   - 返回新的 `access` token

4. **Token过期处理**
   - 返回 `401 UNAUTHORIZED` 状态码
   - 前端应自动调用刷新接口获取新token
   - 如果 `refresh` token也过期，需要重新登录

### 权限模型

系统使用基于角色的权限控制（RBAC）：

| 权限类 | 说明 | 适用场景 |
|--------|------|---------|
| AllowAny | 无需认证 | 商品列表、分类、热门搜索 |
| IsAuthenticated | 需要有效Token | 用户资料、订单、收藏 |
| IsAdminOrReadOnly | 管理员可写，其他人只读 | 商品、品牌、分类 |
| IsOwnerOrAdmin | 仅所有者或管理员 | 用户订单、地址 |

### 用户类型

系统支持两种用户类型：

| 类型 | 说明 | 登录方式 | 权限 |
|------|------|---------|------|
| wechat | 微信小程序用户 | 微信code登录 | 浏览商品、下单、支付 |
| admin | 管理员用户 | 用户名密码登录 | 管理商品、订单、用户、统计 |

---

## 错误处理详解

### 错误响应格式

所有错误响应遵循统一格式：

```json
{
  "error": "ERROR_CODE",
  "message": "用户友好的错误描述",
  "details": {
    "field": "错误字段",
    "reason": "具体原因"
  }
}
```

### HTTP状态码

| 状态码 | 含义 | 常见原因 |
|--------|------|---------|
| 200 | OK | 请求成功 |
| 201 | Created | 资源创建成功 |
| 204 | No Content | 请求成功但无返回内容 |
| 400 | Bad Request | 请求参数错误、验证失败 |
| 401 | Unauthorized | 缺少或无效的认证令牌 |
| 403 | Forbidden | 无权限执行此操作 |
| 404 | Not Found | 资源不存在 |
| 409 | Conflict | 资源冲突（如重复收藏） |
| 429 | Too Many Requests | 请求过于频繁，已被限流 |
| 500 | Internal Server Error | 服务器内部错误 |
| 503 | Service Unavailable | 服务暂时不可用 |

### 常见错误码

#### 认证相关

| 错误码 | HTTP状态 | 说明 | 解决方案 |
|--------|---------|------|---------|
| UNAUTHORIZED | 401 | 缺少或无效的Token | 检查Authorization头，重新登录 |
| TOKEN_EXPIRED | 401 | Token已过期 | 调用刷新接口获取新Token |
| INVALID_CREDENTIALS | 401 | 用户名或密码错误 | 检查输入的用户名和密码 |
| PERMISSION_DENIED | 403 | 无权限执行此操作 | 检查用户权限，联系管理员 |

#### 验证相关

| 错误码 | HTTP状态 | 说明 | 解决方案 |
|--------|---------|------|---------|
| VALIDATION_ERROR | 400 | 字段验证失败 | 检查请求参数，查看details字段 |
| REQUIRED_FIELD | 400 | 缺少必填字段 | 添加缺失的必填字段 |
| INVALID_FORMAT | 400 | 字段格式不正确 | 检查字段格式（如日期、邮箱） |
| FILE_TOO_LARGE | 400 | 文件大小超过限制 | 上传小于2MB的文件 |
| INVALID_FILE_TYPE | 400 | 不支持的文件类型 | 上传jpg/png/gif格式的图片 |

#### 业务相关

| 错误码 | HTTP状态 | 说明 | 解决方案 |
|--------|---------|------|---------|
| NOT_FOUND | 404 | 资源不存在 | 检查资源ID是否正确 |
| INSUFFICIENT_STOCK | 400 | 库存不足 | 减少购买数量或选择其他商品 |
| INVALID_ORDER_STATUS | 400 | 订单状态不允许此操作 | 检查订单当前状态 |
| DUPLICATE_FAVORITE | 409 | 商品已收藏 | 取消收藏后重新添加 |
| BRAND_HAS_PRODUCTS | 400 | 品牌有关联商品 | 先删除关联商品或使用force_delete |

#### 限流相关

| 错误码 | HTTP状态 | 说明 | 解决方案 |
|--------|---------|------|---------|
| RATE_LIMIT_EXCEEDED | 429 | 请求过于频繁 | 等待后重试，查看Retry-After头 |
| LOGIN_RATE_LIMIT | 429 | 登录尝试过于频繁 | 等待5分钟后重试 |
| PAYMENT_RATE_LIMIT | 429 | 支付请求过于频繁 | 等待后重试 |

### 错误响应示例

#### 验证错误

```json
{
  "error": "VALIDATION_ERROR",
  "message": "请求数据验证失败",
  "details": {
    "price": ["价格必须大于0"],
    "stock": ["库存不能为负数"]
  }
}
```

#### 认证错误

```json
{
  "error": "UNAUTHORIZED",
  "message": "无效的认证令牌",
  "details": {
    "reason": "Token已过期，请刷新"
  }
}
```

#### 业务错误

```json
{
  "error": "INSUFFICIENT_STOCK",
  "message": "库存不足",
  "details": {
    "product_id": 123,
    "requested": 10,
    "available": 5
  }
}
```

#### 限流错误

```json
{
  "error": "RATE_LIMIT_EXCEEDED",
  "message": "请求过于频繁，请稍后再试",
  "details": {
    "retry_after": 60
  }
}
```

### 错误处理最佳实践

1. **前端处理**
   - 检查HTTP状态码
   - 根据错误码显示相应的用户提示
   - 对于401错误，自动刷新Token后重试
   - 对于429错误，显示重试倒计时

2. **日志记录**
   - 记录所有5xx错误
   - 记录异常的业务错误
   - 包含请求ID便于追踪

3. **用户提示**
   - 使用用户友好的错误信息
   - 提供解决方案建议
   - 避免暴露技术细节

---

## 使用示例

### 小程序登录流程

```javascript
// 1. 获取微信code
wx.login({
  success: (res) => {
    const code = res.code;
    
    // 2. 调用登录接口
    fetch('/api/login/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code })
    })
    .then(res => res.json())
    .then(data => {
      // 3. 保存token
      localStorage.setItem('access_token', data.access);
      localStorage.setItem('refresh_token', data.refresh);
      // 4. 跳转到首页
      window.location.href = '/';
    });
  }
});
```

### 管理员登录流程

```javascript
// 1. 提交用户名密码
fetch('/api/admin/login/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'admin',
    password: 'password123'
  })
})
.then(res => res.json())
.then(data => {
  // 2. 保存token
  localStorage.setItem('access_token', data.access);
  localStorage.setItem('refresh_token', data.refresh);
  // 3. 跳转到管理后台
  window.location.href = '/admin';
});
```

### API请求示例

```javascript
// 获取商品列表
fetch('/api/products/?search=冰箱&sort_by=sales', {
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
  }
})
.then(res => res.json())
.then(data => {
  // 处理响应数据
});

// 创建订单
fetch('/api/orders/create_order/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
  },
  body: JSON.stringify({
    product_id: 123,
    address_id: 456,
    quantity: 2,
    note: '请尽快发货'
  })
})
.then(res => res.json())
.then(data => {
  // 处理订单数据
});

// Token刷新
fetch('/api/token/refresh/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    refresh: localStorage.getItem('refresh_token')
  })
})
.then(res => res.json())
.then(data => {
  localStorage.setItem('access_token', data.access);
});
```

---

**备注**
- 基础路径为 `/api/`
- 所有需要鉴权的接口都需要在请求头中添加 `Authorization: Bearer <token>`
- 生产环境强制使用 HTTPS
- 所有时间戳均为 ISO 8601 格式（UTC）
- 详细的部署说明请参考 `DEPLOYMENT_GUIDE.md`

---

### ✅ 推荐补充的 API（便于前后端协作与体验提升）

- 商品
  - `POST /products/{id}/media/` 绑定已上传图片到商品的主图或详情图（需要业务约定）

- 购物车
  - `POST /cart/decrement_item/` 减少商品数量（与 `add_item` 对称，当前可用 `update_item` 实现）

- 订单
  - `PATCH /orders/{id}/ship/` 管理员发货（状态置为 `shipped`）
  - `PATCH /orders/{id}/complete/` 完成订单（状态置为 `completed`）
  - `GET /orders/?status=pending|paid|...` 已实现；建议在文档中强调分页参数 `page` / `page_size`

- 支付
  - `GET /payments/?order_id=` 已实现；建议增加第三方回调模拟接口（便于联调）

- 折扣
  - `DELETE /discounts/{id}/targets/{targetId}/` 删除某个适用范围（当前通过规则重建实现，细化更灵活）

- 图片上传
  - 支持多文件上传：`POST /media-images/batch/`（服务器端循环保存）

- 系统
  - `GET /healthz` 健康检查，用于前端部署/CI监测（简单返回 `{status: ok}`）
---


## 当前实现状态（2025-11-18更新）

### ✅ 已完整实现的功能

#### 用户认证与授权
- ✅ `POST /api/login/` - 微信小程序登录
- ✅ `POST /api/password_login/` 或 `/api/admin/login/` - 管理员密码登录
- ✅ `POST /api/token/refresh/` - JWT Token刷新
- ✅ `GET /api/user/profile/` - 获取用户资料
- ✅ `PATCH /api/user/profile/` - 更新用户资料
- ✅ `GET /api/user/statistics/` - 获取用户统计信息

#### 收货地址管理
- ✅ `GET /api/addresses/` - 获取地址列表
- ✅ `POST /api/addresses/` - 创建地址
- ✅ `GET /api/addresses/{id}/` - 获取地址详情
- ✅ `PUT/PATCH /api/addresses/{id}/` - 更新地址
- ✅ `DELETE /api/addresses/{id}/` - 删除地址
- ✅ `POST /api/addresses/{id}/set_default/` - 设为默认地址
- ✅ `POST /api/addresses/parse/` - 地址智能解析

#### 商品管理
- ✅ `GET /api/products/` - 获取商品列表（支持搜索、筛选、排序、分页）
- ✅ `GET /api/products/{id}/` - 获取商品详情
- ✅ `GET /api/products/by_category/?category=名称` - 按分类获取商品
- ✅ `GET /api/products/by_brand/?brand=名称` - 按品牌获取商品
- ✅ `GET /api/products/recommendations/` - 获取推荐商品
- ✅ `GET /api/products/{id}/related/` - 获取相关商品
- ✅ `GET /api/products/search_suggestions/` - 搜索建议
- ✅ `GET /api/products/hot_keywords/` - 热门关键词
- ✅ `POST /api/products/` - 创建商品（管理员）
- ✅ `PUT/PATCH /api/products/{id}/` - 更新商品（管理员）
- ✅ `DELETE /api/products/{id}/` - 删除商品（管理员）

#### 分类管理
- ✅ `GET /api/categories/` - 获取分类列表
- ✅ `GET /api/categories/{id}/` - 获取分类详情
- ✅ `POST /api/categories/` - 创建分类（管理员）
- ✅ `PUT/PATCH /api/categories/{id}/` - 更新分类（管理员）
- ✅ `DELETE /api/categories/{id}/` - 删除分类（管理员）

#### 品牌管理
- ✅ `GET /api/brands/` - 获取品牌列表
- ✅ `GET /api/brands/{id}/` - 获取品牌详情
- ✅ `POST /api/brands/` - 创建品牌（管理员）
- ✅ `PUT/PATCH /api/brands/{id}/` - 更新品牌（管理员）
- ✅ `DELETE /api/brands/{id}/` - 删除品牌（管理员，支持force_delete）

#### 媒体图片管理
- ✅ `GET /api/media-images/` - 获取图片列表
- ✅ `POST /api/media-images/` - 上传图片（支持压缩和格式转换）
- ✅ `GET /api/media-images/{id}/` - 获取图片详情
- ✅ `DELETE /api/media-images/{id}/` - 删除图片

#### 商品收藏
- ✅ `GET /api/favorites/` - 获取收藏列表
- ✅ `POST /api/favorites/` - 添加收藏
- ✅ `POST /api/favorites/toggle/` - 切换收藏状态
- ✅ `GET /api/favorites/check/?product_ids=1,2,3` - 批量检查收藏状态
- ✅ `DELETE /api/favorites/{id}/` - 取消收藏

#### 搜索日志
- ✅ `GET /api/search-logs/` - 获取搜索日志（管理员）
- ✅ `GET /api/search-logs/hot-keywords/` - 获取热门关键词

#### 购物车管理
- ✅ `GET /api/cart/my_cart/` - 获取购物车
- ✅ `POST /api/cart/add_item/` - 添加商品
- ✅ `POST /api/cart/update_item/` - 更新数量
- ✅ `POST /api/cart/remove_item/` - 移除商品
- ✅ `POST /api/cart/clear/` - 清空购物车

#### 订单管理
- ✅ `POST /api/orders/create_order/` - 创建订单
- ✅ `GET /api/orders/my_orders/` - 获取我的订单
- ✅ `GET /api/orders/` - 获取订单列表（支持筛选）
- ✅ `GET /api/orders/{id}/` - 获取订单详情
- ✅ `PATCH /api/orders/{id}/status/` - 更新订单状态
- ✅ `PATCH /api/orders/{id}/cancel/` - 取消订单
- ✅ `PATCH /api/orders/{id}/ship/` - 发货（管理员）
- ✅ `PATCH /api/orders/{id}/complete/` - 完成订单（管理员）

#### 支付管理
- ✅ `GET /api/payments/` - 获取支付记录列表
- ✅ `POST /api/payments/` - 创建支付记录
- ✅ `GET /api/payments/{id}/` - 获取支付详情
- ✅ `POST /api/payments/{id}/start/` - 开始支付
- ✅ `POST /api/payments/{id}/succeed/` - 支付成功
- ✅ `POST /api/payments/{id}/fail/` - 支付失败
- ✅ `POST /api/payments/{id}/cancel/` - 取消支付
- ✅ `POST /api/payments/{id}/expire/` - 支付过期
- ✅ `POST /api/payments/callback/{provider}/` - 支付回调（支持mock和wechat）

#### 折扣系统
- ✅ `GET /api/discounts/` - 获取折扣列表
- ✅ `POST /api/discounts/` - 创建折扣（管理员）
- ✅ `GET /api/discounts/{id}/` - 获取折扣详情
- ✅ `PATCH /api/discounts/{id}/` - 更新折扣（管理员）
- ✅ `DELETE /api/discounts/{id}/` - 删除折扣（管理员）
- ✅ `POST /api/discounts/batch_set/` - 批量设置折扣（管理员）
- ✅ `GET /api/discounts/query_user_products/` - 查询用户商品折扣

#### 数据分析（管理员）
- ✅ `GET /api/analytics/sales_summary/` - 销售汇总统计
- ✅ `GET /api/analytics/top_products/` - 热销商品排行
- ✅ `GET /api/analytics/daily_sales/` - 每日销售统计
- ✅ `GET /api/analytics/user_growth/` - 用户增长统计

#### 供应商集成（管理员）
- ✅ `GET /api/suppliers/` - 获取供应商列表
- ✅ `POST /api/suppliers/` - 创建供应商配置
- ✅ `GET /api/suppliers/{id}/` - 获取供应商详情
- ✅ `PUT/PATCH /api/suppliers/{id}/` - 更新供应商配置
- ✅ `DELETE /api/suppliers/{id}/` - 删除供应商配置
- ✅ `POST /api/suppliers/{id}/test/` - 测试供应商连接
- ✅ `POST /api/supplier-sync/sync-products/` - 同步商品
- ✅ `POST /api/supplier-sync/sync-stock/` - 同步库存
- ✅ `POST /api/supplier-sync/push-order/` - 推送订单
- ✅ `GET /api/supplier-sync/logs/` - 获取同步日志

#### 用户管理（管理员）
- ✅ `GET /api/users/` - 获取用户列表
- ✅ `POST /api/users/` - 创建用户
- ✅ `GET /api/users/{id}/` - 获取用户详情
- ✅ `PUT/PATCH /api/users/{id}/` - 更新用户
- ✅ `DELETE /api/users/{id}/` - 删除用户
- ✅ `POST /api/users/{id}/set_admin/` - 设置为管理员
- ✅ `POST /api/users/{id}/unset_admin/` - 取消管理员

#### 系统功能
- ✅ `GET /healthz` - 健康检查
- ✅ `GET /api/docs/` - API文档（Swagger UI）
- ✅ `GET /api/redoc/` - API文档（ReDoc）
- ✅ `GET /api/schema/` - OpenAPI Schema

### 📊 数据模型完整性

#### Product（商品）模型
- ✅ id, name, description
- ✅ category, brand, category_id, brand_id
- ✅ price, stock
- ✅ main_images, detail_images（JSONField数组）
- ✅ is_active, sales_count, view_count
- ✅ created_at, updated_at
- ✅ discounted_price（计算字段，考虑用户折扣）

#### Category（分类）模型
- ✅ id, name, order
- ✅ created_at, updated_at

#### Brand（品牌）模型
- ✅ id, name, logo, description
- ✅ order, is_active
- ✅ created_at, updated_at

#### MediaImage（媒体图片）模型
- ✅ id, file, original_name
- ✅ content_type, size
- ✅ created_at

#### SearchLog（搜索日志）模型
- ✅ id, keyword, user
- ✅ created_at

#### ProductFavorite（商品收藏）模型
- ✅ id, user, product
- ✅ created_at

#### InventoryLog（库存日志）模型
- ✅ id, product, change_type
- ✅ quantity, reason, created_by
- ✅ created_at

#### Order（订单）模型
- ✅ id, order_number, user, product
- ✅ quantity, total_amount, status, note
- ✅ snapshot_contact_name, snapshot_phone, snapshot_address
- ✅ created_at, updated_at

#### Payment（支付）模型
- ✅ id, order, amount, method, status
- ✅ created_at, updated_at, expires_at, logs

#### Discount（折扣）模型
- ✅ id, name, discount_type, amount, priority
- ✅ effective_time, expiration_time
- ✅ users, products（多对多关系）

### 🎯 API端点总结

**总计**: 80+ 个API端点
- 用户认证: 6个
- 商品管理: 12个
- 分类管理: 5个
- 品牌管理: 5个
- 媒体管理: 4个
- 收藏管理: 5个
- 购物车: 5个
- 订单管理: 8个
- 支付管理: 9个
- 折扣系统: 6个
- 数据分析: 4个
- 供应商集成: 10个
- 用户管理: 7个
- 系统功能: 4个

### 📝 API调用示例

```bash
# 用户认证
curl -X POST http://127.0.0.1:8000/api/login/ \
  -H "Content-Type: application/json" \
  -d '{"code":"test_code"}'

# 获取商品列表（带搜索和筛选）
curl "http://127.0.0.1:8000/api/products/?search=冰箱&category=家电&sort_by=sales&page=1&page_size=20"

# 获取商品详情
curl http://127.0.0.1:8000/api/products/1/

# 创建订单
curl -X POST http://127.0.0.1:8000/api/orders/create_order/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"product_id":1,"address_id":1,"quantity":2}'

# 获取购物车
curl http://127.0.0.1:8000/api/cart/my_cart/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# 上传图片
curl -X POST http://127.0.0.1:8000/api/media-images/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@image.jpg"

# 查看API文档
open http://127.0.0.1:8000/api/docs/
```

### 🔒 权限说明

| 权限类型 | 说明 | 适用端点 |
|---------|------|---------|
| AllowAny | 无需认证 | 商品列表、分类、品牌、健康检查 |
| IsAuthenticated | 需要登录 | 购物车、订单、收藏、用户资料 |
| IsAdminOrReadOnly | 管理员可写，其他只读 | 商品、分类、品牌管理 |
| IsOwnerOrAdmin | 所有者或管理员 | 订单详情、支付记录 |
| IsAdmin | 仅管理员 | 用户管理、数据分析、供应商 |

### 🚀 性能优化

- ✅ 数据库查询优化（select_related, prefetch_related）
- ✅ 缓存机制（用户统计、折扣查询）
- ✅ 数据库索引（所有关键字段）
- ✅ 分页支持（默认20条/页，最大100条）
- ✅ API限流（开发环境无限制，生产环境有限制）

### 🔐 安全特性

- ✅ JWT认证
- ✅ CORS配置
- ✅ XSS防护（SecureCharField）
- ✅ 文件上传验证（类型、大小、内容）
- ✅ SQL注入防护（Django ORM）
- ✅ 限流保护
- ✅ 密码哈希存储

---

**最后更新时间**: 2025-11-18 17:00  
**后端版本**: Django 5.2.7 + DRF 3.16.1  
**当前状态**: ✅ 所有核心功能已完整实现并测试通过
