# 微信支付分账闭环实施计划

**Goal:** 基于现有 `CheckoutOrder` 支付主单和 `SubOrder` 履约子单，接入微信支付分账；订单包含合作方店铺时，支付下单开启 `profit_sharing=true`，允许用户先支付，平台后补合作方分账配置后再手动发起分账。

**Architecture:** 主店铺仍是 `Store` 经营主体和平台入口。微信支付由平台/主店商户号统一收款；`store_type=self_operated` 的主店子单资金留存在平台商户号，`store_type=partner` 的合作方子单生成分账流水。合作方缺少接收方配置时不阻断支付，但分账流水进入待配置状态。平台管理员补齐配置并确认资金风险后，手动调用微信分账。第一版不自动处理分账后退款回退。

**Confirmed decisions:**

- 微信模式：先按平台普通商户号收款 + 合作方商户号作为 `MERCHANT_ID` 分账接收方实现，不做服务商/子商户模式。
- 适用店铺：只对 `store_type=partner` 的合作方店铺发起微信分账；主店 `store_type=self_operated` 留存在平台商户号；`supplier` 暂不参与。
- 支付开关：订单只要包含合作方店铺商品，就在微信 JSAPI/小程序下单时传 `settle_info.profit_sharing=true`。
- 接收方缺失：允许用户支付，合作方子单分账流水进入 `pending_receiver_config`，待平台管理员补齐配置后手动分账。
- 分账方式：第一版只支持平台管理员手动分账，不自动发起真实资金动作。
- 分账入口：以 `CheckoutOrder` 为入口，可分当前已满足条件的合作方流水；最后提供完结并解冻剩余资金动作。
- 冻结期：按子单确认收货时间 + `StoreSettlementRule.settlement_cycle_days` 计算，默认 7 天。
- 抽佣：复用 `StoreSettlementRule.commission_rate`，默认 0。
- 运费与优惠：第一版不新增独立分摊规则，分账金额以子单当前 `actual_amount` 为基础。
- 已分账后退款：第一版只做人工审核和内部负向调整；微信分账回退后续单独接入。
- 未配置处理期限：支付后 25 天预警，30 天前要求处理；超期转人工结算处理。
- 尾差：金额按分提交微信，尾差留存在平台商户号。
- 证书兼容：分账复用现有微信支付 API v3 证书和密钥配置，不新增独立证书路径；Docker 继续使用 `/etc/electric-miniprogram/certs/wechatpay` 只读挂载。

---

## 影响范围

- 修改：`backend/stores/models.py`
- 修改：`backend/stores/serializers.py`
- 修改：`backend/stores/views.py`
- 修改：`backend/orders/models.py`
- 修改：`backend/orders/payment_service.py`
- 新增：`backend/orders/profit_sharing.py`
- 新增：`backend/orders/management/commands/sync_profit_sharing.py`
- 新增：`backend/orders/tests/test_profit_sharing.py`
- 修改：`backend/backend/settings/base.py`
- 修改：`docs/backend.md`、`docs/backend/backend.md`
- 修改：`docs/api/api.md`
- 修改：`docs/merchant.md`、`docs/merchant/merchant.md`
- 如新增商户端页面，再同步修改 `merchant/src/` 对应菜单、权限和 API 封装。

## 字段复用与新增

复用现有字段：

- `StorePaymentConfig.wechat_mch_id`：合作方分账接收商户号。
- `StorePaymentConfig.wechat_sub_mch_id`：保留给后续服务商/子商户模式，第一版不作为主流程依赖。
- `StorePaymentConfig.is_active`：该店铺微信支付/分账配置是否启用。
- `StoreSettlementRule.commission_rate`：平台抽佣比例，默认 0。
- `StoreSettlementRule.settlement_cycle_days`：售后冻结/可结算周期，默认 7。

复用现有微信支付配置：

- `WECHAT_PAY_MCHID`：平台/主店收款商户号，也是微信 API v3 请求签名商户号。
- `WECHAT_PAY_SERIAL_NO`：平台/主店商户 API 证书序列号。
- `WECHAT_PAY_PRIVATE_KEY_PATH`：平台/主店商户 API 私钥路径，继续由 `PaymentService._load_private_key()` 读取。
- `WECHAT_PAY_API_V3_KEY`：支付、退款、回调解密和分账相关 API 复用的 API v3 密钥。
- `WECHAT_PAY_PUBLIC_KEY_PATH` / `WECHAT_PAY_PLATFORM_CERT_PATH`：继续用于微信回调验签。
- `WECHAT_PAY_NOTIFY_URL`：支付回调地址；如后续启用分账结果回调，再新增单独回调地址。

Docker 兼容要求：

- 生产和预发继续使用现有挂载 `/etc/electric-miniprogram/certs/wechatpay:/etc/electric-miniprogram/certs/wechatpay:ro`。
- 不新增 `WECHAT_PROFIT_SHARING_PRIVATE_KEY_PATH`、`WECHAT_PROFIT_SHARING_CERT_DIR` 等重复配置。
- 合作方店铺的 `StorePaymentConfig.wechat_mch_id` 只作为分账接收方商户号，不参与请求签名，也不要求读取合作方证书。
- 开发 Docker 不强制挂载真实微信证书；分账测试使用 mock，不依赖真实证书文件。

