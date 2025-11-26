# 后端项目概述

## 项目简介

这是一个基于Django和Django REST Framework构建的电商小程序后端系统，专门为海尔家电产品销售设计。

## 技术栈

### 核心框架
- **Django 5.2**: Web框架
- **Django REST Framework**: RESTful API框架
- **Django REST Framework SimpleJWT**: JWT认证
- **drf-spectacular**: API文档自动生成

### 数据库
- **开发环境**: SQLite3
- **生产环境**: PostgreSQL

### 其他依赖
- **django-cors-headers**: CORS跨域支持
- **django-filter**: 查询过滤
- **django-extensions**: Django扩展工具
- **requests**: HTTP客户端（用于海尔API集成）
- **simpleui**: Django Admin美化

## 项目结构

```
backend/
├── backend/              # 项目配置目录
│   ├── settings/        # 分环境配置
│   │   ├── base.py     # 基础配置
│   │   ├── development.py  # 开发环境
│   │   ├── production.py   # 生产环境
│   │   └── env_config.py   # 环境配置管理
│   ├── urls.py          # 主路由配置
│   ├── wsgi.py          # WSGI入口
│   └── asgi.py          # ASGI入口
├── users/               # 用户模块
├── catalog/             # 商品目录模块
├── orders/              # 订单模块
├── integrations/        # 第三方集成（海尔API）
├── common/              # 公共工具模块
├── logs/                # 日志目录
├── media/               # 媒体文件
├── manage.py            # Django管理脚本
└── db.sqlite3           # SQLite数据库（开发环境）
```

## 核心功能模块

### 1. 用户模块 (users)
- 微信小程序登录
- 管理员密码登录
- 用户资料管理
- 收货地址管理
- 地址智能解析

### 2. 商品目录模块 (catalog)
- 商品管理（CRUD）
- 分类管理
- 品牌管理
- 商品搜索
- 收藏功能
- 购物车功能

### 3. 订单模块 (orders)
- 订单创建
- 订单状态管理（状态机）
- 支付集成（微信支付）
- 订单查询和统计
- 订单分析

### 4. 海尔API集成 (integrations)
- OAuth2.0认证
- 商品查询
- 价格查询
- 库存查询
- 物流查询
- 余额查询
- 订单推送（易理货系统）

### 5. 公共工具 (common)
- 统一异常处理
- 日志配置
- 分页器
- 权限控制
- 限流器
- 地址解析器
- 审计日志

## 环境配置

### 开发环境
- DEBUG=True
- SQLite数据库
- CORS允许所有本地域名
- 详细日志输出
- 支持管理员快捷登录

### 生产环境
- DEBUG=False
- PostgreSQL数据库
- 严格的CORS配置
- 限流保护
- SSL/HTTPS强制
- 生产级日志配置

## API文档

### 自动生成文档
- Swagger UI: `/api/docs/`
- ReDoc: `/api/redoc/`
- OpenAPI Schema: `/api/schema/`

### API版本
- v1: `/api/v1/`
- 向后兼容: `/api/`

## 认证方式

### 1. JWT Token认证
- 用于API访问
- Access Token有效期: 7天
- Refresh Token有效期: 30天

### 2. 微信小程序登录
- 通过微信code换取openid
- 自动创建用户
- 返回JWT token

### 3. 管理员密码登录
- 用户名+密码
- 仅限管理员用户
- 返回JWT token

## 数据库模型

### 用户相关
- User: 用户表（支持微信用户和管理员）
- Address: 收货地址表

### 商品相关
- Product: 商品表
- Category: 分类表
- Brand: 品牌表
- ProductImage: 商品图片表
- Favorite: 收藏表
- Cart: 购物车表

### 订单相关
- Order: 订单表
- OrderItem: 订单明细表
- Payment: 支付记录表

### 集成相关
- HaierConfig: 海尔API配置表
- HaierSyncLog: 海尔API同步日志表

## 安全特性

### 认证和授权
- JWT Token认证
- 基于角色的权限控制
- 资源所有权验证

### 数据保护
- 密码哈希存储
- CSRF保护
- XSS防护
- SQL注入防护

### 限流保护
- 登录接口: 5次/分钟
- 支付接口: 10次/分钟
- 匿名用户: 20次/分钟
- 认证用户: 100次/分钟

### 日志审计
- API访问日志
- 错误日志
- 数据库查询日志
- 支付审计日志

## 性能优化

### 缓存策略
- 用户统计缓存（5分钟）
- 商品列表缓存
- 分类树缓存

### 数据库优化
- 索引优化
- 查询优化
- 连接池配置
- 慢查询日志

### 文件存储
- 开发环境: 本地文件系统
- 生产环境: 可配置CDN

## 部署说明

### 环境变量
参考 `.env.example` 文件配置以下变量：
- DJANGO_ENV: 环境标识
- SECRET_KEY: Django密钥
- DATABASE_URL: 数据库连接
- WECHAT_APPID: 微信AppID
- WECHAT_SECRET: 微信密钥
- HAIER_*: 海尔API配置

### 数据库迁移
```bash
python manage.py migrate
```

### 创建超级用户
```bash
python manage.py createsuperuser
```

### 收集静态文件
```bash
python manage.py collectstatic
```

### 运行服务
```bash
# 开发环境
python manage.py runserver

# 生产环境
gunicorn backend.wsgi:application
```

## 健康检查

- 端点: `/healthz`
- 返回: `{"status": "healthy"}`
- 用于负载均衡器健康检查

## 监控和日志

### 日志文件
- `logs/app.log`: 应用日志
- `logs/api.log`: API访问日志
- `logs/error.log`: 错误日志
- `logs/db_queries.log`: 数据库查询日志
- `logs/payment_audit.log`: 支付审计日志

### 日志级别
- 开发环境: DEBUG
- 生产环境: INFO

## 开发指南

### 代码规范
- PEP 8 Python代码规范
- Django最佳实践
- RESTful API设计原则

### 测试
- 单元测试: `python manage.py test`
- API测试: 使用Swagger UI或Postman

### 调试
- Django Debug Toolbar（开发环境）
- 详细错误页面（开发环境）
- 日志文件分析

## 常见问题

### 1. 微信登录失败
- 检查WECHAT_APPID和WECHAT_SECRET配置
- 查看日志文件获取详细错误信息
- 开发环境可使用模拟登录

### 2. 数据库连接失败
- 检查数据库配置
- 确认数据库服务运行
- 检查网络连接

### 3. 静态文件404
- 运行collectstatic命令
- 检查STATIC_ROOT配置
- 确认Web服务器配置

## 更新日志

参考各模块的CHANGELOG.md文件

## 联系方式

- 技术支持: support@example.com
- 文档: 参考各模块README.md
