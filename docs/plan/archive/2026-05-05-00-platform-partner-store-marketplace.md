# 平台入驻合作店铺与商家权限收敛实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 把现有多店铺能力收敛为“庆勋愉悦家平台 + 入驻合作方店铺”的多商户经营模型，并让合作方管理员只能经营自己的商品、专区、订单、统计和账务数据。

**Architecture:** `Store` 表示一个真实经营主体，庆勋愉悦家本身也是一个 `Store`，合作方也是 `Store`。新增平台归属和公开展示字段，用于表达“这个合作店铺入驻庆勋愉悦家平台并可在平台小程序展示”，不是传统组织上下级；订单、履约、对账、交易和分账都按真实售卖店铺拆分，庆勋愉悦家作为平台方/自营店铺参与管理和抽佣。

**Tech Stack:** Django 5.2、DRF、Django migrations、Taro 4、React 18、Ant Design、Vite、Django test runner、微信开发者工具。

---

## 背景与当前问题

已归档的四个计划已经完成多店铺底座、动态专区后端、商家后台动态专区、小程序动态专区消费。但当前实现和后续计划还需要校正业务语义：

- 业务不是“主店下面管一批子店铺”的组织层级，而是类似淘宝/京东的多商户平台：庆勋愉悦家自己是一个店铺，合作方也是入驻店铺。
- 平台首页可以给合作方开“品牌店铺专区”或“合作方专区”，但该专区只是流量入口，不代表合作方变成庆勋愉悦家的下级门店。
- 小程序目前可用 `SpecialZone(kind=brand)` 或商品卡片模拟品牌入口，但缺少真正的入驻店铺列表页和店铺详情页。
- 商家后台已经按店铺上下文隐藏部分菜单，但仍属于菜单层过滤，路由和后端权限还需要同步收紧。
- 当前 `stores.permissions.is_platform_admin()` 把 `is_staff=True` 和 `role='admin'` 也视为平台管理员；如果合作方管理员为了进入商家后台被设置为 `is_staff=True`，就存在越权风险。
- 结算单、子单和服务商分账必须以真实售卖/履约店铺为归属；庆勋愉悦家既可能是平台方，也可能作为自营店铺出售自己的商品。

## 目标业务形态

庆勋愉悦家平台：

- 作为平台入口和自营店铺存在，仍是一个 `Store`。
- 承载小程序默认首页、平台运营专区、合作方店铺入口专区。
- 可以经营自己的商品、订单、专区和轮播。
- 可以作为平台方管理入驻合作方、抽佣、分账、对账和风控。

入驻合作方店铺：

- 例如 `志邦家具品牌馆`、`海尔智慧家电馆`、`慕思床垫睡眠馆`、`马可波罗瓷砖馆`。
- 入驻庆勋愉悦家平台，在平台小程序中获得店铺入口或专区入口。
- 拥有自己的商品、分类、品牌、动态专区、轮播图、订单、销售统计、对账单、交易记录。
- 合作方管理员登录 `http://127.0.0.1:3001/` 后，只看到本店经营相关菜单。

小程序路径：

- 用户登录或未登录时默认浏览庆勋愉悦家平台首页。
- 首页点击“品牌店铺专区”或“合作方专区”进入入驻店铺列表。
- 入驻店铺列表展示在庆勋愉悦家平台上架展示的合作方店铺。
- 点击某个合作方店铺进入店铺详情页。
- 店铺详情页展示该合作方店铺的轮播、介绍、分类、商品、活动专区和优惠专区。
- 用户在任意店铺详情页浏览，不获得该店铺后台权限。

## 权限设计

### 平台管理员

判定规则：

- `user.is_superuser=True`；或
- 用户拥有庆勋愉悦家平台店铺的有效 `StoreMember(role='platform_admin')`。

能力：

- 管理庆勋愉悦家自营店铺和所有入驻合作方店铺。
- 创建、编辑、停用入驻合作方店铺。
- 为任意入驻店铺代配商品、分类、品牌、专区、轮播。
- 查看跨店用户、认证、信用账户、平台级销售统计、全部订单、全部对账单和全部交易记录。
- 配置合作方店铺的支付、结算、抽佣和服务商分账参数。

### 庆勋愉悦家自营店铺管理员

判定规则：

- 用户拥有庆勋愉悦家店铺有效 `StoreMember(role='store_admin')`，但不是 `platform_admin`。

能力：

- 管理庆勋愉悦家自营商品、分类、品牌、专区、轮播、订单、销售统计、对账单和交易记录。
- 不自动拥有管理所有合作方店铺的能力。
- 是否允许其代管合作方，应通过 `platform_admin` 或单独授权实现，而不是因为属于主店就天然拥有全部权限。

