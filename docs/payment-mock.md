# 支付与通知（模拟版）说明

当前项目的支付链路默认为 **模拟实现**（未开启 `WECHAT_PAY_ENABLE_REAL`），方便联调和演示。若已配置商户号/证书并将 `WECHAT_PAY_ENABLE_REAL=true`，后端会调用微信支付 V3 JSAPI 下单并按官方要求验签+解密回调。

## 现有行为（模拟）
- `POST /payments/{id}/start/`：返回本地生成的 JSAPI 参数（`prepay_id` 为随机值，签名使用本地密钥 HMAC），前端用 `wx.requestPayment` 拉起“假支付”。
- 支付成功：前端调用 `POST /payments/{id}/succeed/`，后端将订单状态置为 `paid`，并记录支付成功通知。
- 支付过期：`start` 会检查 `expires_at`，过期则拒绝；管理命令 `python manage.py expire_payments` 可批量标记过期并取消订单。
- 回调：允许 `provider=wechat` 和 `mock` 的简化回调。验签使用共享密钥 HMAC（非微信 V3 证书验签），仅用于开发/联调。
- 退款：当前仅有数据库记录和状态流转，未调用支付渠道退款。
- 通知：支付成功/过期会写入 `users_notification` 表，留给后续订阅消息/短信等网关消费。
- 漏回调自愈：提供 `manage.py reconcile_payments` 扫描 `init/processing` 支付单，自动过期已超时的记录；支持基于模拟字段（如 `order.metadata.auto_success`）补记成功，后续可替换为真实查单。

## 接入真实微信支付需要补充的事项
1) **统一下单获取 prepay_id**  
   - 使用微信支付 V3 JSAPI 下单接口，参数包含 `mchid/appid/out_trade_no/amount/description/notify_url`。  
   - 将返回的 `prepay_id` 与 `timeStamp/nonceStr/package/signType/paySign` 按官方算法签名后返回前端。  
   - 在 `PaymentService.generate_wechat_jsapi_params` 中替换为真实下单逻辑。

2) **回调验签与解密**  
   - 启用微信支付平台证书，使用 V3 `HttpUtil` 或官方 SDK 验签 HTTP 头 `Wechatpay-Signature`、`Wechatpay-Timestamp`、`Wechatpay-Nonce`。  
   - 解密回调 `resource`，校验 `mchid/appid/out_trade_no/total/transaction_id/trade_state`。  
   - 拒绝任何不匹配金额或商户号的回调。

3) **通知 URL**  
   - 在统一下单时配置 `notify_url` 指向 `/api/payments/callback/wechat/`（生产需要公网可访问且 HTTPS）。
   - 生产环境中应仅允许微信官方 IP/头部；可在回调视图增加白名单或额外签名校验。

4) **退款**  
   - 为 `RefundViewSet.succeed` 增加微信退款 API 调用与回调处理，校验退款金额/币种/商户号，幂等更新退款与订单状态。

5) **安全与风控**  
   - 落地订单状态检查（已加）、支付记录幂等锁（已加），还需：  
     - 校验订单是否属于当前用户。  
     - 在回调/主动查单时校验金额、币种、mchid、appid。  
     - 使用 `manage.py reconcile_payments` 作为定时任务替代当前模拟查单；接入真实查单后替换内部逻辑。

6) **配置与密钥**  
   - 环境变量（示例）：  
     - `WECHAT_APPID`：小程序 appid  
     - `WECHAT_PAY_MCHID`：商户号  
     - `WECHAT_PAY_SERIAL_NO`：商户证书序列号  
     - `WECHAT_PAY_PRIVATE_KEY`：商户私钥（文件路径或内容）  
     - `WECHAT_PAY_PLATFORM_CERT`：平台证书（路径或内容）  
     - `WECHAT_PAY_NOTIFY_URL`：支付回调地址  
   - 保持密钥仅存储于安全的密钥管理服务，不要写入仓库。

## 本地/测试环境使用方法
- 直接使用当前模拟接口，无需真实密钥。  
- 触发过期清理：`python manage.py expire_payments --dry-run` 查看将要过期的支付，去掉 `--dry-run` 实际执行。  
- 若要测试回调，可向 `/api/payments/callback/mock/` 或 `/api/payments/callback/wechat/` 发送包含 `payment_id` 与 `status=SUCCESS` 的 POST 请求（仅开发环境允许 mock）。

## 开启真实微信支付（可选）
- 环境变量需提供：`WECHAT_APPID`、`WECHAT_PAY_MCHID`、`WECHAT_PAY_SERIAL_NO`、`WECHAT_PAY_PRIVATE_KEY_PATH`、`WECHAT_PAY_API_V3_KEY`、`WECHAT_PAY_NOTIFY_URL`，并设置 `WECHAT_PAY_ENABLE_REAL=true`。验签可用 `WECHAT_PAY_PUBLIC_KEY_PATH`（微信支付公钥文件，需同时填 `WECHAT_PAY_PUBLIC_KEY_ID` 以比对 header `Wechatpay-Serial`），也可继续使用平台证书 `WECHAT_PAY_PLATFORM_CERT_PATH`。
- 后端会在统一下单附带 `attach`（包含 `payment_id`），回调时通过公钥/平台证书头 `Wechatpay-*` 验签并用 APIv3 Key 解密 `resource`，校验商户号、appid、订单号与金额后再落库。
- 处理成功会返回微信要求的 `{"code": "SUCCESS", "message": "成功"}` 响应，避免重复推送；校验失败会返回 `FAIL` 以便重试。

## 前端提示
- 拉起支付使用返回的 `pay_params`；失败或取消会跳转支付结果页支持重试。  
- 真实支付接入后，需确保 `requestPayment` 参数来自后端真实签名，且失败时不要调用成功接口。
