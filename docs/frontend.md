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
- 构建（微信小程序）：
  ```bash
  npm run build:weapp
  ```
- H5 开发/构建：
  ```bash
  npm run dev:h5
  npm run build:h5
  ```
- 其它平台脚本参见 `frontend/package.json`

## 环境配置
- 后端 API 基址通过环境变量控制：`frontend/src/utils/request.ts:3`
  - `TARO_APP_API_BASE_URL`（默认 `http://127.0.0.1:8000/api`）
- 认证 Header 由请求工具自动添加与刷新：`frontend/src/utils/request.ts:61`

## 请求封装详解
- Token 管理：`frontend/src/utils/request.ts:19`
  - 读取/设置/清理 Access/Refresh Token `frontend/src/utils/request.ts:21`
  - 自动刷新 401：`frontend/src/utils/request.ts:93`
- 错误处理：统一 Toast 提示与限流 429 提示 `frontend/src/utils/request.ts:108`
- GET 查询串构造：`frontend/src/utils/request.ts:137`

## 服务层接口清单
- 商品服务：`frontend/src/services/product.ts:4`
  - `getProducts` 列表（分页/排序/搜索）`frontend/src/services/product.ts:6`
  - `getProductDetail` 详情 `frontend/src/services/product.ts:16`
  - `getProductsByCategory`/`getProductsByBrand` 分类/品牌筛选 `frontend/src/services/product.ts:21`
  - `getCategories`/`getBrands` 列表 `frontend/src/services/product.ts:36`
    - 分类层级：`level=major|minor|item`（品类/子品类/品项）
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
  - 工单列表/详情/创建/关闭
  - 消息列表/发送（支持增量拉取、离线发送）
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
  - 分类、品牌、轮播与商品列表，分页加载与下拉刷新
  - 加载商品列表：`frontend/src/pages/home/index.tsx:67`
- 分类页（`/pages/category/index`）：左侧分类 + 右侧商品列表，支持排序与分页
- 搜索页（`/pages/search/index`）：关键词检索、热门关键词、搜索建议
- 购物车（`/pages/cart/index`）：选中/数量/移除/结算，跳转确认订单（Token 保护）
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
- 菜单调整：客服支持入口已移动到“信用账户”下方，以更符合用户使用习惯（经销商用户显示为：收货地址 → 经销商认证 → 信用账户 → 客服支持）。
- 客服支持系统：
  - **入口**：个人中心 -> 客服支持（直接进入聊天页面，不再有工单列表）
  - **功能**：
    - 实时聊天（`/pages/support-chat/index`）：与客服进行实时对话
    - 消息发送：支持文本、图片、视频、关联订单、关联商品
  - **优化特性**：
    - **增量轮询**：使用 `after` 参数仅拉取新消息，节省流量
    - **本地缓存**：消息缓存在本地存储，进入页面秒开
    - **离线支持**：断网时发送消息存入离线队列，网络恢复后自动重试
    - **乐观更新**：发送消息立即上屏，提升体验
  - **消息类型**：文本、图片、视频、订单卡片、商品卡片（渲染见 `frontend/src/pages/support-chat/index.tsx:320`，视频样式见 `frontend/src/pages/support-chat/index.scss:69`）。
  - **选择订单/商品**：在聊天面板中点击“订单”或“商品”打开选择页：
    - 订单选择页：`/pages/support-chat/select-order/index`
    - 商品选择页：`/pages/support-chat/select-product/index`
    - 页面间通信：通过事件通道发送选择结果，稳定获取 `EventChannel` 使用 `Taro.getCurrentPages()`。
  - **消息发送**：统一封装在 `supportService.sendMessage`（`frontend/src/services/support.ts:31`），支持文本、图片、视频以及 `order_id`/`product_id`。
  - **动作面板**：为避免歧义，动作面板将“相册”重命名为“图片/视频”。
  - **卡片渲染**：订单/商品消息在聊天中以信息卡片展示，点击可跳转到详情页；订单卡片右上角显示状态标签。
- 信用账户与账务（`/pages/credit-account`、`/pages/account-statements`、`/pages/statement-detail`）：额度、账期、对账单与交易明细
  - 账期规则：固定月度账期，正常 `30` 天；采购的应付日期为“交易日 + 账期天数”所在月份的最后一天。
  - 对账明细中的“应付日期/付款状态”与后端同步，逾期状态按天更新。

## 页面交互流程
- 登录与鉴权：
  - 调用微信登录获取 `code`，后端交换为 JWT（开发支持模拟）
  - 请求自动带 `Authorization` Header；401 时自动刷新并重试 `frontend/src/utils/request.ts:93`
- 购物车结算：
  - 选中商品并导航至确认页 `frontend/src/pages/cart/index.tsx:156`
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

## 数据与缓存
- 分类与品牌本地缓存，减少重复请求：`frontend/src/pages/home/index.tsx:33`
- 分页列表合并与加载状态处理：`frontend/src/pages/home/index.tsx:70`

## 类型与数据结构
- 用户与登录响应：`frontend/src/types/index.ts:2`、`frontend/src/types/index.ts:16`
- 商品与列表响应：`frontend/src/types/index.ts:23`、`frontend/src/types/index.ts:45`
- 购物车与地址：`frontend/src/types/index.ts:71`、`frontend/src/types/index.ts:86`
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