### 合作方店铺管理员

判定规则：

- 用户拥有当前合作方店铺有效 `StoreMember(role='store_admin')`。
- 可以 `is_staff=True` 用于登录商家后台，但 `is_staff` 不再等同平台管理员。

可见菜单：

- 销售统计：只看本店。
- 对账单：只看本店。
- 交易记录：只看本店。
- 动态专区：只管理本店专区。
- 轮播图管理：只管理本店首页/专区轮播。
- 商品管理：本店商品。
- 分类管理：本店分类。
- 品牌管理：本店品牌。
- 订单管理：本店订单。
- 发票管理：本店订单相关发票。
- 折扣管理：本店可用折扣。

不可见菜单：

- 用户管理。
- 用户统计。
- 认证审核。
- 信用账户全局管理。
- 平台店铺管理。
- 平台成员管理。
- 支付配置、结算规则、服务商分账配置。
- 案例管理和平台级内容配置，除非后续明确开放。

### 合作方店铺员工

判定规则：

- 用户拥有当前合作方店铺有效 `StoreMember(role='store_staff')`。

能力：

- 默认只读查看销售统计、订单、商品、专区、对账和交易。
- 本计划先实现安全默认：员工不可删除，不可跨店，不可配置店铺级敏感信息。

## 数据模型语义

不要把入驻合作方建成传统组织树的“下级门店”。建议字段语义如下：

- `Store.is_main`：保留，表示系统默认平台入口店铺，通常为庆勋愉悦家。
- `Store.store_type`：新增，至少支持 `self_operated`、`partner`、`supplier`。
- `Store.platform_store`：新增，可空自关联；合作方店铺填庆勋愉悦家店铺，表示入驻到该平台展示和结算体系，不表示组织上下级。
- `Store.logo`、`cover_image`、`description`、`show_on_home`、`home_order`、`contact_phone`、`address`：新增公开展示字段。
- `Store.status`：继续控制是否可用。
- `Store.allow_haier`：仍只允许庆勋愉悦家平台/自营店按业务需要开启。

## 影响范围

- 修改：`backend/stores/models.py`
- 修改：`backend/stores/serializers.py`
- 修改：`backend/stores/views.py`
- 修改：`backend/stores/permissions.py`
- 新增：`backend/stores/migrations/0002_store_marketplace_fields.py`
- 新增：`backend/stores/tests/test_marketplace_store_public_api.py`
- 新增：`backend/stores/tests/test_store_permissions.py`
- 修改：`backend/catalog/views.py`
- 修改：`backend/catalog/serializers.py`
- 修改：`backend/orders/views.py`
- 修改：`backend/users/views.py`
- 修改：`merchant/src/services/types.ts`
- 修改：`merchant/src/services/api.ts`
- 修改：`merchant/src/components/Layout/index.tsx`
- 修改：`merchant/src/components/RoleGuard/index.tsx`
- 新增或修改：`merchant/src/utils/permissions.ts`
- 修改：`merchant/src/App.tsx`
- 修改：`merchant/src/pages/SalesStats/`
- 修改：`merchant/src/pages/AccountStatements/`
- 修改：`merchant/src/pages/AccountTransactions/`
- 修改：`frontend/src/app.config.ts`
- 新增：`frontend/src/pages/store-list/index.tsx`
- 新增：`frontend/src/pages/store-list/index.scss`
- 新增：`frontend/src/pages/store-detail/index.tsx`
- 新增：`frontend/src/pages/store-detail/index.scss`
- 新增或修改：`frontend/src/services/store.ts`
- 修改：`frontend/src/pages/home/index.tsx`
- 修改：`frontend/src/pages/special-zone/index.tsx`
- 修改：`frontend/src/types/index.ts`
- 修改：`docs/backend.md`
- 修改：`docs/frontend.md`
- 修改：`docs/merchant.md`

## 执行步骤

