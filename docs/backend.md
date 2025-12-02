# 后端技术文档（Django + DRF）

## 概述
- 基于 `Django 5` 与 `Django REST Framework` 的电商后端，提供商品、订单、支付、用户、信用账户等 API。
- 使用 `SimpleJWT` 做认证，`drf-spectacular` 生成 OpenAPI 文档，依赖管理使用 `uv`。

## 技术栈
- 框架：Django、Django REST Framework
- 认证：`djangorestframework-simplejwt`
- 文档：`drf-spectacular`
- 依赖管理：`uv`
- 数据库：开发 `SQLite`，生产建议 `PostgreSQL`

## 架构总览
- 分层：`views`（控制器）→ `serializers`（数据转换）→ `models`（领域模型）→ `services`（业务服务）
- 应用划分：
  - `users/` 用户、地址、公司认证、信用账户与账务
  - `catalog/` 商品、分类、品牌、媒体资源、搜索日志
  - `orders/` 购物车、订单、支付、折扣、状态机与分析
  - `integrations/` 海尔与易理货系统的对接
  - `common/` 权限、分页、异常、限流、健康检查、日志配置

## 目录结构
- 主工程：`backend/backend/`（环境配置、入口、路由）
- 模块：`catalog/`（商品）、`orders/`（订单与支付）、`users/`（用户与地址、信用账户）、`integrations/`（海尔/易理货对接）、`common/`（权限、分页、异常等）

## 快速开始
- 环境准备：Python 3.12+，建议安装 `uv`
- 安装依赖：
  ```bash
  pip install uv
  uv sync
  ```
- 数据库迁移：
  ```bash
  python manage.py makemigrations
  python manage.py migrate
  ```
- 启动开发服务器：
  ```bash
  python manage.py runserver
  # http://localhost:8000/
  ```
- API 文档：
  - Swagger UI：`/api/docs/`
  - ReDoc：`/api/redoc/`
  - OpenAPI：`/api/schema/`

## 环境变量
- 开发：
  ```env
  DJANGO_ENV=development
  SECRET_KEY=your-secret-key
  DEBUG=True
  ALLOWED_HOSTS=localhost,127.0.0.1
  WECHAT_APPID=your-appid
  WECHAT_SECRET=your-secret
  ```
- 生产：
  ```env
  DJANGO_ENV=production
  SECRET_KEY=your-production-secret
  DEBUG=False
  ALLOWED_HOSTS=yourdomain.com
  POSTGRES_DB=...
  POSTGRES_USER=...
  POSTGRES_PASSWORD=...
  POSTGRES_HOST=...
  POSTGRES_PORT=5432
  CORS_ALLOWED_ORIGINS=https://yourdomain.com
  WECHAT_APPID=...
  WECHAT_SECRET=...
  ```

## 路由入口
- 用户与认证：`backend/users/urls.py:25`
- 订单与支付：`backend/orders/urls.py:1`
- 商品与品牌：`backend/catalog/urls.py:5`
- 集成与回调：`backend/integrations/urls.py:17`

## 认证与权限
- 所有需要认证的端点在 Header 携带：`Authorization: Bearer <token>`
- 权限类：
  - 所有者或管理员：`backend/common/permissions.py:12`
  - 管理员或只读：`backend/common/permissions.py:70`
  - 仅管理员：`backend/common/permissions.py:101`
  - 环境感知权限：`backend/common/permissions.py:126`

## 核心模块
- 用户与地址（`users/`）：微信登录、密码登录、用户资料、地址管理、公司认证、信用账户与账务对账
- 商品目录（`catalog/`）：商品/分类/品牌、搜索与筛选、媒体资源
- 订单与支付（`orders/`）：购物车、订单创建、状态机、支付与回调、折扣系统、数据分析
- 第三方集成（`integrations/`）：海尔 API、易理货 API，对接认证与调用

## 账期与对账
- 固定账期：以月为单位，正常账期为 `30` 天；到期日以“月末”结算。
- 到期日计算：以交易日加账期天数得到目标日期，实际应付日期为该目标日期所在月份的最后一天（`backend/users/credit_services.py:48`）。
- 对账单生成：管理员在“账务对账单”中选择账期起止（建议选择某月 `1` 日至该月最后一天），系统汇总本期采购/付款/退款并计算期末未付。
- 账期内统计：
  - 账期内应付：到期日在账期内且未付款的采购金额（`backend/users/credit_services.py:183`）。
  - 账期内已付：在账期内完成支付的采购金额（按采购记录的 `paid_date` 统计，`backend/users/credit_services.py:190`）。
  - 逾期金额：到期日至账期末已逾期的采购金额（`backend/users/credit_services.py:197`）。
