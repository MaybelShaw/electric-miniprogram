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
  - `utils/` 认证、当前店铺选择与通用方法
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
- 店铺上下文：登录后 `Layout` 调用 `GET /api/stores/current/`，平台管理员可在顶栏选择当前店铺；选中店铺会随请求作为 `store` 参数透传。
- 店铺用户：拥有激活 `StoreMember` 的账号可登录商家后台。自营店铺菜单包含本店经营入口；合作店铺只作为展示店铺，菜单收敛为本店成员、客户分组、商品、分类、品牌、轮播、活动和问题建议等展示配置入口。
- 主要路由：`merchant/src/App.tsx:31`
  - `/users` 用户管理
  - `/user-stats` 用户统计
  - `/sales-stats` 销售统计
  - `/stores` 店铺管理（新增店铺默认勾选“展示”和“首页展示”；关闭“展示”后小程序公开侧同时隐藏该店铺详情和商品等信息，关闭“首页展示”仅隐藏首页/公开店铺列表入口）
  - `/store-members` 店铺成员
  - `/brands` 品牌管理
  - `/categories` 品类管理
  - `/products` 商品管理
  - `/product-skus` SKU 管理
  - `/customer-groups` 客户分组
  - `/media-images` 媒体库
  - `/search-logs` 搜索日志（平台管理员）
  - `/inventory-logs` 库存日志
  - `/orders` 订单管理
  - `/discounts` 折扣管理
  - `/company-certification` 公司认证审核
  - `/credit-accounts` 信用账户
  - `/account-statements` 账务对账单
  - `/account-transactions` 账务交易记录
  - `/profit-sharing` 店铺分账（平台管理员在主店铺上下文）
  - `/invoices` 发票管理
  - `/home-banners` 轮播图管理
  - `/home-store-cards` 首页卡片管理（平台管理员）
  - `/special-zones` 动态运营专区
  - `/special-zone-covers` 专区封面
  - `/cases` 案例管理
  - 客服管理分组：`/admin/support-chats` 为聊天会话，`/admin/support-templates` 为自动回复，`/admin/feedback-tickets` 为问题建议工单；旧 `/support/*` 路由仅做兼容跳转。

## 页面与操作流程
- 用户管理：列表、创建/编辑、设为管理员/取消管理员 `merchant/src/services/api.ts:8`
  - 统计功能已分离至独立页面“用户统计”
- 店铺管理：新增/编辑店铺时，店铺 Logo 与封面图使用图片上传控件，上传后仍保存为 `logo`、`cover_image` URL 字段；图片上传复用 `POST /api/catalog/media-images/`。
- 店铺成员：页面位置 `merchant/src/pages/StoreMembers/index.tsx`，菜单入口 `/admin/store-members`
  - 新增成员时不再从已有用户候选中选择，而是在弹窗内填写用户名、手机号、邮箱和初始密码，提交后创建新的商户后台账号并绑定为店铺管理员。
  - 新建账号用于后台登录，后端强制 `is_staff=true`、`role=admin`、`is_superuser=false`，成员角色固定为 `store_admin`；绑定主店铺时在界面上显示为“平台管理员”，绑定普通店铺时显示为“店铺管理员”。
  - 平台管理员新增成员时可选择任意店铺；普通店铺管理员新增成员时店铺默认当前店铺且不可切换。编辑成员时保留店铺、角色和状态维护能力。
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
- 产品管理会根据当前选中店铺的 `allow_haier` 控制商品来源：未启用海尔能力的加盟/合作方店铺只显示“本地商品”，隐藏“海尔商品”选项和海尔同步区域，提交时也固定为 `source=local`。
- SKU 管理：新增/编辑 SKU 时，`image` 主图字段使用图片上传控件，上传后保存图片 URL。
- 图片上传提示（商品图片除外）：后台在相关上传控件旁标注建议尺寸或比例。店铺/品牌/分类 Logo 建议 1:1、400x400；店铺封面建议 16:9、1200x675；首页轮播建议 750x456；专区封面建议约 2:1；案例展示图建议 3:2、900x600，案例详情图建议宽度不小于 750px；客服图文卡片建议 3:2、900x600；媒体库、聊天附件与工单附件不固定比例，提示上传清晰原图并按最终场景裁剪。
- 商品新增/编辑表单支持上传 PDF 附件（最多 10 个、单个最大 20MB），后台以“原始文件名 / 显示文件名 / 操作”表格维护附件，不直接展示文件 URL；删除附件并提交商品后，后端会清理未被其他商品引用的服务器文件。
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
- 客户分组：
  - 页面位置：`merchant/src/pages/CustomerGroups/index.tsx`，菜单入口 `/admin/customer-groups`
  - 店铺管理员可维护本店客户分组、按手机号加入客户、批量粘贴手机号导入成员、维护分组产品价格表；平台管理员可按当前店铺上下文代配置。
  - 分组列表展示启用成员数/总成员数和价格规则数，用于快速判断分组是否已经完成客户归组和价格配置。
  - 同一小程序用户在同一店铺只能属于一个分组，但可以分别属于多个店铺的分组；手机号未注册时会先保存手机号，用户后续登录/绑定手机号后自动归组。
  - 分组价格支持本地商品和海尔商品的整品价、SKU 价；价格配置弹窗居中展示，录入区按商品、SKU、分组价和操作按钮分列展示，表格展示商品/SKU 默认参考价和已配置分组价，SKU 留空表示配置整品统一分组价；未配置的商品/SKU 使用默认价格，海尔商品分组价只影响本系统展示价和下单锁价，不修改海尔同步基础价。
  - 店铺页顶部的“小程序展示分组名称”开关控制用户端是否显示当前价格身份，关闭时仅展示最终价格。
  - 接口：`GET/POST/PATCH/DELETE /api/stores/customer-groups/`、`/api/stores/customer-group-members/`、`/api/stores/customer-group-prices/`
