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
  - `stores/` 店铺、店铺成员、店铺支付配置与结算规则
  - `catalog/` 商品、分类、品牌、媒体资源、搜索日志
  - `orders/` 购物车、订单、支付、折扣、状态机与分析
  - `integrations/` 海尔与易理货系统的对接
  - `common/` 权限、分页、异常、限流、健康检查、日志配置
  - `support/` 客服系统（直接聊天优先，兼容工单）

## 目录结构
- 主工程：`backend/backend/`（环境配置、入口、路由）
- 模块：`stores/`（店铺与权限）、`catalog/`（商品）、`orders/`（订单与支付）、`users/`（用户与地址、信用账户）、`integrations/`（海尔/易理货对接）、`common/`（权限、分页、异常等）
  - 新增：`support/`（客服工单与消息）

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
- OpenAPI schema 生成使用显式 `@extend_schema`、`@extend_schema_field` 与枚举命名覆盖，`manage.py spectacular --validate` 应保持无 drf-spectacular warning；`/api/admin/login/` 作为密码登录别名使用独立 `admin_password_login` operationId，避免与 `/api/password_login/` 冲突。

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

### 订单与支付相关
- `ORDER_PAYMENT_TIMEOUT_MINUTES`：未支付订单自动取消超时（单位分钟，默认 `1440`，即 24 小时）。
- 自动取消实现：后台守护线程定期扫描并取消超时未支付订单，同时将相关支付记录置为 `expired` 并释放库存。
- 手动执行：可运行命令 `python manage.py cancel_unpaid_orders --dry-run` 预览，去掉 `--dry-run` 实际执行。

## 路由入口
- 路由入口：
- 用户与认证：`backend/users/urls.py:25`
- 店铺与上下文：`backend/stores/urls.py:1`
- 订单与支付：`backend/orders/urls.py:1`
- 商品与品牌：`backend/catalog/urls.py:5`
- 集成与回调：`backend/integrations/urls.py:17`
- 客服系统：`backend/support/urls.py:1`

## 认证与权限
- 所有需要认证的端点在 Header 携带：`Authorization: Bearer <token>`
- 权限类：
  - 所有者或管理员：`backend/common/permissions.py:12`
  - 管理员或只读：`backend/common/permissions.py:70`
  - 仅管理员：`backend/common/permissions.py:101`
  - 环境感知权限：`backend/common/permissions.py:126`