- [x] 写失败测试：庆勋愉悦家作为 `is_main=true` 的自营/平台入口店铺存在，合作方店铺通过 `platform_store` 入驻到庆勋愉悦家。
- [x] 写失败测试：系统仍只能有一个 `is_main=true` 店铺，但可以有多个 `store_type='partner'` 的合作方店铺。
- [x] 写失败测试：合作方店铺不能设置 `allow_haier=true`。
- [x] 写失败测试：未登录公开接口只返回 `platform_store=庆勋愉悦家`、`show_on_home=true` 且 `status=active` 的入驻合作方店铺，并按 `home_order` 排序。
- [x] 写失败测试：公开店铺详情接口返回店铺基础信息、轮播图、分类、动态专区和商品摘要，且数据只来自该店铺。
- [x] 写失败测试：`is_staff=True` 的合作方管理员不再被 `is_platform_admin()` 识别为平台管理员。
- [x] 写失败测试：庆勋愉悦家自营店铺管理员只能管理庆勋愉悦家自己的经营数据，不能天然管理合作方店铺。
- [x] 写失败测试：合作方管理员访问其他店铺商品、专区、轮播、订单、对账单和交易记录时返回空列表或 403。
- [x] 写失败测试：合作方管理员访问用户管理、认证审核、信用账户全局管理、店铺成员管理、支付配置和结算规则接口时返回 403。
- [x] 新增 `Store.store_type` 字段，至少支持 `self_operated`、`partner`、`supplier`。
- [x] 新增 `Store.platform_store` 字段，指向平台入口店铺；庆勋愉悦家可为空，合作方店铺指向庆勋愉悦家。
- [x] 新增 `Store.logo`、`Store.cover_image`、`Store.description`、`Store.show_on_home`、`Store.home_order`、`Store.contact_phone`、`Store.address` 字段。
- [x] 新增模型校验：`is_main=true` 店铺必须是 `store_type='self_operated'`；合作方店铺必须设置 `platform_store`；合作方店铺不能启用海尔能力；`platform_store` 不能指向自己。
- [x] 写数据迁移：现有唯一主店保留为庆勋愉悦家自营/平台入口店铺；现有非主店默认设为 `store_type='partner'`，`platform_store=main_store`，`show_on_home=true`。
- [x] 调整 `StoreSerializer`，补充平台归属、店铺类型、公开展示字段。
- [x] 新增 `PublicStoreSerializer`，只返回小程序公开展示字段，不暴露支付、结算、成员等管理信息。
- [x] 新增公开接口 `GET /api/stores/public/partners/?platform=<store_id>`，返回某个平台下可见合作方店铺。
- [x] 新增公开接口 `GET /api/stores/public/{id}/detail/`，返回店铺详情聚合数据。
- [x] 调整 `is_platform_admin()`：只认 `is_superuser` 或庆勋愉悦家平台店铺有效 `StoreMember.role='platform_admin'`，不再把普通 `is_staff` 或 `user.role='admin'` 自动视为平台管理员。
- [x] 新增 `has_store_role(user, store, roles)`、`can_view_store_dashboard()`、`can_manage_store_catalog()`、`can_manage_store_operations()` 等权限工具。
- [x] 调整 `get_accessible_stores()`：平台管理员返回庆勋愉悦家和全部合作方店铺；普通店铺用户只返回自己有成员关系的店铺；公开匿名仍默认庆勋愉悦家。
- [x] 调整 `get_default_store()`：平台管理员默认庆勋愉悦家；合作方用户默认自己第一个有效店铺；庆勋愉悦家自营管理员默认庆勋愉悦家。
- [x] 调整 catalog、orders、users 相关接口权限，确保合作方用户只能访问本店经营数据。
- [x] 将店铺成员、支付配置、结算规则接口限制为平台管理员；合作方管理员不可见不可改。
- [x] 商家后台新增权限映射文件，集中定义平台管理员、自营店铺管理员、合作方店铺管理员、合作方员工可访问路由和菜单。
- [x] 调整 `Layout` 菜单：非平台管理员只展示本店经营菜单，不展示平台配置菜单。
- [x] 调整 `RoleGuard` 或新增 `RouteGuard`：隐藏菜单之外，还要阻止手动输入 URL 访问平台页面。
- [x] 调整商家后台默认跳转：平台管理员进入平台概览或 `/admin/users`；普通店铺管理员进入 `/admin/sales-stats`。
- [x] 调整商家后台请求参数：普通店铺用户不显示跨店选择器；平台管理员切换店铺时显式传 `store_id`。
- [x] 调整销售统计、对账单、交易记录页面，确保展示的是当前真实经营店铺数据，并在页面标题或筛选区明确当前店铺。
- [x] 小程序新增 `storeService.getPartnerStores(platformStoreId?)` 和 `storeService.getStoreDetail(storeId)`。
- [x] 小程序新增入驻店铺列表页 `/pages/store-list/index`，展示庆勋愉悦家平台下可见合作方入口。
- [x] 小程序新增店铺详情页 `/pages/store-detail/index?store_id=<id>`，展示该店铺轮播、介绍、分类、专区和商品。
- [x] 首页动态专区中 `kind='brand'` 的“品牌店铺专区”入口跳转到 `/pages/store-list/index`，不再用商品卡片伪装店铺入口。
- [x] 店铺详情页中的动态专区点击仍跳转 `/pages/special-zone/index?zone_id=<id>&store_id=<store_id>`。
- [x] 保留旧动态专区路径兼容：没有店铺详情页参数时，首页和专区页继续按庆勋愉悦家默认店铺或显式 `store_id` 工作。
- [x] 更新后端、商家后台和小程序文档，说明平台入驻、合作方店铺入口和权限边界。

