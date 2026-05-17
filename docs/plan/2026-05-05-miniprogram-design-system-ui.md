# 小程序全量 UI 重设计实施计划

**Goal:** 将“庆勋愉悦家”小程序统一改造为克制的质感生活电商风格，覆盖 `frontend/src/app.config.ts` 已注册页面，并保留现有路由、接口、登录、下单、支付、售后业务逻辑。

**Architecture:** 以 Sass token 和通用 UI 组件作为底座，核心交易与账户页面优先接入组件，其余页面通过 token、导航配置、状态色和页面样式同步收敛。

**Tech Stack:** Taro 4、React 18、TypeScript、Sass、微信小程序构建。

**执行边界:** 不改后端接口、不改服务层请求参数、不改页面 path 和 query 契约。

---

## 影响范围

- 设计底座：`frontend/src/styles/variables.scss`、`frontend/src/styles/global.scss`
- 新增组件：`AppIcon`、`SearchBar`、`SectionHeader`、`ProductCard` 扩展、`OrderCard` 刷新、`StatusBadge`、`PriceText`、`EmptyState`、`LoadingState`、`BottomActionBar`、`QuantityStepper`、`PageShell`
- 核心页面：首页、分类、搜索、商品列表、商品详情、购物车、下单、订单列表、订单详情、我的、资料、专区、消息、认证、信用流水、退货、客服
- 导航配置：全局与页面级 navigation/tabBar 颜色统一为新品牌色

## 执行步骤

- [x] 盘点当前页面样式和组件复用情况，确认旧蓝色、emoji、缺失占位图和 inline style 风险。
- [x] 定义颜色、字号、间距、圆角、阴影和状态色 token，并保留旧变量名兼容现有页面。
- [x] 建立基础组件：图标、搜索、区块标题、价格、状态徽标、空态、加载态、底部操作栏、数量步进器。
- [x] 扩展商品卡和订单卡，保留现有调用方式。
- [x] 改造首页、分类、搜索、商品列表、专区和店铺相关页面的视觉方向。
- [x] 改造商品详情、购物车、下单、订单列表、订单详情等交易链路页面。
- [x] 改造我的、资料、消息、认证、信用流水、退货、客服等账户与服务型页面的视觉一致性。
- [x] 清理明显 emoji 图标、缺失 `/assets/empty-*`/`default-avatar` 引用、旧蓝色硬编码和可替换 inline style。

## 验证命令

- [x] `frontend` 下使用 bundled Node 执行 `node .\node_modules\@tarojs\cli\bin\taro build --type weapp`
- [x] 搜索 `frontend/dist`，确认没有运行时 `process.env`
- [x] 静态搜索确认没有残留明显 emoji、`style={{...}}`、缺失本地空态资源引用

## 完成标准

- [x] 全量页面共享新的质感生活色彩、表面、状态和底部操作风格。
- [x] 动态专区、首页入口、分类/商品/交易链路保持可构建。
- [x] 构建通过；Sass `@import` 已迁移，剩余 legacy JS API 输出为既有依赖层技术债警告，不阻断发布。

## 2026-05-12 高价感二次升级

- [x] 将视觉方向从清爽生活感继续收敛到精品家电 showroom：象牙纸底、深墨主按钮、香槟金细节、陶土红价格与交易强调。
- [x] 移除首页、商品、店铺、交易、账户、客服页面残留的冷蓝绿背景、亮蓝选中色和粉紫/橙色模板渐变。
- [x] 重绘 TabBar 本地图标，替换原亮蓝选中态为深墨/香槟金图标。
- [x] 构建通过：`node .\node_modules\@tarojs\cli\bin\taro build --type weapp`。
- [x] 静态检查通过：未发现旧蓝绿硬编码、emoji、明显 inline style、缺失占位图引用或 `frontend/dist` 中的 `process.env`。

## 2026-05-13 精品展厅收口

- [x] 按方案 A 将全局视觉进一步压成精品家电 showroom：减少渐变、厚阴影、圆胖按钮和模板化彩色块。
- [x] 统一 `我的`、订单详情、地址、信用账户、对账、发票、退货、支付结果、门店、专区、消息、客服等页面为暖象牙底、白色细边卡片、深墨按钮、香槟金细节。
- [x] 同步 `app.config.ts` 和页面级 config 的导航/背景色为 `#fffdf8`、`#f7f3ec`，保留所有页面 path 和业务跳转契约。
- [x] 静态检查通过：未发现旧蓝绿硬编码、明显 emoji、`style={{...}}`、缺失空态资源引用或 `frontend/dist` 中的 `process.env`。
- [x] 构建通过：`node .\node_modules\@tarojs\cli\bin\taro build --type weapp`；Sass `@import` 已迁移，剩余 Sass legacy JS API、Browserslist/baseline-browser-mapping 输出为既有依赖警告。

## 2026-05-13 清爽轻奢修正

- [x] 按用户确认的方案 B 调整为高级家居馆方向：瓷白底、近黑主文字、香槟金细节、鼠尾草绿辅助，减少暖旧和泥土感。
- [x] 将 `AppIcon` 从中文/符号字标和纯 CSS 线性图标改为 PNG 图标资源，小程序端不使用 SVG。
- [x] 重排首页视觉权重：首屏 Banner、三入口、灵感专区、店铺卡、品类、品牌、商品列表依次呈现，减少信息同屏争抢。
- [x] 优化核心页面：首页、分类、购物车、我的、商品列表、商品详情、订单确认，并同步搜索、商品卡、区块标题、空态、价格、数量器、底部操作条等公共组件质感。
- [x] 静态检查通过：核心页面未发现 `GLYPHS`、emoji 搜索/空态、中文服务承诺字标、`+` 字符加购、旧亮蓝色硬编码。
- [x] 全项目 Sass `@import` 已迁移为 `@use ... as *`，用户反馈的 `PrivacyPopup/index.scss` 警告已处理。
- [x] 构建通过：`npm run build:weapp`；剩余 Sass `legacy-js-api`、Browserslist/baseline-browser-mapping 输出为 Taro/Vite 依赖层警告，不是业务样式报错。

## 2026-05-14 全页面细节精修

- [x] 统一所有页面级 navigation/background 配置，避免详情、财务、客服、表单页面进入时顶部和页面底色跳变。
- [x] 补强公共页面容器、卡片、按钮、列表、表单、空态、吸底栏的统一视觉规则，让 34 个注册页面共享同一套细节质感。
- [x] 按页面类型做局部精修：首页/分类/商品/交易/账户/财务/售后/客服/选择器页面各自优化可读性、层级、留白和状态反馈。
- [x] 静态检查旧亮蓝硬编码、明显 emoji、内联 style、缺失本地资源引用、`frontend/dist` 运行时 `process.env`。
- [x] 执行 `npm run build:weapp`，确认小程序构建通过。
