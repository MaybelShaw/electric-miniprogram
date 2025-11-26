# 后端详细文档

## 概述

- 技术栈：`Django` + `Django REST Framework` + `SimpleJWT` + `drf-spectacular`
- 模块划分：`users`（用户与认证）、`catalog`（商品目录）、`orders`（订单与支付）、`integrations`（第三方集成）、`common`（通用设施）
- API 前缀：`/api/`；开发环境自动提供 Swagger 和 ReDoc
  - Swagger UI：`/api/docs/`
  - ReDoc：`/api/redoc/`
  - OpenAPI：`/api/schema/`

## 项目结构

- 根目录：`backend/`
- 应用模块：
  - `users/` 用户、地址、认证
  - `catalog/` 商品、分类、品牌、媒体、搜索
  - `orders/` 订单、购物车、支付、统计
  - `integrations/` 海尔与易理货系统集成
  - `common/` 权限、限流、异常处理、工具
- 配置：`backend/settings/`
  - `base.py` 基础配置
  - `development.py` 开发配置
  - `production.py` 生产配置
  - `env_config.py` 环境变量装载

## 运行与环境

- 开发运行：`python manage.py runserver`
- 迁移：`python manage.py migrate`
- 超级用户：`python manage.py createsuperuser`
- 静态文件：`python manage.py collectstatic`
- 关键环境变量（摘）：
  - `DJANGO_ENV`：环境（development/production）
  - `SECRET_KEY`：Django 密钥
  - `DATABASE_URL`：数据库连接
  - `WECHAT_APPID`、`WECHAT_SECRET`：微信凭证
  - `HAIER_*`：海尔 API 配置（生产环境）

## 认证与权限

- JWT 认证：`SimpleJWT`
  - 登录接口返回 `access` 与 `refresh`；通过 `Authorization: Bearer <token>` 访问接口
  - 刷新令牌：`POST /api/token/refresh/`
- 登录方式与路由：
  - 管理员密码登录：`POST /api/admin/login/`（别名）与 `POST /api/password_login/`
    - 路由：`backend/users/urls.py:9-16`
    - 视图：`backend/users/views.py:155-233`
  - 微信登录（小程序）：`POST /api/login/`（`WeChatLoginView`）
    - 视图：`backend/users/views.py:1-52`（类定义与描述）
- 权限模型：
  - `IsAuthenticated`：认证用户访问
  - `IsAdmin`：仅管理员访问 `common/permissions.py:1-188`
  - `IsOwnerOrAdmin`：仅资源所有者或管理员可访问（订单、地址等）
- 限流：
  - 登录限流：`LoginRateThrottle` `backend/common/throttles.py`
  - 支付回调限流：`PaymentRateThrottle` `orders/views.py:1129-1143`

## 通用机制

- 分页：`StandardResultsSetPagination`，默认每页 20；统一分页响应 `{count,next,previous,results}`
- 过滤：各 ViewSet 支持查询参数（如 `status`、`order_number`、`username`、`created_after` 等）
- 异常处理：统一异常处理器 `common.exceptions.custom_exception_handler`
- 日志：`common.logging_config.get_logging_config`，区分开发与生产日志级别

## 模块与接口

### 用户模块（users）

- 地址接口（路由：`backend/users/urls.py:5-18`）
  - 列表：`GET /api/addresses/`
  - 创建：`POST /api/addresses/`
  - 详情：`GET /api/addresses/{id}/`
  - 设为默认：`POST /api/addresses/{id}/set_default/`
- 用户接口
  - 管理员用户列表/管理：`/api/users/`（仅管理员）
  - 用户资料：`GET/PATCH /api/user/profile/`（`backend/users/urls.py:13`）
  - 用户统计：`GET /api/user/statistics/`（`backend/users/urls.py:14`）

### 商品目录（catalog）

- 商品接口：`/api/products/`（ViewSet，典型 CRUD）
  - 列表与筛选：支持 `search`、`brand_id`、`category_id`、价格区间、排序等
  - 详情：`GET /api/products/{id}/`
  - 创建/更新/删除：管理员权限
- 分类接口：`/api/categories/`（CRUD）
- 品牌接口：`/api/brands/`（CRUD）
- 媒体图片接口：`/api/media-images/`
  - 列表：`GET`
  - 上传：`POST` 表单（multipart）字段：
    - `file`：图片文件
    - `product_id`：可选，绑定产品
    - `field_name`：可选，`main_images` 或 `detail_images`
  - 响应示例：`{"url":"http://.../media/xxx.png","product_updated":true}`
  - 详情与删除：`GET/DELETE /api/media-images/{id}/`
  - 绑定逻辑：若携带 `product_id` 与 `field_name`，服务端将把图片追加到产品对应字段
  - URL 统一：序列化器将相对路径转换为绝对 URL（参考 `backend/catalog/serializers.py:84-101`）

### 订单与支付（orders）

