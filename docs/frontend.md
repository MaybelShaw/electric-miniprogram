# 前端技术文档（微信小程序 · Taro + React）

## 概述
- 基于 `Taro 4.1.8` 与 `React 18` 的微信小程序，覆盖首页、分类、搜索、购物车、订单、个人中心、信用账户等功能。

## 技术栈
- 框架：Taro（Vite Runner）、React、TypeScript
- 构建：`taro build`，多平台支持（weapp/h5 等）
- 代码规范：ESLint、Stylelint、Sass

## 架构与目录
- 目录结构：`frontend/src/`
  - `pages/` 页面模块（home、category、cart、order、profile、credit 等）
  - `components/` 通用组件（如商品卡片 `ProductCard`、订单卡片 `OrderCard`）
  - `services/` 服务层，封装 API 调用与数据契约
  - `utils/` 请求封装、存储工具、格式化方法
  - `types/` TypeScript 类型定义（用户、商品、订单、支付、分页等）`frontend/src/types/index.ts:22`

## 构建与平台配置
- 配置入口：`frontend/config/index.ts:7`
  - 设计稿宽度、设备比例、插件、H5/RN 配置等
- 开发配置：`frontend/config/dev.ts:3`
- 生产配置：`frontend/config/prod.ts:4`

## 开发与构建
- 开发（微信小程序）：
  ```bash
  npm run dev:weapp
  ```
  - 启动前会自动清理旧 `frontend/dist`，避免删除页面后 watch 仍加载旧页面依赖。
- 构建（微信小程序）：
  ```bash
  npm run build:weapp
  ```
  - 构建前会自动清理旧 `frontend/dist`。
- H5 开发/构建：
  ```bash
  npm run dev:h5
  npm run build:h5
  ```
- 其它平台脚本参见 `frontend/package.json`

## 环境配置
- 后端 API 基址通过环境变量控制：`frontend/src/utils/request.ts:3`
  - `TARO_APP_API_BASE_URL`（默认 `http://127.0.0.1:8000/api`）
- 生产小程序构建必须显式设置 `TARO_APP_API_BASE_URL` 为线上 HTTPS API 地址，例如 `https://www.qxelectric.cn/api`。当前生产配置缺失该变量时仍会回退到本地地址，这是待修风险；上线构建前应通过脚本或 CI 明确校验该变量。
- 认证 Header 由请求工具自动添加与刷新：`frontend/src/utils/request.ts:61`

## 请求封装详解
- Token 管理：`frontend/src/utils/request.ts:19`
  - 读取/设置/清理 Access/Refresh Token `frontend/src/utils/request.ts:21`
  - 自动刷新 401：`frontend/src/utils/request.ts:93`
- 错误处理：统一 Toast 提示与限流 429 提示 `frontend/src/utils/request.ts:108`
- GET 查询串构造：`frontend/src/utils/request.ts:137`

## 服务层接口清单
- 商品服务：`frontend/src/services/product.ts:4`
  - `getHomeBanners` 获取轮播图（支持 `position=home|gift|designer|best_seller|promotion`）
  - `getProducts` 列表（分页/排序/搜索）`frontend/src/services/product.ts:6`
  - `getProductDetail` 详情 `frontend/src/services/product.ts:16`
  - `getProductsByCategory`/`getProductsByBrand` 分类/品牌筛选 `frontend/src/services/product.ts:21`
  - `getCategories`/`getBrands` 列表 `frontend/src/services/product.ts:36`
    - 分类层级：`level=major|minor|item`（品类/子品类/品项）
    - 列表接口默认分页（常见为 20 条）；需要全量数据时通过 `fetchAllPaginated` 自动拉取全部分页：`frontend/src/utils/request.ts:229`
  - `getRecommendations`/`getRelatedProducts` 推荐/相关 `frontend/src/services/product.ts:49`
