# 结算单与子单重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 支持跨店统一购物车和统一支付，支付成功后按“店铺 + 商品 SPU”拆成子单。

**Architecture:** 新增 `CheckoutOrder` 表示一次结算和支付聚合，新增 `SubOrder` 表示用户和后台主要操作的履约单。旧 `Order` 能力逐步迁移到子单语义，避免一次性大爆炸重写。

**Tech Stack:** Django 5.2、DRF、订单服务层、支付服务层、Django test runner。

---

## 影响范围

- 修改：`backend/orders/models.py`
- 修改：`backend/orders/services.py`
- 修改：`backend/orders/payment_service.py`
- 修改：`backend/orders/serializers.py`
- 修改：`backend/orders/views.py`
- 新增：`backend/orders/tests/test_checkout_suborders.py`
- 修改：`docs/backend.md`、`docs/backend/backend.md`

## 执行步骤

- [ ] 写失败测试：跨两个店铺、多个商品、多个 SKU 创建结算单。
- [ ] 写失败测试：支付成功后按 `store_id + product_id` 拆子单，同一 SPU 的多个 SKU 保留在同一子单明细中。
- [ ] 写失败测试：用户订单列表默认返回子单，不以结算单为主展示。
- [ ] 新增 `CheckoutOrder` 模型，保存用户、地址、支付金额、支付状态和支付单号。
- [ ] 新增 `SubOrder` 模型，关联 `CheckoutOrder`、店铺、商品 SPU、状态和金额。
- [ ] 调整订单行模型或新增子单行模型，保留 SKU、数量、单价和折扣。
- [ ] 调整下单服务，先生成结算单，再生成子单和子单行。
- [ ] 调整支付成功回调，更新结算单和所有子单状态。
- [ ] 调整取消、发货、完成、退货、退款逻辑，使其以子单为主要对象。
- [ ] 更新订单 API 文档。

## 验证命令

- [ ] `cd backend && .\.venv\Scripts\python.exe manage.py test orders.tests.test_checkout_suborders`
- [ ] `cd backend && .\.venv\Scripts\python.exe manage.py test orders`
- [ ] `cd backend && .\.venv\Scripts\python.exe manage.py check`

## 完成标准

- 跨店商品能一次结算。
- 一次支付能追踪到一张结算单和多张子单。
- 子单能独立发货、售后、退款。
- 旧订单核心测试仍通过。
- 测试通过后，本计划可单独提交并归档。
