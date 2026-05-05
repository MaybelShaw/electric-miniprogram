# 文档索引

这里是家电商城系统的技术文档目录。

## 文档目录

- **[计划与路线图](./plan/)** - 可执行计划、任务拆分、归档约定；当前主线见 [平台升级实施计划 v3（动态专区修订）](./plan/2026-04-29-platform-upgrade-v3.md)
- **[后端技术文档](./backend/)** - Django + DRF 后端 API 技术文档
- **[前端技术文档](./frontend/)** - Taro + React 小程序前端技术文档
- **[商户管理端技术文档](./merchant/)** - React + Ant Design Pro 管理后台技术文档
- **[部署文档](./deployment/)** - Docker 部署、运维指南

## 快速链接

### 后端
- [后端技术文档](./backend/backend.md) - 完整的后端 API 文档，包含认证、商品、订单、支付、客服等模块

### 前端（小程序）
- [前端技术文档](./frontend/frontend.md) - 小程序前端开发指南，包含技术栈、服务层接口、页面功能说明

### 商户管理端
- [商户管理端技术文档](./merchant/merchant.md) - 管理后台开发指南，包含路由结构、页面操作、API 封装

### 部署
- [部署指南](./deployment/deployment.md) - Docker Compose 部署全流程，包含开发、预发布、生产环境配置

## 计划与路线图

- [计划目录说明](./plan/README.md) - `docs/plan/` 与 `docs/plan/archive/` 的用途、命名与归档规则
- [平台升级实施计划 v3（动态专区修订）](./plan/2026-04-29-platform-upgrade-v3.md) - 平台化（多店）、订单结算单与子单、微信快捷登录、小程序 UI 与店铺级动态运营专区的分阶段实施蓝图
- [平台多店铺底座](./plan/2026-05-05-store-platform-foundation.md) - 店铺、成员、角色、平台代管和店铺后台数据隔离计划
- [动态运营专区后端基础](./plan/2026-05-05-dynamic-special-zones-backend.md) - 多活动、多优惠、多品类专区的店铺级后端模型、接口与测试计划
- [动态运营专区商家后台配置](./plan/2026-05-05-dynamic-special-zones-merchant.md) - 平台代配、店铺自管、专区排序显隐、商品绑定和专区轮播配置计划
- [动态运营专区小程序接入](./plan/2026-05-05-dynamic-special-zones-miniprogram.md) - 首页专区入口和专区页按 `zone_id` 加载的接入计划

## 其他文档

- [API 文档](./api/) - 完整 API 接口文档、海尔 API 对接详情
- [DEVELOPER_GUIDE.md](../DEVELOPER_GUIDE.md) - 开发者技术指南（若仓库内未放置该文件，以本目录与各子模块文档为准）
- [CLAUDE.md](../CLAUDE.md) - Claude Code 开发指南

## 资源文件

- [生态商开放接口 20260120.pdf](./assets/生态商开放接口 20260120.pdf) - 海尔生态商接口规范
