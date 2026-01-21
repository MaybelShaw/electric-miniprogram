# 商户管理端技术文档（Vite + React + Ant Design）

## 概述
- 基于 `React 18` 与 `Vite` 的商户后台，提供品牌/品类/商品/订单/折扣、公司认证、信用账户、对账单与交易管理等功能。

## 技术栈
- 框架：React、React Router
- UI：Ant Design、ProComponents
- 网络：Axios（统一 `/api` 代理）
- 构建：Vite、TypeScript

## 目录与架构
- 目录：`merchant/src/`
  - `pages/` 页面模块（用户、品牌、品类、商品、订单、折扣、公司认证、信用账户、对账单、交易）
  - `components/` 布局与通用组件（如 `Layout`）
  - `services/` 统一 API 封装 `merchant/src/services/api.ts:1`
  - `utils/` 认证工具与通用方法
  - `App.tsx`：路由与登录保护 `merchant/src/App.tsx:16`

## 开发与构建
- 启动开发：
  ```bash
  npm install
  npm run dev
  # http://localhost:5173
  ```
- 构建与预览：
  ```bash
  npm run build
  npm run preview
  ```

## 环境变量
- 后端代理地址：`VITE_BACKEND_ORIGIN`
  - 在 `.env.development` 或 `.env.production` 指定，如：
  - `VITE_BACKEND_ORIGIN=http://127.0.0.1:8000`
- 说明与用法：`merchant/ENVIRONMENT.md:11`
  - Vite 代理片段：`vite.config.ts` 中将 `/api` 代理到该 Origin

## 路由结构
- 登录保护：`merchant/src/App.tsx:16`
- 主要路由：`merchant/src/App.tsx:31`
  - `/users` 用户管理
  - `/brands` 品牌管理
  - `/categories` 品类管理
  - `/products` 商品管理
  - `/orders` 订单管理
  - `/discounts` 折扣管理
  - `/company-certification` 公司认证审核
  - `/credit-accounts` 信用账户
  - `/account-statements` 账务对账单
  - `/account-transactions` 账务交易记录
  - `/invoices` 发票管理
  - `/home-banners` 轮播图管理
  - `/cases` 案例管理

## 页面与操作流程
- 用户管理：列表、创建/编辑、设为管理员/取消管理员 `merchant/src/services/api.ts:8`
  - 统计功能已分离至独立页面“用户统计”
- 用户统计：独立页面，采用现代化 ProCard 布局，通过顶部标签页切换查看“平台统计”或“用户统计”
  - 平台统计：默认展示平台整体交易数据（按月/年），顶部提供关键指标卡片（总订单数、总交易金额），直观展示业务概况。
  - 用户统计：提供用户搜索功能，支持通过用户名或手机号搜索并选择特定用户。选择用户后展示该用户的订单总数、收藏数、已完成订单数及交易趋势。
  - 可视化增强：
    - 订单数使用彩色标签（Tag）高亮显示
    - 交易金额配备进度条（Progress），直观展示金额占比
    - 表格底部自动计算本页总计
  - 统计维度：支持按年/月切换，可选年份，可选是否包含“已支付未完成”订单
  - 数据导出：点击“导出Excel”按钮，即可下载当前筛选条件下的统计报表
  - API支持：
    - 数据接口：`GET /api/users/{id}/transaction_stats/`、`GET /api/users/customers_transaction_stats/`
    - Excel导出：`GET /api/users/{id}/export_transaction_stats/`、`GET /api/users/export_customers_transaction_stats/`
- 销售统计：独立页面，提供基于地区和商品的销售分析
  - 地区销售统计：
    - 图表可视化：支持按销售金额、订单数、销售数量展示饼图
    - 数据表格：展示各省/市/区县的详细数据，支持排序
    - 筛选：支持按时间范围、行政级别（省/市/区）、特定商品筛选
  - 商品地区分布：
    - 图表可视化：展示特定商品在各地区的销售分布（金额/数量/订单数）的饼图
    - 数据表格：展示详细分布数据
    - 筛选：支持按时间范围、行政级别筛选
  - API支持：`GET /analytics/regional_sales/`、`GET /analytics/product_region_distribution/`
