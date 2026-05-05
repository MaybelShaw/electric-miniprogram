# 动态运营专区后端实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把固定专区升级为店铺级可配置后端能力，支持每个店铺拥有自己的多个活动、优惠、主题、品类和品牌专区。

**Architecture:** 新增 `SpecialZone` 与 `SpecialZoneProduct`，让专区基础信息、封面、商品绑定、显示顺序、显隐和专区轮播从固定枚举中解耦。每个专区归属一个 `Store`；平台管理员可跨店管理，店铺用户只能管理本店专区。

**Tech Stack:** Django 5.2、Django REST Framework、SQLite/PostgreSQL、Django test runner、openpyxl。

---

## 影响范围

- 修改：`backend/catalog/models.py`
- 修改：`backend/catalog/serializers.py`
- 修改：`backend/catalog/views.py`
- 修改：`backend/catalog/urls.py`
- 修改：`backend/catalog/search.py`
- 新增：`backend/catalog/migrations/0037_special_zone.py`
- 新增：`backend/catalog/tests/test_dynamic_special_zones.py`
- 依赖：`backend/stores/` 已完成店铺模型、当前店铺上下文和权限工具
- 可选修改：`docs/backend.md`、`docs/backend/backend.md`

## 执行步骤

- [ ] 确认 [平台店铺底座与权限计划](./2026-05-05-store-platform-foundation.md) 已完成，后端已有 `Store`、店铺成员权限和当前店铺上下文。
- [ ] 写失败测试：创建 `志邦家具` 与 `main_store` 两个店铺，验证 `GET /api/catalog/special-zones/?store=<zhibang_id>` 只返回 `志邦家具` 下可见专区。
- [ ] 写失败测试：创建启用专区、未启用专区、未勾选首页展示专区、未到开始时间专区、已过结束时间专区，验证公开列表只返回当前店铺下可见且 `show_on_home=true` 的专区。
- [ ] 写失败测试：平台管理员可给 `志邦家具` 创建专区；`志邦家具` 店铺管理员可编辑本店专区；其他店铺管理员编辑时返回 403。
- [ ] 写失败测试：给同一专区绑定多个商品并设置排序和显隐，验证专区商品接口只返回 `SpecialZoneProduct.is_active=true` 的商品，并按 `SpecialZoneProduct.order` 返回。
- [ ] 写失败测试：专区绑定商品时，商品必须属于同一店铺；跨店商品绑定返回 400。
- [ ] 写失败测试：创建 `HomeBanner(special_zone=zone)`，验证 `GET /api/catalog/home-banners/?special_zone=<id>` 只返回该专区轮播图。
- [ ] 写失败测试：验证 `GET /api/catalog/products/?special_zone=<id>` 只返回绑定到该专区的商品。
- [ ] 新增 `SpecialZone` 模型：`store`、`title`、`slug`、`kind`、`subtitle`、`cover_image`、`is_active`、`show_on_home`、`home_order`、`start_at`、`end_at`、时间戳。
- [ ] `SpecialZone.kind` 至少支持 `activity`、`promotion`、`category`、`brand`、`custom`，用于区分活动专区、优惠活动专区和普通主题专区。
- [ ] 给 `SpecialZone` 添加 `(store, slug)` 唯一约束，避免不同店铺之间 slug 冲突。
- [ ] 新增 `SpecialZoneProduct` 模型：`zone`、`product`、`is_active`、`order`、`created_at`，并添加 `(zone, product)` 唯一约束。
- [ ] 给 `HomeBanner` 增加可空 `special_zone` 外键，旧 `position` 保留兼容；多店铺启用后校验 `HomeBanner.store == special_zone.store`。
- [ ] 生成并检查 migration，确认不回填默认专区，不删除任何旧字段。
- [ ] 新增 `SpecialZoneSerializer` 和 `SpecialZoneProductSerializer`。
- [ ] 新增 `SpecialZoneViewSet`，支持列表、详情、创建、编辑、删除，并按当前账号角色过滤店铺范围。
- [ ] 新增 `SpecialZoneViewSet.products` action，支持读取和维护专区商品绑定。
- [ ] 扩展 `ProductViewSet` 和 `ProductSearchService`，支持 `special_zone` 查询参数，并保证只返回同店铺商品。
- [ ] 扩展 `HomeBannerViewSet.get_queryset()`，支持 `special_zone` 查询参数，并保证只返回同店铺轮播图。
- [ ] 注册 `/api/catalog/special-zones/` 路由。
- [ ] 更新后端文档，说明店铺级动态专区接口、显示顺序、显隐和旧固定专区兼容策略。

## 验证命令

- [ ] `cd backend && .\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run`
- [ ] `cd backend && .\.venv\Scripts\python.exe manage.py test catalog.tests.test_dynamic_special_zones`
- [ ] `cd backend && .\.venv\Scripts\python.exe manage.py test catalog.tests.test_promotion_zone`
- [ ] `cd backend && .\.venv\Scripts\python.exe manage.py check`

## 完成标准

- 可以给 `志邦家具` 创建多个动态专区，例如 `618大促`、`夏季大促`、`瓷砖专区`、`床垫专区`。
- 首页专区列表接口只返回当前店铺下启用、允许首页展示且处于有效期内的专区，并按 `home_order` 排序。
- 每个专区能维护独立商品列表、商品排序、商品显隐和独立轮播图。
- 店铺用户不能管理其他店铺专区或绑定其他店铺商品。
- 旧固定专区接口不破坏。
- 测试通过后，本计划可单独提交并归档。