- 订单服务：`frontend/src/services/order.ts:4`
  - `createOrder` 创建订单 `frontend/src/services/order.ts:6`
  - `createBatchOrders` 批量创建（购物车，支持 `payment_method=online|credit`）`frontend/src/services/order.ts:16`
  - `getMyOrders` 我的订单（分页）`frontend/src/services/order.ts:28`
  - `getOrderDetail` 详情 `frontend/src/services/order.ts:37`
  - `cancelOrder` 取消（支持 `reason`）`frontend/src/services/order.ts:46`
  - `confirmReceipt` 确认收货 `frontend/src/services/order.ts`
  - `requestInvoice` 申请发票 `frontend/src/services/order.ts`
  - `requestReturn` 申请退货 `frontend/src/services/order.ts`
  - `addReturnTracking` 填写退货物流 `frontend/src/services/order.ts`
- 客服支持服务：`frontend/src/services/support.ts`
  - 消息列表/发送（支持增量拉取、离线发送）
- 问题建议工单服务：`frontend/src/services/feedback.ts`
  - `getStores` 获取可提交问题建议的启用店铺列表。
  - `getTickets`/`getTicket` 获取当前用户自己的工单列表和详情。
  - `createTicket` 创建问题或需求工单；提交前会先上传图片附件。
  - `supplementTicket` 在未关闭工单中补充文字或图片。
- 支付服务：`frontend/src/services/payment.ts:4`
  - 列表/创建/详情/开始/成功/失败/取消/过期 `frontend/src/services/payment.ts:6`
- 地址服务：`frontend/src/services/address.ts:4`
  - CRUD/设为默认/智能解析 `frontend/src/services/address.ts:6`
- 用户服务：`frontend/src/services/user.ts:4`
  - 资料获取/更新、用户统计 `frontend/src/services/user.ts:6`
- 信用账户与账务：`frontend/src/services/credit.ts:65`
  - 我的账户/对账单/交易、对账单确认 `frontend/src/services/credit.ts:67`

## 页面与功能
- 首页（`/pages/home/index`）：
  - 分类、品牌、特色专区（含爆品专区、优惠专区）、轮播与商品列表，分页加载与下拉刷新
  - 加载商品列表：`frontend/src/pages/home/index.tsx:67`
- 专区页（`/pages/special-zone/index`）：
  - 场景展示（通过 `position` 获取轮播图）与商品列表展示
  - 支持“礼品专区”、“设计师专区”、“爆品专区”与“优惠专区”四种模式，通过 `type` 参数控制
  - 设计师专区展示精选案例（`Case`）
- 品牌列表页（`/pages/brand-list/index`）：
  - 展示所有品牌，支持点击跳转至品牌详情页
- 分类页（`/pages/category/index`）：
  - 左侧大类导航 + 右侧子类/品项展示
  - 首页“品类专区”点击“更多”跳转至此页（显示全部品类）
  - 支持从首页点击具体分类图标跳转并自动选中对应大类
- 搜索页（`/pages/search/index`）：关键词检索、热门关键词、搜索建议
- 购物车（`/pages/cart/index`）：按店铺分组展示，支持店铺全选、单品选择、数量调整、移除、清空与结算；已下架、规格下架或库存不足商品会显示不可结算原因并排除在结算选择外。
- 订单确认页（`/pages/order-confirm/index`）：从购物车进入时延续店铺分组展示；提交参数仍为平铺 `items`，后端继续按店铺拆子单。
- 订单详情/列表：状态筛选、支付入口、退款与取消、申请/查看发票
  - **确认收货**：当订单状态为 `shipped` 时，用户可在订单列表或详情页点击“确认收货”按钮，确认后订单状态变更为 `completed`。
  - **物流信息展示**：在订单详情页（`/pages/order-detail/index`），支持查看物流公司、快递单号、发货单号与 SN 码；快递单号支持长按复制。
  - **发票状态实时更新**：在订单详情页（`/pages/order-detail/index`），支持发票状态实时刷新（`useDidShow`）。
  - **状态可视化**：通过颜色区分发票状态（已开具：绿色 `#07c160`、已取消：红色 `#ff4d4f`、已申请：橙色 `#faad14`）。
  - **订单取消**：用户可在订单列表或详情页取消 `pending`（待支付）或 `paid`（已支付/待发货）状态的订单。取消时支持输入原因。
    - 待支付订单：直接取消。
    - 已支付订单：取消后，若为信用支付则自动退款至信用账户；在线支付需等待后台处理。
  - **退货与售后**：
    - **申请退货**：在订单详情页（`/pages/order-detail/index`），针对 `paid`（已支付）、`shipped`（已发货）、`completed`（已完成）且未申请过退货的订单，可发起退货申请。需填写退货原因并上传凭证（最多3张）。
    - **填写退货物流**：当退货申请状态为 `requested`（已申请/待发货）时，用户可填写退货物流公司与单号。
    - **状态跟踪**：在订单详情页实时展示退货状态（已申请、退货在途、已收到退货、已拒绝）及处理备注。