## 店铺与数据隔离
- `stores.Store` 是真实经营主体模型；庆勋愉悦家自身也是一个 `Store`，合作方入驻店铺也是 `Store`，不是“主店挂载子店铺”的组织层级。
- `Store.is_main=true` 表示唯一主平台店铺；`store_type` 支持 `self_operated`、`partner`、`supplier`。当前模型固定为一个主店铺 + 多个合作店铺，不再维护额外的平台归属字段。
- `Store.logo`、`cover_image`、`description`、`is_visible`、`show_on_home`、`home_order`、`contact_phone`、`address` 用于小程序公开展示；合作店铺 `is_visible=false` 时，公开侧不返回该店铺入口、店铺详情、商品、分类、品牌、轮播、专区等信息；`show_on_home=false` 仅隐藏首页/公开店铺列表入口。
- `stores.StoreMember` 绑定用户、店铺和角色；业务可见角色为 `platform_admin` 与 `store_admin`。历史 `store_sub_admin`、`store_staff` 数据保留兼容，但权限按店铺管理员处理，后台不再新增或展示这两个角色。
- `GET /api/stores/current/` 返回当前账号可访问店铺、默认店铺、平台管理员标记和店铺成员关系。
- 平台管理员只认超级用户、主平台店铺有效 `StoreMember(role='platform_admin')` 或主平台店铺有效 `StoreMember(role='store_admin')`；普通 `is_staff` 或 `role='admin'` 不再自动代表平台管理员。
- 平台管理员可跨店查看和代配置，并可查看搜索日志；自营店铺管理员可访问自己店铺下的商品、分类、品牌、专区、轮播图、订单、销售统计、账务数据、客户分组和问题建议。合作方店铺当前仅作为前台展示店铺使用，后台只保留本店商品、分类、品牌、专区、轮播图、客户分组、店铺成员和问题建议等展示配置入口，不提供订单、发票、销售统计、账务、折扣、库存日志、信用账户或店铺分账经营入口。
- 店铺成员接口允许平台管理员管理全部成员；普通店铺管理员只能管理本店店铺管理员账号。`POST /api/stores/members/create_user_member/` 用于创建新的商户后台账号并绑定为店铺管理员，后端强制 `is_staff=true`、`role=admin`、`is_superuser=false`，且成员角色只允许 `store_admin`。当绑定到主平台店铺时，该账号按平台管理员处理；绑定到普通店铺时只具备本店权限。支付配置、结算规则接口仅平台管理员可访问。
- 公开接口 `GET /api/stores/public/partners/` 返回 `status=active`、`store_type=partner`、`is_visible=true`、`show_on_home=true` 的合作方店铺；`is_visible=false` 的合作店铺公开详情和商品信息会被过滤。
- 公开接口 `GET /api/stores/public/{id}/detail/` 返回指定店铺公开信息、图片轮播、一级分类、当前分类下可见品牌、动态专区和商品摘要，数据只来自该真实店铺；传入 `category_id` 时商品与品牌都会收敛到该分类树下。
- 合作方店铺商品只用于小程序公开展示，商品列表和详情会返回价格、图片、规格等展示信息，但后端禁止加入购物车、更新购物车购买数量和创建订单；历史购物车项会以 `is_available=false` 和“合作店铺商品仅展示，暂不支持购买”提示前端排除结算。
- 只有主店允许启用海尔能力，合作方店铺开启 `allow_haier` 会触发模型校验错误。
- `Store.show_customer_group_name` 字段保留用于后台配置和接口兼容；当前小程序用户端不展示客户分组名称，只使用后端计算后的最终价格。
- `stores.StoreCustomerGroup` 表示店铺自己的客户分组；列表响应包含 `member_count`、`active_member_count`、`price_count` 统计字段，方便后台快速判断配置完整度；`StoreCustomerGroupMember` 通过手机号或已注册用户绑定客户，约束为同一小程序用户在同一店铺只能属于一个分组，但可以分别属于多个店铺的各一个分组。
- `stores.StoreCustomerGroupPrice` 保存分组产品价格表，支持本地商品和海尔商品的整品价格、SKU 价格；未配置分组价时回退商品/SKU 默认价，海尔商品分组价只影响本系统展示价和下单锁价，不修改海尔同步基础价。
- 客户分组权限码为 `customer_groups.manage`：平台管理员和店铺管理员拥有；历史店铺角色按店铺管理员兼容。

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
  - `POST /wechat/explicit-login/` 显式微信快捷登录：请求体包含 `code` 和微信手机号授权 `phone_code`；首次登录缺少手机号授权会返回 `400`，不会创建用户。登录成功返回 `access`、`refresh` 和用户资料，并保存手机号与 `last_login_at`。若同一手机号已存在账号，登录会归并到该账号，不会再创建重复手机号账号。
  - 当微信凭证未配置时，显式登录直接返回 `503`，不会使用固定手机号或模拟账号兜底。
  - `POST /login/` 旧微信 code 登录入口（保留兼容，不用于普通浏览触发账号创建）
  - `POST /password_login/` 密码登录（管理员/客服）`backend/users/urls.py`
  - `POST /admin/login/` 管理员登录别名 `backend/users/urls.py`
  - `POST /token/refresh/` 刷新 Token `backend/users/urls.py`
  - `GET/PATCH /user/profile/` 用户资料 `backend/users/urls.py`
  - `GET /user/statistics/` 用户统计 `backend/users/urls.py`
  - `GET/POST/... /addresses/` 地址 CRUD 与解析 `backend/users/urls.py:18`
- 店铺与权限（前缀 `/api/stores/`）：
  - `GET /current/` 当前账号店铺上下文，包含可访问店铺、默认店铺、平台管理员标记、成员关系和权限码。
  - `GET/POST/PATCH/DELETE /` 店铺管理；非平台管理员仅可更新本店 `show_customer_group_name` 展示开关。
  - `GET /public/partners/` 公开合作方店铺列表；`GET /public/{id}/detail/` 公开店铺详情、图片轮播、一级分类、分类下品牌、专区和商品摘要。合作店铺 `is_visible=false` 时公开详情返回 404；`show_on_home=false` 时仅不出现在公开合作方店铺列表。
  - `GET/POST/PATCH/DELETE /members/` 店铺成员管理；`POST /members/create_user_member/` 创建新的商户后台账号并绑定为店铺管理员；`GET /members/available_users/` 返回可绑定后台账号候选。
  - `GET/POST/PATCH/DELETE /customer-groups/` 店铺客户分组。
  - `GET/POST/PATCH/DELETE /customer-group-members/` 客户分组成员，支持按 `store`、`group`、`phone` 过滤。
  - `GET/POST/PATCH/DELETE /customer-group-prices/` 客户分组价格，支持按 `store`、`group`、`product` 过滤。
  - `GET/POST/PATCH/DELETE /payment-configs/` 店铺支付配置（平台管理员）。`wechat_mch_id` 保留为合作店铺未来服务商子商户号或线下结算参考；当前店铺分账不调用微信分账，不读取合作方证书，旧 `profit_sharing_*` 字段仅兼容历史配置。
  - `GET/POST/PATCH/DELETE /settlement-rules/` 店铺结算规则（平台管理员）。