- 逾期状态更新：每日根据应付日期更新逾期状态（`backend/users/credit_services.py:130`）。

## 主要 API 端点
- 认证与用户（前缀 `/api/`）：
  - `POST /auth/wechat/` 微信登录（开发支持模拟）`backend/users/views.py:54`
  - `POST /auth/password/` 密码登录（管理员）`backend/users/urls.py:27`
  - `POST /auth/refresh/` 刷新 Token `backend/users/urls.py:29`
  - `GET/PATCH /user/profile/` 用户资料 `backend/users/urls.py:30`
  - `GET /user/statistics/` 用户统计 `backend/users/urls.py:31`
  - `GET/POST/... /addresses/` 地址 CRUD 与解析 `backend/users/urls.py:18`
- 商品目录：
  - `GET/POST/... /products/` 商品 CRUD `backend/catalog/urls.py:6`
  - `GET /products/by_category/` 按分类筛选 `backend/catalog/views.py`
  - `GET /products/by_brand/` 按品牌筛选 `backend/catalog/views.py`
  - `GET /categories/` 分类列表 `backend/catalog/urls.py:7`
    - 数据结构：`{ id, name, order, logo }`（`logo` 为可选的图片 URL）
  - `GET /brands/` 品牌列表 `backend/catalog/urls.py:9`
  - `POST /media-images/` 图片上传 `backend/catalog/urls.py:8`
  - `GET/POST/... /home-banners/` 首页轮播图管理 `backend/catalog/urls.py:8`
    - GET（公开）：返回启用的轮播图列表，按 `order` 升序。
    - POST/PATCH/DELETE（管理员）：创建/更新/删除轮播图。
    - 数据结构：`{ id, title, link_url, order, is_active, image_id, image_url, created_at }`。
  - `POST /home-banners/upload/` 上传图片并创建轮播图（管理员） `backend/catalog/views.py`
    - 表单字段：`file`（必填）、`title`（可选）、`link_url`（可选）、`order`（可选，默认 `0`）、`is_active`（可选，默认 `true`）。
    - 返回：已创建轮播图数据，包含 `image_url` 为完整可访问地址。
