# 用户模块文档 (users)

## 模块概述

用户模块负责用户认证、授权和用户信息管理，支持微信小程序登录和管理员密码登录两种认证方式。

## 数据模型

### User (用户模型)

继承自Django的AbstractUser，扩展了微信小程序相关字段。

**字段说明：**

| 字段 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | BigAutoField | 主键 | 自增 |
| openid | CharField(64) | 微信OpenID | 唯一，可空 |
| username | CharField(150) | 用户名 | 唯一，自动生成 |
| avatar_url | URLField | 头像URL | 默认Gravatar |
| phone | CharField(20) | 手机号 | 可空 |
| email | EmailField | 电子邮箱 | 可空 |
| user_type | CharField(20) | 用户类型 | wechat/admin |
| last_login_at | DateTimeField | 最后登录时间 | 可空 |
| is_staff | BooleanField | 是否管理员 | 默认False |
| is_superuser | BooleanField | 是否超级用户 | 默认False |

**用户类型：**
- `wechat`: 微信小程序用户
- `admin`: 管理员用户

**自动生成用户名：**
```python
def generate_unique_username():
    import uuid
    return "用户_" + str(uuid.uuid4())[:16]
```

### Address (收货地址模型)

**字段说明：**

| 字段 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | BigAutoField | 主键 | 自增 |
| user | ForeignKey | 用户 | 外键关联User |
| contact_name | CharField(50) | 联系人 | 必填 |
| phone | CharField(20) | 手机号 | 必填 |
| province | CharField(20) | 省份 | 必填 |
| city | CharField(20) | 城市 | 必填 |
| district | CharField(20) | 区县 | 必填 |
| detail | CharField(200) | 详细地址 | 必填 |
| is_default | BooleanField | 是否默认 | 默认False |
| created_at | DateTimeField | 创建时间 | 自动 |

## API端点

### 认证相关

#### 1. 微信小程序登录
```
POST /api/users/wechat-login/
```

**请求参数：**
```json
{
  "code": "微信登录code"
}
```

**响应：**
```json
{
  "access": "JWT access token",
  "refresh": "JWT refresh token",
  "user": {
    "id": 1,
    "username": "用户_abc123",
    "openid": "oXXXX...",
    "avatar_url": "https://...",
    "user_type": "wechat",
    "is_staff": false
  }
}
```

**登录流程：**
1. 前端调用wx.login()获取code
2. 发送code到后端
3. 后端调用微信API验证code
4. 获取openid
5. 创建或获取用户
6. 生成JWT token
7. 返回token和用户信息

**特殊功能：**
- 开发环境：code以'admin'开头自动授予管理员权限
- 未配置微信凭证：使用模拟登录（code直接作为openid）

#### 2. 管理员密码登录
```
POST /api/users/password-login/
```

**请求参数：**
```json
{
  "username": "admin",
  "password": "password123"
}
```

**响应：**
```json
{
  "access": "JWT access token",
  "refresh": "JWT refresh token",
  "user": {
    "id": 1,
    "username": "admin",
    "user_type": "admin",
    "is_staff": true
  }
}
```

**登录规则：**
1. 系统无管理员时，首次登录自动创建管理员
2. 仅管理员用户可登录
3. 非管理员返回403错误
4. 密码错误返回401错误

### 用户资料

#### 3. 获取/更新用户资料
```
GET /api/users/profile/
PATCH /api/users/profile/
```

**权限：** 需要认证

**可更新字段：**
```json
{
  "username": "新用户名",
  "avatar_url": "https://...",
  "phone": "13800138000",
  "email": "user@example.com"
}
```

#### 4. 用户统计信息
```
GET /api/users/statistics/
```

**权限：** 需要认证

**响应：**
```json
{
  "orders_count": 10,
  "completed_orders_count": 8,
  "pending_orders_count": 2,
  "total_spent": 5999.00
}
```

**缓存：** 5分钟

### 收货地址管理

#### 5. 地址列表
```
GET /api/users/addresses/
```

**权限：** 需要认证

**响应：** 数组格式（不分页）
```json
[
  {
    "id": 1,
    "contact_name": "张三",
    "phone": "13800138000",
    "province": "北京市",
    "city": "北京市",
    "district": "朝阳区",
    "detail": "建国路88号",
    "is_default": true
  }
]
```

**排序：** 默认地址优先，然后按ID倒序