- 申请发票（`/pages/invoice-request/index`）：
   - 界面布局优化：采用对齐的表单设计，必填项标记不影响文字排版
  - 支持普通发票与专用发票两种类型（通过按钮快速切换）
  - 必填项动态校验：
    - 普通发票：发票抬头、邮箱
    - 专用发票：发票抬头、邮箱、税号、公司地址、联系电话、开户行及账号
  - 增加邮箱格式正则校验
  - 税率由后端计算，前端无需传递 `tax_rate` 字段
- 个人中心（`/pages/profile/index`）：资料展示与编辑、地址管理入口
- 菜单调整：客服支持入口位于“信用账户”下方，问题建议入口位于“客服支持”之后（经销商用户显示为：收货地址 → 经销商认证 → 信用账户 → 客服支持 → 问题建议）。
- 客服支持系统：
  - **入口**：个人中心 -> 客服支持（直接进入聊天页面，不再有工单列表）
  - **功能**：
    - 实时聊天（`/pages/support-chat/index`）：与客服进行实时对话
    - 消息发送：支持文本、图片、视频、关联订单、关联商品
  - **优化特性**：
    - **增量轮询**：使用 `after` 参数仅拉取新消息，节省流量
    - 为避免同秒产生的自动回复被过滤，前端会将 `after` 回退 1 秒再拉取
    - 每次进入或返回聊天页都会触发自动回复接口（`POST /support/chat/auto-reply/`），同时刷新 `last_user_entered_at`
    - idle_contact 以用户上次进入会话时间为基准进行判断
    - **本地缓存**：消息缓存在本地存储，进入页面秒开
    - **离线支持**：断网时发送消息存入离线队列，网络恢复后自动重试
    - **乐观更新**：发送消息立即上屏，提升体验
  - **消息类型**：文本、图片、视频、订单卡片、商品卡片、模板卡片与快捷按钮（渲染见 `frontend/src/pages/support-chat/index.tsx:395`）。
    - `content_type=card` 时使用 `content_payload` 渲染图文卡片（标题、描述、图片与跳转配置）。
    - `content_type=quick_buttons` 时使用 `content_payload.buttons` 渲染快捷问题按钮，点击自动发送文本。
  - **选择订单/商品**：在聊天面板中点击“订单”或“商品”打开选择页：
    - 订单选择页：`/pages/support-chat/select-order/index`
    - 商品选择页：`/pages/support-chat/select-product/index`
    - 页面间通信：通过事件通道发送选择结果，稳定获取 `EventChannel` 使用 `Taro.getCurrentPages()`。
  - **消息发送**：统一封装在 `supportService.sendMessage`（`frontend/src/services/support.ts:31`），支持文本、图片、视频以及 `order_id`/`product_id`。
  - **动作面板**：为避免歧义，动作面板将“相册”重命名为“图片/视频”。
  - **卡片渲染**：订单/商品消息在聊天中以信息卡片展示，点击可跳转到详情页；订单卡片右上角显示状态标签。
- 问题建议工单：
  - **入口**：个人中心 -> 问题建议。
  - **列表页**：`/pages/feedback-list/index`，支持按全部、待处理、已回复、已关闭筛选，并分页加载当前用户自己的工单。
  - **提交页**：`/pages/feedback-submit/index`，用户需选择启用店铺，选择“问题”或“需求”，填写标题、内容和可选联系电话；只支持图片附件，最多 9 张。
  - **详情页**：`/pages/feedback-detail/index`，展示用户提交内容和后台处理记录；未关闭时允许继续补充文字或图片，关闭后只读。
  - **状态流转**：用户新建或补充后为 `pending`，后台回复后为 `replied`，店铺管理员或平台管理员关闭后为 `closed`。
