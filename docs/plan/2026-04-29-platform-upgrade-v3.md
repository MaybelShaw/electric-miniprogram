# 平台升级实施计划 v3（动态专区修订）

> 2026-05-05 修订：原方案把“活动/优惠专区”设计为第四个固定枚举 `promotion`。这个设计只能承载一个优惠专区，无法支持“618 大促、夏季大促、瓷砖专区、床垫专区”等多个并存的运营专区。最终蓝图改为“店铺级动态运营专区”。

## 概要

本计划用于把当前项目从“单店商城”升级为“平台型店铺服务商系统”，并在不废掉现有主店业务的前提下，分阶段完成五条主线：

- 运营主线：把固定专区升级为店铺级可配置 `SpecialZone`，支持多个活动、主题、品类、品牌和优惠专区并存。
- 交易主线：支持多子店铺，用户统一购物车、统一支付，支付成功后按“店铺 + 商品 SPU”自动拆子单，后续接微信服务商分账。
- 用户主线：小程序取消当前自动登录模式，改成显式微信快捷登录，首次登录即完成手机号授权；昵称默认生成，并支持登录后补充头像昵称。
- 体验主线：小程序建立新的设计系统，并完成全站现代化 UI 改版，核心风格为“现代生活方式”。
- 后台主线：商家后台从固定入口配置升级为可维护本店商品、动态专区、商品绑定、专区轮播、显示顺序和显隐配置。

## 当前基础

当前系统已经具备专区能力的基础闭环：

- 后端已有 `SpecialZoneCover` 作为首页专区封面配置。
- 后端已有 `HomeBanner.position` 作为专区页轮播配置。
- 商品已有 `show_in_gift_zone`、`show_in_designer_zone`、`show_in_best_seller_zone` 控制固定专区商品曝光。
- 已新增过渡字段 `show_in_promotion_zone` 和 `promotion` choices，但它只适合单个优惠专区。
- 商家后台已有 `HomeBanners`、`SpecialZoneCovers`、`Products` 三个配置入口。
- 小程序首页和 `special-zone` 页面已经消费固定专区链路。

最终方向不再继续增加 `show_in_xxx_zone` 字段，也不再为每个活动新增枚举。固定专区保留为兼容层，新增店铺级动态专区能力作为后续主要实现。

## 动态运营专区设计

### 产品定义

动态运营专区用于承载多个可配置入口，且每个专区必须归属一个店铺。例如平台管理员可为“志邦家具”创建：

- `志邦家具 618大促`
- `志邦家具 夏季大促`
- `志邦家具 瓷砖专区`
- `志邦家具 床垫专区`
- `志邦家具 新品专区`
- `志邦家具 清仓专区`

每个专区拥有自己的店铺归属、专区类型、封面、标题、首页展示排序、首页显隐状态、可选有效期、轮播图和商品列表。首页可展示多个启用且允许首页展示的专区入口，用户点击任意专区进入同一个 `special-zone` 页面，但页面数据按专区 ID 加载。

平台系统管理员可以跨店创建和代配置专区；店铺管理员和店铺员工只能管理自己店铺下的商品、专区、轮播和优惠活动配置。店铺后台不是单独复制一套系统，优先复用 `merchant` 管理端，通过账号角色和当前店铺上下文限制数据范围。

### 后端模型

新增 `catalog.SpecialZone`：

- `store`：所属店铺，例如 `志邦家具`
- `title`：专区标题，例如 `618大促`
- `slug`：店铺内稳定标识，例如 `618-sale`
- `kind`：专区类型，例如 `activity`、`promotion`、`category`、`brand`、`custom`
- `subtitle`：可选副标题
- `cover_image`：首页入口封面图
- `is_active`：是否启用
- `show_on_home`：是否在前端首页展示入口
- `home_order`：前端首页展示排序
- `start_at` / `end_at`：可选生效时间
- `created_at` / `updated_at`

新增 `catalog.SpecialZoneProduct`：

- `zone`：关联专区
- `product`：关联同店铺商品
- `is_active`：是否在该专区内展示
- `order`：专区内商品排序
- `created_at`

调整 `catalog.HomeBanner`：

- 增加可选 `special_zone` 外键，用于配置某个动态专区页的轮播图。
- 多店铺上线后必须同时归属 `store`，并校验 `HomeBanner.store == special_zone.store`。
- 旧 `position=gift|designer|best_seller|promotion` 保留兼容，不再作为新增专区的扩展方式。

