## 📱 家电电商微信小程序（基于 Taro + React + TypeScript）

### 🎨 设计原则

#### 目标用户
- **主要用户群体**: 家电经销商、批发商、零售商
- **使用场景**: 快速浏览商品、下单采购、管理订单
- **核心需求**: 高效、简洁、易用

#### UI/UX 设计要求

**1. 简洁至上**
- 采用简洁的界面设计，避免过度装饰
- 减少不必要的动画和特效
- 突出核心功能，弱化次要信息
- 使用大量留白，提升可读性

**2. 色彩方案**
- **主色调**: 蓝色系（#1989FA）- 专业、可信赖
- **辅助色**: 灰色系（#F7F8FA, #EBEDF0）- 背景和分割
- **强调色**: 橙色/红色（#FF6034）- 价格、促销、按钮
- **文字色**: 深灰（#323233）、浅灰（#969799）
- 避免使用过多颜色，保持整体统一

**3. 排版规范**
- **字体大小**:
  - 标题: 32-36rpx（加粗）
  - 正文: 28-30rpx
  - 辅助信息: 24-26rpx
  - 价格: 32-40rpx（加粗，橙红色）
- **行间距**: 1.5-1.8倍
- **对齐方式**: 左对齐为主，价格和数字右对齐

**4. 组件使用**
- 使用 Taro 原生组件和自定义组件，保持一致性
- 商品卡片: 简洁的图片 + 标题 + 价格布局
- 按钮: 使用 Taro Button 组件，主要操作用 primary 类型
- 列表: 使用自定义 Cell 组件或原生 View，清晰的分割线
- 表单: 使用 Taro Input/Textarea 组件，简洁的输入框样式

**5. 图片处理**
- 商品图片统一使用 1:1 方形比例
- 图片加载使用占位图，避免闪烁
- 使用 WebP 格式优化加载速度
- 图片圆角: 8rpx

**6. 交互反馈**
- 点击反馈: 使用 hover-class 属性实现点击态
- 加载状态: 使用 Taro.showLoading() 或自定义 Loading 组件
- 操作提示: 使用 Taro.showToast()（简短、清晰）
- 确认操作: 使用 Taro.showModal()（删除、取消订单等）

**7. 页面布局**
- 顶部导航栏: 固定，白色背景，标题居中
- 搜索栏: 圆角矩形，灰色背景，搜索图标
- 商品列表: 双列瀑布流或单列列表
- 底部 TabBar: 固定，4个入口，图标 + 文字

**8. 性能优化**
- 列表使用虚拟滚动（长列表）
- 图片懒加载
- 分页加载，每页 20 条
- 静态数据本地缓存

**9. 避免的设计**
- ❌ 复杂的渐变背景
- ❌ 过多的动画效果
- ❌ 花哨的字体样式
- ❌ 过度的阴影和边框
- ❌ 信息密集的页面
- ❌ 不必要的弹窗和引导

**10. 参考风格**
- 京东批发、1688 的简洁风格
- 以功能为导向，而非视觉炫技
- 快速加载，流畅操作

---

### 🔧 API 配置
- **Base URL**: `http://127.0.0.1:8000/api/`（开发环境）
- **认证方式**: JWT Token，在请求头添加 `Authorization: Bearer <access_token>`
- **响应格式**: JSON
- **时间格式**: ISO 8601（UTC）

---

### 🧭 底部导航栏（TabBar）
固定于页面底部，包含 4 个入口：
- **首页** (`/pages/home/index`)
- **分类** (`/pages/category/index`)
- **购物车** (`/pages/cart/index`)
- **我的** (`/pages/profile/index`)

---

### 🔐 登录流程

#### 微信小程序登录
**API**: `POST /login/`
- **权限**: AllowAny
- **请求体**: 
  ```json
  { "code": "微信登录code" }
  ```
- **响应**:
  ```json
  {
    "access": "访问令牌（15分钟有效）",
    "refresh": "刷新令牌（7天有效）",
    "user": {
      "id": 1,
      "username": "用户_xxx",
      "avatar_url": "头像URL",
      "phone": "手机号",
      "email": "邮箱",
      "user_type": "wechat"
    }
  }
  ```