- 品牌/品类/商品：CRUD，删除支持强制删除参数（品牌） `merchant/src/services/api.ts:20`
- 新增/编辑商品表单中的“品牌/品项”下拉数据来自 `GET /api/catalog/brands/` 与 `GET /api/catalog/categories/?level=item`（接口默认分页）。实现位置：`merchant/src/pages/Products/index.tsx:1`
- 下拉等“需要全量数据”的场景使用 `fetchAllPaginated` 拉取全部分页数据：`merchant/src/utils/request.ts:10`
- 若数据库已有更多条目但下拉仅显示 20 条，优先在浏览器 Network 检查是否实际请求了下一页，或确认服务器已更新到最新前端构建产物（可通过重启对应容器/进程生效）
  - **海尔商品查询**：在创建/编辑海尔来源的商品时，支持输入海尔产品编码并点击“查询”按钮，自动调用海尔API获取商品详情。
    - 自动填充：名称（自动映射型号）、价格（含供价/开票价/市场价/返利）、库存。
    - 优化体验：自动过滤库位编码、仓库等级、内部产品组等冗余字段，仅展示核心业务信息。
  - 删除策略：后端禁用级联删除
    - 删除分类：当存在子分类或产品时禁止删除，返回提示信息
    - 删除品牌：当存在关联产品时禁止删除，返回提示信息
  - 分类层级（后端）：品类 → 子品类 → 品项 → 单品
    - 创建子品类时需选择父“品类”；创建品项时需选择父“子品类”
    - 产品关联建议指向“品项”，兼容指向“子品类”
- 订单管理：取消/发货/完成、海尔推送与物流查询 `merchant/src/services/api.ts:53`
  - **发货操作**：管理员点击发货时，需在弹窗中填写快递单号与物流公司。
  - **取消订单**：支持对 `pending` 和 `paid` 状态的订单进行取消。点击取消时需在弹窗中填写取消原因与备注。
  - **退货与退款**：新增退货处理动作（对接后端接口）
    - **验收退货**：当订单有退货申请且状态为 `requested`（已申请）或 `in_transit`（退货在途）时，管理员可点击“验收退货”按钮，填写验收备注后确认收货。
    - **完成退款**：当退货状态为 `received`（已收到退货）时，管理员可点击“完成退款”按钮，系统将执行退款逻辑（如冲减信用账户欠款）并将订单状态更新为 `refunded`。
    - **详情查看**：订单详情抽屉中新增“退货信息”板块，展示退货原因、物流信息、凭证图片及处理记录。
    - 接口映射：
      - 用户发起：`POST /api/orders/{id}/request_return/`
      - 用户补充：`PATCH /api/orders/{id}/add_return_tracking/`
      - 管理员验收：`PATCH /api/orders/{id}/receive_return/`
      - 管理员退款：`PATCH /api/orders/{id}/complete_refund/`
- 轮播图管理：
  - 支持按位置管理轮播图：首页、礼品专区、设计师专区
  - 功能：列表查看、新增、编辑、删除、启用/禁用
  - 接口：`GET/POST/PATCH/DELETE /api/catalog/home-banners/`，`POST /api/catalog/home-banners/upload/`
- 案例管理：
- 折扣管理：创建/更新/删除、批量设置目标（后端支持） `backend/orders/views.py:1047`
- 公司认证：审核通过/拒绝、详情弹窗操作 `merchant/src/pages/CompanyCertification/index.tsx:262`
- 信用账户：列表与编辑（额度、账期、激活状态） `merchant/src/services/api.ts:74`
- 对账单：
  - 列表筛选与状态展示 `merchant/src/pages/AccountStatements/index.tsx:20`
  - 创建对账单（账期选择 + 账户选择） `merchant/src/pages/AccountStatements/index.tsx:296`
  - 确认/结清操作与刷新 `merchant/src/pages/AccountStatements/index.tsx:113`
  - 导出为 Excel（Blob 下载） `merchant/src/pages/AccountStatements/index.tsx:147`
  - 详情抽屉（基本信息 + 财务汇总 + 交易明细） `merchant/src/pages/AccountStatements/index.tsx:332`
- 交易记录：列表与筛选（付款状态、日期范围） `merchant/src/services/api.ts:90`
- 发票管理：
  - 列表：展示发票请求，支持按状态/发票类型/抬头筛选
  - 订单详情：点击订单号可快速查看关联订单的详细信息（商品、金额、收货信息等）
  - 详情：查看发票详细信息（含订单号、用户信息、金额等）
  - 开具：填写发票号码与文件链接，完成开票
  - 取消：对已开具或请求中的发票进行作废/取消操作

## 客服支持页面
- 页面位置：`merchant/src/pages/Support/index.tsx`
- 能力概览：
  - 会话列表展示，按更新时间排序。
  - 实时聊天：基于轮询机制的实时消息收发。
  - 发送消息：支持文本、**图片**与**视频**附件，以及关联**订单**或**商品**。
  - 快捷回复：支持按关键词/分组检索模板，支持置顶排序与预览。
  - 模板管理：支持列表筛选、新增、编辑、删除、启用/停用、分组与置顶配置。
