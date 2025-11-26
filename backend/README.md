# 电商小程序后端 API

基于Django REST Framework的电商系统后端API，支持商品管理、订单处理、用户认证、支付集成等功能。

## 技术栈

- **框架**: Django 5.2+ / Django REST Framework 3.16+
- **数据库**: SQLite (开发) / PostgreSQL (生产)
- **认证**: JWT (djangorestframework-simplejwt)
- **API文档**: drf-spectacular (OpenAPI 3.0)
- **包管理**: uv
- **Python版本**: 3.12+

## 项目结构

```
backend/
├── backend/              # 项目配置
│   ├── settings/        # 环境配置
│   │   ├── base.py     # 基础配置
│   │   ├── development.py  # 开发环境
│   │   ├── production.py   # 生产环境
│   │   └── env_config.py   # 环境检测
│   ├── urls.py          # URL路由
│   └── wsgi.py          # WSGI入口
├── catalog/             # 商品目录应用
│   ├── models.py       # 商品、分类、品牌模型
│   ├── views.py        # API视图
│   ├── serializers.py  # 序列化器
│   ├── search.py       # 搜索服务
│   └── urls.py         # 路由配置
├── orders/              # 订单应用
│   ├── models.py       # 订单、购物车、支付模型
│   ├── views.py        # API视图
│   ├── services.py     # 业务逻辑
│   ├── state_machine.py # 订单状态机
│   ├── payment_service.py # 支付服务
│   └── analytics.py    # 数据分析
├── users/               # 用户应用
│   ├── models.py       # 用户、地址模型
│   ├── views.py        # 认证、用户管理
│   └── serializers.py  # 序列化器
├── integrations/        # 第三方集成
│   ├── models.py       # 供应商配置
│   ├── haierapi.py     # 海尔API集成
│   ├── manager.py      # 供应商管理器
│   └── sync.py         # 数据同步服务
├── common/              # 公共模块
│   ├── permissions.py  # 权限类
│   ├── serializers.py  # 通用序列化器
│   ├── pagination.py   # 分页配置
│   ├── throttles.py    # 限流配置
│   ├── exceptions.py   # 异常处理
│   └── health.py       # 健康检查
├── manage.py            # Django管理命令
├── pyproject.toml       # 项目依赖
└── db.sqlite3           # SQLite数据库（开发）
```

## 快速开始

### 1. 环境准备

确保已安装：
- Python 3.12+
- uv (推荐) 或 pip

### 2. 安装依赖

使用uv（推荐）：
```bash
# 安装uv
pip install uv

# 创建虚拟环境并安装依赖
uv sync
```

或使用pip：
```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 数据库迁移

```bash
# 创建迁移文件
python manage.py makemigrations

# 执行迁移
python manage.py migrate
```

**重要**: 如果是首次设置或刚更新了models.py，请参阅 `MIGRATION_GUIDE.md` 获取详细的迁移指南。

### 4. 创建管理员用户

```bash
# 方式1: 使用Django命令
python manage.py createsuperuser

# 方式2: 使用提供的脚本
python create_admin.py
```

### 5. 启动开发服务器

```bash
python manage.py runserver
```

服务器将在 http://localhost:8000 启动

### 6. 访问API文档

- Swagger UI: http://localhost:8000/api/docs/
- ReDoc: http://localhost:8000/api/redoc/
- OpenAPI Schema: http://localhost:8000/api/schema/

## 主要功能

### 1. 用户认证

- **微信小程序登录**: `POST /api/auth/wechat/`
- **管理员密码登录**: `POST /api/auth/password/`
- **JWT令牌刷新**: `POST /api/auth/refresh/`

### 2. 商品管理

- **商品列表**: `GET /api/products/`
  - 支持搜索、过滤、排序
  - 分页支持
- **商品详情**: `GET /api/products/{id}/`
- **创建商品**: `POST /api/products/` (管理员)
- **更新商品**: `PUT/PATCH /api/products/{id}/` (管理员)
- **删除商品**: `DELETE /api/products/{id}/` (管理员)
- **商品推荐**: `GET /api/products/recommendations/`
- **相关商品**: `GET /api/products/{id}/related/`

### 3. 分类和品牌

- **分类列表**: `GET /api/categories/`
- **品牌列表**: `GET /api/brands/`
- **按分类筛选**: `GET /api/products/by_category/?category=分类名`
- **按品牌筛选**: `GET /api/products/by_brand/?brand=品牌名`

### 4. 搜索功能

- **商品搜索**: `GET /api/products/?search=关键词`
- **搜索建议**: `GET /api/products/search_suggestions/?prefix=关键词前缀`
- **热门关键词**: `GET /api/products/hot_keywords/`

### 5. 购物车

- **查看购物车**: `GET /api/cart/my_cart/`
- **添加商品**: `POST /api/cart/add_item/`
- **更新数量**: `POST /api/cart/update_item/`
- **移除商品**: `POST /api/cart/remove_item/`
- **清空购物车**: `POST /api/cart/clear/`

### 6. 订单管理

- **创建订单**: `POST /api/orders/create_order/`
- **我的订单**: `GET /api/orders/my_orders/`
- **订单详情**: `GET /api/orders/{id}/`
- **取消订单**: `PATCH /api/orders/{id}/cancel/`
- **订单状态**: `PATCH /api/orders/{id}/status/` (管理员)

### 7. 支付

- **创建支付**: `POST /api/payments/`
- **支付列表**: `GET /api/payments/`
- **支付详情**: `GET /api/payments/{id}/`
- **支付回调**: `POST /api/payments/callback/{provider}/`

### 8. 用户管理

- **用户资料**: `GET/PATCH /api/profile/`
- **用户统计**: `GET /api/statistics/`
- **地址管理**: `/api/addresses/`
- **地址解析**: `POST /api/addresses/parse/`

### 9. 收藏功能

- **我的收藏**: `GET /api/favorites/`
- **添加/取消收藏**: `POST /api/favorites/toggle/`
- **检查收藏状态**: `GET /api/favorites/check/?product_ids=1,2,3`

### 10. 图片上传

- **上传图片**: `POST /api/media/`
- **图片列表**: `GET /api/media/`

## 环境配置

### 开发环境

创建 `.env` 文件：
```env
DJANGO_ENV=development
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# 微信小程序配置
WECHAT_APPID=your-appid
WECHAT_SECRET=your-secret
```

### 生产环境

```env
DJANGO_ENV=production
SECRET_KEY=your-production-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# 数据库配置
POSTGRES_DB=your_db_name
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_db_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# CORS配置
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# 微信小程序配置
WECHAT_APPID=your-production-appid
WECHAT_SECRET=your-production-secret
```

## API认证

大多数API端点需要JWT认证。在请求头中包含：

```
Authorization: Bearer <your-jwt-token>
```

获取令牌：
```bash
# 微信登录
curl -X POST http://localhost:8000/api/auth/wechat/ \
  -H "Content-Type: application/json" \
  -d '{"code": "wechat-code"}'