- 商品目录：
  - `GET/POST/... /products/` 商品 CRUD `backend/catalog/urls.py:6`
    - 字段与校验补充：
      - `category_id`：商品必须挂在“子品类（minor）”或“品项（item）”下，否则返回 `400`，错误键为 `category_id`，错误信息“商品必须关联到子品类或品项”（`backend/catalog/serializers.py:409`，与 `Product.clean` 保持一致）。
      - `source`：商品来源支持 `local` 和 `haier`；只有启用 `allow_haier` 的店铺可创建或更新为海尔商品，加盟/合作方店铺提交 `source=haier` 会返回 `400 Bad Request`。
      - `product_code`：海尔产品编码，数据库层面为唯一索引。
        - 海尔商品（`source=haier`）必须填写且唯一；缺失将返回 `400 Bad Request`，错误信息“海尔商品必须设置产品编码”。
        - 本地商品（`source=local`）可为空；当提交空白时后端会保存为 `NULL`，不参与唯一约束。
        - 当提交已被其他商品占用的非空编码时，返回 `400 Bad Request`，错误信息为“海尔产品编码已存在，请使用唯一编码”。
      - 价格字段与展示：
        - `price`：商户对外销售价；若从海尔同步且未手工调整，初始为“市场价（market_price）或供价（supply_price）”。
        - `display_price`：展示价；对经销商优先使用经销价（dealer_price），否则回退零售价 `price`。
        - 客户分组价：若当前用户在商品所属店铺存在启用分组，且该分组配置了产品/SKU价格，`display_price` 会优先使用分组价；SKU 会先找 SKU 分组价，再回退整品分组价，最后回退默认价。
        - 分组展示字段：商品响应包含 `customer_group_id`、`customer_group_name`、`show_customer_group_name`，字段保留兼容；当前小程序用户端不渲染分组名称，只展示 `display_price`。
        - `discounted_price`：折后价；基于当前登录用户与商品的最佳有效折扣计算（`orders.services.get_best_active_discount`）。
        - `originalPrice`：原价字段；优先返回 `market_price`，否则返回 `price`。
      - 海尔商品辅助字段：
        - `is_haier_product`：是否为海尔商品，仅根据 `source == haier` 判断。
        - `haier_info`：仅当为海尔商品且存在 `product_code` 时返回，结构为：`{ product_code, product_model, product_group, supply_price, invoice_price, market_price, is_sales, no_sales_reason, warehouse_code, warehouse_grade, last_sync_at }`。
      - 图片与拉页：
        - `main_images`：主图列表，优先使用本地上传的图片；如为空且存在海尔主图 `product_image_url`，则使用该 URL 作为主图。
        - `detail_images`：详情图列表，优先使用海尔拉页 `product_page_urls`；若海尔拉页为空，则回退到本地上传的详情图（最多 50 张）。
      - SKU 聚合：
        - 当商品存在启用的 `skus` 时，响应中会附带 `skus` 与 `spec_options`，并自动聚合库存与价格：`stock` 为启用 SKU 库存之和，`price/display_price/discounted_price` 为对应最小值，便于前端直接展示区间内最低价格。
  - `GET /products/by_category/` 按分类筛选 `backend/catalog/views.py`
  - `GET /products/by_brand/` 按品牌筛选，支持 `category_id` 限定到某个分类树 `backend/catalog/views.py`
  - `GET /categories/` 分类列表 `backend/catalog/urls.py:7`
    - 数据结构：`{ id, name, order, logo }`（`logo` 为可选的图片 URL）
  - `GET /brands/` 品牌列表 `backend/catalog/urls.py:9`
    - 返回的 `logo` 会自动补全为当前请求域名下的绝对 URL；提交 `/media/...` 或完整地址均可，后端会在保存时规范化路径。
    - 若历史数据存有其他域名的媒体 URL（如旧 CDN 域名），响应时会剥离相同资源的域名并按当前请求域名重建绝对地址；外部/CDN 域名的完全外链则保持不变。
  - `POST /media-images/` 图片上传 `backend/catalog/urls.py:8`
  - `GET/POST/... /home-banners/` 首页轮播图管理 `backend/catalog/urls.py:8`
    - GET（公开）：返回启用的轮播图列表，按 `order` 升序。
    - 查询参数：`position` 继续支持固定专区轮播；`special_zone=<id>` 返回指定动态运营专区轮播。
    - POST/PATCH/DELETE（管理员）：创建/更新/删除轮播图。
    - 数据结构：`{ id, title, position, special_zone, special_zone_id, order, is_active, image_id, image_url, created_at }`。
  - `POST /home-banners/upload/` 上传图片并创建轮播图（管理员） `backend/catalog/views.py`
    - 表单字段：`file`（必填）、`title`（可选）、`link_url`（可选）、`order`（可选，默认 `0`）、`is_active`（可选，默认 `true`）。
    - 返回：已创建轮播图数据，包含 `image_url` 为完整可访问地址。
  - `GET/POST/PATCH/DELETE /special-zones/` 动态运营专区 `backend/catalog/urls.py`
    - `GET /special-zones/?store=<store_id>`：公开返回指定店铺下 `is_active=true`、`show_on_home=true` 且处于有效期内的专区，按 `home_order` 升序。
    - 字段：`store_id`、`title`、`slug`、`kind(platform_activity|store_activity|activity|promotion|category|brand|custom)`、`subtitle`、`cover_image`、`is_active`、`show_on_home`、`home_order`、`start_at`、`end_at`。
    - 权限：平台管理员可跨店创建和维护；店铺管理员只能维护自己店铺下的 `store_activity`。如“新品上新”这类店铺活动，使用 `store_activity` + 商品绑定手动配置。
    - 商品绑定：`GET/POST/DELETE /special-zones/{id}/products/` 读取或维护专区商品；商品必须与专区属于同一店铺，返回时只包含启用绑定并按绑定 `order` 排序。
    - 管理端商品绑定：店铺管理员或平台管理员可追加 `include_inactive=true` 读取绑定记录，返回 `product`、`order`、`is_active`，用于后台调整排序和恢复隐藏商品。
    - 商品列表兼容：`GET /products/?special_zone=<id>` 可按动态专区筛选商品；旧固定专区字段与 `position` 仍保留兼容。
  - `GET/POST/PATCH/DELETE /home-store-cards/` 首页卡片 `backend/catalog/urls.py`
    - 用途：配置庆勋主店/平台首页橱窗卡片，不用于“新品上新”活动。
    - 字段：店铺、`store_type`、`store_is_main`、标题、副标题、排序、启停、1 个主推商品、4 个副推商品、至少 3 个一级分类。
    - 权限：公开 GET 只返回启用卡片；POST/PATCH/DELETE 仅平台管理员可用。
  - `GET /cases/` 案例列表（公开）`backend/catalog/urls.py`
    - 返回字段：`{ id, title, order, is_active, cover_image_id, cover_image_url, created_at, updated_at }`
    - 说明：非管理员默认只返回 `is_active=true` 的案例，并按 `order` 升序。
  - `GET /cases/{id}/` 案例详情（公开）`backend/catalog/urls.py`
    - 返回字段：在列表字段基础上包含 `detail_blocks`
    - `detail_blocks`：图文详情块数组 `[{ id, block_type, text, order, image_id, image_url }]`
    - 说明：详情块用于实现“详细（图文）”，支持文本块与图片块按 `order` 排序组合展示。