- 订单管理：取消/发货/完成、海尔推送与物流查询 `merchant/src/services/api.ts:53`
  - 列表中的“数量”列来自后端订单的总购买数量字段（汇总所有明细行的数量），与 Django 管理后台中直接展示的单个 `quantity` 字段保持逻辑一致，用于反映整单实际采购件数。
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
  - 店铺首页共用模板复用本页轮播图能力，只展示图片，不支持视频；店铺管理员维护本店轮播图，作为小程序店铺首页图片展示来源。
  - 支持按位置管理轮播图：首页、礼品专区、设计师专区、爆品专区、优惠专区
  - 支持选择动态运营专区作为轮播归属，用于 `618大促`、`夏季大促` 等专区页顶部轮播
  - 功能：列表查看、新增、编辑、删除、启用/禁用
  - 接口：`GET/POST/PATCH/DELETE /api/catalog/home-banners/`，`POST /api/catalog/home-banners/upload/`
- 动态运营专区：
  - 页面位置：`merchant/src/pages/SpecialZones/index.tsx`，菜单入口“运营管理 -> 专区配置” `/admin/special-zones`
  - 平台管理员可在专区表单选择店铺，为任意店铺创建、编辑、删除活动、优惠、品类、品牌或自定义专区
  - 店铺管理员只看到并维护本店 `store_activity`；请求会随当前店铺上下文带上 `store` 参数
  - 配置字段：标题、标识、类型、副标题、封面、首页排序、首页显示、启停、开始时间、结束时间
  - 商品绑定：在专区列表点击“商品”，可搜索本店商品并维护专区内排序与显隐，跨店商品由后端拒绝
  - 接口：`GET/POST/PATCH/DELETE /api/catalog/special-zones/`，`GET/POST/DELETE /api/catalog/special-zones/{id}/products/`
- 首页卡片管理：
  - 页面位置：`merchant/src/pages/HomeStoreCards/index.tsx`，菜单入口 `/admin/home-store-cards`
  - 用于平台/主店首页橱窗卡片：选择店铺、1 个主推商品、4 个副推商品和至少 3 个一级分类。
  - 仅平台管理员可新增、编辑、删除；店铺管理员通过轮播图和动态运营专区配置本店首页内容。