#### 6. 创建地址
```
POST /api/users/addresses/
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

**自动处理：**
- 设为默认时，自动取消其他地址的默认状态

#### 7. 更新地址
```
PUT /api/users/addresses/{id}/
PATCH /api/users/addresses/{id}/
```

#### 8. 删除地址
```
DELETE /api/users/addresses/{id}/
```

#### 9. 设置默认地址
```
POST /api/users/addresses/{id}/set_default/
```

**响应：**
```json
{
  "status": "默认地址已设置"
}
```

#### 10. 地址智能解析
```
POST /api/users/addresses/parse/
```

**请求参数：**
```json
{
  "address": "北京市朝阳区建国路88号SOHO现代城A座1001室"
}
```

**响应：**
```json
{
  "success": true,
  "message": "地址解析成功",
  "data": {
    "province": "北京市",
    "city": "北京市",
    "district": "朝阳区",
    "detail": "建国路88号SOHO现代城A座1001室"
  }
}
```

**解析规则：**
- 识别省、市、区
- 提取详细地址
- 支持各种地址格式
- 使用正则表达式匹配

### 管理员用户管理

#### 11. 用户列表（管理员）
```
GET /api/users/admin-users/
```

**权限：** 管理员

**查询参数：**
- `search`: 搜索用户名或OpenID
- `phone`: 按手机号搜索
- `is_staff`: 筛选管理员（true/false）
- `page`: 页码
- `page_size`: 每页数量

#### 12. 创建用户（管理员）
```
POST /api/users/admin-users/
```

**权限：** 管理员

**请求参数：**
```json
{
  "username": "newuser",
  "password": "password123",
  "phone": "13800138000",
  "email": "user@example.com",
  "user_type": "wechat"
}
```

**自动处理：**
- 未提供openid时自动生成
- 密码自动哈希

#### 13. 授予管理员权限
```
POST /api/users/admin-users/{id}/set_admin/
```

**权限：** 管理员

#### 14. 撤销管理员权限
```
POST /api/users/admin-users/{id}/unset_admin/
```

**权限：** 管理员

## 序列化器

### UserSerializer
- 包含所有用户字段
- 计算字段：orders_count, completed_orders_count
- 使用缓存优化性能

### UserProfileSerializer
- 仅包含可编辑字段
- 用于用户资料更新

### AddressSerializer
- 地址完整信息
- 自动关联当前用户
- 处理默认地址逻辑

## 权限控制

### IsAuthenticated
- 用户必须登录
- 用于所有需要认证的端点

### IsOwnerOrAdmin
- 用户只能访问自己的资源
- 管理员可以访问所有资源

### IsAdmin
- 仅管理员可访问
- 用于用户管理端点

## 限流策略

### LoginRateThrottle
- 登录接口：5次/分钟
- 防止暴力破解

### 默认限流
- 匿名用户：20次/分钟
- 认证用户：100次/分钟

## 缓存策略

### 用户统计
- 缓存键：`user_stats_{user_id}`
- 缓存时间：5分钟
- 包含订单统计和消费金额

### 订单计数
- 缓存键：`user_orders_count_{user_id}`
- 缓存时间：5分钟

## 日志记录

### 登录日志
- 记录登录成功/失败
- 包含用户ID、OpenID
- 记录管理员权限授予

### 错误日志
- 微信API调用失败
- 认证失败
- 权限错误

## 安全特性

### 密码安全
- 使用Django的密码哈希
- 支持密码强度验证
- 密码不可逆加密

### Token安全
- JWT Token有效期控制
- Refresh Token轮换
- Token黑名单（可选）

### 数据保护
- 用户只能访问自己的数据
- 管理员操作审计
- 敏感信息脱敏

## 开发环境特性

### 快捷管理员登录
```python
# code以'admin'开头自动授予管理员权限
code = "admin123"  # 自动成为管理员
```

### 模拟登录
- 未配置微信凭证时启用
- code直接作为openid
- 仅用于本地测试

### 首次管理员创建
- 系统无管理员时
- 任意用户名密码登录
- 自动创建管理员账号

## 常见问题

### 1. 微信登录返回401
- 检查code是否有效
- 确认微信配置正确
- 查看日志获取详细错误

### 2. 管理员登录失败
- 确认用户是管理员
- 检查密码是否正确
- 查看is_staff字段

### 3. 地址解析不准确
- 检查地址格式
- 确认包含省市区信息
- 可手动修正解析结果

## 最佳实践

### 用户创建
1. 微信用户自动创建
2. 管理员手动创建
3. 设置合适的user_type

### 地址管理
1. 限制地址数量（建议最多10个）
2. 至少保留一个默认地址
3. 删除前检查是否被订单使用

### 权限管理
1. 谨慎授予管理员权限
2. 定期审查管理员列表
3. 记录权限变更日志