# 管理员登录
curl -X POST http://localhost:8000/api/auth/password/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'
```

响应：
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "username": "admin",
    ...
  }
}
```

## 权限系统

- **AllowAny**: 任何人可访问（商品列表、详情等）
- **IsAuthenticated**: 需要登录（购物车、订单等）
- **IsAdminOrReadOnly**: 读取公开，写入需要管理员（商品、分类管理）
- **IsAdmin**: 仅管理员（用户管理、数据分析等）
- **IsOwnerOrAdmin**: 所有者或管理员（订单、支付等）

## 限流配置

- **匿名用户**: 20次/分钟
- **认证用户**: 100次/分钟
- **登录接口**: 5次/分钟
- **支付接口**: 10次/分钟

## 测试

```bash
# 运行所有测试
python manage.py test

# 运行特定应用的测试
python manage.py test catalog
python manage.py test orders

# 运行特定测试文件
python manage.py test catalog.tests.test_models
```

## 常用管理命令

```bash
# 创建超级用户
python manage.py createsuperuser

# 数据库迁移
python manage.py makemigrations
python manage.py migrate

# 收集静态文件（生产环境）
python manage.py collectstatic

# 创建缓存表
python manage.py createcachetable

# 清理过期会话
python manage.py clearsessions

# Django shell
python manage.py shell

# 数据库shell
python manage.py dbshell
```

## 故障排除

### 问题1: 模块未找到

```bash
# 确保虚拟环境已激活
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# 重新安装依赖
uv sync
```

### 问题2: 数据库迁移错误

参阅 `MIGRATION_GUIDE.md` 获取详细的迁移指南和故障排除。

### 问题3: CORS错误

检查 `backend/settings/base.py` 中的CORS配置：
```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
```

### 问题4: 静态文件404

开发环境会自动处理。生产环境需要：
```bash
python manage.py collectstatic
```

## 性能优化

1. **数据库查询优化**
   - 使用 `select_related()` 和 `prefetch_related()`
   - 添加适当的数据库索引

2. **缓存**
   - 使用Django缓存框架
   - 缓存热门数据和查询结果

3. **分页**
   - 所有列表接口都支持分页
   - 默认每页20条，最大100条

4. **异步任务**
   - 考虑使用Celery处理耗时任务
   - 如：邮件发送、数据同步等

## 安全建议

1. **生产环境**
   - 设置 `DEBUG=False`
   - 使用强密码的 `SECRET_KEY`
   - 配置 `ALLOWED_HOSTS`
   - 启用HTTPS

2. **数据库**
   - 使用PostgreSQL而非SQLite
   - 定期备份数据库
   - 限制数据库访问权限

3. **API安全**
   - 启用限流
   - 验证所有输入
   - 使用HTTPS传输敏感数据

## 部署

### 使用Gunicorn

```bash
# 安装Gunicorn
pip install gunicorn

# 启动服务
gunicorn backend.wsgi:application --bind 0.0.0.0:8000
```

### 使用Docker

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync

COPY . .

CMD ["gunicorn", "backend.wsgi:application", "--bind", "0.0.0.0:8000"]
```

### 使用Nginx

配置Nginx作为反向代理：
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /static/ {
        alias /path/to/static/;
    }

    location /media/ {
        alias /path/to/media/;
    }
}
```

## 贡献指南

1. Fork项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 许可证

MIT License

## 联系方式

- 项目地址: [GitHub Repository]
- 问题反馈: [Issues]
- API文档: http://localhost:8000/api/docs/

## 更新日志

### v0.1.0 (2025-11-18)
- ✅ 修复catalog/models.py模型定义不完整问题
- ✅ 添加Product、Category、Brand缺失字段
- ✅ 创建MediaImage、SearchLog、ProductFavorite模型
- ✅ 完善API文档
- ✅ 添加数据库索引优化查询性能

详细修复内容请参阅 `FIXES_APPLIED.md`