- 合作方入口文案：在“平台管理 -> 店铺管理 -> 首页配置”中配置 `首页入口标题`、`首页入口副标题`、`首页板块标题`；店铺卡片角标和描述归属具体店铺，不做统一配置。
- 案例管理：
- 折扣管理：创建/更新/删除、批量设置目标（平台管理员） `backend/orders/views.py:1047`
- 公司认证：审核通过/拒绝、详情弹窗操作 `merchant/src/pages/CompanyCertification/index.tsx:262`
- 信用账户：列表与编辑（额度、账期、激活状态） `merchant/src/services/api.ts:74`
- 对账单：
  - 列表筛选与状态展示 `merchant/src/pages/AccountStatements/index.tsx:20`
  - 创建对账单（账期选择 + 账户选择） `merchant/src/pages/AccountStatements/index.tsx:296`
  - 确认/结清操作与刷新 `merchant/src/pages/AccountStatements/index.tsx:113`
  - 导出为 Excel（Blob 下载） `merchant/src/pages/AccountStatements/index.tsx:147`
  - 详情抽屉（基本信息 + 财务汇总 + 交易明细） `merchant/src/pages/AccountStatements/index.tsx:332`
- 交易记录：列表与筛选（付款状态、日期范围） `merchant/src/services/api.ts:90`
- 店铺分账：
  - 页面位置：`merchant/src/pages/ProfitSharing/index.tsx`，菜单入口 `/admin/profit-sharing`，仅平台管理员在主店铺上下文可见；平台管理员切换到合作店铺时隐藏入口，直接访问返回 403，且页面会在店铺上下文加载并校验通过后才请求分账表格数据。
  - 分账流水表支持按状态、结算单 ID、店铺筛选，展示子单实付、平台抽佣、店铺应结算金额、收款账号、可结算时间、失败原因。
  - 平台管理员可更新到期冻结流水，并将可结算、异常或旧待配置流水标记为人工结算。
  - 当前不再调用微信分账，也不展示微信分账请求记录。
  - 接口：`GET /api/profit-sharing-entries/`、`POST /api/profit-sharing-entries/mark_available/`、`POST /api/profit-sharing-entries/{id}/mark_manual_settled/`；旧 `POST /api/profit-sharing-entries/share/` 返回 `410 Gone`。
- 发票管理：
  - 列表：展示发票请求，支持按状态/发票类型/抬头筛选
  - 订单详情：点击订单号可快速查看关联订单的详细信息（商品、金额、收货信息等）
  - 详情：查看发票详细信息（含订单号、用户信息、金额等）
  - 开具：填写发票号码与文件链接，完成开票
  - 取消：对已开具或请求中的发票进行作废/取消操作

## 客服支持页面
- 页面位置：`merchant/src/pages/Support/index.tsx`
- 能力概览：
  - 会话列表展示用户、店铺、最新消息，按更新时间排序。
  - 实时聊天：基于轮询机制的实时消息收发。
  - 发送消息：支持文本、**图片**与**视频**附件，以及关联**订单**或**商品**。
  - 快捷回复：支持按关键词/分组检索模板，支持置顶排序与预览。
  - 模板管理：支持列表筛选、新增、编辑、删除、启用/停用、分组与置顶配置；模板按店铺隔离，店铺管理员只维护本店模板。
    - 图文卡片模板的卡片图片使用图片上传控件，上传后写入 `content_payload.image_url`。
- 模板列表：默认展示全部模板类型，可按“模板类型”筛选。
- 模板入口：左侧栏“自动回复”（/admin/support-templates）。
  - 模板类型：纯文本、图文卡片、快捷按钮（内容由 `content_type` 与 `content_payload` 决定）。
- 自动回复：触发条件支持“首次联系”“长时间未联系”或同时设置，长时间未联系需填写分钟数。
  - 支持配置日限额与用户冷却天数。
  - 选择发送：弹窗选择订单（`ProTable`）或商品，发送后在聊天中以卡片形式展示。
- 渲染细节：
  - 会话列表：展示用户、最新消息预览（支持多媒体类型识别）、更新时间。
  - 消息记录：
    - 区分“我”与“用户”的消息气泡。
    - 订单卡片：显示订单号、产品图、产品名与金额，并在右上角显示状态标签。
    - 商品卡片：显示主图、名称与价格。
    - 图片/视频：图片使用 `AntImage`；视频由浏览器原生播放器处理。
- 权限：
  - 店铺管理员可查看并回复本店客服会话；平台客服/平台管理员可查看全部会话。
  - 店铺管理员可查看和维护本店回复模板；平台客服/平台管理员可查看和维护全部店铺模板。
  - 后台打开会话后通过 `conversation_id` 拉取和发送消息，避免同一用户多店会话串线。
  - 消息支持已读/未读状态（后端支持，前端暂未展示）。