- 订单与支付：
  - `GET/POST/... /orders/` 订单 CRUD `backend/orders/urls.py:3`
  - `GET /orders/my_orders/` 我的订单 `backend/orders/views.py:113`
    - 查询参数：`status`（支持单状态如 `paid` 或多状态逗号分隔如 `returning,refunding,refunded`）。当传入 `returning` 时，除订单本身状态为 `returning` 外，还会包含存在退货申请且状态为 `requested|approved|in_transit|received` 的订单；当传入 `completed` 时，将排除上述处于退货流程中的订单。
  - `POST /orders/create_order/` 创建订单 `backend/orders/views.py:136`
  - `POST /orders/create_batch_orders/` 批量创建订单 `backend/orders/views.py:235`
    - 请求体：
      - `items` 商品列表（`[{ product_id, quantity }]`）
      - `address_id` 收货地址ID
      - `note` 备注（可选）
      - `payment_method` 支付方式：`online | credit`（默认 `online`）。当为 `credit` 时将直接记录采购到信用账户并将订单置为 `paid`，不创建支付记录；当为 `online` 时创建对应支付记录。
      - `method` 在线支付渠道：`wechat | alipay | bank`（仅当 `payment_method=online` 时有效，默认 `wechat`）
  - `PATCH /orders/{id}/cancel|ship|complete|confirm_receipt/` 状态流转 `backend/orders/views.py:313`
    - 发货请求体：`{ "tracking_number": "SF1234567890" }`（也可使用 `logistics_no` 字段）。
    - 发货校验：管理员必填快递单号；接口会写入订单物流信息后再流转到 `shipped`。
    - 确认收货：订单所有者或管理员可调用 `PATCH /api/orders/{id}/confirm_receipt/`，可选请求体 `{ "note": "已收到" }`，成功后状态从 `shipped` 变为 `completed`，并记录状态历史（`backend/orders/views.py:379`）。
    - 取消订单：订单所有者或管理员可调用 `PATCH /api/orders/{id}/cancel/`；可选请求体 `{ "note": "用户取消", "reason": "下单错误" }`。允许状态：`pending`、`paid`。流转至 `cancelled` 后：
      - 自动释放锁定库存（本地库存产品）。
      - 若订单在取消前为 `paid` 且为信用支付（无支付记录），自动记录信用退款以冲减欠款（`backend/orders/state_machine.py:212`）。
      - 在线支付退款需按支付渠道另行处理（当前版本不自动退款，将在未来的退款流程中实现）。
  - 退货与退款：
    - `POST /orders/{id}/request_return/` 申请退货（订单所有者或管理员）`backend/orders/views.py:441`
      - 请求体：`{ "reason": "尺寸不合适", "evidence_images": ["/media/images/2025/12/01/abc.jpg"] }`
      - 校验：仅 `paid|shipped|completed` 状态可申请；同一订单仅允许存在一条退货申请；`reason` 必填。
      - 说明：退货凭证图片建议先通过 `POST /media-images/` 上传后，取返回的 `url` 作为 `evidence_images` 元素。
    - `PATCH /orders/{id}/approve_return/` 同意退货（管理员）`backend/orders/views.py:512`
      - 请求体：`{ "note": "同意退货，请尽快寄回" }`（可选）
      - 效果：退货申请状态置为 `approved`，记录处理人与时间。
    - `PATCH /orders/{id}/reject_return/` 拒绝退货（管理员）`backend/orders/views.py:526`
      - 请求体：`{ "note": "不满足退货条件" }`
      - 效果：退货申请状态置为 `rejected`，记录处理人与时间。
    - `PATCH /orders/{id}/add_return_tracking/` 填写退货物流（订单所有者或管理员）`backend/orders/views.py:486`
      - 前置条件：退货申请已被管理员同意（状态为 `approved`）。
      - 请求体：`{ "tracking_number": "SF1234567890", "evidence_images": ["/media/images/...webp"] }`
      - 效果：更新退货申请的快递单号与凭证图片，状态置为 `in_transit`；若订单允许，状态机流转为 `returning`。
    - `PATCH /orders/{id}/receive_return/` 标记已收到退货（管理员）`backend/orders/views.py:539`
      - 请求体：`{ "note": "验货通过" }`
      - 前置状态：`in_transit`
      - 效果：退货申请状态更新为 `received`，记录处理人与时间；不直接变更订单状态。
    - `PATCH /orders/{id}/complete_refund/` 完成退款（管理员）`backend/orders/views.py:551`
      - 效果：订单状态机从 `refunding` 流转到 `refunded`。若订单为信用支付（无支付记录），自动记录一条信用退款以冲减欠款（`backend/users/credit_services.py:107`）。
    - 数据结构：退货申请 `ReturnRequest` 模型 `backend/orders/models.py:387`
      - 字段：`status(reason/tracking_number/evidence_images/created_at/updated_at/processed_by/processed_note/processed_at)`
      - 状态：`requested | approved | in_transit | received | rejected`
  - `GET/POST/... /payments/` 支付管理 `backend/orders/views.py:787`
  - `POST /payments/callback/{provider}/` 支付回调 `backend/orders/urls.py:12`
  - `GET/POST/... /discounts/` 折扣管理 `backend/orders/views.py:980`
  - `POST /orders/{id}/request_invoice/` 申请发票（仅订单所有者，订单需 `completed`）`backend/orders/views.py:362`
  - `GET/POST/... /invoices/` 发票管理（普通用户仅看到自己的；管理员可开具/取消）`backend/orders/urls.py:9`
- 统计与分析（仅管理员）：
  - `GET /analytics/sales_summary/` 销售汇总（`start_date/end_date`）
  - `GET /analytics/top_products/` 热销商品排行（`limit/days`）
  - `GET /analytics/daily_sales/` 每日销售统计（`days`）
  - `GET /analytics/user_growth/` 用户增长统计（`days`）
  - `GET /analytics/order_status_distribution/` 订单状态分布（`start_date/end_date`）
  - `GET /analytics/regional_sales/` 地区销售统计（新增）
    - 查询参数：`level`=`province|city`，`start_date`，`end_date`，`product_id`（可选），`order_by`=`orders|total_quantity|amount`，`limit`（可选）
    - 返回：`[{ region_name, orders, total_quantity, amount }]` （注意：返回的地区字段名为 `region_name`，对应请求的 level）
  - `GET /analytics/product_region_distribution/` 商品地区分布（新增）
    - 查询参数：`product_id`（必填），`level`=`province|city`，`start_date`，`end_date`，`order_by`=`orders|total_quantity|amount`
    - 返回：`[{ region_name, orders, total_quantity, amount }]`
  - `GET /analytics/region_product_stats/` 地区热销商品（新增）
    - 查询参数：`region_name`（必填），`level`=`province|city`，`start_date`，`end_date`，`order_by`=`orders|total_quantity|amount`，`limit`（可选）
    - 返回：`[{ product__id, product__name, orders, total_quantity, amount }]`

