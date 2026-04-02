# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

三合一电商系统：
- **backend/**: Django REST API (用户、商品、订单、支付、海尔集成)
- **frontend/**: Taro + React 小程序 (微信/支付宝/抖音/H5)
- **merchant/**: React + Ant Design Pro 管理后台

## Build & Run Commands

### Backend
```bash
cd backend
uv sync                    # 安装/同步依赖
uv add <package>           # 添加新依赖
uv remove <package>        # 删除依赖
uv run python manage.py migrate   # 数据库迁移
uv run python manage.py runserver # 启动开发服务器 (http://localhost:8000)
uv run python manage.py test      # 运行测试
```

### Frontend (小程序)
```bash
cd frontend
npm install
npm run dev:weapp    # 微信小程序开发模式
npm run build:weapp  # 微信小程序生产构建
npm run dev:h5       # H5 开发模式
```

### Merchant (管理后台)
```bash
cd merchant
npm install
npm run dev     # Vite 开发服务器 (http://localhost:5173)
npm run build   # 生产构建
```

## Architecture

### Backend (Django + DRF)

```
backend/
├── backend/settings/    # 多环境配置 (development.py, production.py)
├── users/               # 用户认证、地址管理、积分账户
├── catalog/             # 商品、分类、品牌、搜索
├── orders/              # 订单、购物车、支付、折扣
├── integrations/        # 海尔 API、YLH 物流集成
├── support/             # 客服会话
└── common/              # 权限、分页、限流、异常处理
```

**核心 API**:
- `POST /api/login/` - 微信小程序登录 (code 换 token)
- `POST /api/admin/login/` - 管理员登录
- `GET /api/products/` - 商品列表 (支持搜索、筛选、排序)
- `POST /api/orders/create_order/` - 创建订单
- `POST /api/supplier-sync/sync-products/` - 同步海尔商品

**认证**: JWT Bearer Token (15 分钟 access + 7 天 refresh)

### Frontend (Taro 小程序)

```
frontend/src/
├── pages/           # 页面组件 (home, category, cart, profile, order-*)
├── services/        # API 封装 (auth.ts, user.ts, address.ts)
├── config/          # 配置 (images.ts)
└── app.config.ts    # 路由配置、TabBar
```

**API 地址**: `src/services/auth.ts` 中的 `BASE_URL`

### Merchant (管理后台)

```
merchant/src/
├── pages/
│   ├── Products/    # 商品管理
│   ├── Orders/      # 订单管理
│   ├── Users/       # 用户管理
│   ├── Brands/      # 品牌管理
│   ├── Categories/  # 分类管理 (大类/小类/细类)
│   ├── Discounts/   # 折扣管理
│   ├── Invoices/    # 发票管理
│   ├── Support/     # 客服会话
│   └── Stats/       # 销售/用户统计
├── components/      # 公共组件 (ImageUpload, RoleGuard, Layout)
└── services/        # API 调用 (axios)
```

## Key Development Flows

### 添加新 API 端点
1. 在对应 app 的 `views.py` 创建 ViewSet
2. 在 `urls.py` 注册路由
3. 更新 `api.md` 或 `DEVELOPER_GUIDE.md`

### 小程序新增页面
1. `frontend/src/pages/` 创建页面目录和 `index.tsx`
2. 在 `app.config.ts` 的 `pages` 数组注册路由
3. 如需 TabBar，在 `app.config.ts` 的 `tabBar.list` 添加

### 管理后台新增功能
1. `merchant/src/pages/` 创建页面组件
2. 在 `App.tsx` 添加路由
3. 使用 `src/services/` 封装 API 调用

## Environment Variables

### Backend (.env)
```env
DJANGO_ENV=development
SECRET_KEY=please-set-a-dev-secret
DEBUG=True
WECHAT_APPID=
WECHAT_SECRET=
HAIER_CLIENT_ID=
HAIER_CLIENT_SECRET=
POSTGRES_DB=
POSTGRES_USER=
POSTGRES_PASSWORD=
```

### Frontend
- API 地址：`src/services/auth.ts` 中 `BASE_URL`

### Merchant
- API 地址：`vite.config.ts` 中的 proxy 配置

## Testing

```bash
# Backend
python manage.py test catalog.tests
python manage.py test integrations.test_ylh_callback

# Frontend/Merchant
# 主要依赖手动测试和小程序开发者工具
```

## Third-Party Integrations

- **微信小程序**: `wx.login()` code 换取 openid
- **海尔 API**: 商品同步、订单推送、物流查询 (`integrations/haierapi.py`)
- **YLH 物流**: 订单状态同步 (`integrations/ylhapi.py`)

## Related Documentation

- `api.md` - 完整 API 文档
- `DEVELOPER_GUIDE.md` - 开发者技术指南
- `haier_api.md` - 海尔 API 对接详情
- `docs/` - 部署和运维文档

## 注意事项

- 这是本地开发环境，没有配置postgresql数据库，请考虑其他方式进行测试
- 开发、重构、测试、回答问题前请先阅读相关文档和代码
- 开发、重构、测试后更新相关文档
- 禁止修改haier_api.md，这是要对接的接口