### 接口能力

- `GET /api/catalog/special-zones/`
  返回当前店铺下启用、允许首页展示且处于有效期内的专区列表，按 `home_order` 排序，供首页展示。
- `POST/PATCH/DELETE /api/catalog/special-zones/`
  平台管理员可跨店管理专区基础信息；店铺管理员只能管理本店专区。
- `GET /api/catalog/special-zones/{id}/products/`
  返回专区内启用商品列表。
- `POST/DELETE /api/catalog/special-zones/{id}/products/`
  维护专区商品绑定，商品必须属于同一店铺。
- `GET /api/catalog/home-banners/?special_zone=<id>`
  返回某个专区页顶部轮播图。
- `GET /api/catalog/products/?special_zone=<id>`
  支持按专区筛选商品，便于复用现有商品列表序列化和分页逻辑。

### 兼容策略

- 旧固定专区字段暂不删除，避免破坏已有首页和专区页。
- `promotion` 作为过渡兼容，不再继续扩展。
- 新动态专区上线后，小程序和商家后台优先消费店铺级 `SpecialZone`。
- 固定专区是否迁移为内置 `SpecialZone`，放在动态专区后端计划中通过 migration 或数据脚本单独评估。

## 分阶段实施顺序

### Phase 0：平台底座与权限

先建立店铺、成员、角色和数据隔离底座。没有 `Store` 与店铺权限之前，不开始实现可运营的动态专区，否则后续会出现跨店数据补迁移和权限返工。

### Phase 1：店铺级动态运营专区

完成店铺级动态专区后端，再完成商家后台配置入口，最后接入小程序数据与页面路由。

### Phase 2：订单与支付重构

- 新增 `CheckoutOrder`、`SubOrder`。
- 购物车按店铺分组。
- 下单接口生成结算单和子单。
- 支付成功后按“店铺 + 商品 SPU”拆单。
- 子单驱动发货、售后、退款、分账记录。

### Phase 3：微信快捷登录

- 新增微信快捷登录接口。
- 小程序接入手机号授权。
- 用户资料初始化与默认昵称策略落地。
- 登录弹层和动作守卫接入全站。
- 商品分享落地页接入登录守卫与登录后回跳能力。

### Phase 4：设计系统与核心页 UI 改版

- 重做全局 token 和组件层。
- 先改首页、店铺、商品、购物车、下单、订单、我的页。
- 把动态运营专区纳入首页首批核心运营板块。
- 再统一其余页面风格。

### Phase 5：分账闭环与后台增强

- 接入微信服务商分账流程。
- 子单级分账记录、重试、异常处理。
- 平台后台全局视图。
- 店铺后台只看本店数据。

## 可执行子计划

每个子计划都是一个可以独立执行、测试、提交和归档的文件：

1. [平台店铺底座与权限计划](./2026-05-05-store-platform-foundation.md)
2. [动态运营专区后端计划](./2026-05-05-dynamic-special-zones-backend.md)
3. [动态运营专区商家后台计划](./2026-05-05-dynamic-special-zones-merchant.md)
4. [动态运营专区小程序接入计划](./2026-05-05-dynamic-special-zones-miniprogram.md)
5. [结算单与子单重构计划](./2026-05-05-checkout-suborders.md)
6. [微信快捷登录与分享回跳计划](./2026-05-05-wechat-explicit-login.md)
7. [小程序设计系统与核心页 UI 计划](./2026-05-05-miniprogram-design-system-ui.md)
8. [服务商分账闭环计划](./2026-05-05-service-provider-profit-sharing.md)

## 默认假设

- 多个活动和多个专区是长期能力，不再通过固定枚举和布尔字段扩展。
- `SpecialZone` 是店铺级运营专区的最终主模型，必须从一开始就带 `store`。
- `promotion` 是过渡兼容，不作为最终设计边界。
- 平台管理员可以跨店创建和代配置专区；店铺管理员只能管理本店专区、商品和轮播。
- 小程序继续复用 `special-zone` 页面，不为每个活动创建独立页面模板。
- 首页可展示多个专区入口，入口排序由后台 `home_order` 配置，是否展示由 `show_on_home`、`is_active` 和有效期共同决定。
- 活动专区商品由专区商品绑定表维护，不再用商品字段硬编码；专区内商品排序和显隐由 `SpecialZoneProduct.order`、`SpecialZoneProduct.is_active` 控制。