- 信用账户与账务（`/pages/credit-account`、`/pages/account-statements`、`/pages/statement-detail`）：额度、账期、对账单与交易明细
  - 账期规则：固定月度账期，正常 `30` 天；采购的应付日期为“交易日 + 账期天数”所在月份的最后一天。
  - 对账明细中的“应付日期/付款状态”与后端同步，逾期状态按天更新。

## 页面交互流程
- 登录与鉴权：
  - 显式微信快捷登录通过 `authService.loginWithPhone(phoneCode)` 调用：先用 `Taro.login()` 获取 `code`，再把 `code` 和微信手机号授权返回的 `phone_code` 提交到 `/api/wechat/explicit-login/`。
  - 首次登录必须授权手机号；普通商品浏览不触发登录，也不会隐式创建账号。
  - 如果后端微信凭证未配置，显式登录会返回 `503`，前端不再兜底生成模拟手机号账号。
  - 商品详情页的购买/加购动作通过 `frontend/src/utils/auth-guard.ts` 守卫；未登录时保存当前路径和 `buy/cart` 动作，切到个人中心授权登录，成功后回到原商品详情并携带 `auth_action` 恢复原动作。
  - 请求自动带 `Authorization` Header；401 时自动刷新并重试 `frontend/src/utils/request.ts:93`
- 购物车结算：
  - 购物车读取 `/api/cart/my_cart/` 的 `store_groups`/`items` 契约，页面按店铺展示；店铺顺序由购物车项加入顺序决定。
  - 选中商品并导航至确认页，跳转参数会携带 `product_id`、`sku_id`、`quantity` 以及展示用店铺信息。
  - 批量创建订单与支付记录 `frontend/src/services/order.ts:16`
- 支付成功状态：
  - 成功后将订单状态更新为 `paid`（服务端状态机）
  - 前端可刷新订单详情与支付记录 `frontend/src/services/payment.ts:34`
- 地址智能解析：
  - 输入整段地址文本，解析省市区与详细地址 `frontend/src/services/address.ts:30`
- 信用账户与账务：
  - 展示额度、欠款与账期统计；查看对账单与交易 `frontend/src/services/credit.ts:71`

## API 与认证
- 统一请求封装：`frontend/src/utils/request.ts:61`
  - 自动携带 `Authorization: Bearer <access_token>`
  - 401 自动刷新：`frontend/src/utils/request.ts:93`
- 错误与限流提示：`frontend/src/utils/request.ts:108`
- 本地/Docker 开发默认请求 `http://127.0.0.1:8000/api`，不回退到线上域名；需要连接其他环境时显式设置 `TARO_APP_API_BASE_URL`。
- 生产构建不得使用默认本地 API。若后续代码尚未改为“生产缺失变量即失败”，发布清单中必须人工确认 `TARO_APP_API_BASE_URL` 已设置为线上 HTTPS 域名。
- 小程序运行时图片、视频与分享图统一经过 `resolveLocalMediaUrl` 处理；默认允许远程媒体以展示 CDN/OSS 商品图，若环境需要收紧，可显式设置 `TARO_APP_ALLOW_REMOTE_MEDIA=false`。

## 数据与缓存
- 分类与品牌本地缓存，减少重复请求：`frontend/src/pages/home/index.tsx:33`
- 分页列表合并与加载状态处理：`frontend/src/pages/home/index.tsx:70`

## 类型与数据结构
- 用户与登录响应：`frontend/src/types/index.ts:2`、`frontend/src/types/index.ts:16`
- 商品与列表响应：`frontend/src/types/index.ts:23`、`frontend/src/types/index.ts:45`
- 购物车与地址：购物车类型包含 `CartItem`、`CartStoreGroup` 和 `Cart`；地址类型位于 `frontend/src/types/index.ts`
- 订单与支付：`frontend/src/types/index.ts:99`、`frontend/src/types/index.ts:119`
- 分页响应：`frontend/src/types/index.ts:139`

