# 动态运营专区小程序接入计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 小程序首页和专区页接入店铺级动态专区数据，支持每个店铺展示自己的多个活动、优惠、品类和品牌专区入口。

**Architecture:** 首页请求当前店铺下的动态专区列表并展示多个入口；专区页从 `type` 参数切换为优先使用 `zone_id`，通过专区 ID 加载标题、轮播图和商品列表。视觉 UI 细节由单独 UI 计划或 Claude 执行，本计划只定义数据接入和路由行为。

**Tech Stack:** Taro 4、React 18、TypeScript、微信小程序构建。

---

## 影响范围

- 修改：`frontend/src/types/index.ts`
- 修改：`frontend/src/services/product.ts`
- 新增或修改：`frontend/src/services/special-zone.ts`
- 修改：`frontend/src/pages/home/index.tsx`
- 修改：`frontend/src/pages/special-zone/index.tsx`
- 可选修改：`docs/frontend.md`、`docs/frontend/frontend.md`

## 执行步骤

- [ ] 确认后端动态专区接口已经完成。
- [ ] 增加 `SpecialZone` 类型，字段与后端返回保持一致，包含 `store`、`kind`、`show_on_home`、`home_order`。
- [ ] 增加 `specialZoneService.getZones(storeId?)`，请求 `/catalog/special-zones/`；进入某个店铺首页时带上店铺上下文。
- [ ] 增加 `specialZoneService.getZoneProducts(zoneId)`，请求 `/catalog/special-zones/{id}/products/` 或 `/catalog/products/?special_zone=<id>`。
- [ ] 扩展 `productService.getHomeBanners()`，支持 `special_zone` 参数。
- [ ] 首页加载动态专区列表，并保留旧固定专区逻辑作为兼容；动态专区入口顺序完全以后端返回的 `home_order` 为准。
- [ ] 首页点击动态专区时跳转 `/pages/special-zone/index?zone_id=<id>`。
- [ ] 专区页读取 `zone_id`，优先按动态专区加载标题、轮播图和商品。
- [ ] 当没有 `zone_id` 时，继续兼容旧 `type=gift|designer|best_seller|promotion`。
- [ ] 专区无商品时展示现有空态，不抛异常。
- [ ] 不在本计划中重做视觉风格；只保证数据链路可用。

## 验证命令

- [ ] `cd frontend && npm run build:weapp`
- [ ] 搜索 `frontend/dist`，确认没有残留运行时 `process.env`。
- [ ] 微信开发者工具打开 `frontend/`，首页能看到多个动态专区入口。
- [ ] 点击 `618大促` 能进入对应专区页，并加载该专区轮播和商品。
- [ ] 旧固定专区入口仍可访问。

## 完成标准

- 首页可展示当前店铺下多个动态专区。
- 首页专区入口顺序和是否显示由后台配置决定，小程序不写死顺序和显隐。
- 专区页可按 `zone_id` 加载独立数据。
- 旧固定专区不被破坏。
- 构建通过后，本计划可单独提交并归档。