## 问题建议工单页面
- 页面位置：`merchant/src/pages/FeedbackTickets/index.tsx`
- 菜单入口：
  - 平台后台：`/admin/feedback-tickets`
  - 商户管理后台：`/admin/feedback-tickets`
- 能力概览：
  - 列表展示问题/需求工单，支持按编号、标题关键词、类型、状态筛选。
  - 详情抽屉展示用户提交内容、图片附件和全部处理记录。
  - 后台可多次回复工单，回复内容必填，可附图片。
  - 店铺管理员和平台管理员可关闭工单；关闭后页面只展示历史记录，不再显示回复区。
  - 左侧菜单通过 `getFeedbackTicketStats` 轮询当前账号可见的待处理数量，并显示角标。
- 状态：
  - `pending` 待处理：用户新建或补充后进入。
  - `replied` 已回复：后台回复后进入。
  - `closed` 已关闭：店铺管理员或平台管理员关闭后进入，只读。
- 权限：
  - 平台管理员可查看、回复、关闭全部工单。
  - 店铺管理员可查看、回复、关闭本店工单。
  - 历史店铺角色按店铺管理员兼容处理。
  - support 账号可查看、回复全部工单，不能关闭。

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
  - 问题建议工单：`getFeedbackTickets`、`getFeedbackTicket`、`getFeedbackTicketStats`、`replyFeedbackTicket`、`closeFeedbackTicket`
- Axios 基础：前端统一使用 `/api` 前缀，依赖 Vite 代理转发到后端

### 端点映射示例
- 问题建议工单：
  - 列表：`GET /support/feedback-tickets/`
  - 详情：`GET /support/feedback-tickets/{id}/`
  - 待处理统计：`GET /support/feedback-tickets/stats/`
  - 回复：`POST /support/feedback-tickets/{id}/reply/`
  - 关闭：`POST /support/feedback-tickets/{id}/close/`
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
- 店铺分账：
  - 流水列表：`GET /profit-sharing-entries/`
  - 更新到期流水：`POST /profit-sharing-entries/mark_available/`
  - 人工结算：`POST /profit-sharing-entries/{id}/mark_manual_settled/`
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

## 多商户后台权限边界
- 商家后台通过 `merchant/src/utils/permissions.ts` 集中判断平台管理员与店铺经营用户的可访问路由。
- 平台管理员可看到平台级用户、认证、信用账户、店铺成员、支付配置、结算规则和跨店经营菜单，并可使用顶部店铺选择器切换经营店铺；店铺分账仅在当前选择店铺为主店铺时显示和操作。
- 店铺分账在商户后台提供 `/admin/profit-sharing` 页面：支付后可查看内部店铺分账流水、更新到期冻结流水，并将线下或人工处理完成的流水标记为人工结算；当前不再发起微信分账。合作店铺商品不能产生新订单，因此不会产生新的合作店铺分账流水。
- 自营店铺管理员显示本店经营菜单：销售统计、对账单、交易记录、首页轮播、动态专区、品牌、分类、商品、订单、发票、客户分组、店铺成员和问题建议。合作方管理员只显示展示配置菜单：商品、SKU、品牌、分类、客户分组、店铺成员、首页轮播、动态专区、媒体库和问题建议。
- 商户管理后台侧边栏中，“客服聊天”“自动回复”“问题建议”统一展示在“客服管理”分组下。
- 非平台管理员手动访问 `/admin/users`、`/admin/credit-accounts`、`/admin/discounts`、`/admin/search-logs`、认证审核、支付配置、结算规则等平台页面时，会回到默认可访问页面；合作方管理员访问订单、发票、销售统计、账务、折扣、库存日志、信用账户或店铺分账页面时，会回到 `/admin/products`。
- 普通店铺用户不显示跨店选择器；平台管理员切换店铺时，请求层显式注入 `store_id`，不覆盖调用方已经传入的 `store` 或 `store_id`。
- 前端基于本地缓存用户信息做默认跳转时，将超级用户、`store_roles` 中 `role=platform_admin` 的有效成员关系，以及主店铺 `role=store_admin` 的有效成员关系识别为平台管理员；最终页面权限仍以 `GET /api/stores/current/` 返回的实时店铺上下文为准。
- 合作方管理员登录后台只获得本店经营权限，进入小程序店铺详情页不会产生任何后台授权。
