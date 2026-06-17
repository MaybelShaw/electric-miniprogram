# 动态运营专区商家后台实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在商家后台提供店铺级动态专区配置能力，让平台管理员代配店铺专区，并让店铺用户自管本店商品、活动专区和优惠专区。

**Architecture:** 新增专区管理入口，复用现有图片上传、商品选择和轮播图管理能力。平台管理员可选择店铺并代配置专区；店铺管理员进入后台后只看到本店数据。后台只做功能配置，不在本计划中做视觉重构。

**Tech Stack:** React 18、Vite、TypeScript、Ant Design、ProComponents、Axios。

---

## 影响范围

- 新增：`merchant/src/pages/SpecialZones/index.tsx`
- 修改：`merchant/src/App.tsx`
- 修改：`merchant/src/components/Layout/index.tsx` 或当前菜单配置文件
- 修改：`merchant/src/services/api.ts`
- 修改：`merchant/src/services/types.ts`
- 修改：`merchant/src/pages/HomeBanners/index.tsx`
- 依赖：`merchant` 已接入当前店铺上下文和平台/店铺角色菜单
- 可选修改：`docs/merchant.md`、`docs/merchant/merchant.md`

## 执行步骤

- [ ] 确认平台店铺底座计划已完成，商家后台能识别当前账号是平台管理员还是店铺用户。
- [ ] 确认后端动态专区计划已完成，接口包括 `/api/catalog/special-zones/`、专区商品绑定和 `home-banners?special_zone=<id>`。
- [ ] 在 `merchant/src/services/types.ts` 增加 `SpecialZone` 与 `SpecialZoneProduct` 类型。
- [ ] `SpecialZone` 类型包含 `store`、`title`、`slug`、`kind`、`subtitle`、`cover_image`、`is_active`、`show_on_home`、`home_order`、`start_at`、`end_at`。
- [ ] `SpecialZoneProduct` 类型包含 `zone`、`product`、`is_active`、`order`。
- [ ] 在 `merchant/src/services/api.ts` 增加专区 CRUD、专区商品绑定、专区商品解绑、专区商品排序和专区商品显隐接口。
- [ ] 新增 `SpecialZones` 页面，列表字段包含店铺、标题、类型、标识、封面、首页排序、首页显示、启停、开始时间、结束时间。
- [ ] 平台管理员在 `SpecialZones` 页面显示店铺筛选和店铺选择字段，可为 `志邦家具` 创建专区；店铺用户不显示跨店选择器，接口默认使用当前店铺。
- [ ] 新增专区创建和编辑表单，字段包含 `store`、`title`、`slug`、`kind`、`subtitle`、`cover_image`、`home_order`、`show_on_home`、`is_active`、`start_at`、`end_at`。
- [ ] 增加专区商品绑定区域，商品搜索结果必须只显示当前专区所属店铺的商品。
- [ ] 专区商品绑定区域支持添加商品、移除商品、调整排序、切换是否在该专区展示。
- [ ] 在菜单和路由中加入 `/special-zones`。
- [ ] 修改 `HomeBanners` 页面，支持选择动态专区作为轮播归属；平台管理员先选店铺再选专区，店铺用户只能选本店专区；旧 `position` 下拉保留。
- [ ] 更新商家后台文档，说明平台代配和店铺自管两个运营路径。

## 验证命令

- [ ] `cd merchant && npm run build`
- [ ] 浏览器手测：平台管理员为 `志邦家具` 创建 `618大促` 专区并绑定志邦商品。
- [ ] 浏览器手测：志邦店铺管理员登录后只能看到并编辑志邦自己的商品、专区和轮播图。
- [ ] 浏览器手测：调整 `618大促` 的 `home_order`，确认列表顺序按后台配置变化。
- [ ] 浏览器手测：关闭 `show_on_home` 后，后端公开专区列表不再返回该专区入口。
- [ ] 浏览器手测：为 `618大促` 配置专区轮播图。
- [ ] 浏览器手测：禁用专区后，后端公开列表不再返回该专区。

## 完成标准

- 平台后台可为任意店铺创建、编辑、删除多个动态专区。
- 店铺后台只允许管理本店商品、本店动态专区和本店专区轮播。
- 后台可配置专区类型、首页显示顺序、首页是否显示、专区启停和有效期。
- 后台可给本店任意专区绑定多个本店商品，并配置专区内商品排序和显隐。
- 后台可给本店任意专区配置轮播图。
- 不需要新增固定字段或固定枚举。
- 构建通过后，本计划可单独提交并归档。