- 订单与支付：
  - `GET /cart/my_cart/` 获取购物车 `backend/orders/views.py:1661`
    - 响应保留原平铺 `items`，并新增 `store_groups`，每组包含 `store_id`、`store_name`、`store_logo`、`store_type`、`store_is_main`、`item_count`、`total_quantity` 和该店铺下的 `items`。
    - 店铺顺序按购物车项加入顺序确定：某店铺最早加入的商品越早，该店铺越靠前；`store_is_main` 用于前端将主店铺入口返回平台首页；单个购物车项返回 `is_available` 与 `unavailable_reason`，用于前端拦截已下架、规格下架、库存不足或合作店铺仅展示商品。
  - `GET/POST/... /orders/` 订单 CRUD `backend/orders/urls.py:3`
  - `GET /orders/my_orders/` 我的订单 `backend/orders/views.py:113`
    - 查询参数：`status`（支持单状态如 `paid` 或多状态逗号分隔如 `returning,refunding,refunded`）。当传入 `returning` 时，除订单本身状态为 `returning` 外，还会包含存在退货申请且状态为 `requested|approved|in_transit|received` 的订单；当传入 `completed` 时，将排除上述处于退货流程中的订单。
    - 结算单兼容：跨店结算会创建一张支付主单和多张履约子单；列表默认隐藏支付主单，仅展示可履约的子单。需要排查支付主单时可传 `include_checkout_main=1`。
  - `POST /orders/create_order/` 创建订单 `backend/orders/views.py:136`
  - `POST /orders/create_batch_orders/` 批量创建订单 `backend/orders/views.py:235`
    - 请求体：
      - `items` 商品列表（`[{ product_id, sku_id, quantity }]`）
      - `address_id` 收货地址ID
      - `note` 备注（可选）
      - `payment_method` 支付方式：`online | credit`（默认 `online`）。当为 `credit` 时将直接记录采购到信用账户并将订单置为 `paid`，不创建支付记录；当为 `online` 时创建对应支付记录。
      - `method` 在线支付渠道：`wechat | alipay | bank`（仅当 `payment_method=online` 时有效，默认 `wechat`）
    - 结算拆单：后端创建 `CheckoutOrder` 作为一次结算和支付聚合，并按 `store_id + product_id` 生成子单；同一 SPU 下的多个 SKU 会保留在同一子单的明细中。
    - 合作店铺限制：`store_type=partner` 的商品仅展示，`add_item`、`update_item`、`create_order` 和 `create_batch_orders` 均会拒绝购买，返回“合作店铺商品仅展示，暂不支持购买”。
    - 响应兼容：`order` 仍返回支付主单，`payment` 绑定该主单；`order.child_orders` 返回可发货、售后、退款的子单摘要。
  - `PATCH /orders/{id}/cancel|ship|complete|confirm_receipt/` 状态流转 `backend/orders/views.py:313`
    - 跨店结算后，履约操作应使用列表或 `child_orders` 中返回的子单 `id`，不要对支付主单做发货或售后操作。
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
    - 微信支付：统一使用平台/主店铺商户号普通收款，JSAPI 下单不传 `settle_info.profit_sharing=true`，不要求微信分账权限。
    - 店铺分账：支付成功后按子单生成 `StoreProfitSharingEntry` 内部店铺分账流水；合作店铺商品当前不能新下单，因此不会产生新的合作店铺分账流水。历史流水保留，可继续由平台管理员查看、更新到期状态或标记人工结算。
  - `POST /payments/callback/{provider}/` 支付回调 `backend/orders/urls.py:12`
  - `GET /profit-sharing-entries/` 店铺分账流水列表（平台管理员），支持 `status`、`checkout_order`、`store` 过滤。
  - `POST /profit-sharing-entries/mark_available/` 将已到冻结期的店铺分账流水转为可结算。
  - `POST /profit-sharing-entries/share/` 微信分账已停用，接口返回 `410 Gone`。
  - `POST /profit-sharing-entries/{id}/mark_manual_settled/` 将异常或到期流水标记为人工结算。
  - `GET/POST/... /discounts/` 折扣管理 `backend/orders/views.py:980`
  - `POST /orders/{id}/request_invoice/` 申请发票（仅订单所有者，订单需 `completed`）`backend/orders/views.py:362`
  - `GET/POST/... /invoices/` 发票管理（普通用户仅看到自己的；管理员可开具/取消）`backend/orders/urls.py:9`