## 历史数据处理
- 订单地区数据修复：
  - 由于部分历史订单缺少快照地区信息，导致统计图表显示空白地区。
  - 可运行命令修复：`python manage.py fix_order_regions`
  - 该命令会解析 `snapshot_address` 填充 `snapshot_province/city/district`。
- 集成与回调：
  - `GET/POST ... /integrations/haier/api/*` 海尔查询与操作 `backend/integrations/urls.py:18`
  - `POST /integrations/ylh/orders/*` 易理货订单操作 `backend/integrations/urls.py:28`
  - `POST /integrations/ylh/callback/` 易理货回调 `backend/integrations/urls.py:25`

## 错误处理与统一异常
- 统一异常处理：`backend/common/exceptions.py:251`
- 业务异常类型：库存不足、订单状态非法、支付验证失败等 `backend/common/exceptions.py:59`
- 响应结构：包含 `success/code/message/error_code`，开发环境包含详细错误 `backend/common/exceptions.py:295`

## 限流策略
- 登录限流：每分钟 5 次 `backend/common/throttles.py:11`
- 支付限流：每分钟 10 次 `backend/common/throttles.py:32`
- 在视图中通过 `throttle_classes` 应用，如支付视图 `backend/orders/views.py:795`

## 日志与审计
- 配置入口：`backend/common/logging_config.py:30`
- 分环境日志级别与文件滚动，支付审计日志独立输出 `backend/common/logging_config.py:243`

## 健康检查与监控
- 健康检查端点：数据库与缓存连通性检测 `backend/common/health.py:23`
- 不同组件的响应时间与总体状态 `backend/common/health.py:61`

## 订单状态机
- 状态枚举：`backend/orders/state_machine.py:14`
- 合法转换检查：`backend/orders/state_machine.py:60`
- 执行转换：`backend/orders/state_machine.py:97`
- 转换后处理：`backend/orders/state_machine.py:178`

## 测试与常用命令
- 运行测试：
  ```bash
  python manage.py test
  ```
- 常用命令：数据库迁移、收集静态、清理会话、创建超级用户等（`manage.py` 系列）

## 部署与安全
- 生产务必设置 `DEBUG=False`，强随机 `SECRET_KEY`，限制 `ALLOWED_HOSTS`，启用 HTTPS。
- 使用 `PostgreSQL`，按需配置缓存与限流，严格校验输入。
 - 反向代理与 CORS：在 `ALLOWED_HOSTS/CORS_ALLOWED_ORIGINS` 中配置网关域名，开启 HTTPS；按需启用 `django-cors-headers`。
- 回调安全：海尔回调签名验证与错误处理 `backend/orders/views.py:585`

## 发票功能说明
- 申请条件：订单状态为 `completed`
- 申请端点：`POST /api/orders/{id}/request_invoice/`
- 管理端点：
  - 列表与详情：`GET /api/invoices/`、`GET /api/invoices/{id}/`
  - 开具：`POST /api/invoices/{id}/issue/`（需要 `invoice_number`，可选 `file_url`）
  - 取消：`POST /api/invoices/{id}/cancel/`（已开具不可取消）
  - 上传文件：`POST /api/invoices/{id}/upload_file/`（`multipart/form-data`，字段 `file`）
  - 下载文件：`GET /api/invoices/{id}/download/`（返回附件或文件绝对链接）
- 数据字段：`title/taxpayer_id/email/phone/address/bank_account/invoice_type/amount/tax_rate/tax_amount/status/invoice_number/file_url/requested_at/issued_at`

## 退货功能说明
- 角色与权限：
  - 用户（订单所有者）：可申请退货；仅在管理员同意后可填写退货物流与凭证。
  - 管理员：可同意/拒绝退货、验收退货、完成退款。
- 图片上传：通过 `POST /api/media-images/` 上传图片，返回的 `url` 可作为 `evidence_images` 列表元素传入退货接口。
 - 状态机配合：填写退货物流后，若订单允许，将进入 `returning` 状态；完成退款后进入 `refunded` 并释放库存（`backend/orders/state_machine.py:203`）。
