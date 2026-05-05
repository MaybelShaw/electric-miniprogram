# 小程序设计系统与核心页 UI 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立现代生活方式风格的小程序设计系统，并逐步改造核心页面。

**Architecture:** 先沉淀 token 和通用组件，再分批替换页面。动态专区作为首页运营板块的一部分，由 UI 执行方设计具体视觉，但必须消费动态专区数据契约。

**Tech Stack:** Taro 4、React 18、TypeScript、Sass、微信开发者工具。

**执行边界:** 本计划用于交给 Claude 或前端 UI 执行方单独处理；本轮不修改 `frontend` UI 代码。后端与接口计划只提供数据契约，不决定具体视觉实现。

---

## 影响范围

- 修改：`frontend/src/app.scss`
- 新增或修改：`frontend/src/styles/tokens.scss`
- 新增或修改：`frontend/src/components/`
- 修改：`frontend/src/pages/home/`
- 修改：`frontend/src/pages/special-zone/`
- 修改：`frontend/src/pages/product-detail/`
- 修改：`frontend/src/pages/cart/`
- 修改：`frontend/src/pages/order-list/`
- 修改：`frontend/src/pages/order-detail/`
- 修改：`frontend/src/pages/profile/`

## 执行步骤

- [ ] 盘点当前页面样式和组件复用情况，列出第一批需要抽出的基础组件。
- [ ] 定义颜色、字号、间距、圆角、阴影和按钮状态 token。
- [ ] 建立基础组件：按钮、标签、价格、商品卡、专区入口、空态、加载态。
- [ ] 改造首页，接入动态专区入口并保留分类、品牌、轮播和商品列表。
- [ ] 改造专区页，支持动态专区标题、轮播、商品列表和空态。
- [ ] 改造商品详情页，强化内容、价格、SKU、购买动作和登录守卫。
- [ ] 改造购物车、下单、支付结果、订单列表、订单详情、我的页。
- [ ] 在微信开发者工具中检查主要机型，不允许文字重叠和按钮溢出。

## 验证命令

- [ ] `cd frontend && npm run build:weapp`
- [ ] 微信开发者工具手测：首页、动态专区页、商品详情、购物车、订单、我的页。
- [ ] 搜索 `frontend/dist`，确认没有运行时 `process.env`。

## 完成标准

- 核心页面风格统一。
- 动态专区入口在首页可用。
- 主要流程没有布局错位、文字溢出和交互阻断。
- 构建通过后，本计划可单独提交并归档。