- 客服 Support（前缀 `/api/support/` 与 `/api/v1/support/`）：
  - 聊天会话现在按店铺隔离：`SupportConversation.store` 标记会话所属店铺，历史会话迁移到主店。
  - 用户从店铺页、店铺商品或店铺订单进入客服时，前端传 `store_id`；个人中心客服没有店铺上下文，默认主店。
  - 店铺管理员可在商家后台查看和回复本店聊天会话；平台客服/平台管理员可查看全部会话。回复模板仍仅平台客服/平台管理员维护。
  - 直接聊天 Chat：
    - `GET /support/chat/` 获取当前用户的会话消息 `backend/support/views.py:412`
      - 查询参数：`after`（ISO 时间）、`limit`（条数）、`user_id`（仅客服/管理员）
      - 返回字段：消息数组 `{ id, conversation, sender, sender_username, role, content, content_type, content_payload, template, attachment_type, attachment_url, order_info, product_info, created_at }`
      - 说明：系统按 `用户 + 店铺` 自动维护会话；未传 `store_id` 时默认主店。
    - `POST /support/chat/auto-reply/` 触发当前用户的自动回复 `backend/support/views.py:389`
      - 触发时会更新 `last_user_entered_at` 以记录用户进入会话时间
      - 空闲触发基准优先使用 `last_user_entered_at`，为空时依次回退到 `last_user_message_at/updated_at/created_at`
      - 默认返回 `debug` 字段，包含触发判定信息
      - 同时在服务端日志输出 `SUPPORT_AUTO_REPLY_DEBUG`，便于排查触发条件（控制台与 `backend/logs/app.log`）
      - 日限额与日统计按照北京时间（Asia/Shanghai）计算
    - `POST /support/chat/` 发送消息（支持文本、图片、视频、订单、商品）`backend/support/views.py:437`
      - 请求方式：`multipart/form-data`
      - 表单字段：
        - `content` 文本（可选；当未上传附件时必填）
        - `attachment` 文件（可选；支持图片或视频）
        - `attachment_type` 类型（可选；`image|video`，未提供时将根据 `Content-Type` 自动判定）
        - `user_id` 目标用户ID（仅客服/管理员）
        - `order_id` 关联订单ID（可选；仅允许关联当前会话用户的订单）
        - `product_id` 关联商品ID（可选；与 `order_id` 互斥）
        - `template_id` 快捷回复模板（仅客服/管理员，启用模板可用）
      - 返回字段：`{ id, ticket, sender, sender_username, role, content, content_type, content_payload, template, attachment_type, attachment_url, order_info, product_info, created_at }`
        - `order_info`：当关联了订单时返回 `{ id, order_number, status, quantity, total_amount, product_id, product_name, image }`
        - `product_info`：当关联了商品时返回 `{ id, name, price, image }`
      - 校验：当 `attachment` 存在且类型无法判定或不为 `image|video` 时返回 `400`。
    - 存储与序列化：
      - 附件存储路径：`support/attachments/%Y/%m/%d/`（`backend/support/models.py:33`），上传后可通过返回的 `attachment_url` 直接访问。
      - 附件类型字段：`attachment_type` 支持 `image|video` 并建立索引（`backend/support/models.py:34`）。
  - 自动回复与模板：
    - `GET/POST/PATCH/DELETE /support/reply-templates/` 客服模板管理（仅客服/管理员）
      - 字段：`template_type(auto|quick)`、`title`、`content`、`content_type(text|card|quick_buttons)`、`content_payload`、`group_name`、`is_pinned`、`enabled`
      - 自动回复字段：`trigger_event(first_contact|idle_contact)`、`idle_minutes`、`daily_limit`、`user_cooldown_days`
      - idle_contact 计算基于用户上次进入会话时间（`last_user_entered_at`），为空时回退到最近的用户消息/会话更新时间
      - 统计字段：`usage_count`、`last_used_at`
      - 自动回复消息会写入为略晚于触发用户消息的时间，避免增量拉取遗漏
    - `POST /support/conversations/{id}/auto-reply/` 手动触发自动回复（仅客服/管理员）
      - 默认返回 `debug` 字段，包含触发判定信息
    - `content_payload` 用途：
      - `card`：`{ title, description, image_url, link_type, link_value }`
      - `quick_buttons`：`{ buttons: [{ text, value }] }`
  - 问题建议工单 FeedbackTicket（独立工单，不走聊天）：
    - `GET /support/feedback-tickets/stores/` 获取可提交问题建议的启用店铺列表。
    - `POST /support/feedback-tickets/upload-image/` 上传单张图片附件，返回 `{ path, url }`；附件存储路径为 `support/feedback/%Y/%m/%d/`。
    - `GET /support/feedback-tickets/` 工单列表，普通用户仅返回自己的工单；店铺后台用户返回可管理店铺的工单；平台管理员和 support 返回全部可见工单。
      - 查询参数：`status`、`ticket_type`/`type`、`store`/`store_id`、`date_from`/`created_from`、`date_to`/`created_to`、`search`/`keyword`。
    - `POST /support/feedback-tickets/` 用户创建问题或需求工单。
      - 请求体：`store_id`、`ticket_type=question|requirement`、`title`、`content`、`contact_phone`、`attachments`。
      - 校验：标题 `5-60` 字，内容 `10-1000` 字；只支持图片，单次最多 9 张；后台账号不能代用户创建。
    - `GET /support/feedback-tickets/{id}/` 查看工单详情，返回用户提交内容和处理记录。
    - `POST /support/feedback-tickets/{id}/supplement/` 用户补充文字或图片；关闭后不可补充，补充后状态回到 `pending`。
    - `POST /support/feedback-tickets/{id}/reply/` 后台回复，回复内容必填，可附图片；回复后状态为 `replied`。
    - `POST /support/feedback-tickets/{id}/close/` 关闭工单，关闭后只读。
    - `GET /support/feedback-tickets/stats/` 返回当前账号可见的待处理数量 `{ pending_count }`，用于商家后台菜单角标。
    - 状态：`pending` 待处理、`replied` 已回复、`closed` 已关闭。
    - 权限：小程序用户仅自己的工单；`store_admin` 可看/回/关本店；历史店铺角色按 `store_admin` 兼容；`platform_admin` 可看/回/关全部；`support` 可看/回全部但不能关闭。
    - 相关模型：`FeedbackTicket`、`FeedbackTicketReply`（`backend/support/models.py`）。
  - 环境差异：
    - 开发与生产环境均注册聊天、回复模板和问题建议工单端点 `backend/support/urls.py`。
    - 聊天中店铺管理员仅可查看本店会话；平台客服/平台管理员可查看全部会话；普通用户仅能看到自己的会话消息。
    - 问题建议工单按用户、店铺成员、平台管理员和 support 角色分别隔离。

