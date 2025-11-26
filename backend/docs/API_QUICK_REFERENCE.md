# API快速参考

## 基础信息

### Base URL
- 开发环境: `http://localhost:8000`
- 生产环境: `https://your-domain.com`

### API版本
- v1: `/api/v1/`
- 向后兼容: `/api/`

### 认证方式
```
Authorization: Bearer <JWT_TOKEN>
```

### 响应格式
所有API返回JSON格式数据

## 认证接口

### 微信小程序登录
```http
POST /api/users/wechat-login/
Content-Type: application/json

{
  "code": "微信登录code"
}
```

### 管理员密码登录
```http
POST /api/users/password-login/
Content-Type: application/json

{
  "username": "admin",
  "password": "password123"
}
```

## 用户接口

### 获取用户资料
```http
GET /api/users/profile/
Authorization: Bearer <token>
```

### 更新用户资料
```http
PATCH /api/users/profile/
Authorization: Bearer <token>
Content-Type: application/json

{
  "username": "新用户名",
  "phone": "13800138000"
}
```

### 用户统计
```http
GET /api/users/statistics/
Authorization: Bearer <token>
```

## 地址接口

### 地址列表
```http
GET /api/users/addresses/
Authorization: Bearer <token>
```

### 创建地址
```http
POST /api/users/addresses/
Authorization: Bearer <token>
Content-Type: application/json

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

### 地址解析
```http
POST /api/users/addresses/parse/
Authorization: Bearer <token>
Content-Type: application/json

{
  "address": "北京市朝阳区建国路88号"
}
```

## 商品接口

### 商品列表
```http
GET /api/products/?page=1&page_size=20
```

**查询参数：**
- `page`: 页码
- `page_size`: 每页数量
- `category`: 分类ID
- `brand`: 品牌ID
- `search`: 搜索关键词
- `min_price`: 最低价格
- `max_price`: 最高价格
- `ordering`: 排序（price, -price, sales, -sales）

### 商品详情
```http
GET /api/products/{id}/
```

### 分类列表
```http
GET /api/categories/
```

### 品牌列表
```http
GET /api/brands/
```

### 商品搜索
```http
GET /api/products/search/?q=关键词
```

## 收藏接口

### 收藏列表
```http
GET /api/favorites/
Authorization: Bearer <token>
```

### 添加收藏
```http
POST /api/favorites/
Authorization: Bearer <token>
Content-Type: application/json

{
  "product": 1
}
```

### 取消收藏
```http
DELETE /api/favorites/{id}/
Authorization: Bearer <token>
```

### 检查收藏状态
```http
GET /api/favorites/check/?product_id=1
Authorization: Bearer <token>
```

## 购物车接口

### 购物车列表
```http
GET /api/cart/
Authorization: Bearer <token>
```

### 添加到购物车
```http
POST /api/cart/
Authorization: Bearer <token>
Content-Type: application/json

{
  "product": 1,
  "quantity": 2
}
```

### 更新购物车
```http
PATCH /api/cart/{id}/
Authorization: Bearer <token>
Content-Type: application/json

{
  "quantity": 3
}
```

### 删除购物车项
```http
DELETE /api/cart/{id}/
Authorization: Bearer <token>
```

### 清空购物车
```http
POST /api/cart/clear/
Authorization: Bearer <token>
```

## 订单接口

### 订单列表
```http
GET /api/orders/?status=pending
Authorization: Bearer <token>
```

**查询参数：**
- `status`: 订单状态（pending, paid, shipped, completed, cancelled）
- `page`: 页码
- `page_size`: 每页数量

### 创建订单
```http
POST /api/orders/
Authorization: Bearer <token>
Content-Type: application/json

{
  "address": 1,
  "items": [
    {
      "product": 1,
      "quantity": 2
    }
  ],
  "remark": "备注信息"
}
```

### 订单详情
```http
GET /api/orders/{id}/
Authorization: Bearer <token>
```

### 取消订单
```http
POST /api/orders/{id}/cancel/
Authorization: Bearer <token>
Content-Type: application/json

{
  "reason": "取消原因"
}
```

### 确认收货
```http
POST /api/orders/{id}/confirm/
Authorization: Bearer <token>
```

### 订单统计
```http
GET /api/orders/statistics/
Authorization: Bearer <token>
```

## 支付接口

### 创建支付
```http
POST /api/payments/
Authorization: Bearer <token>
Content-Type: application/json

{
  "order": 1,
  "payment_method": "wechat"
}
```

### 支付回调
```http
POST /api/payments/wechat-callback/
Content-Type: application/json