- 模板列表：默认展示全部模板类型，可按“模板类型”筛选。
- 模板入口：左侧栏“模板管理”（/support/templates）。
  - 模板类型：纯文本、图文卡片、快捷按钮（内容由 `content_type` 与 `content_payload` 决定）。
- 自动回复：需配置触发条件（首次联系/长时间未联系），长时间未联系需填写分钟数。
  - 选择发送：弹窗选择订单（`ProTable`）或商品，发送后在聊天中以卡片形式展示。
- 渲染细节：
  - 会话列表：展示用户、最新消息预览（支持多媒体类型识别）、更新时间。
  - 消息记录：
    - 区分“我”与“用户”的消息气泡。
    - 订单卡片：显示订单号、产品图、产品名与金额，并在右上角显示状态标签。
    - 商品卡片：显示主图、名称与价格。
    - 图片/视频：图片使用 `AntImage`；视频由浏览器原生播放器处理。
- 权限：
  - 客服/管理员可通过 `user_id` 指定目标用户并向其会话发送消息。
  - 消息支持已读/未读状态（后端支持，前端暂未展示）。

## 账务对账单页面
- 列表、筛选、状态、操作与导出：`merchant/src/pages/AccountStatements/index.tsx:256`
- 详情抽屉与财务汇总：`merchant/src/pages/AccountStatements/index.tsx:332`
- 行为与接口：
  - 创建：`createAccountStatement`
  - 确认：`confirmAccountStatement`
  - 结清：`settleAccountStatement`
  - 导出：`exportAccountStatement`
  - 获取详情：`getAccountStatement`
- 对应后端路由：`backend/users/urls.py:22`（`account-statements`）

### 账期规则
- 固定账期按月结算，正常账期为 `30` 天，实际到期日为对应月份的最后一天。
- 建议在“生成对账单”时选择整月的起止日期（如 `2025-11-01` 至 `2025-11-30/31`）。
- 列表与详情展示的“账期内应付/已付/逾期金额”与后端对账逻辑一致：
  - 账期内应付：到期日在所选账期内且未付款的采购金额。
  - 账期内已付：在所选账期内完成支付的采购金额。
  - 逾期金额：到期日至账期末已逾期的采购金额。

## API 封装
- 统一服务：`merchant/src/services/api.ts:74`
  - `credit-accounts`、`account-statements`、`account-transactions` 等端点
- Axios 基础：前端统一使用 `/api` 前缀，依赖 Vite 代理转发到后端

### 端点映射示例
- 对账单：
  - 列表：`GET /account-statements/`
  - 详情：`GET /account-statements/{id}/`
  - 创建：`POST /account-statements/`
  - 确认：`POST /account-statements/{id}/confirm/`
  - 结清：`POST /account-statements/{id}/settle/`
  - 导出：`GET /account-statements/{id}/export/`
- 交易记录：
  - 列表：`GET /account-transactions/`
  - 我的交易：`GET /account-transactions/my_transactions/`（前端用户端）
- 订单：
  - 发货/完成/取消：`PATCH /orders/{id}/ship|complete|cancel/`
    - 发货请求体：`{ "tracking_number": "SF1234567890" }`
    - 管理员发货时需填写快递单号，系统会记录运单号并将状态流转为 `shipped`。
  - 海尔推送：`POST /orders/{id}/push_to_haier/`
  - 海尔物流：`GET /orders/{id}/haier_logistics/`

## 权限与认证
- 登录态判断：`merchant/src/App.tsx:16`
- 登录接口：`/admin/login/`（密码登录，返回 JWT）
- 请求头：`Authorization: Bearer <token>`

## 安全与部署建议
- 登录态校验与路由保护：`merchant/src/App.tsx:16`
- 后端启用 HTTPS 与 CORS 限制；接口权限区分管理员与普通用户 `backend/common/permissions.py:70`
 - 发票权限：普通用户仅访问自己的发票；管理员可开具与取消 `backend/orders/views.py:InvoiceViewSet`
- 生产环境通过统一网关代理 `/api` 到后端服务，隔离跨域与证书配置

## 目录结构
- 源码根：`merchant/src/`
  - `pages/` 各页面模块
  - `components/` 布局与通用组件
  - `services/` API 封装
  - `utils/` 认证与工具

## 部署建议
- 生产构建使用 `npm run build`，将 `dist/` 产物发布到静态服务器或 CDN
- 在网关层配置 `/api` 反向代理到后端服务，统一域名与 HTTPS