> 聊天说明：为简化实现，后端通过轮询/增量拉取的方式支持聊天体验。前端实现建议：
> 1. **增量拉取**：利用 `after` 参数传入本地缓存中最后一条消息的时间，实现高效的增量更新。
> 2. **本地缓存**：建议前端缓存消息记录（如 localStorage），减少重复拉取并提升首屏加载速度。
> 3. **离线队列**：发送消息时可先存入本地队列，网络恢复后自动重试，提升弱网环境下的可靠性。
> 4. **状态反馈**：发送消息会刷新会话的 `updated_at`，以便列表按最近活跃排序。

> 相关模型：`SupportConversation`、`SupportMessage`、`SupportReplyTemplate`（`backend/support/models.py`）
> - `SupportMessage` 新增：`attachment(FileField)`、`attachment_type(image|video)`，文本字段 `content` 允许为空；返回的 `attachment_url` 为可直接访问的绝对地址。
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
  - 回调处理：按 `PlatformOrderNo`（订单号，对应本地 `order_number`）定位订单并更新 `haier_order_no/haier_status`；下单时 `onlineNo` 与 `soId` 均使用本地订单号，避免子订单号与平台订单号不一致
  - 回调安全：配置 `YLH_CALLBACK_APP_KEY` 与 `YLH_CALLBACK_SECRET` 做 AppKey 校验与签名验证
  - 调试日志：
    - `INTEGRATIONS_API_DEBUG=True` 时输出海尔/YLH API 请求与响应 debug 信息（已脱敏），并将 `integrations` 日志级别提升为 `DEBUG`
    - `INTEGRATIONS_CALLBACK_DEBUG=True` 输出 YLH 回调处理 debug 信息（已脱敏），包括签名生成的过滤参数、排序顺序和计算结果（不包含密钥本身）

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
- 生产运行：生产/预发 Compose 已使用 Gunicorn 启动 Django，并通过 `docker/Dockerfile.backend.prod` 在镜像 build 阶段安装后端依赖。运行阶段只执行迁移、静态收集和 Gunicorn，不再安装 Python 依赖或挂载后端源码目录。
- 生产调试日志：`.env.production` 建议显式设置 `WECHAT_PAY_DEBUG=False`、`INTEGRATIONS_API_DEBUG=False`、`INTEGRATIONS_CALLBACK_DEBUG=False`。需要排查微信支付或海尔/YLH 集成问题时再短时间打开，排障完成后关闭。

