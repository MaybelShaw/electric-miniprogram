# 平台店铺底座与权限实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立多店铺平台底座，让历史数据归属主店，并支持平台管理员代管店铺、店铺用户自管本店后台数据。

**Architecture:** 新建 `stores` 域，提供店铺、成员、角色、页面配置、支付配置和结算规则。核心业务模型逐步补 `store` 外键，并通过权限层限制店铺用户只能访问本店数据；平台管理员可以跨店查看和代配置。

**Tech Stack:** Django 5.2、DRF、Django migrations、JWT 用户角色、Django test runner。

---

## 影响范围

- 新增：`backend/stores/`
- 修改：`backend/backend/settings/base.py`
- 修改：`backend/backend/urls.py`
- 修改：`backend/catalog/models.py`
- 修改：`backend/orders/models.py`
- 修改：`backend/common/permissions.py`
- 修改：`merchant/src/services/types.ts`
- 修改：`merchant/src/services/api.ts`
- 修改：`merchant/src/components/Layout/index.tsx` 或当前菜单配置文件
- 新增：`backend/stores/tests/`
- 修改：`docs/backend.md`、`docs/backend/backend.md`

## 执行步骤

- [x] 新建 `stores` app，注册到 `INSTALLED_APPS`。
- [x] 新增 `Store` 模型，字段包含名称、编码、状态、是否主店、海尔能力开关、创建时间、更新时间；示例店铺可配置为 `志邦家具`。
- [x] 新增 `StoreMember` 模型，绑定用户、店铺、角色和状态；角色至少包含 `platform_admin`、`store_admin`、`store_staff`。
- [x] 新增 `StorePaymentConfig` 和 `StoreSettlementRule`，先落库，不接真实支付。
- [x] 写 migration 创建默认 `main_store`。
- [x] 给商品、分类、品牌、轮播、动态专区、订单相关模型分批补 `store` 外键。
- [x] 写数据迁移，把历史数据归属 `main_store`。
- [x] 增加权限工具：平台管理员可看全部并代配置任意店铺；店铺管理员和员工只能看本店。
- [x] 给关键列表接口加店铺过滤。
- [x] 增加当前店铺上下文接口，例如 `/api/stores/current/`，返回当前账号可管理店铺列表、默认店铺和角色。
- [x] 商家后台接入当前店铺上下文：平台管理员显示店铺选择器；店铺用户不显示跨店选择器，只进入本店后台。
- [x] 商家后台菜单按角色收敛：店铺用户只看到商品、专区、轮播、订单等本店业务菜单；平台管理员保留跨店管理入口。
- [x] 增加后端测试覆盖主店初始化、平台管理员跨店访问、店铺成员本店访问、跨店访问拒绝。

## 验证命令

- [x] `cd backend && .\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run`
- [x] `cd backend && .\.venv\Scripts\python.exe manage.py test stores`
- [x] `cd backend && .\.venv\Scripts\python.exe manage.py test catalog orders`
- [x] `cd backend && .\.venv\Scripts\python.exe manage.py check`

## 完成标准

- 数据库存在唯一主店。
- 历史数据归属主店。
- 平台管理员可以创建和代管 `志邦家具` 这类店铺。
- 店铺用户登录商家后台后只能管理本店商品、专区、轮播和订单，无法访问其他店铺数据。
- 只有主店允许启用海尔能力。
- 测试通过后，本计划可单独提交并归档。