- **限流**: 5次/分钟

#### Token 刷新
**API**: `POST /token/refresh/`
- **请求体**: 
  ```json
  { "refresh": "刷新令牌" }
  ```
- **响应**:
  ```json
  { "access": "新的访问令牌" }
  ```

#### 实现流程
1. 调用 `wx.login()` 获取微信 code
2. 将 code 发送到后端 `/login/` 接口
3. 保存返回的 `access` 和 `refresh` token
4. 后续请求在 header 中携带 `Authorization: Bearer <access_token>`
5. 当 access token 过期（401错误）时，使用 refresh token 刷新

---

### 🔍 通用头部（首页 & 分类页）

#### 搜索功能
- 顶部固定 **搜索栏**，支持关键词输入与搜索功能
- **API**: `GET /products/?search={keyword}`
- **权限**: AllowAny
- **查询参数**:
  - `search`: 搜索关键词（模糊匹配商品名称和描述）
  - `page`: 页码（默认1）
  - `page_size`: 每页数量（默认20）

#### 热门搜索关键词
**API**: `GET /search/hot_keywords/`
- **权限**: AllowAny
- **查询参数**: `limit` (默认10)
- **响应**:
  ```json
  [
    { "keyword": "冰箱", "count": 156 },
    { "keyword": "空调", "count": 142 }
  ]
  ```

---

### 🏠 首页（Home）

页面自上而下分为四个模块：

#### 1. 轮播广告图
- 自动轮播，支持点击跳转商品/活动页
- 数据来源：前端配置或后端管理（待扩展）

#### 2. 品类导航
**API**: `GET /categories/`
- **权限**: AllowAny
- **响应**:
  ```json
  [
    { "id": 1, "name": "空调", "order": 1 },
    { "id": 2, "name": "冰箱", "order": 2 },
    { "id": 3, "name": "洗衣机", "order": 3 }
  ]
  ```
- 横向滚动图标列表，点击进入对应分类
- 图标资源：前端本地配置

#### 3. 品牌专区
**API**: `GET /brands/`
- **权限**: AllowAny
- **响应**:
  ```json
  [
    {
      "id": 1,
      "name": "海尔",
      "logo": "品牌Logo URL",
      "description": "品牌描述",
      "order": 1,
      "is_active": true
    }
  ]
  ```
- 展示热门家电品牌 Logo，支持点击跳转品牌专区
- 点击后调用: `GET /products/by_brand/?brand={品牌名}`

#### 4. 全部商品列表
**API**: `GET /products/`
- **权限**: AllowAny
- **查询参数**: 
  - `page`: 页码（默认1）
  - `page_size`: 每页数量（默认20）
  - `sort_by`: 排序方式（可选）
    - `sales`: 按销量排序
    - `price_asc`: 价格从低到高
    - `price_desc`: 价格从高到低
    - `created`: 按创建时间排序
- **响应**: 
  ```json
  {
    "results": [
      {
        "id": 1,
        "name": "海尔冰箱",
        "price": "2999.00",
        "main_images": ["图片URL"],
        "brand": "海尔",
        "category": "冰箱",
        "sales_count": 1234
      }
    ],
    "total": 100,
    "page": 1,
    "total_pages": 5,
    "has_next": true,
    "has_previous": false
  }
  ```
- 支持分页加载，每项包含：图片、名称、价格、品牌
- 下拉刷新重新加载第一页
- 上拉加载更多（page + 1）

---

### 🗂️ 分类页（Category）

采用 **左侧分类 + 右侧商品列表** 布局：

#### 左侧分类菜单
**API**: `GET /categories/`
- 垂直分类菜单，高亮当前选中项
- 第一项是全部

#### 右侧商品列表
**API**: `GET /products/by_category/?category={分类名}`
- **权限**: AllowAny
- **查询参数**:
  - `category`: 分类名称（必填）
  - `sort_by`: 排序方式
    - `relevance`: 默认（综合）
    - `sales`: 销量从高到低
    - `price_asc`: 价格从低到高
    - `price_desc`: 价格从高到低
  - `page`: 页码
  - `page_size`: 每页数量

