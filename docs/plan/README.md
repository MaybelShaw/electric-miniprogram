# 计划目录说明

这个目录只用于管理尚未完成的执行计划和任务拆分。已经完成、取消或被主文档承接的计划应从当前目录移除，避免计划文件长期失真。

## 目录约定

- `docs/plan/`
  只存放当前正在讨论、准备执行或执行中的计划文件。
- `docs/plan/archive/`
  存放确有复盘或审计价值的历史计划；普通已完成计划默认删除，不再强制归档。

## 使用规则

每次进入一个新任务或一组可独立推进的需求时：

1. 只有需求较大、跨模块或需要分阶段推进时，才在 `docs/plan/` 下新建单独计划文件；小修小补不必建计划。
2. 一个文件只承载一项相对独立、可解耦的任务。
3. 文件中要写清楚目标、拆分、影响范围、执行顺序、测试要求和完成标准。
4. 计划完成后，先把最终实现同步到 `docs/backend.md`、`docs/frontend.md`、`docs/merchant.md`、`docs/api/api.md` 等长期文档，再删除对应计划文件。

## 文档同步规则

代码变更完成前，必须同步检查并更新相关文档，做到“实现变更到哪里，文档更新到哪里”：

- 后端模型、接口、字段、权限、状态流转、业务规则或迁移变化：更新 `docs/backend.md`、`docs/backend/backend.md`，接口变化同时更新 `docs/api/api.md`。
- 小程序页面、入口、服务封装、请求参数、响应字段或用户流程变化：更新 `docs/frontend.md`、`docs/frontend/frontend.md`。
- 商家后台路由、菜单、权限、页面能力、服务封装或运营流程变化：更新 `docs/merchant.md`、`docs/merchant/merchant.md`。
- 部署、Docker、Nginx、环境变量、构建和运行命令变化：更新 `docs/deployment.md`、`docs/deployment/deployment.md`。
- 计划文件新增、删除、归档或路线图变化：更新 `docs/README.md` 和本文件中的当前计划/归档计划索引。

完成任务前需用 `rg` 对照本次触达的代码路径和关键字，清理文档中的旧接口、旧模型、旧页面、旧权限或旧状态说明。若确认无需更新文档，应在最终说明中写明原因。

## 命名建议

建议文件名使用：

`YYYY-MM-DD-任务简述.md`

例如：

- `2026-05-05-service-provider-profit-sharing.md`
- `2026-06-07-order-refund-permission.md`
- `2026-06-07-merchant-dashboard-cleanup.md`

## 收尾规则

当满足以下条件后，优先删除对应计划文件：

- 代码已编写完成
- 必要测试已执行且无错误
- 相关实现已同步到长期文档

只有当计划本身包含仍有复盘价值的背景决策、拆分过程或历史约束时，才移动到 `docs/plan/archive/`。

如果任务较大，可以先拆成多个子计划文件；每个子计划在各自完成后单独删除或归档。

## 当前计划

- [微信支付分账与利润结算](./2026-05-05-service-provider-profit-sharing.md)

## 已归档计划

- [平台入驻合作店铺与商家权限收敛](./archive/2026-05-05-00-platform-partner-store-marketplace.md)
- [结算单与子订单拆分](./archive/2026-05-05-checkout-suborders.md)
- [动态运营专区后端基础](./archive/2026-05-05-dynamic-special-zones-backend.md)
- [动态运营专区商家后台配置](./archive/2026-05-05-dynamic-special-zones-merchant.md)
- [动态运营专区小程序接入](./archive/2026-05-05-dynamic-special-zones-miniprogram.md)
- [平台多店铺底座](./archive/2026-05-05-store-platform-foundation.md)
