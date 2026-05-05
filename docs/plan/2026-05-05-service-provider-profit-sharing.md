# 服务商分账闭环实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 接入微信服务商分账，让子单级交易能形成可追踪、可重试、可审计的分账记录。

**Architecture:** 分账以 `SubOrder` 为粒度生成记录，微信接口调用封装在支付集成服务中。异常不阻塞订单主状态，但必须进入待重试或人工处理状态。

**Tech Stack:** Django 5.2、DRF、微信支付服务商 API、后台任务或管理命令、Django test runner。

---

## 影响范围

- 修改：`backend/orders/models.py`
- 修改：`backend/orders/payment_service.py`
- 新增：`backend/orders/profit_sharing.py`
- 新增：`backend/orders/management/commands/retry_profit_sharing.py`
- 新增：`backend/orders/tests/test_profit_sharing.py`
- 修改：`backend/backend/settings/base.py`
- 修改：`docs/backend.md`、`docs/backend/backend.md`

## 执行步骤

- [ ] 写失败测试：支付成功后为每个需要分账的子单创建分账记录。
- [ ] 写失败测试：分账接口失败时记录错误并进入 `failed` 或 `retrying` 状态。
- [ ] 写失败测试：重试命令只处理可重试记录，不重复处理成功记录。
- [ ] 新增 `ProfitSharingRecord` 模型，关联子单、店铺、金额、状态、请求参数、响应、错误信息。
- [ ] 封装微信服务商分账调用，测试中 mock 外部请求。
- [ ] 在支付成功流程中触发分账记录创建和初次调用。
- [ ] 新增重试管理命令。
- [ ] 后台保留查询分账记录的接口或管理入口。
- [ ] 更新环境变量说明，列出服务商分账所需配置。

## 验证命令

- [ ] `cd backend && .\.venv\Scripts\python.exe manage.py test orders.tests.test_profit_sharing`
- [ ] `cd backend && .\.venv\Scripts\python.exe manage.py check`
- [ ] 使用 mock 配置手动执行 `python manage.py retry_profit_sharing`。

## 完成标准

- 子单支付成功后产生分账记录。
- 分账成功、失败、重试都有状态记录。
- 重试不会重复分账。
- 测试通过后，本计划可单独提交并归档。