#### 排序功能
位于商品列表顶部，支持按以下维度排序：
- 默认（综合）: `sort_by=relevance`
- 销量从高到低: `sort_by=sales`
- 价格从低到高: `sort_by=price_asc`
- 价格从高到低: `sort_by=price_desc`

---

### 🛒 购物车（Cart）

> **注意**: 所有购物车操作需要登录（IsAuthenticated）

#### 获取购物车
**API**: `GET /cart/my_cart/`
- **权限**: IsAuthenticated
- **响应**:
  ```json
  {
    "id": 10,
    "user": 1,
    "items": [
      {
        "id": 99,
        "product": {
          "id": 1,
          "name": "海尔冰箱",
          "price": "2999.00",
          "main_images": ["图片URL"],
          "stock": 50
        },
        "product_id": 1,
        "quantity": 2
      }
    ]
  }
  ```

#### 添加商品到购物车
**API**: `POST /cart/add_item/`
- **请求体**:
  ```json
  {
    "product_id": 1,
    "quantity": 1  // 可选，默认1
  }
  ```
- **说明**: 如果商品已存在，数量会累加

#### 更新商品数量
**API**: `POST /cart/update_item/`
- **请求体**:
  ```json
  {
    "product_id": 1,
    "quantity": 3  // 设置为精确数量，<=0 时移除商品
  }
  ```

#### 移除商品
**API**: `POST /cart/remove_item/`
- **请求体**:
  ```json
  { "product_id": 1 }
  ```

#### 清空购物车
**API**: `POST /cart/clear/`
- **响应**:
  ```json
  { "message": "购物车已清空" }
  ```

#### 功能支持
- 勾选/取消商品（前端状态管理）
- 修改商品数量（调用 `update_item`）
- 删除商品（调用 `remove_item`）
- 全选/取消全选（前端状态管理）
- 结算按钮（跳转订单确认页）

---

### 👤 我的（Profile）

#### 未登录状态
- 显示默认头像
- "立即登录" 按钮（跳转登录页）

#### 已登录状态

##### 获取用户信息
**API**: `GET /user/profile/`
- **权限**: IsAuthenticated
- **响应**:
  ```json
  {
    "id": 1,
    "username": "用户昵称",
    "avatar_url": "头像URL",
    "phone": "手机号",
    "email": "邮箱",
    "user_type": "wechat",
    "last_login_at": "2025-11-16T10:30:00Z",
    "orders_count": 15,
    "favorites_count": 8
  }
  ```

##### 更新用户信息
**API**: `PATCH /user/profile/`
- **请求体**:
  ```json
  {
    "username": "新昵称",
    "avatar_url": "新头像URL",
    "phone": "新手机号",
    "email": "新邮箱"
  }
  ```

##### 功能入口
- **我的订单**: 跳转到订单列表页
  - API: `GET /orders/my_orders/`
  - 支持按状态筛选: `?status=pending|paid|shipped|completed|cancelled`
  
- **收货地址管理**: 跳转到地址管理页
  - 获取地址列表: `GET /addresses/`
  - 创建地址: `POST /addresses/`
  - 更新地址: `PUT/PATCH /addresses/{id}/`
  - 删除地址: `DELETE /addresses/{id}/`
  - 设为默认: `POST /addresses/{id}/set_default/`

- **我的收藏**: 跳转到收藏列表页
  - API: `GET /favorites/`

---

### 📦 商品详情页（Product Detail）

#### 获取商品详情
**API**: `GET /products/{id}/`
- **权限**: AllowAny
- **响应**:
  ```json
  {
    "id": 1,
    "name": "海尔冰箱 BCD-500WDPF",
    "category": "冰箱",
    "brand": "海尔",
    "price": "2999.00",
    "stock": 50,
    "description": "商品描述",
    "main_images": ["主图URL1", "主图URL2"],
    "detail_images": ["详情图URL1", "详情图URL2"],
    "specifications": {
      "颜色": "银色",
      "容量": "500L",
      "能效等级": "一级"
    },
    "is_active": true,
    "sales_count": 1234,
    "view_count": 5678,
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-11-16T10:00:00Z"
  }
  ```