- 订单接口：`/api/orders/`（`backend/orders/views.py:24-97`）
  - 列表筛选：`status`、`order_number`、`product_name`、`username`（管理员）、`user_id`（管理员）、`created_after/before`
  - 状态更新：`PATCH /api/orders/{id}/status/`（`orders/views.py:98-111`）
  - 我的订单：`GET /api/orders/my_orders/`（分页，`orders/views.py:113-135`）
  - 创建订单：`POST /api/orders/create_order/`（`orders/views.py:136-217`）
  - 批量创建：`POST /api/orders/create_batch_orders/`（`orders/views.py:219-305`）
  - 取消：`PATCH /api/orders/{id}/cancel/`（`orders/views.py:307-329`）
  - 发货：`PATCH /api/orders/{id}/ship/`（管理员，`orders/views.py:331-353`）
  - 完成：`PATCH /api/orders/{id}/complete/`（管理员，`orders/views.py:355-377`）
  - 推送至海尔：`POST /api/orders/{id}/push_to_haier/`（管理员，`orders/views.py:379-482`）
  - 海尔物流：`GET /api/orders/{id}/haier_logistics/`（`orders/views.py:484-506`）
- 支付接口：`/api/payments/`（典型 CRUD）
  - 支付状态操作：`POST /api/payments/{id}/fail|cancel|expire/`（`orders/views.py:1101-1125`）
  - 支付回调：`POST /api/payments/callback/{provider}/`（`orders/views.py:1129-1291`）
    - 功能：签名验证、防重复处理、事务更新、审计日志
    - 状态映射：`orders/views.py:1364-1404`
- 订单统计与分析：`/api/analytics/`（`orders/views.py:1406-1511`）
  - 汇总：`GET /api/analytics/sales_summary/`
  - 热销：`GET /api/analytics/top_products/`
  - 日销售：`GET /api/analytics/daily_sales/`
  - 用户增长：`GET /api/analytics/user_growth/`

### 第三方集成（integrations）

- 海尔 API 视图：`backend/integrations/views.py:1-20`
  - 认证、商品与价格查询、库存、物流、余额、同步日志
  - 开发容错：在未配置模块时提供 Mock/降级策略（已在项目中加固）
- 易理货系统（YLH）
  - 订单推送：参考 `orders/views.py:434-457`
  - 配置载入：`YLHSystemAPI.from_settings()`

## 图片上传与展示

- 前端上传注意：不要手动设置 `Content-Type: multipart/form-data`，让浏览器自行生成 boundary
- 响应包含绝对 `url`，前端应设置到 `Upload` 的 `file.url` 以便预览与列表展示（对应修复：`merchant-admin/src/components/ImageUpload/index.tsx:83-91`）
- 产品图片优先级：
  - 若存在本地 `main_images` 列表，序列化输出优先采用本地图片
  - 仅当本地为空时，回退到海尔主图 `product_image_url`
  - 参考实现：`backend/catalog/serializers.py:84-101`

## 示例交互

- 管理员密码登录
  - `POST /api/admin/login/`
  - Body：`{"username":"admin","password":"yourpass"}`
  - 响应：`{"access":"...","refresh":"...","user":{...}}`
- 上传绑定产品主图
  - `POST /api/media-images/` 表单：`file=<图片>, product_id=<ID>, field_name=main_images`
  - 响应：`{"url":"http://localhost:8000/media/xxx.png","product_updated":true}`
- 查询产品详情
  - `GET /api/products/{id}/`
  - `main_images` 为本地图片优先；若为空回退海尔主图
- 创建订单
  - `POST /api/orders/create_order/`
  - Body：`{"product_id":1,"address_id":2,"quantity":1,"method":"wechat"}`
  - 响应：`{"order":{...},"payment":{...}}`
- 支付回调（开发环境 mock）
  - `POST /api/payments/callback/mock` Body：`{"payment_id":123,"status":"succeeded"}`

## 错误与日志

- 统一错误格式：`{"detail":"错误描述"}` 或字段校验错误字典
- 关键日志：订单创建、支付处理、外部推送均记录到应用日志目录 `backend/logs/`
- 回调审计：通过 `PaymentService.log_payment_event` 记录支付事件（见 `orders/views.py:1168-1192` 等）

## 安全与合规

- HTTPS 强制（生产环境）
- JWT 有效期与刷新策略；避免将令牌置于 URL
- 管理员接口仅限 `is_staff` 用户
- 请求限流与重试退避（支付与登录）
- 文件类型与大小限制（图片上传），建议后端校验：`content_type`、`size`

## 性能与稳定性

- 查询优化：`select_related` 与 `prefetch_related`（如 `orders/views.py:39-41`）
- 分页与筛选参数避免一次性大数据返回
- 开发环境降级策略：未配置海尔/易理货时允许 Mock 以保障核心链路可验证

## 附录：关键代码位置索引

- 认证与登录
  - `backend/users/urls.py:1-18`
  - `backend/users/views.py:155-233` 密码登录
  - `backend/users/views.py:1-52` 微信登录概述
- 商品与媒体
  - `backend/catalog/serializers.py:84-101` 本地图片优先策略
  - `backend/catalog/views.py` 媒体上传与产品绑定 ViewSet
- 订单与支付
  - `backend/orders/views.py:24-97` 订单 ViewSet 基础
  - `backend/orders/views.py:136-217` 创建订单
  - `backend/orders/views.py:1129-1291` 支付回调处理
  - `backend/orders/views.py:1406-1511` 分析统计接口
- 集成
  - `backend/integrations/views.py:1-20` 海尔视图入口
  - `orders/views.py:434-457` 易理货订单推送

---

本文档为后端详细指南，适用于开发、测试与运维快速掌握系统结构与接口。建议结合在线 Swagger 文档与源码引用进行日常开发与排错。