## 目录结构
- 源码根：`frontend/src/`
  - `pages/` 页面
  - `components/` 组件（如 `ProductCard`）
  - `services/` API 服务（产品/订单/支付等）
  - `utils/` 请求、存储、格式化
  - `types/` 类型定义

## 运行建议
- 启用 devtools 调试，关注网络请求、渲染性能与加载占位
- 图片使用占位与懒加载，列表场景适当虚拟滚动
 - 统一错误提示与空态组件；长列表尽量开启虚拟滚动与分页

## 资源与限制
- 微信小程序不支持 SVG，请统一使用 `png/jpg/jpeg` 格式的图片资源（如聊天动作面板图标 `camera.png`、`picture.png`）。

## 入驻合作方店铺入口
- 首页继续作为庆勋愉悦家平台默认浏览入口，同时新增“合作方专区”入口聚合，数据来自 `frontend/src/services/store.ts` 的公开店铺接口。
- `kind='brand'` 的品牌店铺专区入口跳转到 `/pages/store-list/index`，不再用商品卡片模拟店铺入口。
- 入驻店铺列表页 `/pages/store-list/index` 展示当前平台下 `show_on_home=true` 且启用中的合作方店铺。
- 店铺详情页 `/pages/store-detail/index?id=<store_id>` 是多店铺共用模板，展示该真实经营店铺的公司名称、Logo、封面、图片轮播、产品类别入口、产品大图、价格、库存、动态专区和商品摘要；品牌分类不在首页默认堆叠展示。
- 店铺详情页、店铺分类页和店铺我的页使用店铺内部底部导航 `首页 / 分类 / 我的`；三项均保留当前 `store_id` 上下文。店铺上下文不提供独立购物车页面或底部购物车入口，平台购物车仍为 `/pages/cart/index`。全局平台 TabBar 不因店铺模板而改变。
- 平台购物车按店铺分组展示；点击合作方店铺进入对应店铺首页，点击主店铺（`store_is_main=true`）返回平台首页 `/pages/home/index`。
- 所有主店铺入口都回到平台首页；店铺上下文页只用于合作方店铺，若旧链接打开主店铺店铺页，会自动返回平台首页。
- “新品上新”不作为底部导航入口，统一由店铺后台的动态运营专区配置成活动卡片。
- 店铺详情页的“产品类别 -> 品牌 -> 商品”流程：默认只展示产品类别；点击一级类别后跳转 `/pages/store-category/index?store_id=<store_id>&category_id=<category_id>`，类别页调用公开店铺详情接口并传入 `category_id`，此时才展示品牌分类，品牌列表只包含该分类树下有上架商品的品牌；点击品牌后调用 `getProductsByBrand` 并携带 `store` 与 `category_id`。
- 店铺详情内进入专区时携带 `store_id`：`/pages/special-zone/index?zone_id=<id>&store_id=<store_id>`，专区页和商品列表页会按该店铺上下文查询数据。
- 进入合作方店铺详情只改变前台浏览上下文，不代表用户获得该店铺后台权限。

## 客户分组价格展示
- 商品接口返回的 `display_price` 已经是当前用户在该店铺下应看到的最终基础展示价：有客户分组价时使用分组价，没有配置时回退店铺商品/SKU默认价。
- SKU 商品的分组价优先级为：SKU 分组价 → 整品分组价 → SKU 默认价；非 SKU 商品为：整品分组价 → 商品默认价。
- 小程序商品卡片、商品列表和商品详情继续只按 `display_price`/`discounted_price` 渲染价格；订单确认和下单由后端再次解析并锁定当时价格。
- 小程序用户端不展示 `customer_group_name`，也不出现“当前价格身份”“客户分组价”等提示；`show_customer_group_name` 字段保留兼容，用户端只展示后端计算后的最终价格。
- 海尔商品同样参与客户分组价格覆盖；命中分组价时用户端展示后端返回的最终价，下单时后端再次锁定该价格。