#### 获取用户折扣价（已登录）
**API**: `GET /products/with_discounts/?product_ids={id}`
- **权限**: IsAuthenticated
- **响应**:
  ```json
  {
    "1": {
      "price": "2999.00",
      "discounted_price": "2699.00",
      "discount_id": 123
    }
  }
  ```

#### 页面元素
- 商品主图（支持放大查看，轮播展示 `main_images`）
- 商品名称、价格、促销信息
- 规格选择（从 `specifications` 字段解析）
- "加入购物车" 按钮（调用 `POST /cart/add_item/`）
- "立即购买" 按钮（跳转订单确认页）
- 商品详情描述（展示 `detail_images`，支持长内容滚动）
- 收藏按钮（调用 `POST /favorites/`）

---

### 📋 订单确认页（Order Confirm）

#### 页面元素
- 收货地址选择（调用 `GET /addresses/`）
- 商品信息（名称、规格、数量、价格）
- 订单备注输入框
- 总价计算
- "提交订单" 按钮

#### 创建订单
**API**: `POST /orders/create_order/`
- **权限**: IsAuthenticated
- **请求体**:
  ```json
  {
    "product_id": 1,
    "address_id": 5,
    "quantity": 2,
    "note": "请尽快发货"
  }
  ```
- **响应**:
  ```json
  {
    "order": {
      "id": 100,
      "user": 1,
      "product": { /* 商品信息 */ },
      "quantity": 2,
      "total_amount": "5998.00",
      "status": "pending",
      "note": "请尽快发货",
      "created_at": "2025-11-16T10:30:00Z"
    },
    "payment": {
      "id": 200,
      "order": 100,
      "amount": "5998.00",
      "method": "wechat",
      "status": "pending",
      "expires_at": "2025-11-16T11:00:00Z"
    }
  }
  ```
- **说明**: 
  - 自动创建支付记录，默认过期30分钟
  - 库存自动锁定
  - 库存不足返回 `400 BAD_REQUEST`

---

### 💳 支付页面（Payment）

#### 发起支付
**API**: `POST /payments/{id}/start/`
- **权限**: IsOwnerOrAdmin
- **响应**: 支付记录状态更新为 `processing`

#### 支付回调（模拟）
**API**: `POST /payments/callback/mock/`
- **权限**: AllowAny
- **请求体**:
  ```json
  {
    "payment_id": 200,
    "status": "succeeded",
    "transaction_id": "MOCK-2025-0001"
  }
  ```
- **说明**: 开发环境用于模拟支付成功/失败

#### 支付状态
- `pending`: 待支付
- `processing`: 处理中
- `succeeded`: 成功（订单状态自动更新为 `paid`）
- `failed`: 失败
- `cancelled`: 已取消
- `expired`: 已过期（订单自动取消，库存释放）

---

### 📦 订单列表页（Order List）

#### 获取订单列表
**API**: `GET /orders/my_orders/`
- **权限**: IsAuthenticated
- **查询参数**: 
  - `status`: 订单状态筛选
    - `pending`: 待支付
    - `paid`: 已支付
    - `shipped`: 已发货
    - `completed`: 已完成
    - `cancelled`: 已取消
    - `refunding`: 退款中
    - `refunded`: 已退款
  - `page`: 页码
  - `page_size`: 每页数量

#### 订单详情
**API**: `GET /orders/{id}/`
- **权限**: IsOwnerOrAdmin
- **响应**: 包含订单详情和状态历史

#### 取消订单
**API**: `PATCH /orders/{id}/cancel/`
- **权限**: IsOwnerOrAdmin
- **说明**: 仅待支付和已支付状态可取消，库存自动释放

---

### ❤️ 收藏列表页（Favorites）

#### 获取收藏列表
**API**: `GET /favorites/`
- **权限**: IsAuthenticated
- **响应**:
  ```json
  [
    {
      "id": 1,
      "product": { /* 商品完整信息 */ },
      "created_at": "2025-11-16T10:00:00Z"
    }
  ]
  ```

#### 添加收藏
**API**: `POST /favorites/`
- **请求体**:
  ```json
  { "product_id": 1 }
  ```
- **错误**: 商品已收藏返回 `400 BAD_REQUEST`

#### 取消收藏
**API**: `DELETE /favorites/{product_id}/`
- **响应**:
  ```json
  { "message": "已取消收藏" }
  ```

