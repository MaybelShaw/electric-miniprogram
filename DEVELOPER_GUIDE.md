# 家电商城系统 - 开发者技术文档

> 📘 本文档面向开发者，详细介绍系统架构、技术栈、开发流程和最佳实践

---

## 📑 目录

- [项目概述](#项目概述)
- [技术架构](#技术架构)
- [项目结构](#项目结构)
- [技术栈详解](#技术栈详解)
- [开发环境搭建](#开发环境搭建)
- [核心功能模块](#核心功能模块)
- [API接口文档](#api接口文档)
- [数据库设计](#数据库设计)
- [第三方集成](#第三方集成)
- [部署指南](#部署指南)
- [开发规范](#开发规范)
- [常见问题](#常见问题)

---

## 项目概述

**家电商城系统**是一个全栈电商解决方案，由三个核心子系统组成：

1. **Backend (后端API)** - Django REST Framework构建的高性能API服务
2. **Frontend (用户端)** - Taro多端小程序应用
3. **Merchant (商户管理)** - React + Ant Design Pro管理后台

### 系统亮点

✅ **微服务架构** - 前后端完全分离，API优先设计  
✅ **多端支持** - 一套代码编译多个小程序平台（微信、支付宝、抖音等）  
✅ **海尔API集成** - 深度对接海尔智能家电生态系统  
✅ **完善的订单流** - 从下单到配送安装的全生命周期管理  
✅ **灵活的折扣系统** - 支持用户级、商品级精准营销  
✅ **企业级安全** - JWT认证、限流保护、输入验证

---

## 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                      用户层                              │
├──────────────┬──────────────┬─────────────────────────┤
│  微信小程序   │  支付宝小程序  │   H5 Web应用            │
│  (Taro)      │   (Taro)     │    (Taro)               │
└──────┬───────┴──────┬───────┴──────┬──────────────────┘
       │              │              │
       └──────────────┴──────────────┘
                      │
          ┌───────────▼───────────┐
          │   Nginx 反向代理       │
          └───────────┬───────────┘
                      │
       ┌──────────────┴──────────────┐
       │                              │
┌──────▼──────┐            ┌─────────▼────────┐
│  Django API  │            │  React Admin     │
│  (Backend)   │            │   (Merchant)     │
└──────┬───────┘            └──────────────────┘
       │
       ├─────── PostgreSQL/SQLite (数据库)
       │
       ├─────── Redis (缓存)
       │
       └─────── 第三方服务
                ├── 微信支付
                ├── 海尔智能家电API
                └── 物流查询服务
```

### 数据流架构

```
用户操作 → 小程序/管理后台 → API Gateway → 业务逻辑层 → 数据访问层 → 数据库
                                ↓
                          第三方服务集成
                          (海尔API/微信支付)
```

---

## 项目结构

```
electric-miniprogram/
│
├── backend/                    # Django后端API服务
│   ├── backend/               # 项目配置
│   │   ├── settings/         # 多环境配置
│   │   │   ├── base.py      # 基础配置
│   │   │   ├── development.py  # 开发环境
│   │   │   ├── production.py   # 生产环境
│   │   │   └── env_config.py   # 环境变量加载
│   │   ├── urls.py           # 全局路由
│   │   └── wsgi.py           # WSGI入口
│   │
│   ├── users/                 # 用户模块
│   │   ├── models.py         # User, Address模型
│   │   ├── views.py          # 认证、用户管理视图
│   │   ├── serializers.py    # 数据序列化
│   │   └── services.py       # 业务逻辑
│   │
│   ├── catalog/               # 商品目录模块
│   │   ├── models.py         # Product, Category, Brand模型
│   │   ├── views.py          # 商品CRUD、搜索
│   │   ├── serializers.py    # 商品序列化
│   │   ├── search.py         # 搜索服务
│   │   └── storage.py        # 文件存储
│   │
│   ├── orders/                # 订单模块
│   │   ├── models.py         # Order, Cart, Payment模型
│   │   ├── views.py          # 订单管理
│   │   ├── services.py       # 订单业务逻辑
│   │   ├── state_machine.py  # 订单状态机
│   │   ├── payment_service.py # 支付服务
│   │   └── analytics.py      # 数据分析
│   │
│   ├── integrations/          # 第三方集成模块
│   │   ├── models.py         # HaierConfig, HaierSyncLog
│   │   ├── haierapi.py       # 海尔API封装
│   │   ├── ylhapi.py         # YLH系统API封装
│   │   └── views.py          # 集成管理接口
│   │
│   ├── common/                # 公共模块
│   │   ├── permissions.py    # 权限类
│   │   ├── serializers.py    # 通用序列化器
│   │   ├── pagination.py     # 分页配置
│   │   ├── throttles.py      # 限流配置
│   │   ├── exceptions.py     # 异常处理
│   │   ├── logging_config.py # 日志配置
│   │   └── health.py         # 健康检查
│   │
│   ├── manage.py              # Django命令行工具
│   ├── pyproject.toml         # Python依赖配置
│   └── uv.lock                # 依赖锁定文件
│
├── frontend/                  # Taro小程序前端
│   ├── src/
│   │   ├── pages/            # 页面组件
│   │   │   ├── home/        # 首页
│   │   │   ├── category/    # 分类
│   │   │   ├── cart/        # 购物车
│   │   │   ├── profile/     # 个人中心
│   │   │   ├── product-detail/  # 商品详情
│   │   │   ├── order-list/      # 订单列表
│   │   │   └── ...
│   │   ├── components/       # 公共组件
│   │   ├── services/         # API服务封装
│   │   ├── utils/            # 工具函数
│   │   ├── types/            # TypeScript类型定义
│   │   └── app.config.ts     # 应用配置
│   ├── config/               # 环境配置
│   │   ├── dev.ts           # 开发环境
│   │   └── prod.ts          # 生产环境
│   ├── package.json
│   └── tsconfig.json
│
├── merchant/                  # React商户管理后台
│   ├── src/
│   │   ├── pages/            # 页面
│   │   │   ├── Products/    # 商品管理
│   │   │   ├── Orders/      # 订单管理
│   │   │   ├── Users/       # 用户管理
│   │   │   ├── Brands/      # 品牌管理
│   │   │   ├── Categories/  # 分类管理
│   │   │   └── Discounts/   # 折扣管理
│   │   ├── components/       # 公共组件
│   │   ├── services/         # API服务
│   │   └── utils/            # 工具函数
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
│
└── docs/                      # 文档目录
    ├── DEVELOPER_GUIDE.md    # 本文档
    ├── USER_INTRODUCTION.md  # 用户介绍
    └── API_REFERENCE.md      # API参考
```

---

## 技术栈详解

### 后端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| **Python** | 3.12+ | 编程语言 |
| **Django** | 5.2+ | Web框架 |
| **Django REST Framework** | 3.16+ | RESTful API框架 |
| **djangorestframework-simplejwt** | 5.5+ | JWT认证 |
| **drf-spectacular** | 0.27+ | OpenAPI文档生成 |
| **PostgreSQL** | 14+ | 生产数据库 |
| **SQLite** | 3.x | 开发数据库 |
| **Redis** | 6+ | 缓存（可选） |
| **uv** | 最新 | Python包管理器 |

### 前端技术栈（用户端）

| 技术 | 版本 | 用途 |
|------|------|------|
| **Taro** | 4.1.8 | 跨端框架 |
| **React** | 18+ | UI框架 |
| **TypeScript** | 5.4+ | 类型系统 |
| **Vite** | 4+ | 构建工具 |
| **Sass** | 1.75+ | CSS预处理器 |

### 前端技术栈（管理后台）

| 技术 | 版本 | 用途 |
|------|------|------|
| **React** | 18+ | UI框架 |
| **Ant Design** | 5.12+ | UI组件库 |
| **Ant Design Pro** | 2.6+ | 中后台解决方案 |
| **TypeScript** | 5.3+ | 类型系统 |
| **Vite** | 5+ | 构建工具 |
| **React Router** | 6+ | 路由管理 |
| **Axios** | 1.6+ | HTTP客户端 |

---

## 开发环境搭建

### 1. 前置要求

- **Python**: 3.12或更高版本
- **Node.js**: 18或更高版本
- **uv**: Python包管理器（推荐）
- **Git**: 版本控制
- **数据库**: PostgreSQL（生产）或 SQLite（开发）

### 2. 后端设置

```bash
# 克隆项目
git clone <repository-url>
cd electric-miniprogram/backend

# 安装uv（如果还没安装）
pip install uv

# 创建虚拟环境并安装依赖
uv sync

# 激活虚拟环境
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入必要的配置

# 执行数据库迁移
python manage.py migrate

# 创建超级管理员
python manage.py createsuperuser

# 启动开发服务器
python manage.py runserver
```

**环境变量配置 (.env)**

```env
# Django配置
DJANGO_ENV=development
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# 微信小程序配置
WECHAT_APPID=your-wechat-appid
WECHAT_SECRET=your-wechat-secret

# 海尔API配置（可选）
HAIER_CLIENT_ID=your-haier-client-id
HAIER_CLIENT_SECRET=your-haier-client-secret
HAIER_BASE_URL=https://openplat-test.haier.net
HAIER_CUSTOMER_CODE=your-customer-code

# 数据库配置（生产环境）
POSTGRES_DB=your_db_name
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_db_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

### 3. 前端设置（用户端小程序）

```bash
cd ../frontend

# 安装依赖
npm install

# 配置开发环境
# 编辑 config/dev.ts，设置API地址

# 启动微信小程序开发
npm run dev:weapp

# 编译其他平台
npm run dev:alipay   # 支付宝小程序
npm run dev:h5       # H5网页
```

### 4. 管理后台设置

```bash
cd ../merchant

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 访问 http://localhost:5173
```

---

## 核心功能模块

### 1. 用户认证模块 (users/)

**功能特性：**

- ✅ 微信小程序登录（code换取openid）
- ✅ 管理员密码登录
- ✅ JWT令牌认证
- ✅ 用户资料管理
- ✅ 收货地址管理
- ✅ 地址智能解析

**关键模型：**

```python
class User(AbstractUser):
    openid = models.CharField(max_length=64, unique=True)
    user_type = models.CharField(choices=[('wechat', '微信用户'), ('admin', '管理员')])
    avatar_url = models.URLField()
    phone = models.CharField(max_length=20)
    # ...

class Address(models.Model):
    user = models.ForeignKey(User)
    contact_name = models.CharField(max_length=50)
    province/city/district = models.CharField()
    detail = models.CharField(max_length=200)
    is_default = models.BooleanField()
```

**API端点：**

- `POST /api/auth/wechat/` - 微信登录
- `POST /api/auth/password/` - 密码登录
- `POST /api/auth/refresh/` - 刷新令牌
- `GET/PATCH /api/profile/` - 用户资料
- `GET/POST/PUT/DELETE /api/addresses/` - 地址管理

### 2. 商品目录模块 (catalog/)

**功能特性：**

- ✅ 商品CRUD操作
- ✅ 分类和品牌管理
- ✅ 全文搜索（名称、描述）
- ✅ 多维度筛选（分类、品牌、价格）
- ✅ 多种排序策略
- ✅ 商品推荐算法
- ✅ 图片上传管理
- ✅ 海尔商品同步

**关键模型：**

```python
class Product(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category)
    brand = models.ForeignKey(Brand)
    price = models.DecimalField()
    stock = models.PositiveIntegerField()
    source = models.CharField(choices=[('local', '本地'), ('haier', '海尔')])
    
    # 海尔专属字段
    product_code = models.CharField()
    supply_price/invoice_price/market_price = models.DecimalField()
    is_sales = models.CharField()  # 是否可采
    # ...

class Category(models.Model):
    name = models.CharField(unique=True)
    order = models.IntegerField()

class Brand(models.Model):
    name = models.CharField(unique=True)
    logo = models.URLField()
```

**API端点：**

- `GET /api/products/` - 商品列表（支持搜索、筛选、排序）
- `GET /api/products/{id}/` - 商品详情
- `POST /api/products/` - 创建商品（管理员）
- `PUT/PATCH /api/products/{id}/` - 更新商品
- `DELETE /api/products/{id}/` - 删除商品
- `GET /api/products/recommendations/` - 推荐商品
- `GET /api/products/{id}/related/` - 相关商品
- `GET /api/categories/` - 分类列表
- `GET /api/brands/` - 品牌列表

### 3. 订单管理模块 (orders/)

**功能特性：**

- ✅ 购物车管理
- ✅ 订单创建
- ✅ 订单状态流转（状态机）
- ✅ 支付集成
- ✅ 订单取消/退款
- ✅ 物流跟踪
- ✅ 海尔订单推送
- ✅ 折扣系统

**订单状态流转：**

```
待支付(pending) → 待发货(paid) → 待收货(shipped) → 已完成(completed)
       ↓
   已取消(cancelled)
       ↓
   退款中(refunding) → 已退款(refunded)
```

**关键模型：**

```python
class Order(models.Model):
    order_number = models.CharField(unique=True)
    user = models.ForeignKey(User)
    product = models.ForeignKey(Product)
    status = models.CharField(choices=STATUS_CHOICES)
    total_amount = models.DecimalField()
    actual_amount = models.DecimalField()
    
    # 海尔订单字段
    haier_order_no = models.CharField()
    haier_so_id = models.CharField(unique=True)
    logistics_company/logistics_no = models.CharField()
    # ...

class Cart(models.Model):
    user = models.ForeignKey(User)
    
class CartItem(models.Model):
    cart = models.ForeignKey(Cart)
    product = models.ForeignKey(Product)
    quantity = models.PositiveIntegerField()

class Payment(models.Model):
    order = models.ForeignKey(Order)
    method = models.CharField(choices=[('wechat', '微信支付'), ...])
    status = models.CharField()
    amount = models.DecimalField()
```

**API端点：**

- `GET /api/cart/my_cart/` - 查看购物车
- `POST /api/cart/add_item/` - 添加商品
- `POST /api/cart/update_item/` - 更新数量
- `POST /api/cart/remove_item/` - 移除商品
- `POST /api/orders/create_order/` - 创建订单
- `GET /api/orders/my_orders/` - 我的订单
- `PATCH /api/orders/{id}/cancel/` - 取消订单
- `POST /api/payments/` - 创建支付

### 4. 第三方集成模块 (integrations/)

**功能特性：**

- ✅ 海尔API集成
  - 商品信息同步
  - 价格库存查询
  - 订单推送
  - 物流查询
- ✅ YLH系统对接
- ✅ 同步日志记录

**关键模型：**

```python
class HaierConfig(models.Model):
    name = models.CharField(unique=True)
    config = models.JSONField()  # 存储API配置
    is_active = models.BooleanField()

class HaierSyncLog(models.Model):
    sync_type = models.CharField(choices=[
        ('products', '商品同步'),
        ('prices', '价格同步'),
        ('stock', '库存同步'),
        ('order', '订单推送'),
    ])
    status = models.CharField()
    total_count/success_count/failed_count = models.IntegerField()
```

**API端点：**

- `GET /api/integrations/haier/products/` - 获取海尔商品
- `POST /api/integrations/haier/sync/` - 同步商品
- `POST /api/integrations/haier/push-order/` - 推送订单
- `GET /api/integrations/haier/logistics/` - 查询物流

---

## API接口文档

### 认证方式

所有需要认证的API使用JWT Bearer Token：

```http
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

### 标准响应格式

**成功响应：**
```json
{
  "id": 1,
  "name": "商品名称",
  ...
}
```

**列表响应：**
```json
{
  "results": [...],
  "total": 100,
  "page": 1,
  "total_pages": 10,
  "has_next": true,
  "has_previous": false
}
```

**错误响应：**
```json
{
  "detail": "错误信息",
  "code": "error_code"
}
```

### 交互式API文档

- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **OpenAPI Schema**: http://localhost:8000/api/schema/

---

## 数据库设计

### 核心表结构

#### 用户表 (users_user)
```sql
CREATE TABLE users_user (
    id BIGSERIAL PRIMARY KEY,
    openid VARCHAR(64) UNIQUE,
    username VARCHAR(150) UNIQUE,
    user_type VARCHAR(20),  -- 'wechat' | 'admin'
    avatar_url VARCHAR(200),
    phone VARCHAR(20),
    email VARCHAR(254),
    is_staff BOOLEAN,
    created_at TIMESTAMP
);
```

#### 商品表 (catalog_product)
```sql
CREATE TABLE catalog_product (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(200),
    category_id BIGINT REFERENCES catalog_category(id),
    brand_id BIGINT REFERENCES catalog_brand(id),
    price DECIMAL(10, 2),
    stock INTEGER,
    source VARCHAR(20),  -- 'local' | 'haier'
    product_code VARCHAR(50) UNIQUE,  -- 海尔商品编码
    supply_price DECIMAL(10, 2),
    is_sales VARCHAR(1),  -- '1'可采, '0'不可采
    main_images JSONB,
    detail_images JSONB,
    is_active BOOLEAN,
    created_at TIMESTAMP,
    INDEX idx_category_active (category_id, is_active),
    INDEX idx_product_code (product_code)
);
```

#### 订单表 (orders_order)
```sql
CREATE TABLE orders_order (
    id BIGSERIAL PRIMARY KEY,
    order_number VARCHAR(100) UNIQUE,
    user_id BIGINT REFERENCES users_user(id),
    product_id BIGINT REFERENCES catalog_product(id),
    status VARCHAR(20),  -- 订单状态
    quantity INTEGER,
    total_amount DECIMAL(10, 2),
    actual_amount DECIMAL(10, 2),
    haier_order_no VARCHAR(100),
    haier_so_id VARCHAR(100) UNIQUE,
    snapshot_address TEXT,  -- 地址快照
    created_at TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_user_created (user_id, created_at)
);
```

### 数据库索引策略

- ✅ 主键自动索引
- ✅ 外键字段索引
- ✅ 常用查询字段组合索引
- ✅ 唯一约束索引

---

## 第三方集成

### 1. 微信小程序

**登录流程：**

```
1. 小程序调用 wx.login() 获取 code
2. 发送 code 到后端 /api/auth/wechat/
3. 后端调用微信API换取 openid
4. 创建/获取用户，返回JWT令牌
```

**配置：**
```python
WECHAT_APPID = 'your-appid'
WECHAT_SECRET = 'your-secret'
```

### 2. 海尔智能家电API

**主要功能：**

- 商品信息同步
- 价格库存查询
- 订单推送
- 物流跟踪

**认证流程：**

```python
from integrations.haierapi import HaierAPI

api = HaierAPI.from_settings()
if api.authenticate():
    products = api.get_product_list()
```

**配置：**
```env
HAIER_CLIENT_ID=your-client-id
HAIER_CLIENT_SECRET=your-client-secret
HAIER_BASE_URL=https://openplat-test.haier.net
```

---

## 部署指南

### Docker部署（推荐）

**1. 创建 Dockerfile（后端）**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# 安装依赖
COPY backend/pyproject.toml backend/uv.lock ./
RUN pip install uv && uv sync --frozen

# 复制代码
COPY backend/ .

# 收集静态文件
RUN python manage.py collectstatic --noinput

# 启动命令
CMD ["gunicorn", "backend.wsgi:application", "--bind", "0.0.0.0:8000"]
```

**2. docker-compose.yml**

```yaml
version: '3.8'

services:
  db:
    image: postgres:14
    environment:
      POSTGRES_DB: electric_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DJANGO_ENV=production
      - DATABASE_URL=postgresql://postgres:password@db:5432/electric_db
    depends_on:
      - db

  merchant:
    build: ./merchant
    ports:
      - "80:80"

volumes:
  postgres_data:
```

**3. 启动服务**

```bash
docker-compose up -d
```

### 传统部署

**后端部署（Ubuntu + Nginx + Gunicorn）**

```bash
# 1. 安装依赖
apt update
apt install python3.12 python3-pip nginx postgresql

# 2. 配置数据库
sudo -u postgres createdb electric_db

# 3. 安装Python包
pip install uv
uv sync

# 4. 迁移数据库
python manage.py migrate

# 5. 收集静态文件
python manage.py collectstatic

# 6. 启动Gunicorn
gunicorn backend.wsgi:application --bind 127.0.0.1:8000 --workers 4

# 7. 配置Nginx
```

**Nginx配置：**

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /static/ {
        alias /path/to/staticfiles/;
    }

    location /media/ {
        alias /path/to/media/;
    }
}
```

---

## 开发规范

### 代码风格

**Python (PEP 8)**
- 缩进：4空格
- 行长度：120字符
- 命名：snake_case（变量、函数），PascalCase（类）

**TypeScript/JavaScript**
- 缩进：2空格
- 引号：单引号
- 分号：必须
- 命名：camelCase（变量、函数），PascalCase（组件、类）

### Git提交规范

```
feat: 新功能
fix: 修复bug
docs: 文档更新
style: 代码格式调整
refactor: 重构
test: 测试相关
chore: 构建工具、依赖更新
```

示例：
```bash
git commit -m "feat: 添加商品批量导入功能"
git commit -m "fix: 修复订单金额计算错误"
```

### API设计规范

1. **RESTful风格**
   - GET: 查询
   - POST: 创建
   - PUT/PATCH: 更新
   - DELETE: 删除

2. **URL命名**
   - 使用小写字母
   - 用连字符分隔单词
   - 复数形式表示集合

3. **响应码**
   - 200: 成功
   - 201: 创建成功
   - 400: 请求错误
   - 401: 未认证
   - 403: 无权限
   - 404: 未找到
   - 500: 服务器错误

---

## 常见问题

### Q1: 数据库迁移冲突

**A:** 
```bash
# 重置迁移
python manage.py migrate catalog zero
python manage.py makemigrations catalog
python manage.py migrate catalog
```

### Q2: CORS跨域错误

**A:** 检查 `backend/settings/base.py` 中的CORS配置：
```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
```

### Q3: JWT令牌过期

**A:** 使用refresh token刷新：
```bash
curl -X POST http://localhost:8000/api/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "your-refresh-token"}'
```

### Q4: 海尔API连接失败

**A:** 
1. 检查网络连接
2. 验证API凭证配置
3. 查看 `HaierSyncLog` 日志

### Q5: 小程序开发者工具提示网络错误

**A:**
1. 检查小程序后台配置的服务器域名
2. 确保API地址在合法域名列表
3. 开发阶段可开启"不校验合法域名"

---

## 性能优化建议

### 数据库优化

1. **使用select_related和prefetch_related**
```python
# 优化前
products = Product.objects.all()

# 优化后
products = Product.objects.select_related('category', 'brand').all()
```

2. **添加数据库索引**
```python
class Meta:
    indexes = [
        models.Index(fields=['category', 'is_active']),
    ]
```

### 缓存策略

```python
from django.core.cache import cache

# 缓存商品列表
products = cache.get('hot_products')
if not products:
    products = Product.objects.filter(is_active=True)[:10]
    cache.set('hot_products', products, 300)  # 5分钟
```

### API限流

```python
# settings/base.py
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_RATES': {
        'anon': '20/minute',
        'user': '100/minute',
    }
}
```

---

## 测试指南

### 单元测试

```bash
# 运行所有测试
python manage.py test

# 运行特定模块测试
python manage.py test catalog.tests

# 运行特定测试用例
python manage.py test catalog.tests.test_models.ProductModelTest
```

### API测试示例

```python
from rest_framework.test import APITestCase

class ProductAPITest(APITestCase):
    def test_list_products(self):
        response = self.client.get('/api/products/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)
```

---

## 监控与日志

### 日志配置

日志文件位置：
- 应用日志：`backend/logs/app.log`
- 错误日志：`backend/logs/error.log`
- 海尔API日志：`backend/logs/haier.log`

### 健康检查

```bash
# API健康检查
curl http://localhost:8000/health/

# 返回示例
{
    "status": "healthy",
    "database": "ok",
    "timestamp": "2025-11-26T10:30:00Z"
}
```

---

## 安全最佳实践

1. **生产环境必做：**
   - [ ] 设置 `DEBUG=False`
   - [ ] 使用强随机SECRET_KEY
   - [ ] 配置ALLOWED_HOSTS
   - [ ] 启用HTTPS
   - [ ] 使用PostgreSQL替代SQLite
   - [ ] 定期备份数据库

2. **输入验证：**
   - 使用DRF的序列化器验证
   - 防止SQL注入（使用ORM）
   - 防止XSS攻击（前端转义）

3. **认证安全：**
   - JWT令牌有效期限制
   - 密码加密存储（Django自动处理）
   - 限流防止暴力破解

---

## 扩展阅读

- [Django官方文档](https://docs.djangoproject.com/)
- [DRF官方文档](https://www.django-rest-framework.org/)
- [Taro文档](https://taro-docs.jd.com/)
- [Ant Design Pro文档](https://pro.ant.design/)
- [海尔API对接文档](./haier_api.md)

---

## 技术支持

- **项目地址**: [GitHub Repository]
- **问题反馈**: [Issues]
- **API文档**: http://localhost:8000/api/docs/
- **技术博客**: [Team Blog]

---

## 贡献指南

我们欢迎任何形式的贡献！

1. **Fork项目**
2. **创建功能分支** (`git checkout -b feature/AmazingFeature`)
3. **提交更改** (`git commit -m 'feat: 添加某个功能'`)
4. **推送到分支** (`git push origin feature/AmazingFeature`)
5. **创建Pull Request**

### 代码审查清单

- [ ] 代码符合PEP 8规范
- [ ] 添加了必要的测试
- [ ] 更新了相关文档
- [ ] 所有测试通过
- [ ] 无明显性能问题

---

## 许可证

MIT License - 详见 [LICENSE](./LICENSE) 文件

---

## 更新日志

### v1.0.0 (2025-11-26)
- ✅ 完整的商品管理系统
- ✅ 订单流程完善
- ✅ 海尔API深度集成
- ✅ 管理后台功能齐全
- ✅ 多端小程序支持
- ✅ 完整的API文档

---

**💡 提示**: 本文档会持续更新，建议定期查看最新版本。

**📧 联系我们**: support@example.com

**⭐ 如果这个项目对你有帮助，请给我们一个Star！**