新增字段和表：

- `StorePaymentConfig.profit_sharing_enabled`：是否启用微信分账。
- `StorePaymentConfig.profit_sharing_receiver_type`：第一版固定 `MERCHANT_ID`。
- `StorePaymentConfig.profit_sharing_receiver_name`：合作方接收方名称。
- `StorePaymentConfig.profit_sharing_receiver_added`：是否已在微信侧添加接收方。
- `StorePaymentConfig.profit_sharing_receiver_verified`：是否已校验可用于分账。
- `Payment.profit_sharing_required`：该支付是否以微信分账订单创建。
- `Payment.profit_sharing_status`：支付主单分账总体状态。
- `Payment.profit_sharing_unfrozen`：剩余未分资金是否已解冻。
- 新增 `StoreProfitSharingEntry`：店铺/子单粒度的内部分账流水。
- 新增 `WechatProfitSharingOrder`：每次调用微信分账接口的请求和结果记录。

## 状态流转

支付下单：

- 订单不含合作方店铺：普通微信支付，不传 `profit_sharing=true`。
- 订单包含合作方店铺：微信下单传 `settle_info.profit_sharing=true`，并将 `Payment.profit_sharing_required=true`。

支付成功：

- 主店子单：生成或标记留存流水，状态 `platform_retained`。
- 合作方子单且接收方已配置：生成分账流水，状态 `frozen`。
- 合作方子单但接收方未配置：生成分账流水，状态 `pending_receiver_config`。

接收方补配置：

- 未过冻结期：`pending_receiver_config -> frozen`。
- 已过冻结期：`pending_receiver_config -> available_for_manual_share`。

手动分账：

- 发起前校验支付成功、微信交易号存在、支付以分账订单创建、流水可分账、接收方已配置并验证、支付主单未最终解冻。
- 微信请求处理中：`processing`。
- 查询成功：`shared`。
- 失败：`failed`，可重试或转人工结算。

完结解冻：

- 当该 `CheckoutOrder` 下无需再微信分账的合作方流水均已 `shared`、`cancelled` 或 `manual_settled`，平台管理员可执行完结并 `unfreeze_unsplit=true`。
- 若仍有未分账流水，允许二次确认后转人工结算，再解冻剩余资金。

## 执行步骤

- [ ] 写失败测试：订单只含主店商品时不启用 `profit_sharing=true`。
- [ ] 写失败测试：订单包含合作方商品时启用 `profit_sharing=true`，即使合作方还未配置接收方。
- [ ] 写失败测试：支付成功后按 `SubOrder` 生成主店留存流水、合作方冻结流水和待配置流水。
- [ ] 写失败测试：补齐合作方接收方配置后，待配置流水按冻结期进入 `frozen` 或 `available_for_manual_share`。
- [ ] 写失败测试：平台管理员手动发起分账时，只处理可分账流水，并记录微信请求和响应。
- [ ] 写失败测试：分账失败进入 `failed`，重试不会重复处理已成功流水。
- [ ] 扩展 `StorePaymentConfig` 分账接收方状态字段，并更新序列化、权限和管理入口。
- [ ] 扩展 `Payment` 分账订单级状态字段。
- [ ] 新增 `StoreProfitSharingEntry` 和 `WechatProfitSharingOrder` 模型、迁移、admin。
- [ ] 封装微信分账请求、查询和完结解冻逻辑，测试中 mock 外部请求。
- [ ] 在微信下单参数中按合作方店铺存在与否注入 `settle_info.profit_sharing=true`。
- [ ] 在支付成功流程中生成内部分账流水，不自动调用微信真实分账。
- [ ] 新增平台管理员手动分账和完结解冻入口。
- [ ] 新增同步/重试管理命令，用于查询微信分账结果和重试失败记录。
- [ ] 增加 25 天预警和 30 天超期转人工结算的筛选或任务。
- [ ] 更新长期文档和 API 文档，清理旧“服务商分账”口径。

## 验证命令

- [ ] `docker compose -f docker/docker-compose.dev.yaml exec backend .venv/bin/python manage.py test orders.tests.test_profit_sharing`
- [ ] `docker compose -f docker/docker-compose.dev.yaml exec backend .venv/bin/python manage.py test stores.tests.test_store_permissions`
- [ ] `docker compose -f docker/docker-compose.dev.yaml exec backend .venv/bin/python manage.py check`
- [ ] 使用 mock 配置手动执行 `docker compose -f docker/docker-compose.dev.yaml exec backend .venv/bin/python manage.py sync_profit_sharing`。

## 完成标准

- 包含合作方的微信支付订单在下单时稳定开启 `profit_sharing=true`。
- 合作方缺少分账接收方时仍可支付，并进入明确的待配置/待手动分账状态。
- 主店资金留存、合作方待分账、失败重试、人工结算和最终解冻都有可审计记录。
- 平台管理员可以补配置、手动分账、重试失败分账和完结解冻。
- 分账后退款第一版进入人工审核和内部负向调整，不误触发自动分账回退。
- 必要测试通过，长期文档同步完成后，本计划可删除或按需归档。