---

### 📍 收货地址管理（Address Management）

#### 获取地址列表
**API**: `GET /addresses/`
- **权限**: IsAuthenticated

#### 创建地址
**API**: `POST /addresses/`
- **请求体**:
  ```json
  {
    "contact_name": "张三",
    "phone": "13800138000",
    "province": "广东省",
    "city": "深圳市",
    "district": "南山区",
    "detail": "科技园南区XX路XX号",
    "is_default": false
  }
  ```

#### 更新地址
**API**: `PUT/PATCH /addresses/{id}/`

#### 删除地址
**API**: `DELETE /addresses/{id}/`

#### 设为默认地址
**API**: `POST /addresses/{id}/set_default/`

---

### 🖼️ 图片上传（Image Upload）

#### 上传图片
**API**: `POST /media-images/`
- **权限**: IsAuthenticated
- **请求**: multipart/form-data，字段名 `file`
- **限制**:
  - 支持格式: `image/jpeg`, `image/png`, `image/gif`
  - 文件大小: ≤ 2MB
- **响应**:
  ```json
  {
    "id": 1,
    "url": "图片访问URL",
    "original_name": "原始文件名",
    "content_type": "image/jpeg",
    "size": 1024000,
    "created_at": "2025-11-16T10:00:00Z"
  }
  ```

---

### ⚠️ 错误处理

#### 统一错误格式
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

#### 常见错误码
| 状态码 | 错误码 | 说明 | 处理方式 |
|--------|--------|------|---------|
| 401 | UNAUTHORIZED | Token无效或过期 | 刷新Token或重新登录 |
| 403 | FORBIDDEN | 无权限 | 提示用户权限不足 |
| 404 | NOT_FOUND | 资源不存在 | 提示资源不存在 |
| 429 | RATE_LIMIT_EXCEEDED | 请求过于频繁 | 显示重试倒计时 |
| 400 | INSUFFICIENT_STOCK | 库存不足 | 提示库存不足 |
| 400 | VALIDATION_ERROR | 参数验证失败 | 显示具体字段错误 |

#### 前端处理建议
1. 401错误：自动调用 `POST /token/refresh/` 刷新Token后重试
2. 429错误：根据 `Retry-After` 头显示倒计时
3. 网络错误：显示友好提示，提供重试按钮
4. 业务错误：根据 `message` 字段显示具体错误信息

---

### 🔒 请求限流

| 用户类型 | 限制 | 说明 |
|---------|------|------|
| 匿名用户 | 20次/分钟 | 生产环境 |
| 认证用户 | 100次/分钟 | 生产环境 |
| 登录接口 | 5次/分钟 | 防止暴力破解 |
| 支付接口 | 10次/分钟 | 防止重复支付 |
| 开发环境 | 无限制 | 便于调试 |

---

### 📄 分页规范

所有列表接口支持分页：

**查询参数**:
- `page`: 页码（默认1）
- `page_size`: 每页数量（默认20，最大100）

**响应格式**:
```json
{
  "results": [ /* 数据列表 */ ],
  "total": 100,
  "page": 1,
  "total_pages": 5,
  "has_next": true,
  "has_previous": false
}
```

补充约定：
- 下拉框/统计类页面如需“全量数据”，使用 `frontend/src/utils/request.ts:228` 的 `fetchAllPaginated` 拉取所有分页

---

### 🎯 开发建议

1. **Token管理**: 
   - 使用拦截器统一处理Token添加和刷新
   - Token存储使用 `wx.setStorageSync()`

2. **错误处理**: 
   - 统一错误处理中间件
   - 根据错误码显示不同提示

3. **加载状态**: 
   - 使用 `wx.showLoading()` 显示加载状态
   - 请求完成后调用 `wx.hideLoading()`

4. **数据缓存**: 
   - 分类、品牌等静态数据可缓存
   - 使用 `wx.setStorage()` 本地缓存

5. **图片优化**: 
   - 使用 `mode="aspectFill"` 保持比例
   - 懒加载优化性能

6. **支付集成**: 
   - 开发环境使用 mock 回调测试
   - 生产环境集成微信支付SDK

---