## 开发环境切换到 PostgreSQL（不保留数据，适合小白）
- 目标：把本地数据库从默认 SQLite 改为 PostgreSQL，直接清空并重新初始化数据。
- 适用系统：macOS（已验证），Windows/Linux 可参考 Docker 方案。

### 一、安装 PostgreSQL（二选一）
- Homebrew 安装：
  - `brew install postgresql@16`
  - `brew services start postgresql@16`
  - 验证：`psql --version`
- Docker 安装：
  - `docker run -d --name electric-postgres -p 5432:5432 -e POSTGRES_USER=electric -e POSTGRES_PASSWORD=electric -e POSTGRES_DB=electric_dev postgres:16`

### 二、创建数据库和用户（本地服务方式）
- 进入 psql：`psql postgres`
- 执行以下命令（全部复制粘贴即可）：
  - `CREATE USER electric WITH PASSWORD 'electric';`
  - `CREATE DATABASE electric_dev OWNER electric;`
  - `GRANT ALL PRIVILEGES ON DATABASE electric_dev TO electric;`
  - 退出：`\q`

### 三、配置后端使用 PostgreSQL（开发环境快速切换）
- 在项目根目录新建或编辑 `.env`（项目会自动加载 .env，参见 `backend/backend/settings/env_config.py:16`）：
  - `DJANGO_ENV=development`
  - `DJANGO_DB=postgres`
  - `SECRET_KEY=dev-secret`
  - `ALLOWED_HOSTS=localhost,127.0.0.1`
  - `CORS_ALLOWED_ORIGINS=http://127.0.0.1:8000,http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173`
  - `POSTGRES_DB=electric_dev`
  - `POSTGRES_USER=electric`
  - `POSTGRES_PASSWORD=electric`
  - `POSTGRES_HOST=127.0.0.1`
  - `POSTGRES_PORT=5432`