## 验证命令

- [x] `cd backend && .\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run`（使用临时 venv 执行，默认 `backend.settings.development`）
- [x] `cd backend && .\.venv\Scripts\python.exe manage.py test stores.tests.test_marketplace_store_public_api`（使用临时 venv 执行，默认 `backend.settings.development`）
- [x] `cd backend && .\.venv\Scripts\python.exe manage.py test stores.tests.test_store_permissions`（使用临时 venv 执行，默认 `backend.settings.development`）
- [x] `cd backend && .\.venv\Scripts\python.exe manage.py test catalog orders users`（使用临时 venv 执行，默认 `backend.settings.development`）
- [x] `cd backend && .\.venv\Scripts\python.exe manage.py check`（使用临时 venv 执行，默认 `backend.settings.development`）
- [x] `cd merchant && npm run build`
- [x] `cd frontend && npm run build:weapp`
- [x] 搜索 `frontend/dist`，确认没有残留运行时 `process.env`。
- [x] 搜索 `frontend/dist`，确认没有残留 `qxelectric.cn`、外部占位图域名，且默认 API 为本地 `http://127.0.0.1:8000/api`。
- [ ] 浏览器手测：平台管理员登录商家后台，能看到跨店菜单和店铺选择器。（未执行：当前未启动真实后台账号会话）
- [ ] 浏览器手测：`brand_zhibang_admin/admin` 登录商家后台，只能看到本店经营菜单，手动访问 `/admin/users`、`/admin/credit-accounts` 等页面会被重定向或拒绝。（未执行：当前未启动真实后台账号会话）
- [ ] 微信开发者工具手测：首页点击品牌店铺专区进入入驻店铺列表，点击 `志邦家具品牌馆` 进入店铺详情页。（未执行：当前环境无微信开发者工具会话）
- [ ] 微信开发者工具手测：店铺详情页能看到店铺轮播、分类、商品和店铺专区，商品列表只属于该店铺。（未执行：当前环境无微信开发者工具会话）

## 完成标准

- 数据库能表达“庆勋愉悦家平台 + 入驻合作方店铺”，但不把合作方建成组织下级门店。
- 生产环境历史数据可迁移为庆勋愉悦家自营店铺数据，已有合作方店铺可入驻到庆勋愉悦家平台，不需要删除或复制商品。
- 小程序不再把合作方店铺入口伪装成商品，而是有真实店铺列表和店铺详情路径。
- 合作方管理员登录商家后台后，只能看到并操作本店销售统计、对账单、交易记录、专区、轮播、商品、分类、品牌、订单、发票和折扣。
- 合作方管理员即使 `is_staff=true`，也不能被识别为平台管理员。
- 庆勋愉悦家自营管理员不自动拥有全部合作方店铺权限；平台管理员可以代管所有店铺。
- 后端接口权限、商家后台菜单和商家后台路由三层权限一致。
- 构建和测试通过后，本计划可单独提交并归档。

## 对后续计划的影响

- **结算单与子单重构：** 庆勋愉悦家和合作方都是真实售卖店铺。跨店统一支付时，按商品所属真实店铺拆子单；庆勋愉悦家自营商品归庆勋愉悦家子单，合作方商品归对应合作方子单。
- **微信显式快捷登录：** 用户登录后默认浏览庆勋愉悦家平台首页；进入合作方店铺详情只改变前台浏览上下文，不产生任何后台经营权限。
- **小程序设计系统与 UI 改版：** UI 计划必须新增入驻店铺列表页和店铺详情页，不再只设计普通动态专区页。
- **服务商分账与利润结算：** 分账规则应绑定真实售卖店铺。庆勋愉悦家作为平台方按规则抽佣，也可以作为自营店铺参与售卖；不能把所有店铺都当无平台关系的平级收款主体。
- **动态专区后续优化：** `SpecialZone` 继续归属具体店铺；庆勋愉悦家首页的品牌店铺专区只负责合作方入口聚合，合作方自己的专区用于店铺详情页内部运营。

