# 计划目录说明

这个目录用于管理项目执行计划、任务拆分和归档记录。

## 目录约定

- `docs/plan/`
  存放当前正在讨论、准备执行或执行中的计划文件。
- `docs/plan/archive/`
  存放已经完成、测试通过并完成 Git 提交后的历史计划。

## 使用规则

每次进入一个新任务或一组可独立推进的需求时：

1. 先在 `docs/plan/` 下新建一个单独的计划文件。
2. 一个文件只承载一项相对独立、可解耦的任务。
3. 文件中要写清楚目标、拆分、影响范围、执行顺序、测试要求和完成标准。

## 命名建议

建议文件名使用：

`YYYY-MM-DD-任务简述.md`

例如：

- `2026-04-29-platform-upgrade-v3.md`
- `2026-04-29-home-promotion-zone.md`
- `2026-04-29-wechat-quick-login.md`

## 归档规则

当满足以下条件后，将对应计划文件移动到 `docs/plan/archive/`：

- 代码已编写完成
- 必要测试已执行且无错误
- 相关修改已完成 Git 提交

如果任务较大，可以先拆成多个子计划文件；每个子计划在各自完成后单独归档。

## 当前计划

- [平台升级实施计划 v3（动态专区修订）](./2026-04-29-platform-upgrade-v3.md) - 总览与阶段顺序，不单独归档代码任务
- [平台多店铺底座](./2026-05-05-store-platform-foundation.md)
- [动态运营专区后端基础](./2026-05-05-dynamic-special-zones-backend.md)
- [动态运营专区商家后台配置](./2026-05-05-dynamic-special-zones-merchant.md)
- [动态运营专区小程序接入](./2026-05-05-dynamic-special-zones-miniprogram.md)
- [结算单与子订单拆分](./2026-05-05-checkout-suborders.md)
- [微信显式快捷登录](./2026-05-05-wechat-explicit-login.md)
- [小程序设计系统与 UI 改版](./2026-05-05-miniprogram-design-system-ui.md)
- [服务商分账与利润结算](./2026-05-05-service-provider-profit-sharing.md)