{
  "out_trade_no": "订单号",
  "transaction_id": "微信交易号",
  "result_code": "SUCCESS"
}
```

### 查询支付状态
```http
GET /api/payments/{id}/status/
Authorization: Bearer <token>
```

## 海尔API接口

### 查询商品
```http
GET /api/haier/api/products/?product_codes=GA0SZC00U,EC6001-HT3
Authorization: Bearer <token>
```

### 查询价格
```http
GET /api/haier/api/prices/?product_codes=GA0SZC00U
Authorization: Bearer <token>
```

### 查询库存
```http
GET /api/haier/api/stock/?product_code=GA0SZC00U&county_code=110101
Authorization: Bearer <token>
```

### 查询余额
```http
GET /api/haier/api/balance/
Authorization: Bearer <token>
```

### 查询物流
```http
GET /api/haier/api/logistics/?order_code=SO.20190106.000003
Authorization: Bearer <token>
```

## 管理员接口

### 用户管理
```http
GET /api/users/admin-users/?search=关键词&is_staff=true
Authorization: Bearer <admin_token>
```

### 商品管理
```http
POST /api/products/
Authorization: Bearer <admin_token>
Content-Type: multipart/form-data

{
  "name": "商品名称",
  "price": 999.00,
  "category": 1,
  "brand": 1,
  "description": "商品描述",
  "stock": 100,
  "image": <file>
}
```

### 订单管理
```http
GET /api/orders/admin-orders/
Authorization: Bearer <admin_token>
```

## 错误码

### HTTP状态码
- `200`: 成功
- `201`: 创建成功
- `204`: 删除成功
- `400`: 请求参数错误
- `401`: 未认证
- `403`: 无权限
- `404`: 资源不存在
- `429`: 请求过于频繁
- `500`: 服务器错误

### 业务错误码
```json
{
  "error": "错误信息",
  "code": "ERROR_CODE",
  "details": {}
}
```

## 分页响应格式

```json
{
  "count": 100,
  "next": "http://api.example.com/api/products/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "商品名称"
    }
  ]
}
```

## 限流规则

- 登录接口: 5次/分钟
- 支付接口: 10次/分钟
- 匿名用户: 20次/分钟
- 认证用户: 100次/分钟

## 常用查询参数

### 分页
- `page`: 页码（默认1）
- `page_size`: 每页数量（默认20）

### 排序
- `ordering`: 排序字段
  - 升序: `field`
  - 降序: `-field`
  - 多字段: `field1,-field2`

### 搜索
- `search`: 搜索关键词
- `q`: 搜索关键词（别名）

### 过滤
- `field`: 精确匹配
- `field__contains`: 包含
- `field__gte`: 大于等于
- `field__lte`: 小于等于

## 请求示例

### cURL
```bash
curl -X GET "http://localhost:8000/api/products/" \
  -H "Authorization: Bearer <token>"
```

### JavaScript (Fetch)
```javascript
fetch('http://localhost:8000/api/products/', {
  headers: {
    'Authorization': 'Bearer ' + token
  }
})
.then(response => response.json())
.then(data => {
  // 处理响应数据
});
```

### Python (Requests)
```python
import requests

headers = {
    'Authorization': f'Bearer {token}'
}
response = requests.get(
    'http://localhost:8000/api/products/',
    headers=headers
)
data = response.json()
```

## 测试工具

### Swagger UI
```
http://localhost:8000/api/docs/
```

### ReDoc
```
http://localhost:8000/api/redoc/
```

### Postman Collection
导出OpenAPI Schema:
```
http://localhost:8000/api/schema/
```

## 开发技巧

### 获取Token
1. 调用登录接口
2. 保存返回的access token
3. 在后续请求中携带token

### 刷新Token
```http
POST /api/token/refresh/
Content-Type: application/json

{
  "refresh": "<refresh_token>"
}
```

### 调试模式
开发环境下，可以在浏览器中直接访问API端点查看可浏览的API界面。

### 错误处理
```javascript
fetch(url, options)
  .then(response => {
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    return response.json();
  })
  .catch(error => {
    console.error('API Error:', error);
  });
```

## 性能优化建议

### 1. 使用分页
避免一次性加载大量数据

### 2. 使用缓存
对不常变化的数据使用缓存

### 3. 减少请求
合并多个请求为一个

### 4. 压缩响应
启用gzip压缩

### 5. 使用CDN
静态资源使用CDN加速

## 安全建议

### 1. HTTPS
生产环境必须使用HTTPS

### 2. Token安全
- 不要在URL中传递token
- 定期刷新token
- 安全存储token

### 3. 输入验证
- 验证所有用户输入
- 防止SQL注入
- 防止XSS攻击

### 4. 限流
- 遵守API限流规则
- 实现指数退避重试

## 更新日志

查看各模块的CHANGELOG.md文件了解API变更历史。