- 切换逻辑：开发环境通过 `DJANGO_DB=postgres` 启用 PostgreSQL（参见 `backend/backend/settings/env_config.py:205`）。生产环境始终使用 PostgreSQL（参见 `backend/backend/settings/production.py:13`），无需额外配置切换。

### 四、清理原有 SQLite 并初始化（不保留数据）
- 删除旧库文件：`rm backend/backend/db.sqlite3`
- 安装依赖（使用 uv）：
  - `pip install uv`
  - `uv sync`
- 迁移数据库：`python manage.py migrate`
- 创建管理员（可选）：`python manage.py createsuperuser`
- 启动服务：`python manage.py runserver`

### 五、验证与常见问题
- 验证连接：启动后在日志中应看到 `django.db.backends.postgresql`；也可运行 `psql -U electric -d electric_dev -c "\dt"` 查看表。
- 连接失败（认证错误）：确认 `.env` 的 `POSTGRES_*` 与数据库中的用户名/密码一致；Docker 场景下主机与端口是 `127.0.0.1:5432`。
- HTTPS 重定向导致无法访问：确保 `.env` 中设置了 `SECURE_SSL_REDIRECT=False`。
- CORS 报错：确保 `.env` 中 `CORS_ALLOWED_ORIGINS` 包含前端来源（如 `http://localhost:5173`）。

### 六、回滚到 SQLite（如需）
- 修改 `.env`：`DJANGO_ENV=development`
- 删除 PostgreSQL 中的库（可选）：`dropdb electric_dev`（Docker 可执行 `docker exec -it electric-postgres dropdb -U electric electric_dev`）
- 删除 Django 迁移产生的表不会影响代码；重新运行 `python manage.py migrate` 会生成新的 SQLite 数据库 `backend/backend/db.sqlite3`。

### 七、切换机制说明
- 开发模式默认使用 SQLite（`env_config.py:219`）。当设置 `DJANGO_DB=postgres` 时，开发模式将改用 PostgreSQL（`env_config.py:205`）。
- 生产模式始终使用 PostgreSQL，并严格校验环境变量（`production.py:13`、`env_config.py:236`）。
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
- 图片上传：通过 `POST /api/catalog/media-images/` 上传图片，返回的 `url` 可作为 `evidence_images` 列表元素传入退货接口。
 - 状态机配合：填写退货物流后，若订单允许，将进入 `returning` 状态；完成退款后进入 `refunded` 并释放库存（`backend/orders/state_machine.py:203`）。
-
## 生产环境 .env 示例
- 在生产环境中，可参考如下 `.env` 模板（请替换为真实值）：
```
DJANGO_ENV=production
DJANGO_SETTINGS_MODULE=backend.settings.production
SECRET_KEY=please-change-to-strong-secret
DEBUG=False
ALLOWED_HOSTS=yourdomain.com
CORS_ALLOWED_ORIGINS=https://yourdomain.com

POSTGRES_DB=electric_miniprogram
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-strong-password
POSTGRES_HOST=your-postgres-host
POSTGRES_PORT=5432

SECURE_SSL_REDIRECT=True
WECHAT_PAY_DEBUG=False
INTEGRATIONS_API_DEBUG=False
INTEGRATIONS_CALLBACK_DEBUG=False
MEDIA_URL=/media/
```
- 校验：生产启动时会检查必需变量是否齐全（`env_config.py:236`）。

## 生产管理员账号策略
- 生产数据库应预先存在受控超级管理员；`POST /api/admin/login/` 与 `POST /api/password_login/` 在 `DJANGO_ENV=production` 下不会创建首个超级管理员，也不会在无管理员时把普通账号自动提升为超级管理员。
- `reset_admin` 管理命令在生产环境只允许重置已有后台账号；如果找不到任何 `is_staff=true` 用户会直接失败，避免线上匿名初始化超级管理员。

## 生产上线剩余后端事项
- P1：调试开关默认值。当前代码仍需后续收紧 `WECHAT_PAY_DEBUG`、`INTEGRATIONS_API_DEBUG`、`INTEGRATIONS_CALLBACK_DEBUG` 的默认行为，生产 `.env.production` 先显式关闭。
